import json
from pathlib import Path

from app.models.response_precision_result import ResponsePrecisionResult


def evaluate_persisted_response_precision(
    log_path: str | Path,
) -> ResponsePrecisionResult:
    supported_claims: list[str] = []
    unsupported_claims: list[str] = []

    if not Path(log_path).is_file():
        return ResponsePrecisionResult(
            supported_claim_count=0,
            verifiable_claim_count=0,
            excluded_claim_count=0,
            precision=0.0,
            formula="supported claims / verifiable claims",
            evaluation_basis=(
                "No persisted semantic-evaluation records are available yet."
            ),
            supported_claims=[],
            unsupported_claims=[],
            excluded_claims=[],
        )
    with Path(log_path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue

            record = json.loads(line)
            semantic = record.get("semantic_evaluation") or {}

            claim_groups = (
                (
                    "structured claims",
                    semantic.get("structured_claims_supported"),
                    semantic.get("structured_claim_failures") or [],
                ),
                (
                    "retrieved claims",
                    semantic.get("retrieved_claims_supported"),
                    semantic.get("retrieval_claim_failures") or [],
                ),
            )

            for label, supported, failures in claim_groups:
                if supported is True:
                    supported_claims.append(
                        f"{label} supported in run {record.get('timestamp_utc', 'unknown')}"
                    )
                elif failures:
                    unsupported_claims.extend(
                        f"{label} failure: {failure}"
                        for failure in failures
                    )
                elif supported is False:
                    unsupported_claims.append(
                        f"{label} unsupported in run {record.get('timestamp_utc', 'unknown')}"
                    )

    verifiable_count = len(supported_claims) + len(unsupported_claims)
    precision = (
        len(supported_claims) / verifiable_count
        if verifiable_count
        else None
    )

    formula = (
        f"{len(supported_claims)} / {verifiable_count} = {precision:.2%}"
        if precision is not None
        else "N/A: zero verifiable claims"
    )

    return ResponsePrecisionResult(
        supported_claim_count=len(supported_claims),
        verifiable_claim_count=verifiable_count,
        excluded_claim_count=0,
        precision=precision,
        formula=formula,
        evaluation_basis=(
            "Persisted semantic-evaluation records. Structured and retrieved "
            "response claims are counted; authority, safety, and relevance "
            "flags are not counted as response claims."
        ),
        supported_claims=supported_claims,
        unsupported_claims=unsupported_claims,
        excluded_claims=[],
    )
