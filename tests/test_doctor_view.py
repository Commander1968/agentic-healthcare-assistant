from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.workflow_state import WorkflowState
from app.ui.doctor_view import NOT_AVAILABLE, build_doctor_view


def test_doctor_view_projects_required_fields_from_workflow_state():
    state = WorkflowState(
        patient_id="P001",
        requested_specialty="Nephrology",
        reason="CKD specialist follow-up",
        patient=Patient(
            patient_id="P001",
            first_name="Robert",
            last_name="Smith",
            age=70,
            primary_condition="Chronic Kidney Disease",
        ),
        selected_doctor=Doctor(
            doctor_id="D001",
            first_name="Sarah",
            last_name="Chen",
            specialty="Nephrology",
            available_slots=["2026-09-02 09:00"],
        ),
        appointment=Appointment(
            appointment_id="A001",
            patient_id="P001",
            doctor_id="D001",
            appointment_time="2026-09-02 09:00",
            status="scheduled",
            reason="CKD specialist follow-up",
        ),
    )

    doctor_view = build_doctor_view(
        state.model_dump(mode="json")
    )

    assert doctor_view == {
        "doctor": "Sarah Chen",
        "specialty": "Nephrology",
        "assigned_patient": "Robert Smith",
        "patient_id": "P001",
        "appointment_time": "2026-09-02 09:00",
        "reason": "CKD specialist follow-up",
        "status": "scheduled",
    }


def test_doctor_view_handles_an_unassigned_workflow_safely():
    doctor_view = build_doctor_view({"patient_id": "P001"})

    assert doctor_view == {
        "doctor": NOT_AVAILABLE,
        "specialty": NOT_AVAILABLE,
        "assigned_patient": NOT_AVAILABLE,
        "patient_id": "P001",
        "appointment_time": NOT_AVAILABLE,
        "reason": NOT_AVAILABLE,
        "status": NOT_AVAILABLE,
    }
