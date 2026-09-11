import hashlib

import numpy as np

from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.retrieval.patient_summary_index import (
    build_patient_summaries,
    search_patient_summaries,
)


def deterministic_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return np.frombuffer(digest[:16], dtype=np.uint8).astype("float32").tolist()


def patient(patient_id: str, name: str, condition: str) -> Patient:
    return Patient(
        patient_id=patient_id,
        first_name=name,
        last_name="Test",
        age=70,
        primary_condition=condition,
    )


def record(patient_id: str, record_id: str, diagnosis: str) -> MedicalRecord:
    return MedicalRecord(
        record_id=record_id,
        patient_id=patient_id,
        diagnoses=[diagnosis],
        medications=[f"Medication for {diagnosis}"],
        treatment_notes=[f"Monitor {diagnosis}"],
        history_notes=[],
    )


def test_patient_summaries_include_patient_linked_metadata():
    summaries = build_patient_summaries(
        [patient("P001", "Robert", "CKD")],
        [record("P001", "R001", "CKD")],
    )

    assert len(summaries) == 1
    assert summaries[0].patient_id == "P001"
    assert summaries[0].record_id == "R001"
    assert "Robert Test" in summaries[0].summary
    assert "CKD" in summaries[0].summary


def test_patient_scoped_search_prevents_cross_patient_leakage():
    patients = [
        patient("P001", "Robert", "CKD"),
        patient("P002", "Alex", "Diabetes"),
    ]
    records = [
        record("P001", "R001", "CKD"),
        record("P002", "R002", "Diabetes"),
    ]

    results = search_patient_summaries(
        query="diabetes medication",
        patients=patients,
        medical_records=records,
        patient_id="P001",
        embedding_function=deterministic_embedding,
    )

    assert len(results) == 1
    assert results[0].patient_id == "P001"
    assert results[0].record_id == "R001"
    assert "Alex" not in results[0].summary
    assert "Diabetes" not in results[0].summary


def test_updated_history_is_present_in_rebuilt_patient_summary():
    patients = [patient("P001", "Robert", "CKD")]
    records = [record("P001", "R001", "CKD")]
    records[0].history_notes.append("Restart persistence verified")

    results = search_patient_summaries(
        query="restart persistence",
        patients=patients,
        medical_records=records,
        patient_id="P001",
        embedding_function=deterministic_embedding,
    )

    assert "Restart persistence verified" in results[0].summary


def test_unknown_patient_returns_no_summary():
    results = search_patient_summaries(
        query="medical history",
        patients=[patient("P001", "Robert", "CKD")],
        medical_records=[record("P001", "R001", "CKD")],
        patient_id="P999",
        embedding_function=deterministic_embedding,
    )

    assert results == []
