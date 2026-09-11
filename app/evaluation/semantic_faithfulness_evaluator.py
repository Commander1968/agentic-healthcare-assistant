import json

from dotenv import load_dotenv
from openai import OpenAI

from app.models.semantic_faithfulness_result import (
    SemanticFaithfulnessResult,
)
from app.models.workflow_state import WorkflowState


load_dotenv()

client = OpenAI()


SEMANTIC_EVALUATOR_SYSTEM_PROMPT = """
You are an evidence-bounded semantic faithfulness evaluator for
an agentic healthcare assistant.

Your task is to evaluate a generated response only against the
evidence supplied to you.

You are NOT acting as a medical expert and must NOT use external
medical knowledge to decide whether the response is medically
reasonable.

EVIDENCE AUTHORITY RULES

1. Structured workflow state is authoritative for patient-specific
   and operational facts, including:
   - patient identity
   - age
   - diagnoses
   - medications
   - treatment notes
   - relevant patient alerts
   - selected doctor
   - specialty
   - appointment details

2. Retrieved documents are supplemental educational evidence only.

3. Retrieved documents must never override or modify authoritative
   structured patient or workflow facts.

4. The generated response is not a source of truth.

EVALUATION RULES

Evaluate whether:

- patient-specific claims are supported by structured workflow state;
- diagnoses, medications, doses, treatment context, relevant alerts, doctor details,
  specialty, and appointment details remain consistent;
- educational claims are supported by the retrieved documents;
- general retrieved information has been improperly personalized
  into advice or treatment instructions for the patient;
- unsupported patient-specific facts have been introduced;
- the authority boundary between structured state and retrieved
  educational material has been respected;
- the retrieved documents are relevant to the user request and
  generated supplemental context.

Do not create new medical advice.
Do not supply missing medical facts.
Do not correct the response using outside knowledge.
Do not infer facts simply because they may be medically plausible.

STATUS POLICY

Return PASS when the supplied evidence supports the response and
the authority boundary is respected.

Return FAIL when there is a supported contradiction, unsupported
patient-specific claim, unsupported retrieved claim, improper
clinical personalization, or authority-boundary violation.

Return UNCERTAIN when the supplied evidence is insufficient or
ambiguous and a reliable determination cannot be made.

For every failure or uncertainty, identify the specific claim or
reason in the appropriate diagnostic field.

The overall result must be inspectable and evidence-bounded.
"""


def build_semantic_evaluation_evidence(
    user_request: str,
    response_text: str,
    state: WorkflowState,
) -> dict:
    """
    Build the evidence package supplied to the semantic evaluator.

    Structured workflow data remains explicitly separated from
    retrieved supplemental evidence.
    """

    authoritative_state = {
        "patient": (
            state.patient.model_dump()
            if state.patient is not None
            else None
        ),
        "medical_record": (
            state.medical_record.model_dump()
            if state.medical_record is not None
            else None
        ),
        "selected_doctor": (
            state.selected_doctor.model_dump()
            if state.selected_doctor is not None
            else None
        ),
        "appointment": (
            state.appointment.model_dump()
            if state.appointment is not None
            else None
        ),
        "workflow_errors": state.errors,
    }

    retrieved_documents = [
        {
            "title": document.title,
            "source_name": document.source_name,
            "source_type": document.source_type,
            "source_url": document.source_url,
            "content": document.content,
        }
        for document in state.retrieved_documents
    ]

    return {
        "user_request": user_request,
        "authoritative_workflow_state": authoritative_state,
        "retrieved_documents": retrieved_documents,
        "generated_response": response_text,
    }


def evaluate_semantic_faithfulness(
    user_request: str,
    response_text: str,
    state: WorkflowState,
) -> SemanticFaithfulnessResult:
    """
    Evaluate semantic faithfulness using structured model output.
    """

    evidence = build_semantic_evaluation_evidence(
        user_request=user_request,
        response_text=response_text,
        state=state,
    )

    evaluator_input = (
        "Evaluate the following healthcare-assistant response "
        "against the supplied evidence only.\n\n"
        f"{json.dumps(evidence, indent=2)}"
    )

    completion = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": SEMANTIC_EVALUATOR_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": evaluator_input,
            },
        ],
        text_format=SemanticFaithfulnessResult,
    )

    return completion.output_parsed
