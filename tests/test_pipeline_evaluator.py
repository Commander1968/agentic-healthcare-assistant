from app.evaluation.pipeline_evaluator import (
    appointment_time_matches,
    evaluate_pipeline_result,
)
from app.models.workflow_state import WorkflowState


def test_appointment_time_accepts_generated_long_date_format():
    response = (
        "Appointment Time: September 2, 2026, at 09:00"
    )

    assert appointment_time_matches(
        "2026-09-02 09:00",
        response,
    )


def test_appointment_time_rejects_incorrect_time():
    response = (
        "Appointment Time: September 2, 2026, at 10:00"
    )

    assert not appointment_time_matches(
        "2026-09-02 09:00",
        response,
    )


def test_summary_only_workflow_passes_without_creating_appointment():
    state = WorkflowState(
        patient_id="P001",
        appointment_requested=False,
    )

    result = evaluate_pipeline_result(
        user_request="Summarize patient information. Do not book an appointment.",
        response_text="Patient summary. No appointment was created.",
        state=state,
    )

    assert result["appointment_requested"] is False
    assert result["appointment_created"] is False
    assert result["contains_appointment_language"] is True
    assert result["appointment_outcome_consistent"] is True


def test_booking_workflow_requires_created_appointment():
    state = WorkflowState(
        patient_id="P001",
        appointment_requested=True,
    )

    result = evaluate_pipeline_result(
        user_request="Book an appointment.",
        response_text="No appointment was created.",
        state=state,
    )

    assert result["appointment_requested"] is True
    assert result["appointment_created"] is False
    assert result["appointment_outcome_consistent"] is False
