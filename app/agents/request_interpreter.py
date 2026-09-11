from dotenv import load_dotenv
from openai import OpenAI

from app.models.request_intent import RequestIntent


load_dotenv()

client = OpenAI()


def interpret_request(user_request: str) -> RequestIntent:
    response = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You interpret healthcare workflow requests. "
                    "Extract only the information needed to populate the "
                    "RequestIntent schema. "
                    "Set appointment_requested true only when the user explicitly "
                    "asks to book or schedule an appointment. Set it false for "
                    "summary-only, information-only, or explicit no-booking requests. "
                    "Use patient_id P001 when the request refers to the "
                    "70-year-old patient with Chronic Kidney Disease in this "
                    "demonstration scenario. "
                    "Do not provide medical advice." "Return an ordered plan_steps list containing the workflow sequence "
                    "needed to satisfy the request. Include retrieval, validation, "
                    "specialty matching, appointment booking only when requested, and "
                    "response synthesis. The plan is descriptive only and does not "
                    "authorize tool execution. "
                ),
            },
            {
                "role": "user",
                "content": user_request,
            },
        ],
        text_format=RequestIntent,
    )

    return response.output_parsed
