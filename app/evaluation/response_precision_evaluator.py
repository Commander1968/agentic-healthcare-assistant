from collections.abc import Sequence

from app.models.response_precision_result import ResponsePrecisionResult


def evaluate_response_precision(
    *,
    supported_claims: Sequence[str],
    unsupported_claims: Sequence[str],
    excluded_claims: Sequence[str] = (),
) -> ResponsePrecisionResult:
    supported = list(supported_claims)
    unsupported = list(unsupported_claims)
    excluded = list(excluded_claims)

    verifiable_count = len(supported) + len(unsupported)

    precision = (
        len(supported) / verifiable_count
        if verifiable_count
        else None
    )

    formula = (
        f"{len(supported)} / {verifiable_count} = {precision:.2%}"
        if precision is not None
        else "N/A: zero verifiable claims"
    )

    return ResponsePrecisionResult(
        supported_claim_count=len(supported),
        verifiable_claim_count=verifiable_count,
        excluded_claim_count=len(excluded),
        precision=precision,
        formula=formula,
        evaluation_basis=(
            "Supported verifiable response claims divided by total "
            "verifiable response claims. Conversational or unverifiable "
            "text is excluded."
        ),
        supported_claims=supported,
        unsupported_claims=unsupported,
        excluded_claims=excluded,
    )
