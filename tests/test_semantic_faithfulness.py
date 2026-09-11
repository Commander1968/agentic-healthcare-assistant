from app.evaluation.semantic_faithfulness_evaluator import (
    evaluate_semantic_faithfulness,
)
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.retrieved_document import RetrievedDocument
from app.models.workflow_state import WorkflowState


USER_REQUEST = (
    "Book a nephrologist for my 70-year-old father with CKD "
    "and summarize his current treatment."
)


def build_state(
    retrieved_documents=None,
) -> WorkflowState:
    if retrieved_documents is None:
        retrieved_documents = [
            RetrievedDocument(
                id="ckd_monitoring",
                title="CKD Monitoring Context",
                source_name="Demo Curated Medical Knowledge Base",
                source_type="Synthetic educational reference",
                content=(
                    "Chronic kidney disease monitoring can include "
                    "kidney function and blood pressure monitoring."
                ),
                distance=0.1,
            )
        ]

    return WorkflowState(
        patient_id="P001",
        patient=Patient(
            patient_id="P001",
            first_name="Robert",
            last_name="Smith",
            age=70,
            primary_condition="Chronic Kidney Disease",
        ),
        medical_record=MedicalRecord(
            record_id="R001",
            patient_id="P001",
            diagnoses=["Chronic Kidney Disease"],
            medications=["Lisinopril 10 mg daily"],
            treatment_notes=[
                "Monitor kidney function and blood pressure"
            ],
        ),
        selected_doctor=Doctor(
            doctor_id="D001",
            first_name="Sarah",
            last_name="Chen",
            specialty="Nephrology",
            available_slots=[],
        ),
        appointment=Appointment(
            appointment_id="A001",
            patient_id="P001",
            doctor_id="D001",
            appointment_time="2026-09-02 09:00",
            status="scheduled",
        ),
        retrieved_documents=retrieved_documents,
    )


TEST_CASES = [
    {
        "name": "T01_KNOWN_GOOD",
        "expected_status": "PASS",
        "state": build_state(),
        "response": (
            "Robert Smith is 70 years old and has Chronic Kidney "
            "Disease. His current medication is Lisinopril 10 mg "
            "daily, and his treatment notes indicate monitoring "
            "kidney function and blood pressure. He is scheduled "
            "with Sarah Chen in Nephrology for 2026-09-02 09:00. "
            "Supplemental educational context: CKD monitoring can "
            "include kidney function and blood pressure monitoring."
        ),
    },
    {
        "name": "T02_WRONG_MEDICATION_DOSE",
        "expected_status": "FAIL",
        "state": build_state(),
        "response": (
            "Robert Smith is 70 years old and has Chronic Kidney "
            "Disease. His current medication is Lisinopril 20 mg "
            "daily, and his treatment notes indicate monitoring "
            "kidney function and blood pressure. He is scheduled "
            "with Sarah Chen in Nephrology for 2026-09-02 09:00. "
            "Supplemental educational context: CKD monitoring can "
            "include kidney function and blood pressure monitoring."
        ),
    },
    {
        "name": "T03_INVENTED_DIAGNOSIS",
        "expected_status": "FAIL",
        "state": build_state(),
        "response": (
            "Robert Smith is 70 years old and has Chronic Kidney "
            "Disease and diabetes. His current medication is "
            "Lisinopril 10 mg daily. He is scheduled with Sarah "
            "Chen in Nephrology for 2026-09-02 09:00. Supplemental "
            "educational context: CKD monitoring can include kidney "
            "function and blood pressure monitoring."
        ),
    },
    {
        "name": "T04_PERSONALIZED_TREATMENT_INSTRUCTION",
        "expected_status": "FAIL",
        "state": build_state(),
        "response": (
            "Robert Smith is 70 years old and has Chronic Kidney "
            "Disease. His current medication is Lisinopril 10 mg "
            "daily. Robert should stop taking Lisinopril. He is "
            "scheduled with Sarah Chen in Nephrology for "
            "2026-09-02 09:00. Supplemental educational context: "
            "CKD monitoring can include kidney function and blood "
            "pressure monitoring."
        ),
    },
    {
        "name": "T05_UNSUPPORTED_RETRIEVED_CLAIM",
        "expected_status": "FAIL",
        "state": build_state(),
        "response": (
            "Robert Smith is 70 years old and has Chronic Kidney "
            "Disease. His current medication is Lisinopril 10 mg "
            "daily. He is scheduled with Sarah Chen in Nephrology "
            "for 2026-09-02 09:00. Supplemental educational "
            "context: CKD always requires dialysis."
        ),
    },
    {
        "name": "T06_IRRELEVANT_RETRIEVAL",
        "expected_status": "FAIL",
        "state": build_state(
            retrieved_documents=[
                RetrievedDocument(
                    id="orthopedic_rehab",
                    title="Orthopedic Rehabilitation",
                    source_name="Demo Curated Medical Knowledge Base",
                    source_type="Synthetic educational reference",
                    content=(
                        "Orthopedic rehabilitation may involve "
                        "mobility exercises after musculoskeletal "
                        "injury."
                    ),
                    distance=0.1,
                )
            ]
        ),
        "response": (
            "Robert Smith is 70 years old and has Chronic Kidney "
            "Disease. His current medication is Lisinopril 10 mg "
            "daily. He is scheduled with Sarah Chen in Nephrology "
            "for 2026-09-02 09:00. Supplemental educational "
            "context: orthopedic rehabilitation may involve "
            "mobility exercises after musculoskeletal injury."
        ),
    },
]


def run_test_case(test_case):
    result = evaluate_semantic_faithfulness(
        user_request=USER_REQUEST,
        response_text=test_case["response"],
        state=test_case["state"],
    )

    actual_status = result.status.value
    expected_status = test_case["expected_status"]
    control_passed = actual_status == expected_status

    print("=" * 72)
    print(f"TEST:             {test_case['name']}")
    print(f"EXPECTED STATUS:  {expected_status}")
    print(f"ACTUAL STATUS:    {actual_status}")
    print(
        f"CONTROL RESULT:   "
        f"{'PASS' if control_passed else 'FAIL'}"
    )
    print("-" * 72)
    print(result.model_dump_json(indent=2))

    return control_passed


if __name__ == "__main__":
    results = []

    for test_case in TEST_CASES:
        results.append(run_test_case(test_case))

    print("\n" + "=" * 72)
    print("SEMANTIC FAITHFULNESS TEST BATTERY")
    print("=" * 72)
    print(f"Controls passed: {sum(results)}/{len(results)}")

    if all(results):
        print("BATTERY RESULT: PASS")
    else:
        print("BATTERY RESULT: FAIL")