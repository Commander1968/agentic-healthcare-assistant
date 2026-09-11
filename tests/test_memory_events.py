import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.memory_events import (
    MemoryAccessEvent,
    build_memory_access_event,
    load_recent_memory_access_events,
    log_memory_access_events,
)
from app.ui.memory_trace import build_memory_trace_rows


FIXED_TIME = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def _event(action="READ", status="SUCCESS", reason="validated_lookup"):
    return build_memory_access_event(
        action=action,
        patient_id="P001",
        status=status,
        reason_code=reason,
        stored_turn_count=1,
        timestamp_utc=FIXED_TIME,
    )


def test_memory_event_contains_timestamp_scope_and_provenance():
    event = _event()

    assert event["timestamp_utc"] == "2026-09-06T12:00:00Z"
    assert event["event_type"] == "MEMORY_ACCESS"
    assert event["patient_id"] == "P001"
    assert event["source_component"] == "PatientMemoryStore"
    assert event["validation_basis"] == "deterministic_and_semantic_acceptance"
    assert event["content_exposed"] is False


@pytest.mark.parametrize(
    ("action", "status"),
    [("READ", "SUCCESS"), ("WRITE", "SUCCESS"), ("SKIP", "SKIPPED")],
)
def test_memory_event_supports_required_actions(action, status):
    assert _event(action=action, status=status)["action"] == action


def test_memory_event_rejects_request_or_response_content():
    event = _event()
    event["assistant_response"] = "Sensitive response text"

    with pytest.raises(ValidationError):
        MemoryAccessEvent.model_validate(event)


def test_memory_event_requires_timezone_aware_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        build_memory_access_event(
            action="READ",
            patient_id="P001",
            status="SUCCESS",
            reason_code="validated_lookup",
            timestamp_utc=datetime(2026, 9, 6, 12, 0),
        )


def test_memory_event_log_round_trip(tmp_path):
    log_file = tmp_path / "memory_events.jsonl"
    events = [_event("READ"), _event("WRITE")]

    log_memory_access_events(events, log_file=log_file)

    assert load_recent_memory_access_events(
        limit=20,
        log_file=log_file,
    ) == events


def test_recent_event_loader_applies_limit(tmp_path):
    log_file = tmp_path / "memory_events.jsonl"
    events = [_event("READ"), _event("WRITE"), _event("SKIP", "SKIPPED")]
    log_memory_access_events(events, log_file=log_file)

    assert load_recent_memory_access_events(
        limit=2,
        log_file=log_file,
    ) == events[-2:]


def test_loader_ignores_content_rich_or_malformed_rows(tmp_path):
    log_file = tmp_path / "memory_events.jsonl"
    invalid = _event()
    invalid["user_request"] = "Do not expose this"
    log_file.write_text(
        json.dumps(invalid) + "\nnot-json\n" + json.dumps(_event("WRITE")) + "\n",
        encoding="utf-8",
    )

    loaded = load_recent_memory_access_events(limit=20, log_file=log_file)

    assert len(loaded) == 1
    assert loaded[0]["action"] == "WRITE"


def test_ui_projection_allow_lists_metadata_fields():
    event = _event()
    event["user_request"] = "must not display"
    event["assistant_response"] = "must not display"

    rows = build_memory_trace_rows([event])

    assert rows[0]["Patient ID"] == "P001"
    assert rows[0]["Content Exposed"] is False
    assert "user_request" not in rows[0]
    assert "assistant_response" not in rows[0]
    assert "must not display" not in str(rows[0])


def test_memory_trace_is_rendered_before_current_run_guard():
    source = Path("app/ui/streamlit_app.py").read_text(encoding="utf-8")

    trace_position = source.index(
        'st.subheader("Memory Diagnostics")'
    )
    current_run_guard_position = source.index(
        "if st.session_state.last_run is not None:"
    )

    assert trace_position < current_run_guard_position
