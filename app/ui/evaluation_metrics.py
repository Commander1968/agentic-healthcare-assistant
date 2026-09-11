from typing import Any


def build_evaluation_metrics(
    run_result: dict[str, Any],
) -> dict[str, Any]:
    """Build rubric-readable model and tool metrics from one run."""

    deterministic = run_result.get(
        "deterministic_evaluation",
        {},
    )
    semantic = run_result.get("semantic_evaluation")
    planning = run_result.get("planning", {})
    steps = planning.get("steps", [])

    attempted_steps = [
        step
        for step in steps
        if step.get("status") != "SKIPPED"
    ]
    attempted_tools = len(attempted_steps)
    successful_tools = sum(
        step.get("status") == "COMPLETED"
        for step in attempted_steps
    )
    failed_tools = attempted_tools - successful_tools
    success_rate = (
        successful_tools / attempted_tools
        if attempted_tools
        else 0.0
    )

    return {
        "model_response": {
            "deterministic": (
                "PASS"
                if deterministic.get("passed", False)
                else "FAIL"
            ),
            "semantic": (
                semantic.get("status", "ERROR")
                if semantic is not None
                else "ERROR"
            ),
            "accepted_for_memory": (
                "YES"
                if run_result.get("accepted_for_memory", False)
                else "NO"
            ),
        },
        "tool_success": {
            "attempted": attempted_tools,
            "successful": successful_tools,
            "failed": failed_tools,
            "success_rate": success_rate,
            "success_rate_display": f"{success_rate:.0%}",
        },
    }
