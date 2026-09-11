from pydantic import BaseModel


class PatientSummary(BaseModel):
    patient_id: str
    record_id: str
    summary: str
    distance: float | None = None
