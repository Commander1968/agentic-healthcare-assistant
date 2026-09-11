from pydantic import BaseModel, Field


class RequestIntent(BaseModel):
    patient_id: str = Field(
        ...,
        description="Unique patient identifier for the requested workflow"
    )

    requested_specialty: str = Field(
        ...,
        description="Medical specialty needed for the request"
    )

    reason: str = Field(
        ...,
        description="Concise reason for the requested appointment or workflow"
    )

    appointment_requested: bool = Field(
        ...,
        description=(
            "True only when the user explicitly requests appointment booking; "
            "false for summary, retrieval, or explicit no-booking requests"
        ),
    )

    plan_steps: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered workflow steps proposed for the request. "
            "These steps describe planning only and do not authorize tool execution."
        ),
    )
