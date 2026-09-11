import json

from app.agents.assistant_pipeline import (
    run_healthcare_assistant_detailed,
)
from app.memory.patient_memory import (
    patient_memory_store,
)


USER_REQUEST = (
    "Book a nephrologist for my 70-year-old father with CKD "
    "and summarize his current treatment."
)


def run_pipeline_integration_test():
    print("=" * 72)
    print("PRODUCTION PIPELINE INTEGRATION TEST")
    print("=" * 72)

    patient_memory_store.clear_all()

    result = run_healthcare_assistant_detailed(
        USER_REQUEST
    )

    print(
        "Response generated:       ",
        bool(result["response"]),
    )

    print(
        "Deterministic evaluation:",
        result["deterministic_evaluation"]["passed"],
    )

    semantic = result["semantic_evaluation"]

    print(
        "Semantic evaluation:     ",
        (
            semantic["status"]
            if semantic is not None
            else "ERROR"
        ),
    )

    print(
        "Accepted for memory:     ",
        result["accepted_for_memory"],
    )

    recalled = patient_memory_store.recall("P001")

    print(
        "Memory recalled:         ",
        recalled is not None,
    )

    assert result["response"]

    if not result["deterministic_evaluation"]["passed"]:
        print("\nDETERMINISTIC FAILURE DIAGNOSTIC")
        print("=" * 72)
        print(
            json.dumps(
                result["deterministic_evaluation"],
                indent=2,
                default=str,
            )
        )
        print("=" * 72)

    assert (
        result["deterministic_evaluation"]["passed"]
        is True
    )

    assert (
        result["semantic_evaluation_error"]
        is None
    )

    assert semantic is not None

    assert semantic["status"] == "PASS"

    assert (
        semantic["overall_semantic_faithfulness"]
        is True
    )

    assert result["accepted_for_memory"] is True

    assert recalled is not None

    assert recalled.patient_id == "P001"

    assert len(recalled.turns) == 1

    assert (
        recalled.last_specialty
        == "Nephrology"
    )

    assert (
        recalled.last_appointment_id
        == "A001"
    )

    print("=" * 72)
    print("PIPELINE INTEGRATION RESULT: PASS")


if __name__ == "__main__":
    run_pipeline_integration_test()