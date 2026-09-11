from app.models.appointment import Appointment
from app.models.doctor import Doctor


def book_appointment(
    appointment_id: str,
    patient_id: str,
    doctor: Doctor,
    appointment_time: str,
    reason: str
) -> Appointment:
    if appointment_time not in doctor.available_slots:
        raise ValueError("Requested appointment time is not available")

    appointment = Appointment(
        appointment_id=appointment_id,
        patient_id=patient_id,
        doctor_id=doctor.doctor_id,
        appointment_time=appointment_time,
        reason=reason
    )

    doctor.available_slots.remove(appointment_time)

    return appointment