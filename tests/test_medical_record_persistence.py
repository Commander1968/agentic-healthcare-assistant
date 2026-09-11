import json
from pathlib import Path

import pytest

from app.models.medical_record import MedicalRecord
from app.persistence.medical_record_store import (
    MEDICAL_RECORD_STORE_SCHEMA_VERSION,
    load_medical_records,
    load_or_initialize_medical_records,
    save_medical_records,
)
from app.ui.history_management import (
    execute_persisted_history_management_action,
)


@pytest.fixture
def records() -> list[MedicalRecord]:
    return [
        MedicalRecord(
            record_id="R001",
            patient_id="P001",
            diagnoses=["Chronic Kidney Disease"],
            medications=["Lisinopril 10 mg daily"],
            treatment_notes=["Monitor blood pressure"],
            history_notes=["Patient called after discharge."],
        )
    ]


def test_missing_store_is_initialized_from_defaults(
    tmp_path: Path,
    records: list[MedicalRecord],
) -> None:
    store_path = tmp_path / "medical_records.json"

    loaded = load_or_initialize_medical_records(records, store_path)

    assert store_path.exists()
    assert loaded == records
    assert loaded is not records
    assert loaded[0] is not records[0]


def test_store_uses_versioned_json_contract(
    tmp_path: Path,
    records: list[MedicalRecord],
) -> None:
    store_path = save_medical_records(
        records,
        tmp_path / "medical_records.json",
    )
    payload = json.loads(store_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        MEDICAL_RECORD_STORE_SCHEMA_VERSION
    )
    assert payload["medical_records"][0]["patient_id"] == "P001"


def test_structured_change_survives_reload(
    tmp_path: Path,
    records: list[MedicalRecord],
) -> None:
    store_path = tmp_path / "medical_records.json"

    result = execute_persisted_history_management_action(
        records,
        patient_id="P001",
        history_type="structured",
        action="add",
        field="diagnoses",
        new_value="Hypertension",
        store_path=store_path,
    )
    reloaded = load_medical_records(store_path)

    assert result["success"] is True
    assert result["status"] == "ADDED"
    assert reloaded[0].diagnoses == [
        "Chronic Kidney Disease",
        "Hypertension",
    ]


def test_unstructured_change_survives_reload(
    tmp_path: Path,
    records: list[MedicalRecord],
) -> None:
    store_path = tmp_path / "medical_records.json"

    result = execute_persisted_history_management_action(
        records,
        patient_id="P001",
        history_type="unstructured",
        action="update",
        current_value="Patient called after discharge.",
        new_value="Patient called two days after discharge.",
        store_path=store_path,
    )
    reloaded = load_medical_records(store_path)

    assert result["success"] is True
    assert reloaded[0].history_notes == [
        "Patient called two days after discharge."
    ]


def test_rejected_change_does_not_rewrite_store(
    tmp_path: Path,
    records: list[MedicalRecord],
) -> None:
    store_path = save_medical_records(
        records,
        tmp_path / "medical_records.json",
    )
    original_bytes = store_path.read_bytes()

    result = execute_persisted_history_management_action(
        records,
        patient_id="P001",
        history_type="structured",
        action="add",
        field="diagnoses",
        new_value="Chronic Kidney Disease",
        store_path=store_path,
    )

    assert result["status"] == "DUPLICATE"
    assert store_path.read_bytes() == original_bytes


def test_persistence_failure_rolls_back_memory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    records: list[MedicalRecord],
) -> None:
    def fail_save(*args, **kwargs):
        raise OSError("simulated write failure")

    monkeypatch.setattr(
        "app.ui.history_management.save_medical_records",
        fail_save,
    )

    result = execute_persisted_history_management_action(
        records,
        patient_id="P001",
        history_type="structured",
        action="add",
        field="diagnoses",
        new_value="Hypertension",
        store_path=tmp_path / "medical_records.json",
    )

    assert result["success"] is False
    assert result["status"] == "PERSISTENCE_ERROR"
    assert records[0].diagnoses == ["Chronic Kidney Disease"]


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"schema_version": 999, "medical_records": []},
        {"schema_version": 1},
    ],
)
def test_invalid_store_contract_is_rejected(
    tmp_path: Path,
    payload: object,
) -> None:
    store_path = tmp_path / "medical_records.json"
    store_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        load_medical_records(store_path)
