import streamlit as st

from app.agents.assistant_pipeline import (
    run_healthcare_assistant_detailed,
)
from app.evaluation.booking_metrics import load_booking_success_metrics
from app.evaluation.memory_events import load_recent_memory_access_events
from app.ui.booking_metrics_view import build_booking_metric_view
from app.ui.doctor_view import build_doctor_view
from app.ui.evaluation_metrics import build_evaluation_metrics
from app.ui.history_management import (
    execute_persisted_history_management_action,
)
from app.ui.memory_trace import build_memory_trace_rows
from app.tools.medical_record_tools import (
    get_medical_record_by_patient,
)
from data.mock_data import medical_records


st.set_page_config(
    page_title="Agentic Healthcare Assistant",
    page_icon="ðŸ¥",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_session_state():
    if "last_run" not in st.session_state:
        st.session_state.last_run = None


initialize_session_state()

if "history_mutation_result" not in st.session_state:
    st.session_state.history_mutation_result = None


st.title("Agentic Healthcare Assistant")

st.caption(
    "Agentic workflow prototype for healthcare task automation, "
    "retrieval, evaluation, and memory."
)


with st.sidebar:
    st.header("Session")

    st.text_input(
        "Patient ID",
        value="P001",
        disabled=True,
    )


st.subheader("Healthcare Request")

user_request = st.text_area(
    "Enter a healthcare workflow request",
    placeholder=(
        "Example: Book a nephrologist for my 70-year-old "
        "father with CKD and summarize his current treatment."
    ),
    height=120,
)


run_button = st.button(
    "Run Assistant",
    type="primary",
)


if run_button:
    if not user_request.strip():
        st.warning(
            "Enter a healthcare workflow request before "
            "running the assistant."
        )

    else:
        try:
            with st.spinner(
                "Running healthcare workflow..."
            ):
                result = run_healthcare_assistant_detailed(
                    user_request.strip()
                )

            st.session_state.last_run = result

        except Exception as exc:
            st.session_state.last_run = None

            st.error(
                "The healthcare workflow could not be completed."
            )

            st.exception(exc)


st.divider()

st.subheader("Assistant Response")


if st.session_state.last_run is None:
    st.info(
        "Run a healthcare workflow to generate a response."
    )

else:
    result = st.session_state.last_run

    patient_view, doctor_view, planning_view = st.tabs(
        ["Patient View", "Doctor View", "Planning View"]
    )


with st.expander("Attendant: Medical History Management"):
    st.caption(
        "Capstone demonstration control for authorized attendants. "
        "Validated changes are saved to durable local storage."
    )

    history_patient_id = "P001"
    history_record = get_medical_record_by_patient(
        medical_records,
        history_patient_id,
    )

    history_type_label = st.selectbox(
        "History type",
        ["Structured", "Unstructured note"],
        key="history_type",
    )
    history_action_label = st.radio(
        "Action",
        ["Add", "Update"],
        horizontal=True,
        key="history_action",
    )

    history_type = (
        "structured"
        if history_type_label == "Structured"
        else "unstructured"
    )
    history_action = history_action_label.lower()
    history_field = ""

    if history_type == "structured":
        field_labels = {
            "Diagnosis": "diagnoses",
            "Medication": "medications",
            "Treatment note": "treatment_notes",
            "Alert": "alerts",
        }
        selected_field_label = st.selectbox(
            "Structured field",
            list(field_labels),
            key="history_field",
        )
        history_field = field_labels[selected_field_label]
        existing_entries = (
            getattr(history_record, history_field)
            if history_record is not None
            else []
        )
    else:
        existing_entries = (
            history_record.history_notes
            if history_record is not None
            else []
        )

    current_history_value = ""

    if history_action == "update":
        if existing_entries:
            current_history_value = st.selectbox(
                "Existing entry",
                existing_entries,
                key="history_current_value",
            )
        else:
            st.info("No existing entries are available to update.")

    new_history_value = st.text_area(
        "New entry" if history_action == "add" else "Replacement entry",
        key="history_new_value",
        height=100,
    )

    apply_history_change = st.button(
        "Apply History Change",
        disabled=(history_action == "update" and not existing_entries),
    )

    if apply_history_change:
        st.session_state.history_mutation_result = (
            execute_persisted_history_management_action(
                records=medical_records,
                patient_id=history_patient_id,
                history_type=history_type,
                action=history_action,
                field=history_field,
                current_value=current_history_value,
                new_value=new_history_value,
            )
        )

    history_result = st.session_state.history_mutation_result

    if history_result is not None:
        if history_result["success"]:
            st.success(history_result["message"])
        else:
            st.error(
                f"{history_result['status']}: "
                f"{history_result['message']}"
            )

    if history_record is not None:
        with st.expander("Current Medical History"):
            st.write("**Diagnoses:**", history_record.diagnoses)
            st.write("**Medications:**", history_record.medications)
            st.write(
                "**Treatment Notes:**",
                history_record.treatment_notes,
            )
            st.write("**Relevant Alerts:**", history_record.alerts)
            st.write("**History Notes:**", history_record.history_notes)


st.divider()
st.subheader("Operational Performance")
st.caption(
    "Aggregated from persisted TOOL_EXECUTION events. Skipped booking steps "
    "are excluded from the attempt denominator."
)

booking_metrics = load_booking_success_metrics()
booking_view = build_booking_metric_view(booking_metrics)

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Booking Success Rate", booking_view["success_rate"])
metric_col2.metric("Successful Bookings", booking_view["successful_bookings"])
metric_col3.metric("Booking Attempts", booking_view["booking_attempts"])
metric_col4.metric("Failed Bookings", booking_view["failed_bookings"])

st.write("**Formula:**", booking_view["formula"])
st.write("**Source:**", booking_view["source"])
st.caption(
    f"Run records scanned: {booking_view['records_scanned']} | "
    f"Malformed records skipped: {booking_view['malformed_records_skipped']}"
)

from app.evaluation.persisted_response_precision import (
    evaluate_persisted_response_precision,
)

precision_result = evaluate_persisted_response_precision(
    "logs/pipeline_runs.jsonl"
)

st.divider()
st.subheader("Response Precision")
st.caption(
    "Claim-level precision calculated from persisted semantic-evaluation "
    "records. Authority, safety, and relevance flags are excluded."
)

precision_col1, precision_col2, precision_col3 = st.columns(3)
precision_col1.metric(
    "Response Precision",
    (
        f"{precision_result.precision:.2%}"
        if precision_result.precision is not None
        else "N/A"
    ),
)
precision_col2.metric(
    "Supported Claims",
    precision_result.supported_claim_count,
)
precision_col3.metric(
    "Verifiable Claims",
    precision_result.verifiable_claim_count,
)

st.write("**Formula:**", precision_result.formula)
st.write("**Evaluation Basis:**", precision_result.evaluation_basis)
st.divider()
st.subheader("Memory Diagnostics")
st.write("**Memory Access Events**")
st.caption(
    "Patient-scoped READ, WRITE, and SKIP metadata. Request and response "
    "content are never included in this trace."
)

memory_events = load_recent_memory_access_events(limit=20)

if memory_events:
    st.dataframe(
        build_memory_trace_rows(memory_events),
        hide_index=True,
        width="stretch",
    )
else:
    st.info("No memory access events were recorded.")


if st.session_state.last_run is not None:
    with patient_view:
        st.write(
            result["response"]
        )

    with doctor_view:
        workflow_state = result["workflow_state"]
        doctor_summary = build_doctor_view(workflow_state)

        st.caption(
            "Clinician-facing appointment assignment generated from "
            "the current workflow state."
        )

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Doctor:**", doctor_summary["doctor"])
            st.write(
                "**Specialty:**",
                doctor_summary["specialty"],
            )
            st.write(
                "**Assigned Patient:**",
                doctor_summary["assigned_patient"],
            )
            st.write(
                "**Patient ID:**",
                doctor_summary["patient_id"],
            )

        with col2:
            st.write(
                "**Appointment Time:**",
                doctor_summary["appointment_time"],
            )
            st.write("**Reason:**", doctor_summary["reason"])
            st.write("**Status:**", doctor_summary["status"])

    with planning_view:
        planning = result["planning"]

        st.caption(
            "Ordered sub-goals generated from the interpreted intent "
            "and mapped to the executed LangGraph workflow."
        )

        st.write("**Goal:**", planning["goal"])
        st.write(
            "**Planning Basis:**",
            planning["planning_basis"],
        )
        st.write(
            "**Execution Framework:**",
            planning["execution_framework"],
        )

        for step in planning["steps"]:
            with st.container(border=True):
                st.write(
                    f"**Step {step['step']}: {step['sub_goal']}**"
                )
                st.write("**LangGraph Node:**", step["graph_node"])
                st.write("**Tool:**", step["tool"])
                st.write("**Capability:**", step["capability"])
                st.write("**Status:**", step["status"])
                st.write(
                    "**Execution Evidence:**",
                    step["execution_evidence"],
                )

    st.divider()

    st.subheader("Evaluation Status")

    evaluation_metrics = build_evaluation_metrics(result)

    st.caption(
        "Rubric-readable model-response and operational tool metrics "
        "for the latest workflow run."
    )

    st.write("**Model Response Metrics**")

    deterministic = result["deterministic_evaluation"]

    semantic = result["semantic_evaluation"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Deterministic Evaluation",
            evaluation_metrics["model_response"]["deterministic"],
        )

    with col2:
        st.metric(
            "Semantic Evaluation",
            evaluation_metrics["model_response"]["semantic"],
        )

    with col3:
        st.metric(
            "Accepted for Memory",
            evaluation_metrics["model_response"][
                "accepted_for_memory"
            ],
        )

    st.write("**Tool Success Metrics**")

    tool_metrics = evaluation_metrics["tool_success"]
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Tools Attempted", tool_metrics["attempted"])

    with col2:
        st.metric("Tools Successful", tool_metrics["successful"])

    with col3:
        st.metric("Tools Failed", tool_metrics["failed"])

    with col4:
        st.metric(
            "Tool Success Rate",
            tool_metrics["success_rate_display"],
        )

    st.divider()

    st.subheader("Appointment Summary")

    workflow_state = result["workflow_state"]

    appointment = workflow_state.get("appointment")

    selected_doctor = workflow_state.get(
        "selected_doctor"
    )

    if appointment is not None:
        col1, col2 = st.columns(2)

        with col1:
            st.write(
                "**Doctor:**",
                (
                    f"{selected_doctor['first_name']} "
                    f"{selected_doctor['last_name']}"
                    if selected_doctor
                    else "Not available"
                ),
            )

            st.write(
                "**Specialty:**",
                (
                    selected_doctor["specialty"]
                    if selected_doctor
                    else "Not available"
                ),
            )

        with col2:
            st.write(
                "**Appointment Time:**",
                appointment["appointment_time"],
            )

            st.write(
                "**Status:**",
                appointment["status"],
            )

    else:
        st.info(
            "No appointment was created in this workflow."
        )

    st.divider()

    st.subheader("Retrieved Sources")

    retrieved_documents = workflow_state.get(
        "retrieved_documents",
        [],
    )

    if not retrieved_documents:
        st.info(
            "No retrieved supplemental documents were used."
        )

    else:
        for index, document in enumerate(
            retrieved_documents,
            start=1,
        ):
            with st.expander(
                f"{index}. {document['title']}"
            ):
                st.write(
                    "**Source Name:**",
                    document["source_name"],
                )

                st.write(
                    "**Source Type:**",
                    document["source_type"],
                )

                if document.get("source_url"):
                    st.write(
                        "**Source URL:**",
                        document["source_url"],
                    )

                if document.get("retrieved_at"):
                    st.write(
                        "**Retrieved At (UTC):**",
                        document["retrieved_at"],
                    )

                st.write(
                    "**Retrieved Content:**"
                )

                st.write(
                    document["content"]
                )

                if document.get("distance") is not None:
                    st.write(
                        "**FAISS Distance:**",
                        document["distance"],
                    )

    st.divider()

    st.subheader("Memory")

    memory = result["memory"]

    if memory is None:
        st.warning(
            "This response was not accepted into patient memory."
        )

    else:
        st.success(
            "This response passed evaluation and was stored "
            "in patient memory."
        )

        st.write(
            "**Patient ID:**",
            memory["patient_id"],
        )

        st.write(
            "**Last Specialty:**",
            memory["last_specialty"],
        )

        st.write(
            "**Last Appointment ID:**",
            memory["last_appointment_id"],
        )

        st.write(
            "**Stored Turns:**",
            len(memory["turns"]),
        )

    st.divider()

    st.subheader("Workflow Diagnostics")

    st.write("**Tool Execution Events**")

    st.caption(
        "Ordered per-tool success/failure events persisted with the "
        "latest pipeline run."
    )

    tool_events = result.get("tool_events", [])

    if tool_events:
        st.dataframe(
            [
                {
                    "Sequence": event["sequence"],
                    "Tool": event["tool"],
                    "LangGraph Node": event["graph_node"],
                    "Capability": event["capability"],
                    "Outcome": event["status"],
                    "Execution Evidence": event[
                        "execution_evidence"
                    ],
                }
                for event in tool_events
            ],
            hide_index=True,
            width="stretch",
        )

    else:
        st.info("No tool execution events were recorded.")

    workflow_errors = workflow_state.get(
        "errors",
        [],
    )

    if workflow_errors:
        st.error(
            "Workflow errors were recorded."
        )

        st.write(
            workflow_errors
        )

    else:
        st.success(
            "No workflow errors recorded."
        )

    if result["semantic_evaluation_error"]:
        st.error(
            "Semantic evaluator error:"
        )

        st.write(
            result["semantic_evaluation_error"]
        )

    with st.expander(
        "Deterministic Evaluation Details"
    ):
        st.json(
            deterministic
        )

    with st.expander(
        "Semantic Evaluation Details"
    ):
        if semantic is not None:
            st.json(
                semantic
            )

        else:
            st.write(
                "No semantic evaluation result available."
            )

    with st.expander(
        "Workflow State"
    ):
        st.json(
            workflow_state
        )

    with st.expander(
        "Interpreted Intent"
    ):
        st.json(
            result["intent"]
        )


