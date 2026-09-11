from app.memory.patient_memory import PatientMemoryStore


def run_memory_test():
    store = PatientMemoryStore(max_turns=2)

    print("=" * 72)
    print("PATIENT MEMORY TEST")
    print("=" * 72)

    first_memory = store.remember(
        patient_id="P001",
        user_request=(
            "Book a nephrologist for my father."
        ),
        assistant_response=(
            "A nephrology appointment was scheduled."
        ),
        specialty="Nephrology",
        appointment_id="A001",
    )

    assert first_memory.patient_id == "P001"
    assert len(first_memory.turns) == 1
    assert first_memory.last_specialty == "Nephrology"
    assert first_memory.last_appointment_id == "A001"

    recalled = store.recall("P001")

    assert recalled is not None
    assert recalled.patient_id == "P001"
    assert recalled.last_specialty == "Nephrology"
    assert recalled.last_appointment_id == "A001"

    store.remember(
        patient_id="P001",
        user_request="What time is his appointment?",
        assistant_response=(
            "The appointment is scheduled for "
            "2026-09-02 09:00."
        ),
    )

    store.remember(
        patient_id="P001",
        user_request="Who is the doctor?",
        assistant_response="The doctor is Sarah Chen.",
    )

    recalled = store.recall("P001")

    assert recalled is not None
    assert len(recalled.turns) == 2

    assert (
        recalled.turns[0].user_request
        == "What time is his appointment?"
    )

    assert (
        recalled.turns[1].user_request
        == "Who is the doctor?"
    )

    assert store.clear("P001") is True
    assert store.recall("P001") is None

    print("Patient memory creation: PASS")
    print("Patient memory recall:   PASS")
    print("Bounded turn retention:  PASS")
    print("Patient memory clear:    PASS")
    print("=" * 72)
    print("MEMORY COMPONENT RESULT: PASS")


if __name__ == "__main__":
    run_memory_test()