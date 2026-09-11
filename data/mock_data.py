from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.medical_record import MedicalRecord
from app.persistence.medical_record_store import (
    load_or_initialize_medical_records,
)


patients = [
    Patient(
        patient_id="P001",
        first_name="Robert",
        last_name="Smith",
        age=70,
        primary_condition="Chronic Kidney Disease"
    )
]


doctors = [
    Doctor(
        doctor_id="D001",
        first_name="Sarah",
        last_name="Chen",
        specialty="Nephrology",
        available_slots=[
            "2026-09-02 09:00",
            "2026-09-02 14:00"
        ]
    ),
    Doctor(
        doctor_id="D002",
        first_name="James",
        last_name="Lee",
        specialty="Cardiology",
        available_slots=[
            "2026-09-03 10:00"
        ]
    )
]


default_medical_records = [
    MedicalRecord(
        record_id="R001",
        patient_id="P001",
        diagnoses=[
            "Chronic Kidney Disease"
        ],
        medications=[
            "Lisinopril 10 mg daily"
        ],
        treatment_notes=[
            "Monitor kidney function and blood pressure"
        ]
    )
]


medical_records = load_or_initialize_medical_records(
    default_medical_records
)
