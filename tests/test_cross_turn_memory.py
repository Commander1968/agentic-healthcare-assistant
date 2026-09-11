import json

from app.agents.assistant_pipeline import (
    run_healthcare_assistant_detailed,
    run_healthcare_assistant_with_memory,
)
from app.memory.patient_memory import (
    patient_memory_store,
)


INITIAL_REQUEST = (
    "Book a nephrologist for my 70-year-old father with CKD "
    "and summarize his current treatment."
)

FOLLOW_UP_REQUEST = (
    "What time is his appointment?"
)


def run_cross_turn_memory_test():
    print("=" * 72)
    print("CROSS-TURN MEMORY CONSUMPTION TEST")
    print("=" * 72)

    patient_memory_store.clear_all()

    initial_result = run_healthcare_assistant_detailed(
        INITIAL_REQUEST
    )

    if not initial_result["accepted_for_memory"]:
        print("\nINITIAL MEMORY ACCEPTANCE DIAGNOSTIC")
        print("=" * 72)

        print("DETERMINISTIC EVALUATION:")
        print(
            json.dumps(
                initial_result["deterministic_evaluation"],
                indent=2,
                default=str,
            )
        )

        print("\nSEMANTIC EVALUATION:")
        print(
            json.dumps(
                initial_result["semantic_evaluation"],
                indent=2,
                default=str,
            )
        )

        print(
            "\nSEMANTIC ERROR:",
            initial_result["semantic_evaluation_error"],
        )

        print("=" * 72)

    assert (
        initial_result["accepted_for_memory"]
        is True
    )

    memory_before_follow_up = (
        patient_memory_store.recall("P001")
    )

    assert memory_before_follow_up is not None

    follow_up_response = (
        run_healthcare_assistant_with_memory(
            FOLLOW_UP_REQUEST,
            patient_id="P001",
        )
    )

    assert follow_up_response

    assert (
        "2026-09-02 09:00"
        in follow_up_response
    )

    memory_after_follow_up = (
        patient_memory_store.recall("P001")
    )

    assert memory_after_follow_up is not None

    assert (
        memory_after_follow_up.last_appointment_id
        == "A001"
    )

    print(
        "Initial validated memory write: PASS"
    )
    print(
        "Follow-up memory resolution:    PASS"
    )
    print(
        "Appointment context retained:   PASS"
    )
    print("=" * 72)
    print(
        "CROSS-TURN MEMORY RESULT: PASS"
    )


if __name__ == "__main__":
    run_cross_turn_memory_test()