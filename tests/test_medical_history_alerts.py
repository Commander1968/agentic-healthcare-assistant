from types import SimpleNamespace

from app.agents import response_synthesizer
from app.evaluation.pipeline_evaluator import (
    evaluate_structured_fact_consistency,
)
from app.evaluation.semantic_faithfulness_evaluator import (
    SEMANTIC_EVALUATOR_SYSTEM_PROMPT,
    build_semantic_evaluation_evidence,
)
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.workflow_state import WorkflowState
from app.persistence.medical_record_store import (
    load_medical_records,
    save_medical_records,
)
from app.retrieval.patient_summary_index import build_patient_summary
from app.tools.medical_record_tools import (
    add_structured_history_entry,
    update_structured_history_entry,
)


ALERT = "Demo alert: Medication allergy information requires verification."


def build_record(*, alerts=None) -> MedicalRecord:
    return MedicalRecord(
        record_id="R001",
        patient_id="P001",
        diagnoses=["Chronic Kidney Disease"],
        medications=["Lisinopril 10 mg daily"],
        treatment_notes=["Monitor kidney function and blood pressure"],
        alerts=[] if alerts is None else alerts,
    )


def test_medical_record_alerts_default_to_empty_list():
    record = MedicalRecord(record_id="R001", patient_id="P001")

    assert record.alerts == []


def test_alert_add_and_update_use_structured_history_contract():
    records = [build_record()]

    added = add_structured_history_entry(
        records,
        patient_id="P001",
        field="alerts",
        value=ALERT,
    )
    updated = update_structured_history_entry(
        records,
        patient_id="P001",
        field="alerts",
        current_value=ALERT,
        new_value="Demo alert: Allergy status verified by attendant.",
    )

    assert added["status"] == "ADDED"
    assert updated["status"] == "UPDATED"
    assert records[0].alerts == [
        "Demo alert: Allergy status verified by attendant."
    ]


def test_alert_mutation_rejects_duplicate_and_empty_values():
    records = [build_record(alerts=[ALERT])]

    duplicate = add_structured_history_entry(
        records,
        patient_id="P001",
        field="alerts",
        value=ALERT.lower(),
    )
    empty = add_structured_history_entry(
        records,
        patient_id="P001",
        field="alerts",
        value="   ",
    )

    assert duplicate["status"] == "DUPLICATE"
    assert empty["status"] == "INVALID_VALUE"
    assert records[0].alerts == [ALERT]


def test_alert_survives_medical_record_store_reload(tmp_path):
    store_path = tmp_path / "medical_records.json"
    save_medical_records([build_record(alerts=[ALERT])], store_path)

    reloaded = load_medical_records(store_path)

    assert reloaded[0].alerts == [ALERT]


def test_patient_summary_includes_relevant_alerts():
    summary = build_patient_summary(
        Patient(
            patient_id="P001",
            first_name="Robert",
            last_name="Smith",
            age=70,
            primary_condition="Chronic Kidney Disease",
        ),
        build_record(alerts=[ALERT]),
    )

    assert f"Relevant alerts: {ALERT}" in summary.summary


def test_deterministic_evaluator_requires_recorded_alert():
    state = WorkflowState(
        patient_id="P001",
        medical_record=build_record(alerts=[ALERT]),
    )

    missing = evaluate_structured_fact_consistency(
        "Chronic Kidney Disease. Lisinopril 10 mg daily.",
        state,
    )
    present = evaluate_structured_fact_consistency(
        "Chronic Kidney Disease. Lisinopril 10 mg daily. "
        f"Monitor kidney function and blood pressure. {ALERT}",
        state,
    )

    assert f"alerts: {ALERT}" in missing["missing_required_facts"]
    assert (
        "treatment_notes: Monitor kidney function and blood pressure"
        in missing["missing_required_facts"]
    )
    assert present["structured_facts_consistent"] is True


def test_semantic_evidence_classifies_alert_as_authoritative():
    state = WorkflowState(
        patient_id="P001",
        medical_record=build_record(alerts=[ALERT]),
    )

    evidence = build_semantic_evaluation_evidence(
        user_request="Summarize the medical history.",
        response_text=ALERT,
        state=state,
    )

    assert evidence["authoritative_workflow_state"]["medical_record"][
        "alerts"
    ] == [ALERT]
    assert "relevant patient alerts" in SEMANTIC_EVALUATOR_SYSTEM_PROMPT


def test_synthesis_prompt_requires_explicit_relevant_alerts(monkeypatch):
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text=f"Relevant Alerts: {ALERT}")

    monkeypatch.setattr(
        response_synthesizer,
        "client",
        SimpleNamespace(responses=FakeResponses()),
    )
    state = WorkflowState(
        patient_id="P001",
        medical_record=build_record(alerts=[ALERT]),
    )

    result = response_synthesizer.synthesize_response(state)
    prompt_text = "\n".join(
        message["content"] for message in captured["input"]
    )

    assert result == f"Relevant Alerts: {ALERT}"
    assert "Include a distinct 'Relevant Alerts' statement" in prompt_text
    assert ALERT in prompt_text
