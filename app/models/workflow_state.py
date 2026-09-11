from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord
from app.models.retrieved_document import RetrievedDocument
from app.models.patient_summary import PatientSummary


class WorkflowState(BaseModel):
    patient_id: str
    requested_specialty: Optional[str] = None
    reason: Optional[str] = None
    appointment_requested: bool = True

    patient: Optional[Patient] = None
    medical_record: Optional[MedicalRecord] = None
    matching_doctors: List[Doctor] = Field(default_factory=list)
    selected_doctor: Optional[Doctor] = None
    appointment: Optional[Appointment] = None
    retrieved_documents: List[RetrievedDocument] = Field(default_factory=list)
    patient_summaries: List[PatientSummary] = Field(default_factory=list)
    external_retrieval_error: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
