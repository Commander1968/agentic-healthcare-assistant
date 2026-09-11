from pathlib import Path
from typing import List

from app.models.medical_record import MedicalRecord
from app.persistence.medical_record_store import save_medical_records
from app.tools.medical_record_tools import (
    StructuredHistoryMutationResult,
    add_structured_history_entry,
    add_unstructured_history_note,
    update_structured_history_entry,
    update_unstructured_history_note,
)


def _invalid_request(
    patient_id: str,
    field: str,
    action: str,
    message: str,
) -> StructuredHistoryMutationResult:
    return {
        "success": False,
        "status": "INVALID_REQUEST",
        "patient_id": patient_id,
        "field": field,
        "action": action,
        "message": message,
    }


def execute_history_management_action(
    records: List[MedicalRecord],
    patient_id: str,
    history_type: str,
    action: str,
    new_value: str,
    field: str = "",
    current_value: str = "",
) -> StructuredHistoryMutationResult:
    if action not in ("add", "update"):
        return _invalid_request(
            patient_id,
            field,
            action,
            "History action must be add or update.",
        )

    if history_type == "structured":
        if not field:
            return _invalid_request(
                patient_id,
                field,
                action,
                "A structured history field is required.",
            )

        if action == "add":
            return add_structured_history_entry(
                records,
                patient_id,
                field,
                new_value,
            )

        return update_structured_history_entry(
            records,
            patient_id,
            field,
            current_value,
            new_value,
        )

    if history_type == "unstructured":
        if action == "add":
            return add_unstructured_history_note(
                records,
                patient_id,
                new_value,
            )

        return update_unstructured_history_note(
            records,
            patient_id,
            current_value,
            new_value,
        )

    return _invalid_request(
        patient_id,
        field,
        action,
        "History type must be structured or unstructured.",
    )


def execute_persisted_history_management_action(
    records: List[MedicalRecord],
    patient_id: str,
    history_type: str,
    action: str,
    new_value: str,
    field: str = "",
    current_value: str = "",
    store_path: str | Path | None = None,
) -> StructuredHistoryMutationResult:
    prior_records = [
        record.model_copy(deep=True)
        for record in records
    ]
    result = execute_history_management_action(
        records=records,
        patient_id=patient_id,
        history_type=history_type,
        action=action,
        new_value=new_value,
        field=field,
        current_value=current_value,
    )

    if not result["success"]:
        return result

    try:
        save_medical_records(records, store_path)
    except (OSError, TypeError, ValueError):
        records[:] = prior_records
        return {
            **result,
            "success": False,
            "status": "PERSISTENCE_ERROR",
            "message": (
                "The history change was not saved; "
                "the in-memory record was restored."
            ),
        }

    return {
        **result,
        "message": f"{result['message']} The change was saved.",
    }
