from app.agents.assistant_pipeline import run_healthcare_assistant_detailed
from app.agents.healthcare_graph import END, route_after_knowledge
from app.agents.workflow_planner import (
    attach_execution_outcomes,
    build_execution_plan,
)
from app.evaluation.tool_events import build_tool_execution_events
from app.models.request_intent import RequestIntent
from app.models.workflow_state import WorkflowState
from app.ui.evaluation_metrics import build_evaluation_metrics


def summary_intent() -> RequestIntent:
    return RequestIntent(
        patient_id="P001",
        requested_specialty="",
        reason="Summarize diagnosis, medication, treatment notes, and alerts",
        appointment_requested=False,
    )


def test_summary_only_intent_routes_directly_to_end_after_retrieval():
    state = WorkflowState(**summary_intent().model_dump())

    assert route_after_knowledge(state) == END


def test_booking_intent_routes_to_doctor_search():
    state = WorkflowState(
        patient_id="P001",
        requested_specialty="Nephrology",
        reason="Book a nephrologist",
        appointment_requested=True,
    )

    assert route_after_knowledge(state) == "find_doctors"


def test_summary_plan_marks_scheduling_steps_skipped_not_failed():
    plan = build_execution_plan(summary_intent())
    completed = attach_execution_outcomes(
        plan,
        {
            "patient": {"patient_id": "P001"},
            "medical_record": {"record_id": "R001"},
            "patient_summaries": [{"record_id": "R001"}],
            "retrieved_documents": [{"id": "ckd"}],
            "matching_doctors": [],
            "appointment": None,
            "errors": [],
        },
    )

    assert [step["status"] for step in completed["steps"]] == [
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "COMPLETED",
        "SKIPPED",
        "SKIPPED",
    ]
    assert completed["all_steps_completed"] is True

    events = build_tool_execution_events(completed)
    assert [event["status"] for event in events] == [
        "SUCCESS",
        "SUCCESS",
        "SUCCESS",
        "SUCCESS",
        "SKIPPED",
        "SKIPPED",
    ]

    metrics = build_evaluation_metrics(
        {
            "deterministic_evaluation": {"passed": True},
            "semantic_evaluation": {"status": "PASS"},
            "accepted_for_memory": True,
            "planning": completed,
        }
    )
    assert metrics["tool_success"] == {
        "attempted": 4,
        "successful": 4,
        "failed": 0,
        "success_rate": 1.0,
        "success_rate_display": "100%",
    }


def test_workflow_errors_skip_semantic_model_evaluation(monkeypatch):
    class ErrorGraph:
        def invoke(self, _payload):
            return WorkflowState(
                patient_id="P001",
                appointment_requested=False,
                errors=["Controlled workflow failure"],
            ).model_dump(mode="json")

    semantic_calls = []

    monkeypatch.setattr(
        "app.agents.assistant_pipeline.interpret_request",
        lambda _request: summary_intent(),
    )
    monkeypatch.setattr(
        "app.agents.assistant_pipeline.build_graph",
        lambda: ErrorGraph(),
    )
    monkeypatch.setattr(
        "app.agents.assistant_pipeline.synthesize_response",
        lambda _state: "The workflow could not be completed.",
    )
    monkeypatch.setattr(
        "app.agents.assistant_pipeline.evaluate_pipeline_result",
        lambda *_args: {"passed": False},
    )
    monkeypatch.setattr(
        "app.agents.assistant_pipeline.evaluate_semantic_faithfulness",
        lambda **_kwargs: semantic_calls.append(True),
    )
    monkeypatch.setattr(
        "app.agents.assistant_pipeline.log_pipeline_run",
        lambda _result: None,
    )

    result = run_healthcare_assistant_detailed("Summary only")

    assert semantic_calls == []
    assert result["semantic_evaluation"] is None
    assert result["semantic_evaluation_error"].startswith(
        "Semantic evaluation skipped"
    )
    assert result["accepted_for_memory"] is False

