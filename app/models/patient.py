from pydantic import BaseModel, Field
from typing import Optional


class Patient(BaseModel):
    patient_id: str = Field(..., description="Unique patient identifier")
    first_name: str
    last_name: str
    age: int = Field(..., ge=0, le=120)
    primary_condition: Optional[str] = None