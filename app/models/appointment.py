from pydantic import BaseModel, Field
from typing import Optional


class Appointment(BaseModel):
    appointment_id: str = Field(..., description="Unique appointment identifier")
    patient_id: str
    doctor_id: str
    appointment_time: str
    status: str = Field(default="scheduled")
    reason: Optional[str] = None