from pydantic import BaseModel, Field
from typing import List


class MedicalRecord(BaseModel):
    record_id: str = Field(..., description="Unique medical record identifier")
    patient_id: str
    diagnoses: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    treatment_notes: List[str] = Field(default_factory=list)
    alerts: List[str] = Field(default_factory=list)
    history_notes: List[str] = Field(default_factory=list)
