import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field


MEMORY_EVENT_LOG_FILE = Path("logs/memory_events.jsonl")


class MemoryAccessEvent(BaseModel):
    """Metadata-only trace of a patient-memory access decision."""

    model_config = ConfigDict(extra="forbid")

    timestamp_utc: datetime
    event_type: Literal["MEMORY_ACCESS"] = "MEMORY_ACCESS"
    action: Literal["READ", "WRITE", "SKIP"]
    patient_id: str
    status: Literal["SUCCESS", "SKIPPED", "FAILURE"]
    source_type: Literal[
        "evaluation_approved_patient_memory"
    ] = "evaluation_approved_patient_memory"
    source_component: Literal["PatientMemoryStore"] = "PatientMemoryStore"
    validation_basis: Literal[
        "deterministic_and_semantic_acceptance"
    ] = "deterministic_and_semantic_acceptance"
    reason_code: str
    stored_turn_count: int | None = Field(default=None, ge=0)
    content_exposed: Literal[False] = False


def build_memory_access_event(
    *,
    action: Literal["READ", "WRITE", "SKIP"],
    patient_id: str,
    status: Literal["SUCCESS", "SKIPPED", "FAILURE"],
    reason_code: str,
    stored_turn_count: int | None = None,
    timestamp_utc: datetime | None = None,
) -> dict:
    """Build a validated event that cannot contain request/response content."""

    timestamp = timestamp_utc or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("Memory-event timestamp must be timezone-aware.")

    event = MemoryAccessEvent(
        timestamp_utc=timestamp.astimezone(timezone.utc),
        action=action,
        patient_id=patient_id,
        status=status,
        reason_code=reason_code,
        stored_turn_count=stored_turn_count,
    )
    return event.model_dump(mode="json")


def log_memory_access_events(
    events: Iterable[dict],
    log_file: Path = MEMORY_EVENT_LOG_FILE,
) -> None:
    """Append validated metadata-only events to the memory audit log."""

    validated_events = [
        MemoryAccessEvent.model_validate(event).model_dump(mode="json")
        for event in events
    ]
    if not validated_events:
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as handle:
        for event in validated_events:
            handle.write(json.dumps(event) + "\n")


def load_recent_memory_access_events(
    *,
    limit: int = 20,
    log_file: Path = MEMORY_EVENT_LOG_FILE,
) -> list[dict]:
    """Load recent valid events while refusing malformed or content-rich rows."""

    if limit < 1 or not log_file.exists():
        return []

    validated_events = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = MemoryAccessEvent.model_validate_json(line)
        except (ValueError, TypeError):
            continue
        validated_events.append(event.model_dump(mode="json"))

    return validated_events[-limit:]
