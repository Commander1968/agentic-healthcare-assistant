import pytest

from app.models.medical_record import MedicalRecord
from app.tools.medical_record_tools import (
    add_structured_history_entry,
    update_structured_history_entry,
)


@pytest.fixture
def records() -> list[MedicalRecord]:
    return [
        MedicalRecord(
            record_id="R001",
            patient_id="P001",
            diagnoses=["Chronic Kidney Disease"],
            medications=["Lisinopril 10 mg daily"],
            treatment_notes=[
                "Monitor kidney function and blood pressure"
            ],
        )
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("diagnoses", "Hypertension"),
        ("medications", "Vitamin D 1000 IU daily"),
        ("treatment_notes", "Repeat renal panel in 30 days"),
    ],
)
def test_add_structured_history_updates_authoritative_record(
    records: list[MedicalRecord],
    field: str,
    value: str,
) -> None:
    result = add_structured_history_entry(
        records,
        patient_id="P001",
        field=field,
        value=value,
    )

    assert result["success"] is True
    assert result["status"] == "ADDED"
    assert value in getattr(records[0], field)


def test_add_structured_history_rejects_duplicate(
    records: list[MedicalRecord],
) -> None:
    result = add_structured_history_entry(
        records,
        patient_id="P001",
        field="diagnoses",
        value="  chronic   kidney disease  ",
    )

    assert result["success"] is False
    assert result["status"] == "DUPLICATE"
    assert records[0].diagnoses == ["Chronic Kidney Disease"]


def test_update_structured_history_preserves_list_position(
    records: list[MedicalRecord],
) -> None:
    records[0].medications.append("Vitamin D 1000 IU daily")

    result = update_structured_history_entry(
        records,
        patient_id="P001",
        field="medications",
        current_value="Lisinopril 10 mg daily",
        new_value="Lisinopril 20 mg daily",
    )

    assert result["success"] is True
    assert result["status"] == "UPDATED"
    assert records[0].medications == [
        "Lisinopril 20 mg daily",
        "Vitamin D 1000 IU daily",
    ]


def test_update_structured_history_rejects_missing_entry(
    records: list[MedicalRecord],
) -> None:
    result = update_structured_history_entry(
        records,
        patient_id="P001",
        field="treatment_notes",
        current_value="Unknown note",
        new_value="Replacement note",
    )

    assert result["success"] is False
    assert result["status"] == "ENTRY_NOT_FOUND"
    assert records[0].treatment_notes == [
        "Monitor kidney function and blood pressure"
    ]


def test_update_structured_history_rejects_duplicate_replacement(
    records: list[MedicalRecord],
) -> None:
    records[0].diagnoses.append("Hypertension")

    result = update_structured_history_entry(
        records,
        patient_id="P001",
        field="diagnoses",
        current_value="Chronic Kidney Disease",
        new_value=" hypertension ",
    )

    assert result["success"] is False
    assert result["status"] == "DUPLICATE"
    assert records[0].diagnoses == [
        "Chronic Kidney Disease",
        "Hypertension",
    ]


@pytest.mark.parametrize(
    ("operation", "expected_status"),
    [
        ("add", "PATIENT_NOT_FOUND"),
        ("update", "PATIENT_NOT_FOUND"),
    ],
)
def test_mutation_rejects_unknown_patient(
    records: list[MedicalRecord],
    operation: str,
    expected_status: str,
) -> None:
    if operation == "add":
        result = add_structured_history_entry(
            records,
            patient_id="P999",
            field="diagnoses",
            value="Hypertension",
        )
    else:
        result = update_structured_history_entry(
            records,
            patient_id="P999",
            field="diagnoses",
            current_value="Chronic Kidney Disease",
            new_value="Hypertension",
        )

    assert result["success"] is False
    assert result["status"] == expected_status


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_add_structured_history_rejects_empty_value(
    records: list[MedicalRecord],
    value: str,
) -> None:
    result = add_structured_history_entry(
        records,
        patient_id="P001",
        field="treatment_notes",
        value=value,
    )

    assert result["success"] is False
    assert result["status"] == "INVALID_VALUE"


def test_mutation_rejects_unsupported_field(
    records: list[MedicalRecord],
) -> None:
    result = add_structured_history_entry(
        records,
        patient_id="P001",
        field="allergies",
        value="Penicillin",
    )

    assert result["success"] is False
    assert result["status"] == "INVALID_FIELD"
