from collections.abc import Callable, Sequence

import faiss
import numpy as np

from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.patient_summary import PatientSummary
from app.retrieval.embeddings import embed_text


EmbeddingFunction = Callable[[str], list[float]]


def build_patient_summary(
    patient: Patient,
    medical_record: MedicalRecord,
) -> PatientSummary:
    summary = (
        f"Patient {patient.patient_id}: {patient.first_name} "
        f"{patient.last_name}, age {patient.age}. "
        f"Primary condition: {patient.primary_condition}. "
        f"Diagnoses: {', '.join(medical_record.diagnoses) or 'None recorded'}. "
        f"Medications: {', '.join(medical_record.medications) or 'None recorded'}. "
        f"Treatment notes: "
        f"{', '.join(medical_record.treatment_notes) or 'None recorded'}. "
        f"Relevant alerts: "
        f"{', '.join(medical_record.alerts) or 'None recorded'}. "
        f"History notes: "
        f"{', '.join(medical_record.history_notes) or 'None recorded'}."
    )

    return PatientSummary(
        patient_id=patient.patient_id,
        record_id=medical_record.record_id,
        summary=summary,
    )


def build_patient_summaries(
    patients: Sequence[Patient],
    medical_records: Sequence[MedicalRecord],
) -> list[PatientSummary]:
    patients_by_id = {
        patient.patient_id: patient
        for patient in patients
    }

    return [
        build_patient_summary(
            patients_by_id[record.patient_id],
            record,
        )
        for record in medical_records
        if record.patient_id in patients_by_id
    ]


def search_patient_summaries(
    query: str,
    patients: Sequence[Patient],
    medical_records: Sequence[MedicalRecord],
    *,
    patient_id: str,
    top_k: int = 1,
    embedding_function: EmbeddingFunction = embed_text,
) -> list[PatientSummary]:
    if not query.strip() or not patient_id.strip() or top_k < 1:
        return []

    candidates = [
        summary
        for summary in build_patient_summaries(
            patients,
            medical_records,
        )
        if summary.patient_id == patient_id
    ]

    if not candidates:
        return []

    matrix = np.asarray(
        [
            embedding_function(summary.summary)
            for summary in candidates
        ],
        dtype="float32",
    )

    if matrix.ndim != 2 or matrix.shape[1] == 0:
        raise ValueError("Patient-summary embeddings must be non-empty vectors")

    index = faiss.IndexFlatL2(matrix.shape[1])
    index.add(matrix)

    query_vector = np.asarray(
        [embedding_function(query)],
        dtype="float32",
    )

    if query_vector.shape[1] != matrix.shape[1]:
        raise ValueError("Query and patient-summary embeddings must have equal dimensions")

    result_count = min(top_k, len(candidates))
    distances, positions = index.search(
        query_vector,
        result_count,
    )

    return [
        candidates[position].model_copy(
            update={"distance": float(distance)}
        )
        for distance, position in zip(
            distances[0],
            positions[0],
        )
        if position >= 0
    ]
