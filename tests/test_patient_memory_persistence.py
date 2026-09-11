import json
from pathlib import Path

import pytest

from app.memory.patient_memory import (
    PATIENT_MEMORY_STORE_SCHEMA_VERSION,
    PatientMemoryStore,
    load_patient_memories,
)


def remember_appointment(store: PatientMemoryStore):
    return store.remember(
        patient_id="P001",
        user_request="Book nephrology.",
        assistant_response="Appointment A001 is scheduled.",
        specialty="Nephrology",
        appointment_id="A001",
    )


def test_missing_persistent_store_is_initialized_on_first_write(tmp_path: Path):
    store_path = tmp_path / "patient_memory.json"

    store = PatientMemoryStore(store_path=store_path)

    assert store_path.exists() is False
    assert store.recall("P001") is None

    remember_appointment(store)

    assert store_path.exists()


def test_store_uses_versioned_json_contract(tmp_path: Path):
    store_path = tmp_path / "patient_memory.json"
    store = PatientMemoryStore(store_path=store_path)

    remember_appointment(store)
    payload = json.loads(store_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == PATIENT_MEMORY_STORE_SCHEMA_VERSION
    assert payload["patient_memories"][0]["patient_id"] == "P001"


def test_validated_memory_survives_new_store_instance(tmp_path: Path):
    store_path = tmp_path / "patient_memory.json"
    first_process = PatientMemoryStore(store_path=store_path)
    remember_appointment(first_process)

    restarted_process = PatientMemoryStore(store_path=store_path)
    recalled = restarted_process.recall("P001")

    assert recalled is not None
    assert recalled.last_specialty == "Nephrology"
    assert recalled.last_appointment_id == "A001"
    assert recalled.turns[0].assistant_response.endswith("scheduled.")


def test_bounded_turn_retention_survives_restart(tmp_path: Path):
    store_path = tmp_path / "patient_memory.json"
    store = PatientMemoryStore(max_turns=2, store_path=store_path)

    for number in range(3):
        store.remember("P001", f"request {number}", f"response {number}")

    restarted = PatientMemoryStore(max_turns=2, store_path=store_path)
    recalled = restarted.recall("P001")

    assert recalled is not None
    assert [turn.user_request for turn in recalled.turns] == [
        "request 1",
        "request 2",
    ]


def test_clear_is_persisted_across_restart(tmp_path: Path):
    store_path = tmp_path / "patient_memory.json"
    store = PatientMemoryStore(store_path=store_path)
    remember_appointment(store)

    assert store.clear("P001") is True
    assert PatientMemoryStore(store_path=store_path).recall("P001") is None


def test_failed_write_rolls_back_in_memory_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    store = PatientMemoryStore(store_path=tmp_path / "patient_memory.json")

    def fail_save(*args, **kwargs):
        raise OSError("simulated write failure")

    monkeypatch.setattr(
        "app.memory.patient_memory.save_patient_memories",
        fail_save,
    )

    with pytest.raises(OSError, match="simulated write failure"):
        remember_appointment(store)

    assert store.recall("P001") is None


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"schema_version": 999, "patient_memories": []},
        {"schema_version": 1},
        {
            "schema_version": 1,
            "patient_memories": [
                {"patient_id": "P001"},
                {"patient_id": "P001"},
            ],
        },
    ],
)
def test_invalid_store_contract_is_rejected(tmp_path: Path, payload: object):
    store_path = tmp_path / "patient_memory.json"
    store_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        load_patient_memories(store_path)
