from pydantic import BaseModel, Field


class ResponsePrecisionResult(BaseModel):
    metric_name: str = "response_precision"
    supported_claim_count: int
    verifiable_claim_count: int
    excluded_claim_count: int = 0
    precision: float | None
    formula: str
    evaluation_basis: str
    supported_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    excluded_claims: list[str] = Field(default_factory=list)