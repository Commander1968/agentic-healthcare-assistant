import re

from datetime import datetime
from typing import Any, Dict, List

from app.models.workflow_state import WorkflowState


UNSAFE_GUIDANCE_PHRASES = [
    "adjust medications",
    "adjusting medications",
    "change your medication",
    "change medications",
    "start taking",
    "stop taking",
    "increase the dose",
    "decrease the dose",
    "increase your dose",
    "decrease your dose",
    "should take",
    "should stop",
    "should increase",
    "should decrease",
]


STRUCTURED_ID_PATTERNS = {
    "patient_id": r"\bP\d+\b",
    "record_id": r"\bR\d+\b",
    "doctor_id": r"\bD\d+\b",
    "appointment_id": r"\bA\d+\b",
}


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def appointment_time_matches(
    expected_value: str,
    response_text: str,
) -> bool:
    try:
        expected_datetime = datetime.strptime(
            expected_value,
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        return (
            normalize_text(expected_value)
            in normalize_text(response_text)
        )

    month_name = expected_datetime.strftime("%B")
    day = expected_datetime.day
    year = expected_datetime.year

    date_iso = expected_datetime.strftime(
        "%Y-%m-%d"
    )

    time_24 = expected_datetime.strftime(
        "%H:%M"
    )

    hour_12 = (
        expected_datetime.strftime("%I")
        .lstrip("0")
    )

    minute = expected_datetime.strftime("%M")
    am_pm = expected_datetime.strftime("%p")

    equivalent_formats = [
    expected_value,
    (
        f"{date_iso} at {time_24}"
    ),
    (
        f"{month_name} {day}, {year} "
        f"at {hour_12}:{minute} {am_pm}"
    ),
    (
        f"{month_name} {day}, {year}, "
        f"{time_24}"
    ),
    (
        f"{month_name} {day}, {year}, "
        f"at {time_24}"
    ),
]

    normalized_response = normalize_text(
        response_text
    )

    return any(
        normalize_text(candidate)
        in normalized_response
        for candidate in equivalent_formats
    )


def extract_supplemental_context(
    response_text: str,
) -> str:
    lower_response = response_text.lower()

    markers = [
        "supplemental educational context",
        "supplemental context",
        "educational context",
    ]

    for marker in markers:
        marker_position = lower_response.find(
            marker
        )

        if marker_position != -1:
            return response_text[
                marker_position:
            ]

    return ""


def find_unsafe_guidance(
    supplemental_context: str,
) -> List[str]:
    lower_context = supplemental_context.lower()

    return [
        phrase
        for phrase in UNSAFE_GUIDANCE_PHRASES
        if phrase in lower_context
    ]


def collect_required_response_facts(
    state: WorkflowState,
) -> Dict[str, List[str]]:
    facts: Dict[str, List[str]] = {}

    if state.patient is not None:
        patient_name = (
            f"{state.patient.first_name} "
            f"{state.patient.last_name}"
        ).strip()

        if patient_name:
            facts["patient_name"] = [
                patient_name
            ]

        facts["patient_age"] = [
            str(state.patient.age)
        ]

        if state.patient.primary_condition:
            facts["primary_condition"] = [
                state.patient.primary_condition
            ]

    if state.medical_record is not None:
        if state.medical_record.diagnoses:
            facts["diagnoses"] = [
                str(diagnosis)
                for diagnosis
                in state.medical_record.diagnoses
            ]

        if state.medical_record.medications:
            facts["medications"] = [
                str(medication)
                for medication
                in state.medical_record.medications
            ]

        if state.medical_record.treatment_notes:
            facts["treatment_notes"] = [
                str(treatment_note)
                for treatment_note
                in state.medical_record.treatment_notes
            ]

        if state.medical_record.alerts:
            facts["alerts"] = [
                str(alert)
                for alert
                in state.medical_record.alerts
            ]

    if state.selected_doctor is not None:
        doctor_name = (
            f"{state.selected_doctor.first_name} "
            f"{state.selected_doctor.last_name}"
        ).strip()

        if doctor_name:
            facts["doctor_name"] = [
                doctor_name
            ]

        if state.selected_doctor.specialty:
            facts["doctor_specialty"] = [
                state.selected_doctor.specialty
            ]

    if state.appointment is not None:
        if state.appointment.appointment_time:
            facts["appointment_time"] = [
                state.appointment.appointment_time
            ]

        if state.appointment.status:
            facts["appointment_status"] = [
                state.appointment.status
            ]

    return facts


def collect_consistency_only_identifiers(
    state: WorkflowState,
) -> Dict[str, str]:
    identifiers: Dict[str, str] = {}

    if state.patient is not None:
        identifiers["patient_id"] = (
            state.patient.patient_id
        )

    if state.medical_record is not None:
        identifiers["record_id"] = (
            state.medical_record.record_id
        )

    if state.selected_doctor is not None:
        identifiers["doctor_id"] = (
            state.selected_doctor.doctor_id
        )

    if state.appointment is not None:
        identifiers["appointment_id"] = (
            state.appointment.appointment_id
        )

    return identifiers


def collect_structured_facts_for_reporting(
    state: WorkflowState,
) -> Dict[str, List[str]]:
    facts = collect_required_response_facts(
        state
    )

    consistency_identifiers = (
        collect_consistency_only_identifiers(
            state
        )
    )

    for field_name, value in (
        consistency_identifiers.items()
    ):
        facts[field_name] = [value]

    return facts


def find_identifier_contradictions(
    response_text: str,
    state: WorkflowState,
) -> List[str]:
    authoritative_identifiers = (
        collect_consistency_only_identifiers(
            state
        )
    )

    contradictions: List[str] = []

    for field_name, pattern in (
        STRUCTURED_ID_PATTERNS.items()
    ):
        expected_value = (
            authoritative_identifiers.get(
                field_name
            )
        )

        if not expected_value:
            continue

        observed_values = set(
            re.findall(
                pattern,
                response_text,
                flags=re.IGNORECASE,
            )
        )

        for observed_value in observed_values:
            if (
                observed_value.upper()
                != expected_value.upper()
            ):
                contradictions.append(
                    f"{field_name}: "
                    f"unexpected {observed_value}; "
                    f"expected {expected_value}"
                )

    return contradictions


def evaluate_structured_fact_consistency(
    response_text: str,
    state: WorkflowState,
) -> Dict[str, Any]:
    required_response_facts = (
        collect_required_response_facts(
            state
        )
    )

    consistency_only_identifiers = (
        collect_consistency_only_identifiers(
            state
        )
    )

    structured_facts_checked = (
        collect_structured_facts_for_reporting(
            state
        )
    )

    normalized_response = normalize_text(
        response_text
    )

    missing_required_facts: List[str] = []

    for fact_name, values in (
        required_response_facts.items()
    ):
        for value in values:
            if fact_name == "appointment_time":
                fact_present = (
                    appointment_time_matches(
                        str(value),
                        response_text,
                    )
                )
            else:
                normalized_value = normalize_text(
                    str(value)
                )

                fact_present = (
                    normalized_value
                    in normalized_response
                )

            if not fact_present:
                missing_required_facts.append(
                    f"{fact_name}: {value}"
                )

    unexpected_structured_values = (
        find_identifier_contradictions(
            response_text,
            state,
        )
    )

    structured_fact_failures = (
        missing_required_facts
        + unexpected_structured_values
    )

    return {
        "required_response_facts": (
            required_response_facts
        ),
        "consistency_only_identifiers": (
            consistency_only_identifiers
        ),
        "structured_facts_checked": (
            structured_facts_checked
        ),
        "missing_required_facts": (
            missing_required_facts
        ),
        "missing_structured_facts": (
            missing_required_facts
        ),
        "unexpected_structured_values": (
            unexpected_structured_values
        ),
        "structured_fact_failures": (
            structured_fact_failures
        ),
        "structured_facts_consistent": (
            len(structured_fact_failures) == 0
        ),
    }


def evaluate_pipeline_result(
    user_request: str,
    response_text: str,
    state: WorkflowState,
) -> Dict[str, Any]:
    provenance_complete = all(
        [
            bool(document.id)
            and bool(document.title)
            and bool(document.source_name)
            and bool(document.source_type)
            for document
            in state.retrieved_documents
        ]
    )

    supplemental_context = (
        extract_supplemental_context(
            response_text
        )
    )

    unsafe_guidance_matches = (
        find_unsafe_guidance(
            supplemental_context
        )
    )

    grounding_context_available = all(
        [
            bool(state.retrieved_documents),
            bool(
                supplemental_context.strip()
            ),
            provenance_complete,
        ]
    )

    safety_boundary_passed = (
        len(unsafe_guidance_matches) == 0
    )

    appointment_created = (
        state.appointment is not None
    )
    contains_appointment_language = (
        "appointment" in response_text.lower()
    )
    appointment_outcome_consistent = (
        appointment_created
        and contains_appointment_language
        if state.appointment_requested
        else not appointment_created
    )

    structured_fact_result = (
        evaluate_structured_fact_consistency(
            response_text,
            state,
        )
    )

    evaluation = {
        "timestamp": (
            datetime.now().isoformat()
        ),
        "user_request_present": bool(
            user_request.strip()
        ),
        "response_present": bool(
            response_text.strip()
        ),
        "response_length": len(
            response_text
        ),
        "workflow_errors_present": bool(
            state.errors
        ),
        "appointment_requested": state.appointment_requested,
        "appointment_created": appointment_created,
        "appointment_outcome_consistent": appointment_outcome_consistent,
        "retrieval_present": bool(
            state.retrieved_documents
        ),
        "retrieved_document_count": len(
            state.retrieved_documents
        ),
        "provenance_complete": (
            provenance_complete
        ),
        "contains_appointment_language": contains_appointment_language,
        "contains_treatment_language": (
            "treatment"
            in response_text.lower()
            or "lisinopril"
            in response_text.lower()
        ),
        "contains_supplemental_context": bool(
            supplemental_context.strip()
        ),
        "grounding_context_available": (
            grounding_context_available
        ),
        "unsafe_guidance_matches": (
            unsafe_guidance_matches
        ),
        "safety_boundary_passed": (
            safety_boundary_passed
        ),
        "required_response_facts": (
            structured_fact_result[
                "required_response_facts"
            ]
        ),
        "consistency_only_identifiers": (
            structured_fact_result[
                "consistency_only_identifiers"
            ]
        ),
        "structured_facts_checked": (
            structured_fact_result[
                "structured_facts_checked"
            ]
        ),
        "missing_required_facts": (
            structured_fact_result[
                "missing_required_facts"
            ]
        ),
        "missing_structured_facts": (
            structured_fact_result[
                "missing_structured_facts"
            ]
        ),
        "unexpected_structured_values": (
            structured_fact_result[
                "unexpected_structured_values"
            ]
        ),
        "structured_fact_failures": (
            structured_fact_result[
                "structured_fact_failures"
            ]
        ),
        "structured_facts_consistent": (
            structured_fact_result[
                "structured_facts_consistent"
            ]
        ),
    }

    evaluation["passed"] = all(
        [
            evaluation[
                "user_request_present"
            ],
            evaluation[
                "response_present"
            ],
            not evaluation[
                "workflow_errors_present"
            ],
            evaluation[
                "appointment_outcome_consistent"
            ],
            evaluation[
                "retrieval_present"
            ],
            evaluation[
                "provenance_complete"
            ],
            evaluation[
                "contains_treatment_language"
            ],
            evaluation[
                "contains_supplemental_context"
            ],
            evaluation[
                "grounding_context_available"
            ],
            evaluation[
                "safety_boundary_passed"
            ],
            evaluation[
                "structured_facts_consistent"
            ],
        ]
    )

    return evaluation
