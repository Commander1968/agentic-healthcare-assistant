import re

from app.agents.healthcare_graph import build_graph
from app.agents.memory_follow_up import (
    synthesize_follow_up_from_validated_memory,
)
from app.agents.request_interpreter import interpret_request
from app.agents.response_synthesizer import synthesize_response
from app.agents.workflow_planner import (
    attach_execution_outcomes,
    build_execution_plan,
)
from app.evaluation.pipeline_evaluator import evaluate_pipeline_result
from app.evaluation.pipeline_logger import log_pipeline_run
from app.evaluation.memory_events import (
    build_memory_access_event,
    log_memory_access_events,
)
from app.evaluation.semantic_faithfulness_evaluator import (
    evaluate_semantic_faithfulness,
)
from app.evaluation.tool_events import build_tool_execution_events
from app.memory.patient_memory import patient_memory_store
from app.models.semantic_faithfulness_result import (
    SemanticEvaluationStatus,
)
from app.models.workflow_state import WorkflowState


def _persist_memory_access_event(**event_fields) -> dict:
    """Build and persist one metadata-only memory access event."""

    event = build_memory_access_event(**event_fields)
    log_memory_access_events([event])
    return event


def run_healthcare_assistant_detailed(
    user_request: str,
) -> dict:
    """
    Run the complete healthcare-assistant workflow and return
    an inspectable application result.

    The detailed result is intended for evaluation, observability,
    testing, and the future Streamlit interface.
    """

    intent = interpret_request(user_request)

    execution_plan = build_execution_plan(intent)

    graph = build_graph()

    graph_result = graph.invoke(
        intent.model_dump()
    )

    state = WorkflowState(**graph_result)

    planning = attach_execution_outcomes(
        execution_plan,
        state.model_dump(mode="json"),
    )

    tool_events = build_tool_execution_events(planning)

    response_text = synthesize_response(state)

    deterministic_evaluation = evaluate_pipeline_result(
        user_request,
        response_text,
        state,
    )

    semantic_evaluation = None
    semantic_evaluation_error = None

    if state.errors:
        semantic_evaluation_error = (
            "Semantic evaluation skipped because workflow errors made the "
            "response ineligible for acceptance."
        )
    else:
        try:
            semantic_evaluation = evaluate_semantic_faithfulness(
                user_request=user_request,
                response_text=response_text,
                state=state,
            )

        except Exception as exc:
            semantic_evaluation_error = (
                f"{type(exc).__name__}: {exc}"
            )

    semantic_evaluation_payload = (
        semantic_evaluation.model_dump(mode="json")
        if semantic_evaluation is not None
        else None
    )

    deterministic_passed = bool(
        deterministic_evaluation.get("passed", False)
    )

    semantic_passed = (
        semantic_evaluation is not None
        and semantic_evaluation.status
        == SemanticEvaluationStatus.PASS
        and semantic_evaluation.overall_semantic_faithfulness
    )

    accepted_for_memory = (
        deterministic_passed
        and semantic_passed
    )

    memory = None
    memory_persistence_error = None

    if accepted_for_memory:
        specialty = (
            state.selected_doctor.specialty
            if state.selected_doctor is not None
            else None
        )

        appointment_id = (
            state.appointment.appointment_id
            if state.appointment is not None
            else None
        )

        try:
            memory = patient_memory_store.remember(
                patient_id=state.patient_id,
                user_request=user_request,
                assistant_response=response_text,
                specialty=specialty,
                appointment_id=appointment_id,
            )
        except (OSError, ValueError) as exc:
            memory_persistence_error = f"{type(exc).__name__}: {exc}"
            accepted_for_memory = False

    if memory is not None:
        memory_events = [
            build_memory_access_event(
                action="WRITE",
                patient_id=state.patient_id,
                status="SUCCESS",
                reason_code="evaluation_accepted_and_persisted",
                stored_turn_count=len(memory.turns),
            )
        ]
    elif memory_persistence_error is not None:
        memory_events = [
            build_memory_access_event(
                action="WRITE",
                patient_id=state.patient_id,
                status="FAILURE",
                reason_code="memory_persistence_failed",
            )
        ]
    else:
        memory_events = [
            build_memory_access_event(
                action="SKIP",
                patient_id=state.patient_id,
                status="SKIPPED",
                reason_code="evaluation_gate_rejected",
            )
        ]

    memory_payload = (
        memory.model_dump(mode="json")
        if memory is not None
        else None
    )

    run_result = {
        "user_request": user_request,
        "intent": intent.model_dump(mode="json"),
        "planning": planning,
        "tool_events": tool_events,
        "workflow_state": state.model_dump(mode="json"),
        "response": response_text,
        "deterministic_evaluation": deterministic_evaluation,
        "semantic_evaluation": semantic_evaluation_payload,
        "semantic_evaluation_error": semantic_evaluation_error,
        "accepted_for_memory": accepted_for_memory,
        "memory": memory_payload,
        "memory_persistence_error": memory_persistence_error,
        "memory_events": memory_events,
    }

    log_pipeline_run(run_result)
    log_memory_access_events(memory_events)

    return run_result


def run_healthcare_assistant(
    user_request: str,
) -> str:
    """
    Preserve the original simple application interface.

    Existing callers receive only the final response text while
    richer callers can use run_healthcare_assistant_detailed().
    """

    result = run_healthcare_assistant_detailed(
        user_request
    )

    return result["response"]


def answer_follow_up_from_memory(
    patient_id: str,
    user_request: str,
) -> str | None:
    """
    Resolve a narrow set of follow-up questions from validated
    patient memory without rerunning the full healthcare workflow.
    """

    explicit_patient_ids = {
        match.upper()
        for match in re.findall(
            r"\bP\d{3,}\b",
            user_request,
            flags=re.IGNORECASE,
        )
    }
    if explicit_patient_ids and explicit_patient_ids != {patient_id.upper()}:
        _persist_memory_access_event(
            action="SKIP",
            patient_id=patient_id,
            status="SKIPPED",
            reason_code="explicit_patient_scope_mismatch",
        )
        return None

    memory = patient_memory_store.recall(patient_id)

    if memory is None:
        _persist_memory_access_event(
            action="SKIP",
            patient_id=patient_id,
            status="SKIPPED",
            reason_code="patient_memory_not_found",
        )
        return None

    normalized_request = user_request.lower().strip()

    if (
        "what time" in normalized_request
        and "appointment" in normalized_request
    ):
        if memory.turns:
            for turn in reversed(memory.turns):
                response_lower = (
                    turn.assistant_response.lower()
                )

                if "scheduled" in response_lower:
                    try:
                        response = synthesize_follow_up_from_validated_memory(
                            patient_id=patient_id,
                            user_request=user_request,
                            memory=memory,
                            relevant_turn=turn,
                        )
                    except ValueError:
                        _persist_memory_access_event(
                            action="SKIP",
                            patient_id=patient_id,
                            status="SKIPPED",
                            reason_code="memory_context_validation_failed",
                        )
                        return None
                    except Exception:
                        _persist_memory_access_event(
                            action="READ",
                            patient_id=patient_id,
                            status="FAILURE",
                            reason_code="memory_follow_up_generation_failed",
                            stored_turn_count=len(memory.turns),
                        )
                        raise

                    _persist_memory_access_event(
                        action="READ",
                        patient_id=patient_id,
                        status="SUCCESS",
                        reason_code="validated_turn_supplied_to_follow_up_prompt",
                        stored_turn_count=len(memory.turns),
                    )
                    return response

        _persist_memory_access_event(
            action="SKIP",
            patient_id=patient_id,
            status="SKIPPED",
            reason_code="relevant_appointment_turn_not_found",
            stored_turn_count=len(memory.turns),
        )
        return None

    if (
        "who is" in normalized_request
        and "doctor" in normalized_request
    ):
        if memory.turns:
            for turn in reversed(memory.turns):
                response_lower = (
                    turn.assistant_response.lower()
                )

                if (
                    memory.last_specialty
                    and memory.last_specialty.lower()
                    in response_lower
                ):
                    try:
                        response = synthesize_follow_up_from_validated_memory(
                            patient_id=patient_id,
                            user_request=user_request,
                            memory=memory,
                            relevant_turn=turn,
                        )
                    except ValueError:
                        _persist_memory_access_event(
                            action="SKIP",
                            patient_id=patient_id,
                            status="SKIPPED",
                            reason_code="memory_context_validation_failed",
                        )
                        return None
                    except Exception:
                        _persist_memory_access_event(
                            action="READ",
                            patient_id=patient_id,
                            status="FAILURE",
                            reason_code="memory_follow_up_generation_failed",
                            stored_turn_count=len(memory.turns),
                        )
                        raise

                    _persist_memory_access_event(
                        action="READ",
                        patient_id=patient_id,
                        status="SUCCESS",
                        reason_code="validated_turn_supplied_to_follow_up_prompt",
                        stored_turn_count=len(memory.turns),
                    )
                    return response

        _persist_memory_access_event(
            action="SKIP",
            patient_id=patient_id,
            status="SKIPPED",
            reason_code="relevant_doctor_turn_not_found",
            stored_turn_count=len(memory.turns),
        )
        return None

    _persist_memory_access_event(
        action="SKIP",
        patient_id=patient_id,
        status="SKIPPED",
        reason_code="unsupported_memory_follow_up",
        stored_turn_count=len(memory.turns),
    )
    return None


def run_healthcare_assistant_with_memory(
    user_request: str,
    patient_id: str = "P001",
) -> str:
    """
    Attempt a narrow memory-based follow-up first.
    If memory cannot safely resolve the request, use the full
    healthcare-assistant pipeline.
    """

    memory_response = answer_follow_up_from_memory(
        patient_id=patient_id,
        user_request=user_request,
    )

    if memory_response is not None:
        return memory_response

    return run_healthcare_assistant(
        user_request
    )
