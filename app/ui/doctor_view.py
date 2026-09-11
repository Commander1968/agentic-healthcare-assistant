from typing import Any, Mapping


NOT_AVAILABLE = "Not available"


def build_doctor_view(
    workflow_state: Mapping[str, Any],
) -> dict[str, str]:
    """Project existing workflow output into the Doctor View contract."""

    patient = workflow_state.get("patient") or {}
    doctor = workflow_state.get("selected_doctor") or {}
    appointment = workflow_state.get("appointment") or {}

    patient_name = " ".join(
        part
        for part in (
            patient.get("first_name"),
            patient.get("last_name"),
        )
        if part
    )

    doctor_name = " ".join(
        part
        for part in (
            doctor.get("first_name"),
            doctor.get("last_name"),
        )
        if part
    )

    return {
        "doctor": doctor_name or NOT_AVAILABLE,
        "specialty": doctor.get("specialty") or NOT_AVAILABLE,
        "assigned_patient": patient_name or NOT_AVAILABLE,
        "patient_id": (
            patient.get("patient_id")
            or workflow_state.get("patient_id")
            or NOT_AVAILABLE
        ),
        "appointment_time": (
            appointment.get("appointment_time") or NOT_AVAILABLE
        ),
        "reason": (
            appointment.get("reason")
            or workflow_state.get("reason")
            or NOT_AVAILABLE
        ),
        "status": appointment.get("status") or NOT_AVAILABLE,
    }
