from typing import List
from app.models.doctor import Doctor


def find_doctors_by_specialty(
    doctors: List[Doctor],
    specialty: str
) -> List[Doctor]:
    return [
        doctor
        for doctor in doctors
        if doctor.specialty.lower() == specialty.lower()
    ]