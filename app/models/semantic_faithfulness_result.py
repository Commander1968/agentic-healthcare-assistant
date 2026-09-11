from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class SemanticEvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNCERTAIN = "UNCERTAIN"


class SemanticFaithfulnessResult(BaseModel):
    status: SemanticEvaluationStatus

    structured_claims_supported: bool

    structured_claim_failures: List[str] = Field(
        default_factory=list
    )

    retrieved_claims_supported: bool

    retrieval_claim_failures: List[str] = Field(
        default_factory=list
    )

    authority_boundary_respected: bool

    authority_boundary_failures: List[str] = Field(
        default_factory=list
    )

    unsupported_patient_claim_detected: bool

    unsupported_patient_claims: List[str] = Field(
        default_factory=list
    )

    clinical_personalization_detected: bool

    clinical_personalization_examples: List[str] = Field(
        default_factory=list
    )

    retrieval_relevance_supported: bool

    retrieval_relevance_notes: List[str] = Field(
        default_factory=list
    )

    overall_semantic_faithfulness: bool

    evaluation_summary: str