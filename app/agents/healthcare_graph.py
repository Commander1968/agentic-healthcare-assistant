from langgraph.graph import StateGraph, START, END

from app.models.workflow_state import WorkflowState
from app.models.retrieved_document import RetrievedDocument
from app.integrations.doctor_schedule import (
    DoctorScheduleService,
    InMemoryDoctorScheduleAdapter,
)
from app.tools.patient_tools import get_patient_by_id
from app.tools.medical_record_tools import get_medical_record_by_patient
from app.retrieval.faiss_index import search_knowledge
from app.retrieval.medlineplus import (
    ExternalRetrievalError,
    search_medlineplus,
)
from app.retrieval.patient_summary_index import search_patient_summaries
from data.mock_data import patients, medical_records, doctors


DEFAULT_DOCTOR_SCHEDULE_SERVICE = InMemoryDoctorScheduleAdapter(doctors)


def retrieve_patient(state: WorkflowState) -> WorkflowState:
    state.patient = get_patient_by_id(
        patients,
        state.patient_id
    )

    if state.patient is None:
        state.errors.append("Patient not found")

    return state


def retrieve_medical_record(state: WorkflowState) -> WorkflowState:
    if state.patient is None:
        state.errors.append("Cannot retrieve medical record without patient")
        return state

    state.medical_record = get_medical_record_by_patient(
        medical_records,
        state.patient_id
    )

    if state.medical_record is None:
        state.errors.append("Medical record not found")

    return state


def retrieve_knowledge(state: WorkflowState) -> WorkflowState:
    query_parts = []

    if state.requested_specialty:
        query_parts.append(state.requested_specialty)

    if state.reason:
        query_parts.append(state.reason)

    if state.medical_record is not None:
        query_parts.extend(state.medical_record.diagnoses)

    query = " ".join(query_parts)

    if not query.strip():
        state.errors.append("Unable to build knowledge retrieval query")
        return state

    # MedlinePlus performs best with a concise health-topic term. Prefer the
    # authoritative diagnosis instead of sending the full workflow context.
    external_query = query
    if state.medical_record is not None and state.medical_record.diagnoses:
        external_query = state.medical_record.diagnoses[0]
    elif state.reason:
        external_query = state.reason
    elif state.requested_specialty:
        external_query = state.requested_specialty

    try:
        state.retrieved_documents = search_medlineplus(
            external_query,
            top_k=2,
        )
    except ExternalRetrievalError as exc:
        state.external_retrieval_error = str(exc)

    if not state.retrieved_documents:
        results = search_knowledge(
            query,
            top_k=2
        )

        state.retrieved_documents = [
            RetrievedDocument(**result)
            for result in results
        ]

    return state


def retrieve_patient_summary(state: WorkflowState) -> WorkflowState:
    if state.patient is None or state.medical_record is None:
        state.errors.append(
            "Cannot retrieve patient summary without patient and medical record"
        )
        return state

    query = " ".join(
        part
        for part in (
            state.reason,
            state.requested_specialty,
            *state.medical_record.diagnoses,
        )
        if part
    )

    state.patient_summaries = search_patient_summaries(
        query=query or state.patient_id,
        patients=patients,
        medical_records=medical_records,
        patient_id=state.patient_id,
        top_k=1,
    )

    if not state.patient_summaries:
        state.errors.append("Patient summary not found")

    return state


def find_doctors(
    state: WorkflowState,
    doctor_schedule: DoctorScheduleService = DEFAULT_DOCTOR_SCHEDULE_SERVICE,
) -> WorkflowState:
    if not state.requested_specialty:
        state.errors.append("Requested specialty not provided")
        return state

    state.matching_doctors = doctor_schedule.find_doctors_by_specialty(
        state.requested_specialty
    )

    if not state.matching_doctors:
        state.errors.append("No matching doctor found")

    return state


def book_appointment_node(
    state: WorkflowState,
    doctor_schedule: DoctorScheduleService = DEFAULT_DOCTOR_SCHEDULE_SERVICE,
) -> WorkflowState:
    if not state.matching_doctors:
        state.errors.append("No matching doctor available for booking")
        return state

    state.selected_doctor = state.matching_doctors[0]

    if not state.selected_doctor.available_slots:
        state.errors.append("No available appointment slots")
        return state

    appointment_time = state.selected_doctor.available_slots[0]

    state.appointment = doctor_schedule.book_appointment(
        appointment_id="A001",
        patient_id=state.patient_id,
        doctor=state.selected_doctor,
        appointment_time=appointment_time,
        reason=state.reason or "Specialist follow-up"
    )

    return state


def route_after_knowledge(state: WorkflowState) -> str:
    """Continue to scheduling only when booking was explicitly requested."""

    return "find_doctors" if state.appointment_requested else END


def build_graph(
    doctor_schedule: DoctorScheduleService | None = None,
):
    schedule_service = doctor_schedule or DEFAULT_DOCTOR_SCHEDULE_SERVICE
    builder = StateGraph(WorkflowState)

    builder.add_node(
        "retrieve_patient",
        retrieve_patient
    )

    builder.add_node(
        "retrieve_medical_record",
        retrieve_medical_record
    )

    builder.add_node(
        "retrieve_knowledge",
        retrieve_knowledge
    )

    builder.add_node(
        "retrieve_patient_summary",
        retrieve_patient_summary
    )

    builder.add_node(
        "find_doctors",
        lambda state: find_doctors(state, schedule_service)
    )

    builder.add_node(
        "book_appointment",
        lambda state: book_appointment_node(state, schedule_service)
    )

    builder.add_edge(
        START,
        "retrieve_patient"
    )

    builder.add_edge(
        "retrieve_patient",
        "retrieve_medical_record"
    )

    builder.add_edge(
        "retrieve_medical_record",
        "retrieve_patient_summary"
    )

    builder.add_edge(
        "retrieve_patient_summary",
        "retrieve_knowledge"
    )

    builder.add_conditional_edges(
        "retrieve_knowledge",
        route_after_knowledge,
        {
            "find_doctors": "find_doctors",
            END: END,
        },
    )

    builder.add_edge(
        "find_doctors",
        "book_appointment"
    )

    builder.add_edge(
        "book_appointment",
        END
    )

    return builder.compile()
