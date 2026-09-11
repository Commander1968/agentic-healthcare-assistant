from typing import Any

from app.evaluation.booking_metrics import BookingSuccessMetrics


def build_booking_metric_view(
    metrics: BookingSuccessMetrics,
) -> dict[str, Any]:
    """Create an explicit numerator/denominator UI projection."""

    rate = metrics.success_rate_percent
    return {
        "success_rate": "N/A" if rate is None else f"{rate:.2f}%",
        "successful_bookings": metrics.successful_bookings,
        "booking_attempts": metrics.booking_attempts,
        "failed_bookings": metrics.failed_bookings,
        "formula": metrics.metric_definition,
        "source": metrics.source_type,
        "records_scanned": metrics.records_scanned,
        "malformed_records_skipped": metrics.malformed_records_skipped,
    }
