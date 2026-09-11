from typing import Protocol, Sequence, runtime_checkable

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.tools.appointment_tools import book_appointment
from app.tools.doctor_tools import find_doctors_by_specialty


@runtime_checkable
class DoctorScheduleService(Protocol):
    """Boundary for doctor availability lookup and appointment booking."""

    def find_doctors_by_specialty(self, specialty: str) -> list[Doctor]: ...

    def book_appointment(
        self,
        appointment_id: str,
        patient_id: str,
        doctor: Doctor,
        appointment_time: str,
        reason: str,
    ) -> Appointment: ...


class InMemoryDoctorScheduleAdapter:
    """Deterministic Doctor Schedule implementation backed by local demo data."""

    def __init__(self, doctors: Sequence[Doctor]) -> None:
        self._doctors = list(doctors)

    def find_doctors_by_specialty(self, specialty: str) -> list[Doctor]:
        return find_doctors_by_specialty(self._doctors, specialty)

    def book_appointment(
        self,
        appointment_id: str,
        patient_id: str,
        doctor: Doctor,
        appointment_time: str,
        reason: str,
    ) -> Appointment:
        return book_appointment(
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor=doctor,
            appointment_time=appointment_time,
            reason=reason,
        )
