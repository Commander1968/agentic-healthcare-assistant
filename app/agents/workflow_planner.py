from copy import deepcopy
from typing import Any

from app.models.request_intent import RequestIntent


WORKFLOW_SUB_GOALS = (
    {
        "step": 1,
        "sub_goal": "Identify the patient and load patient context",
        "graph_node": "retrieve_patient",
        "tool": "get_patient_by_id",
        "capability": "Patient DB lookup",
        "evidence_field": "patient",
    },
    {
        "step": 2,
        "sub_goal": "Retrieve the patient's medical history",
        "graph_node": "retrieve_medical_record",
        "tool": "get_medical_record_by_patient",
        "capability": "EHR / Patient DB lookup",
        "evidence_field": "medical_record",
    },
    {
        "step": 3,
        "sub_goal": "Retrieve the patient-scoped longitudinal summary",
        "graph_node": "retrieve_patient_summary",
        "tool": "search_patient_summaries",
        "capability": "Patient-scoped FAISS summary retrieval",
        "evidence_field": "patient_summaries",
    },
    {
        "step": 4,
        "sub_goal": "Retrieve relevant medical information",
        "graph_node": "retrieve_knowledge",
        "tool": "search_medlineplus / search_knowledge fallback",
        "capability": "Trusted external retrieval with FAISS fallback",
        "evidence_field": "retrieved_documents",
    },
    {
        "step": 5,
        "sub_goal": "Find a doctor matching the requested specialty",
        "graph_node": "find_doctors",
        "tool": "find_doctors_by_specialty",
        "capability": "Doctor Schedule API adapter lookup",
        "evidence_field": "matching_doctors",
    },
    {
        "step": 6,
        "sub_goal": "Book the selected appointment",
        "graph_node": "book_appointment",
        "tool": "book_appointment",
        "capability": "Doctor Schedule API adapter booking (deterministic demo)",
        "evidence_field": "appointment",
    },
)


def build_execution_plan(intent: RequestIntent) -> dict[str, Any]:
    """Create the explicit pre-execution plan from interpreted intent."""

    return {
        "goal": intent.reason,
        "patient_id": intent.patient_id,
        "requested_specialty": intent.requested_specialty,
        "planning_basis": "Structured RequestIntent",
        "execution_framework": "LangGraph",
        "appointment_requested": intent.appointment_requested,
        "steps": [
            {
                **deepcopy(step),
                "required": (
                    True
                    if step["graph_node"] not in {"find_doctors", "book_appointment"}
                    else intent.appointment_requested
                ),
                "status": (
                    "PLANNED"
                    if step["graph_node"] not in {"find_doctors", "book_appointment"}
                    or intent.appointment_requested
                    else "NOT REQUIRED"
                ),
                "execution_evidence": (
                    None
                    if step["graph_node"] not in {"find_doctors", "book_appointment"}
                    or intent.appointment_requested
                    else "Skipped because appointment_requested is false"
                ),
            }
            for step in WORKFLOW_SUB_GOALS
        ],
    }


def attach_execution_outcomes(
    plan: dict[str, Any],
    workflow_state: dict[str, Any],
) -> dict[str, Any]:
    """Project post-run state onto the plan without changing execution."""

    completed_plan = deepcopy(plan)
    errors = workflow_state.get("errors", [])

    for step in completed_plan["steps"]:
        if not step.get("required", True):
            step["status"] = "SKIPPED"
            step["execution_evidence"] = (
                "Skipped because appointment_requested is false"
            )
            continue

        evidence_field = step["evidence_field"]
        evidence_value = workflow_state.get(evidence_field)
        completed = bool(evidence_value)

        step["status"] = "COMPLETED" if completed else "NOT COMPLETED"
        step["execution_evidence"] = (
            f"workflow_state.{evidence_field} populated"
            if completed
            else f"workflow_state.{evidence_field} not populated"
        )

    completed_plan["workflow_errors"] = list(errors)
    completed_plan["all_steps_completed"] = all(
        step["status"] in {"COMPLETED", "SKIPPED"}
        for step in completed_plan["steps"]
    )

    return completed_plan
