import re

from dotenv import load_dotenv
from openai import OpenAI

from app.models.workflow_state import WorkflowState


load_dotenv()

client = OpenAI()


def synthesize_response(state: WorkflowState) -> str:
    if state.errors:
        return (
            "The workflow could not be completed. "
            f"Errors: {', '.join(state.errors)}"
        )

    retrieved_context = "\n\n".join(
        [
            (
                f"Title: {document.title}\n"
                f"Source name: {document.source_name}\n"
                f"Source type: {document.source_type}\n"
                f"Source URL: {document.source_url}\n"
                f"Content: {document.content}"
            )
            for document in state.retrieved_documents
        ]
    )

    if not retrieved_context:
        retrieved_context = "No supplemental knowledge was retrieved."

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You generate concise healthcare workflow summaries. "
                    "Structured patient and workflow data are authoritative. "
                    "Retrieved knowledge is supplemental educational context only. "
                    "Do not use retrieved knowledge to modify, infer, or override "
                    "patient-specific diagnoses, medications, treatments, doctor "
                    "selection, appointment details, or other structured facts. "
                    "Do not add medical advice, diagnoses, treatments, or "
                    "recommendations that are not present in the structured data. "
                    "Do not generate medication-management instructions or language "
                    "that suggests starting, stopping, changing, adjusting, increasing, "
                    "or decreasing medications or medication doses. "
                    "Do not convert general educational information into patient-specific "
                    "treatment guidance or recommendations. "
                    "When supplemental retrieved knowledge is provided, include a brief "
                    "section titled exactly 'Supplemental Educational Context'. "
                    "Use only retrieved knowledge that is directly relevant to the request. "
                    "The section must remain general and educational and must not modify, "
                    "infer, personalize, or override patient-specific diagnoses, medications, "
                    "treatments, doctor selection, appointment details, or other structured facts. "
                    "Clearly distinguish appointment information, existing treatment "
                    "information, relevant patient alerts, and the Supplemental "
                    "Educational Context section. "
                    "Include a distinct 'Relevant Alerts' statement using only the "
                    "authoritative medical_record.alerts values. If that list is empty, "
                    "state 'Relevant Alerts: None recorded.'"
                ),
            },
            {
                "role": "user",
                "content": (
                    "AUTHORITATIVE STRUCTURED WORKFLOW DATA\n"
                    f"Patient: {state.patient}\n"
                    f"Medical record: {state.medical_record}\n"
                    f"Selected doctor: {state.selected_doctor}\n"
                    f"Appointment: {state.appointment}\n\n"
                    "SUPPLEMENTAL RETRIEVED KNOWLEDGE\n"
                    f"{retrieved_context}\n"
                ),
            },
        ],
    )

    response_text = response.output_text

    if "relevant alerts:" not in response_text.lower():
        response_text, replacements = re.subn(
            r"\balerts\s*:",
            "Relevant Alerts:",
            response_text,
            count=1,
            flags=re.IGNORECASE,
        )

        if replacements == 0:
            alerts = (
                ", ".join(state.medical_record.alerts)
                if state.medical_record is not None
                and state.medical_record.alerts
                else "None recorded"
            )
            response_text = (
                f"{response_text.rstrip()}\n\n"
                f"Relevant Alerts: {alerts}"
            )

    return response_text
