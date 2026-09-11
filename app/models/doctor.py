from pydantic import BaseModel, Field
from typing import List


class Doctor(BaseModel):
    doctor_id: str = Field(..., description="Unique doctor identifier")
    first_name: str
    last_name: str
    specialty: str
    available_slots: List[str] = Field(default_factory=list)