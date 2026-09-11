import json
from pathlib import Path

from app.evaluation.booking_metrics import (
    calculate_booking_success_metrics,
    load_booking_success_metrics,
)
from app.ui.booking_metrics_view import build_booking_metric_view


def _run(status, *, event_type="TOOL_EXECUTION", tool="book_appointment"):
    return {
        "tool_events": [
            {
                "event_type": event_type,
                "tool": tool,
                "status": status,
            }
        ]
    }


def test_booking_success_rate_exposes_numerator_and_denominator():
    metrics = calculate_booking_success_metrics(
        [_run("SUCCESS"), _run("SUCCESS"), _run("FAILURE")]
    )

    assert metrics.successful_bookings == 2
    assert metrics.booking_attempts == 3
    assert metrics.failed_bookings == 1
    assert metrics.success_rate_percent == 66.67


def test_skipped_booking_step_is_not_an_attempt():
    metrics = calculate_booking_success_metrics(
        [_run("SKIPPED", event_type="TOOL_SKIPPED")]
    )

    assert metrics.booking_attempts == 0
    assert metrics.success_rate_percent is None


def test_unrelated_tools_are_excluded():
    metrics = calculate_booking_success_metrics(
        [_run("SUCCESS", tool="get_patient_by_id"), _run("FAILURE")]
    )

    assert metrics.booking_attempts == 1
    assert metrics.failed_bookings == 1


def test_zero_attempts_report_unavailable_rate():
    metrics = calculate_booking_success_metrics([])
    view = build_booking_metric_view(metrics)

    assert view["success_rate"] == "N/A"
    assert view["booking_attempts"] == 0


def test_jsonl_loader_skips_malformed_rows(tmp_path):
    log_file = tmp_path / "pipeline_runs.jsonl"
    log_file.write_text(
        json.dumps(_run("SUCCESS"))
        + "\nnot-json\n"
        + json.dumps(["not", "a", "record"])
        + "\n",
        encoding="utf-8",
    )

    metrics = load_booking_success_metrics(log_file)

    assert metrics.booking_attempts == 1
    assert metrics.successful_bookings == 1
    assert metrics.records_scanned == 1
    assert metrics.malformed_records_skipped == 2


def test_ui_projection_displays_formula_and_provenance():
    metrics = calculate_booking_success_metrics([_run("SUCCESS")])
    view = build_booking_metric_view(metrics)

    assert view["success_rate"] == "100.00%"
    assert view["formula"].startswith("successful book_appointment")
    assert view["source"] == "persisted_tool_execution_events"


def test_booking_metric_panel_is_independent_of_current_run():
    source = Path("app/ui/streamlit_app.py").read_text(encoding="utf-8")

    metric_position = source.index(
        'st.subheader("Operational Performance")'
    )
    current_run_guard_position = source.index(
        "if st.session_state.last_run is not None:"
    )

    assert metric_position < current_run_guard_position
