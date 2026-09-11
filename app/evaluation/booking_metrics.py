import json
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.evaluation.pipeline_logger import LOG_FILE


class BookingSuccessMetrics(BaseModel):
    """Reproducible aggregate derived from persisted booking tool events."""

    model_config = ConfigDict(extra="forbid")

    metric_name: Literal[
        "appointment_booking_success_rate"
    ] = "appointment_booking_success_rate"
    successful_bookings: int = Field(ge=0)
    booking_attempts: int = Field(ge=0)
    failed_bookings: int = Field(ge=0)
    success_rate_percent: float | None = Field(default=None, ge=0, le=100)
    source_type: Literal[
        "persisted_tool_execution_events"
    ] = "persisted_tool_execution_events"
    source_file: str
    records_scanned: int = Field(ge=0)
    malformed_records_skipped: int = Field(ge=0)
    metric_definition: Literal[
        "successful book_appointment executions / book_appointment attempts"
    ] = (
        "successful book_appointment executions / "
        "book_appointment attempts"
    )

    @model_validator(mode="after")
    def validate_totals(self):
        if self.successful_bookings + self.failed_bookings != self.booking_attempts:
            raise ValueError("Booking metric totals are inconsistent.")
        if self.booking_attempts == 0 and self.success_rate_percent is not None:
            raise ValueError("A zero-attempt rate must be unavailable.")
        return self


def calculate_booking_success_metrics(
    records: Iterable[dict[str, Any]],
    *,
    source_file: str = str(LOG_FILE),
    malformed_records_skipped: int = 0,
) -> BookingSuccessMetrics:
    """Count only executed booking events; skipped steps are not attempts."""

    attempts = 0
    successes = 0
    failures = 0
    records_scanned = 0

    for record in records:
        records_scanned += 1
        for event in record.get("tool_events", []):
            if not isinstance(event, dict):
                continue
            if event.get("event_type") != "TOOL_EXECUTION":
                continue
            if event.get("tool") != "book_appointment":
                continue

            status = event.get("status")
            if status not in {"SUCCESS", "FAILURE"}:
                continue

            attempts += 1
            if status == "SUCCESS":
                successes += 1
            else:
                failures += 1

    rate = (
        round((successes / attempts) * 100, 2)
        if attempts
        else None
    )

    return BookingSuccessMetrics(
        successful_bookings=successes,
        booking_attempts=attempts,
        failed_bookings=failures,
        success_rate_percent=rate,
        source_file=source_file,
        records_scanned=records_scanned,
        malformed_records_skipped=malformed_records_skipped,
    )


def load_booking_success_metrics(
    log_file: Path = LOG_FILE,
) -> BookingSuccessMetrics:
    """Load valid JSON-object run records and report malformed rows."""

    records = []
    malformed = 0

    if log_file.exists():
        for line in log_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(record, dict):
                malformed += 1
                continue
            records.append(record)

    return calculate_booking_success_metrics(
        records,
        source_file=str(log_file),
        malformed_records_skipped=malformed,
    )
