from typing import Any


def build_tool_execution_events(
    planning: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create ordered, log-ready events from execution-plan outcomes."""

    events = []

    for step in planning.get("steps", []):
        if step.get("status") == "SKIPPED":
            events.append(
                {
                    "sequence": step.get("step"),
                    "event_type": "TOOL_SKIPPED",
                    "tool": step.get("tool"),
                    "graph_node": step.get("graph_node"),
                    "capability": step.get("capability"),
                    "status": "SKIPPED",
                    "execution_evidence": step.get("execution_evidence"),
                }
            )
            continue

        completed = step.get("status") == "COMPLETED"

        events.append(
            {
                "sequence": step.get("step"),
                "event_type": "TOOL_EXECUTION",
                "tool": step.get("tool"),
                "graph_node": step.get("graph_node"),
                "capability": step.get("capability"),
                "status": "SUCCESS" if completed else "FAILURE",
                "execution_evidence": step.get("execution_evidence"),
            }
        )

    return events
