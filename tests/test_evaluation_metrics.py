from app.ui.evaluation_metrics import build_evaluation_metrics


def test_evaluation_metrics_report_model_and_tool_success():
    metrics = build_evaluation_metrics(
        {
            "deterministic_evaluation": {"passed": True},
            "semantic_evaluation": {"status": "PASS"},
            "accepted_for_memory": True,
            "planning": {
                "steps": [
                    {"status": "COMPLETED"},
                    {"status": "COMPLETED"},
                    {"status": "COMPLETED"},
                ]
            },
        }
    )

    assert metrics["model_response"] == {
        "deterministic": "PASS",
        "semantic": "PASS",
        "accepted_for_memory": "YES",
    }
    assert metrics["tool_success"] == {
        "attempted": 3,
        "successful": 3,
        "failed": 0,
        "success_rate": 1.0,
        "success_rate_display": "100%",
    }


def test_evaluation_metrics_count_incomplete_tools_as_failed():
    metrics = build_evaluation_metrics(
        {
            "deterministic_evaluation": {"passed": False},
            "semantic_evaluation": {"status": "FAIL"},
            "accepted_for_memory": False,
            "planning": {
                "steps": [
                    {"status": "COMPLETED"},
                    {"status": "NOT COMPLETED"},
                ]
            },
        }
    )

    assert metrics["model_response"]["deterministic"] == "FAIL"
    assert metrics["model_response"]["semantic"] == "FAIL"
    assert metrics["model_response"]["accepted_for_memory"] == "NO"
    assert metrics["tool_success"] == {
        "attempted": 2,
        "successful": 1,
        "failed": 1,
        "success_rate": 0.5,
        "success_rate_display": "50%",
    }


def test_evaluation_metrics_handle_no_tool_attempts_safely():
    metrics = build_evaluation_metrics(
        {
            "deterministic_evaluation": {},
            "semantic_evaluation": None,
            "accepted_for_memory": False,
            "planning": {"steps": []},
        }
    )

    assert metrics["model_response"] == {
        "deterministic": "FAIL",
        "semantic": "ERROR",
        "accepted_for_memory": "NO",
    }
    assert metrics["tool_success"] == {
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "success_rate": 0.0,
        "success_rate_display": "0%",
    }
