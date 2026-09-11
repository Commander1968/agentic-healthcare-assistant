from data.mock_data import patients, doctors, medical_records
from app.tools.patient_tools import get_patient_by_id
from app.tools.medical_record_tools import get_medical_record_by_patient
from app.tools.doctor_tools import find_doctors_by_specialty
from app.tools.appointment_tools import book_appointment
from app.models.workflow_state import WorkflowState


def run_demo():
    state = WorkflowState(
        patient_id="P001",
        requested_specialty="Nephrology",
        reason="CKD nephrology follow-up"
    )

    state.patient = get_patient_by_id(
        patients,
        state.patient_id
    )

    if state.patient is None:
        state.errors.append("Patient not found")
        raise ValueError(state.errors[-1])

    state.medical_record = get_medical_record_by_patient(
        medical_records,
        state.patient_id
    )

    if state.medical_record is None:
        state.errors.append("Medical record not found")
        raise ValueError(state.errors[-1])

    state.matching_doctors = find_doctors_by_specialty(
        doctors,
        state.requested_specialty
    )

    if not state.matching_doctors:
        state.errors.append("No matching doctor found")
        raise ValueError(state.errors[-1])

    state.selected_doctor = state.matching_doctors[0]

    if state.selected_doctor is None:
        state.errors.append("No doctor selected")
        raise ValueError(state.errors[-1])

    if not state.selected_doctor.available_slots:
        state.errors.append("No available appointment slots")
        raise ValueError(state.errors[-1])

    appointment_time = state.selected_doctor.available_slots[0]

    state.appointment = book_appointment(
        appointment_id="A001",
        patient_id=state.patient.patient_id,
        doctor=state.selected_doctor,
        appointment_time=appointment_time,
        reason=state.reason
    )

    print("Workflow State:")
    print(state)

    print("\nBooked Appointment:")
    print(state.appointment)

    print("\nRemaining Doctor Availability:")
    print(state.selected_doctor.available_slots)


if __name__ == "__main__":
    run_demo()
