import pytest

from app.models.medical_record import MedicalRecord
from app.tools.medical_record_tools import (
    add_unstructured_history_note,
    update_unstructured_history_note,
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
            history_notes=[
                "Patient reports improved medication adherence."
            ],
        )
    ]


def test_medical_record_defaults_to_empty_history_notes() -> None:
    record = MedicalRecord(record_id="R002", patient_id="P002")

    assert record.history_notes == []


def test_add_unstructured_note_preserves_free_text(
    records: list[MedicalRecord],
) -> None:
    note = "Patient called after discharge.\nFollow-up requested next week."

    result = add_unstructured_history_note(
        records,
        patient_id="P001",
        note=f"  {note}  ",
    )

    assert result["success"] is True
    assert result["status"] == "ADDED"
    assert records[0].history_notes[-1] == note


def test_add_unstructured_note_rejects_duplicate(
    records: list[MedicalRecord],
) -> None:
    result = add_unstructured_history_note(
        records,
        patient_id="P001",
        note=" patient reports improved   medication adherence. ",
    )

    assert result["success"] is False
    assert result["status"] == "DUPLICATE"
    assert len(records[0].history_notes) == 1


def test_update_unstructured_note_preserves_list_position(
    records: list[MedicalRecord],
) -> None:
    records[0].history_notes.append("Second note")

    result = update_unstructured_history_note(
        records,
        patient_id="P001",
        current_note="Patient reports improved medication adherence.",
        new_note="Patient reports full medication adherence.",
    )

    assert result["success"] is True
    assert result["status"] == "UPDATED"
    assert records[0].history_notes == [
        "Patient reports full medication adherence.",
        "Second note",
    ]


def test_update_unstructured_note_rejects_duplicate_replacement(
    records: list[MedicalRecord],
) -> None:
    records[0].history_notes.append("Second note")

    result = update_unstructured_history_note(
        records,
        patient_id="P001",
        current_note="Patient reports improved medication adherence.",
        new_note=" second   note ",
    )

    assert result["success"] is False
    assert result["status"] == "DUPLICATE"


def test_update_unstructured_note_rejects_missing_entry(
    records: list[MedicalRecord],
) -> None:
    result = update_unstructured_history_note(
        records,
        patient_id="P001",
        current_note="Unknown note",
        new_note="Replacement note",
    )

    assert result["success"] is False
    assert result["status"] == "ENTRY_NOT_FOUND"


@pytest.mark.parametrize("operation", ["add", "update"])
def test_unstructured_note_mutation_rejects_unknown_patient(
    records: list[MedicalRecord],
    operation: str,
) -> None:
    if operation == "add":
        result = add_unstructured_history_note(
            records,
            patient_id="P999",
            note="New note",
        )
    else:
        result = update_unstructured_history_note(
            records,
            patient_id="P999",
            current_note="Old note",
            new_note="New note",
        )

    assert result["success"] is False
    assert result["status"] == "PATIENT_NOT_FOUND"


@pytest.mark.parametrize("note", ["", "   ", "\n\t"])
def test_add_unstructured_note_rejects_empty_value(
    records: list[MedicalRecord],
    note: str,
) -> None:
    result = add_unstructured_history_note(
        records,
        patient_id="P001",
        note=note,
    )

    assert result["success"] is False
    assert result["status"] == "INVALID_VALUE"


def test_update_unstructured_note_rejects_empty_replacement(
    records: list[MedicalRecord],
) -> None:
    result = update_unstructured_history_note(
        records,
        patient_id="P001",
        current_note="Patient reports improved medication adherence.",
        new_note="   ",
    )

    assert result["success"] is False
    assert result["status"] == "INVALID_VALUE"
