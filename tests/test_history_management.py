import pytest

from app.models.medical_record import MedicalRecord
from app.ui.history_management import (
    execute_history_management_action,
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


def test_dispatcher_adds_structured_history(
    records: list[MedicalRecord],
) -> None:
    result = execute_history_management_action(
        records,
        patient_id="P001",
        history_type="structured",
        action="add",
        field="diagnoses",
        new_value="Hypertension",
    )

    assert result["status"] == "ADDED"
    assert records[0].diagnoses[-1] == "Hypertension"


def test_dispatcher_updates_structured_history(
    records: list[MedicalRecord],
) -> None:
    result = execute_history_management_action(
        records,
        patient_id="P001",
        history_type="structured",
        action="update",
        field="medications",
        current_value="Lisinopril 10 mg daily",
        new_value="Lisinopril 20 mg daily",
    )

    assert result["status"] == "UPDATED"
    assert records[0].medications == ["Lisinopril 20 mg daily"]


def test_dispatcher_adds_unstructured_note(
    records: list[MedicalRecord],
) -> None:
    result = execute_history_management_action(
        records,
        patient_id="P001",
        history_type="unstructured",
        action="add",
        new_value="Family requested a follow-up call.",
    )

    assert result["status"] == "ADDED"
    assert records[0].history_notes[-1] == (
        "Family requested a follow-up call."
    )


def test_dispatcher_updates_unstructured_note(
    records: list[MedicalRecord],
) -> None:
    result = execute_history_management_action(
        records,
        patient_id="P001",
        history_type="unstructured",
        action="update",
        current_value="Patient called after discharge.",
        new_value="Patient called two days after discharge.",
    )

    assert result["status"] == "UPDATED"
    assert records[0].history_notes == [
        "Patient called two days after discharge."
    ]


@pytest.mark.parametrize(
    ("history_type", "action", "field"),
    [
        ("unsupported", "add", ""),
        ("structured", "delete", "diagnoses"),
        ("structured", "add", ""),
    ],
)
def test_dispatcher_rejects_invalid_ui_request(
    records: list[MedicalRecord],
    history_type: str,
    action: str,
    field: str,
) -> None:
    result = execute_history_management_action(
        records,
        patient_id="P001",
        history_type=history_type,
        action=action,
        field=field,
        new_value="New value",
    )

    assert result["success"] is False
    assert result["status"] == "INVALID_REQUEST"


def test_dispatcher_surfaces_tool_failure(
    records: list[MedicalRecord],
) -> None:
    result = execute_history_management_action(
        records,
        patient_id="P999",
        history_type="unstructured",
        action="add",
        new_value="New note",
    )

    assert result["success"] is False
    assert result["status"] == "PATIENT_NOT_FOUND"
