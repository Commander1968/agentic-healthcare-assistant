from typing import List, Literal, Optional, TypedDict

from app.models.medical_record import MedicalRecord


StructuredHistoryField = Literal[
    "diagnoses",
    "medications",
    "treatment_notes",
    "alerts",
]

STRUCTURED_HISTORY_FIELDS = (
    "diagnoses",
    "medications",
    "treatment_notes",
    "alerts",
)


class StructuredHistoryMutationResult(TypedDict):
    success: bool
    status: str
    patient_id: str
    field: str
    action: Literal["add", "update"]
    message: str


UnstructuredHistoryMutationResult = StructuredHistoryMutationResult


def get_medical_record_by_patient(
    records: List[MedicalRecord],
    patient_id: str
) -> Optional[MedicalRecord]:
    for record in records:
        if record.patient_id == patient_id:
            return record

    return None


def _normalize_history_value(value: str) -> str:
    return " ".join(value.split())


def _result(
    *,
    success: bool,
    status: str,
    patient_id: str,
    field: str,
    action: Literal["add", "update"],
    message: str,
) -> StructuredHistoryMutationResult:
    return {
        "success": success,
        "status": status,
        "patient_id": patient_id,
        "field": field,
        "action": action,
        "message": message,
    }


def add_structured_history_entry(
    records: List[MedicalRecord],
    patient_id: str,
    field: str,
    value: str,
) -> StructuredHistoryMutationResult:
    normalized_value = _normalize_history_value(value)

    if field not in STRUCTURED_HISTORY_FIELDS:
        return _result(
            success=False,
            status="INVALID_FIELD",
            patient_id=patient_id,
            field=field,
            action="add",
            message="The structured history field is not supported.",
        )

    if not normalized_value:
        return _result(
            success=False,
            status="INVALID_VALUE",
            patient_id=patient_id,
            field=field,
            action="add",
            message="History value cannot be empty.",
        )

    record = get_medical_record_by_patient(records, patient_id)

    if record is None:
        return _result(
            success=False,
            status="PATIENT_NOT_FOUND",
            patient_id=patient_id,
            field=field,
            action="add",
            message="Medical record was not found for the patient.",
        )

    entries = getattr(record, field)

    if any(
        _normalize_history_value(entry).casefold()
        == normalized_value.casefold()
        for entry in entries
    ):
        return _result(
            success=False,
            status="DUPLICATE",
            patient_id=patient_id,
            field=field,
            action="add",
            message="The structured history entry already exists.",
        )

    entries.append(normalized_value)

    return _result(
        success=True,
        status="ADDED",
        patient_id=patient_id,
        field=field,
        action="add",
        message="The structured history entry was added.",
    )


def update_structured_history_entry(
    records: List[MedicalRecord],
    patient_id: str,
    field: str,
    current_value: str,
    new_value: str,
) -> StructuredHistoryMutationResult:
    normalized_current = _normalize_history_value(current_value)
    normalized_new = _normalize_history_value(new_value)

    if field not in STRUCTURED_HISTORY_FIELDS:
        return _result(
            success=False,
            status="INVALID_FIELD",
            patient_id=patient_id,
            field=field,
            action="update",
            message="The structured history field is not supported.",
        )

    if not normalized_current or not normalized_new:
        return _result(
            success=False,
            status="INVALID_VALUE",
            patient_id=patient_id,
            field=field,
            action="update",
            message="Current and replacement values cannot be empty.",
        )

    record = get_medical_record_by_patient(records, patient_id)

    if record is None:
        return _result(
            success=False,
            status="PATIENT_NOT_FOUND",
            patient_id=patient_id,
            field=field,
            action="update",
            message="Medical record was not found for the patient.",
        )

    entries = getattr(record, field)
    current_index = next(
        (
            index
            for index, entry in enumerate(entries)
            if _normalize_history_value(entry).casefold()
            == normalized_current.casefold()
        ),
        None,
    )

    if current_index is None:
        return _result(
            success=False,
            status="ENTRY_NOT_FOUND",
            patient_id=patient_id,
            field=field,
            action="update",
            message="The structured history entry was not found.",
        )

    if any(
        index != current_index
        and _normalize_history_value(entry).casefold()
        == normalized_new.casefold()
        for index, entry in enumerate(entries)
    ):
        return _result(
            success=False,
            status="DUPLICATE",
            patient_id=patient_id,
            field=field,
            action="update",
            message="The replacement history entry already exists.",
        )

    entries[current_index] = normalized_new

    return _result(
        success=True,
        status="UPDATED",
        patient_id=patient_id,
        field=field,
        action="update",
        message="The structured history entry was updated.",
    )


def add_unstructured_history_note(
    records: List[MedicalRecord],
    patient_id: str,
    note: str,
) -> UnstructuredHistoryMutationResult:
    cleaned_note = note.strip()

    if not cleaned_note:
        return _result(
            success=False,
            status="INVALID_VALUE",
            patient_id=patient_id,
            field="history_notes",
            action="add",
            message="History note cannot be empty.",
        )

    record = get_medical_record_by_patient(records, patient_id)

    if record is None:
        return _result(
            success=False,
            status="PATIENT_NOT_FOUND",
            patient_id=patient_id,
            field="history_notes",
            action="add",
            message="Medical record was not found for the patient.",
        )

    if any(
        _normalize_history_value(existing_note).casefold()
        == _normalize_history_value(cleaned_note).casefold()
        for existing_note in record.history_notes
    ):
        return _result(
            success=False,
            status="DUPLICATE",
            patient_id=patient_id,
            field="history_notes",
            action="add",
            message="The unstructured history note already exists.",
        )

    record.history_notes.append(cleaned_note)

    return _result(
        success=True,
        status="ADDED",
        patient_id=patient_id,
        field="history_notes",
        action="add",
        message="The unstructured history note was added.",
    )


def update_unstructured_history_note(
    records: List[MedicalRecord],
    patient_id: str,
    current_note: str,
    new_note: str,
) -> UnstructuredHistoryMutationResult:
    cleaned_current = current_note.strip()
    cleaned_new = new_note.strip()

    if not cleaned_current or not cleaned_new:
        return _result(
            success=False,
            status="INVALID_VALUE",
            patient_id=patient_id,
            field="history_notes",
            action="update",
            message="Current and replacement notes cannot be empty.",
        )

    record = get_medical_record_by_patient(records, patient_id)

    if record is None:
        return _result(
            success=False,
            status="PATIENT_NOT_FOUND",
            patient_id=patient_id,
            field="history_notes",
            action="update",
            message="Medical record was not found for the patient.",
        )

    current_key = _normalize_history_value(cleaned_current).casefold()
    new_key = _normalize_history_value(cleaned_new).casefold()
    current_index = next(
        (
            index
            for index, existing_note in enumerate(record.history_notes)
            if _normalize_history_value(existing_note).casefold()
            == current_key
        ),
        None,
    )

    if current_index is None:
        return _result(
            success=False,
            status="ENTRY_NOT_FOUND",
            patient_id=patient_id,
            field="history_notes",
            action="update",
            message="The unstructured history note was not found.",
        )

    if any(
        index != current_index
        and _normalize_history_value(existing_note).casefold()
        == new_key
        for index, existing_note in enumerate(record.history_notes)
    ):
        return _result(
            success=False,
            status="DUPLICATE",
            patient_id=patient_id,
            field="history_notes",
            action="update",
            message="The replacement history note already exists.",
        )

    record.history_notes[current_index] = cleaned_new

    return _result(
        success=True,
        status="UPDATED",
        patient_id=patient_id,
        field="history_notes",
        action="update",
        message="The unstructured history note was updated.",
    )
