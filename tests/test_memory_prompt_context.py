from types import SimpleNamespace

import pytest

from app.agents import assistant_pipeline, memory_follow_up
from app.memory.patient_memory import MemoryTurn, PatientMemory, PatientMemoryStore


@pytest.fixture(autouse=True)
def disable_runtime_memory_event_log(monkeypatch):
    monkeypatch.setattr(
        assistant_pipeline,
        "log_memory_access_events",
        lambda events: None,
    )


def _memory(patient_id: str = "P001") -> PatientMemory:
    return PatientMemory(
        patient_id=patient_id,
        last_specialty="Nephrology",
        last_appointment_id="A001",
        turns=[
            MemoryTurn(
                user_request="Book the first Nephrology appointment.",
                assistant_response=(
                    "Sarah Chen scheduled appointment A001 for "
                    "2026-09-02 09:00."
                ),
            )
        ],
    )


def test_prompt_context_exposes_provenance_and_isolation_controls():
    memory = _memory()
    context = memory_follow_up.build_validated_memory_prompt_context(
        requested_patient_id="P001",
        memory=memory,
        relevant_turn=memory.turns[0],
    )

    assert context.source_type == "evaluation_approved_patient_memory"
    assert context.validation_status == "deterministic_and_semantic_pass"
    assert context.requested_patient_id == "P001"
    assert context.memory_patient_id == "P001"
    assert context.last_appointment_id == "A001"
    assert "single_patient_context_only" in context.isolation_controls


def test_prompt_context_rejects_cross_patient_memory():
    memory = _memory(patient_id="P002")

    with pytest.raises(ValueError, match="does not match"):
        memory_follow_up.build_validated_memory_prompt_context(
            requested_patient_id="P001",
            memory=memory,
            relevant_turn=memory.turns[0],
        )


def test_prompt_context_rejects_turn_outside_recalled_memory():
    memory = _memory()

    with pytest.raises(ValueError, match="not present"):
        memory_follow_up.build_validated_memory_prompt_context(
            requested_patient_id="P001",
            memory=memory,
            relevant_turn=MemoryTurn(
                user_request="Different request",
                assistant_response="Different response",
            ),
        )


def test_prompt_context_rejects_cross_patient_id_inside_turn():
    memory = PatientMemory(
        patient_id="P001",
        turns=[
            MemoryTurn(
                user_request="For P001, book the appointment.",
                assistant_response="P002 has appointment A002.",
            )
        ],
    )

    with pytest.raises(ValueError, match="different patient ID"):
        memory_follow_up.build_validated_memory_prompt_context(
            requested_patient_id="P001",
            memory=memory,
            relevant_turn=memory.turns[0],
        )


def test_llm_prompt_contains_only_scoped_validated_context(monkeypatch):
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            output_text="The appointment is at 2026-09-02 09:00."
        )

    monkeypatch.setattr(
        memory_follow_up.client.responses,
        "create",
        fake_create,
    )

    memory = _memory()
    response = memory_follow_up.synthesize_follow_up_from_validated_memory(
        patient_id="P001",
        user_request="What time is his appointment?",
        memory=memory,
        relevant_turn=memory.turns[0],
    )

    prompt = captured["input"][1]["content"]
    assert response == "The appointment is at 2026-09-02 09:00."
    assert "VALIDATED PATIENT MEMORY CONTEXT WITH PROVENANCE" in prompt
    assert '"requested_patient_id": "P001"' in prompt
    assert '"memory_patient_id": "P001"' in prompt
    assert '"source_type": "evaluation_approved_patient_memory"' in prompt
    assert "P002" not in prompt


def test_follow_up_rejects_explicit_different_patient_before_llm(monkeypatch):
    store = PatientMemoryStore()
    store.remember(
        patient_id="P001",
        user_request="Book the appointment.",
        assistant_response="Appointment A001 is scheduled for 2026-09-02 09:00.",
        specialty="Nephrology",
        appointment_id="A001",
    )

    def fail_if_called(**kwargs):
        raise AssertionError("LLM must not receive cross-patient context")

    monkeypatch.setattr(
        memory_follow_up.client.responses,
        "create",
        fail_if_called,
    )
    monkeypatch.setattr(assistant_pipeline, "patient_memory_store", store)

    assert assistant_pipeline.answer_follow_up_from_memory(
        patient_id="P001",
        user_request="For P002, what time is the appointment?",
    ) is None


def test_supported_follow_up_consumes_memory_prompt(monkeypatch):
    store = PatientMemoryStore()
    store.remember(
        patient_id="P001",
        user_request="Book the appointment.",
        assistant_response="Appointment A001 is scheduled for 2026-09-02 09:00.",
        specialty="Nephrology",
        appointment_id="A001",
    )

    monkeypatch.setattr(
        "app.agents.assistant_pipeline.synthesize_follow_up_from_validated_memory",
        lambda **kwargs: "The appointment is at 2026-09-02 09:00.",
    )
    monkeypatch.setattr(assistant_pipeline, "patient_memory_store", store)

    response = assistant_pipeline.answer_follow_up_from_memory(
        patient_id="P001",
        user_request="What time is his appointment?",
    )

    assert response == "The appointment is at 2026-09-02 09:00."


def test_unsupported_follow_up_does_not_call_memory_llm(monkeypatch):
    store = PatientMemoryStore()
    store.remember(
        patient_id="P001",
        user_request="Book the appointment.",
        assistant_response="Appointment A001 is scheduled for 2026-09-02 09:00.",
        specialty="Nephrology",
        appointment_id="A001",
    )

    monkeypatch.setattr(
        "app.agents.assistant_pipeline.synthesize_follow_up_from_validated_memory",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("Unsupported follow-up must not invoke the memory LLM")
        ),
    )
    monkeypatch.setattr(assistant_pipeline, "patient_memory_store", store)

    assert assistant_pipeline.answer_follow_up_from_memory(
        patient_id="P001",
        user_request="Should he stop taking Lisinopril?",
    ) is None
