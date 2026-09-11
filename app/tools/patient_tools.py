from typing import List, Optional
from app.models.patient import Patient


def get_patient_by_id(
    patients: List[Patient],
    patient_id: str
) -> Optional[Patient]:
    for patient in patients:
        if patient.patient_id == patient_id:
            return patient

    return None
