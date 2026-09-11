from app.agents.workflow_planner import (
    attach_execution_outcomes,
    build_execution_plan,
)
from app.models.request_intent import RequestIntent


def test_planner_decomposes_intent_into_actual_graph_tools():
    intent = RequestIntent(
        patient_id="P001",
        requested_specialty="Nephrology",
        reason="Book nephrology and summarize current treatment",
        appointment_requested=True,
    )

    plan = build_execution_plan(intent)

    assert plan["goal"] == intent.reason
    assert plan["planning_basis"] == "Structured RequestIntent"
    assert plan["execution_framework"] == "LangGraph"
    assert [step["step"] for step in plan["steps"]] == [1, 2, 3, 4, 5, 6]
    assert [step["graph_node"] for step in plan["steps"]] == [
        "retrieve_patient",
        "retrieve_medical_record",
        "retrieve_patient_summary",
        "retrieve_knowledge",
        "find_doctors",
        "book_appointment",
    ]
    assert [step["tool"] for step in plan["steps"]] == [
        "get_patient_by_id",
        "get_medical_record_by_patient",
        "search_patient_summaries",
        "search_medlineplus / search_knowledge fallback",
        "find_doctors_by_specialty",
        "book_appointment",
    ]
    assert all(step["status"] == "PLANNED" for step in plan["steps"])
    assert plan["steps"][4]["capability"] == "Doctor Schedule API adapter lookup"
    assert plan["steps"][5]["capability"] == (
        "Doctor Schedule API adapter booking (deterministic demo)"
    )


def test_planner_outcomes_correspond_to_workflow_state():
    plan = build_execution_plan(
        RequestIntent(
            patient_id="P001",
            requested_specialty="Nephrology",
            reason="Book nephrology",
            appointment_requested=True,
        )
    )
    state = {
        "patient": {"patient_id": "P001"},
        "medical_record": {"record_id": "R001"},
        "patient_summaries": [{"record_id": "R001"}],
        "retrieved_documents": [{"id": "ckd_overview"}],
        "matching_doctors": [{"doctor_id": "D001"}],
        "appointment": {"appointment_id": "A001"},
        "errors": [],
    }

    completed = attach_execution_outcomes(plan, state)

    assert completed["all_steps_completed"] is True
    assert all(
        step["status"] == "COMPLETED"
        for step in completed["steps"]
    )
    assert all(
        step["execution_evidence"].endswith("populated")
        for step in completed["steps"]
    )
    assert all(step["status"] == "PLANNED" for step in plan["steps"])


def test_planner_exposes_an_incomplete_execution_step():
    plan = build_execution_plan(
        RequestIntent(
            patient_id="P001",
            requested_specialty="Nephrology",
            reason="Book nephrology",
            appointment_requested=True,
        )
    )

    completed = attach_execution_outcomes(
        plan,
        {
            "patient": {"patient_id": "P001"},
            "medical_record": None,
            "patient_summaries": [],
            "retrieved_documents": [],
            "matching_doctors": [],
            "appointment": None,
            "errors": ["Medical record not found"],
        },
    )

    assert completed["all_steps_completed"] is False
    assert completed["steps"][1]["status"] == "NOT COMPLETED"
    assert completed["workflow_errors"] == ["Medical record not found"]
