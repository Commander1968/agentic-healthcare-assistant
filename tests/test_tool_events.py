import json

from app.evaluation.pipeline_logger import log_pipeline_run
from app.evaluation.tool_events import build_tool_execution_events


def test_tool_events_expose_ordered_success_details():
    events = build_tool_execution_events(
        {
            "steps": [
                {
                    "step": 1,
                    "tool": "get_patient_by_id",
                    "graph_node": "retrieve_patient",
                    "capability": "Patient DB lookup",
                    "status": "COMPLETED",
                    "execution_evidence": (
                        "workflow_state.patient populated"
                    ),
                },
                {
                    "step": 2,
                    "tool": "get_medical_record_by_patient",
                    "graph_node": "retrieve_medical_record",
                    "capability": "EHR / Patient DB lookup",
                    "status": "COMPLETED",
                    "execution_evidence": (
                        "workflow_state.medical_record populated"
                    ),
                },
            ]
        }
    )

    assert [event["sequence"] for event in events] == [1, 2]
    assert [event["status"] for event in events] == [
        "SUCCESS",
        "SUCCESS",
    ]
    assert events[0]["event_type"] == "TOOL_EXECUTION"
    assert events[0]["tool"] == "get_patient_by_id"
    assert events[0]["graph_node"] == "retrieve_patient"


def test_tool_events_expose_failure_evidence():
    events = build_tool_execution_events(
        {
            "steps": [
                {
                    "step": 1,
                    "tool": "get_patient_by_id",
                    "graph_node": "retrieve_patient",
                    "capability": "Patient DB lookup",
                    "status": "NOT COMPLETED",
                    "execution_evidence": (
                        "workflow_state.patient not populated"
                    ),
                }
            ]
        }
    )

    assert events[0]["status"] == "FAILURE"
    assert events[0]["execution_evidence"].endswith(
        "not populated"
    )


def test_pipeline_logger_persists_tool_events(tmp_path):
    log_file = tmp_path / "pipeline_runs.jsonl"
    record = {
        "user_request": "Book nephrology",
        "tool_events": [
            {
                "sequence": 1,
                "event_type": "TOOL_EXECUTION",
                "tool": "get_patient_by_id",
                "graph_node": "retrieve_patient",
                "capability": "Patient DB lookup",
                "status": "SUCCESS",
                "execution_evidence": (
                    "workflow_state.patient populated"
                ),
            }
        ],
    }

    log_pipeline_run(record, log_file=log_file)

    persisted = json.loads(
        log_file.read_text(encoding="utf-8").splitlines()[-1]
    )

    assert persisted["tool_events"] == record["tool_events"]