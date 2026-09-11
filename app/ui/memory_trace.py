from typing import Any


def build_memory_trace_rows(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Project allow-listed metadata into the clinician-visible trace."""

    return [
        {
            "Timestamp (UTC)": event.get("timestamp_utc"),
            "Action": event.get("action"),
            "Patient ID": event.get("patient_id"),
            "Outcome": event.get("status"),
            "Source": event.get("source_component"),
            "Validation Basis": event.get("validation_basis"),
            "Reason": event.get("reason_code"),
            "Stored Turns": event.get("stored_turn_count"),
            "Content Exposed": event.get("content_exposed", False),
        }
        for event in events
    ]
