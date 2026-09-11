from app.evaluation.response_precision_evaluator import (
    evaluate_response_precision,
)


def test_mixed_supported_and_unsupported_claims():
    result = evaluate_response_precision(
        supported_claims=["appointment date", "selected specialty", "doctor name"],
        unsupported_claims=["unverified dosage change"],
    )

    assert result.supported_claim_count == 3
    assert result.verifiable_claim_count == 4
    assert result.precision == 0.75
    assert result.formula == "3 / 4 = 75.00%"


def test_all_verifiable_claims_supported():
    result = evaluate_response_precision(
        supported_claims=["appointment date", "doctor name"],
        unsupported_claims=[],
    )

    assert result.precision == 1.0
    assert result.formula == "2 / 2 = 100.00%"


def test_zero_verifiable_claims_returns_na():
    result = evaluate_response_precision(
        supported_claims=[],
        unsupported_claims=[],
        excluded_claims=["disclaimer"],
    )

    assert result.precision is None
    assert result.formula == "N/A: zero verifiable claims"
    assert result.excluded_claim_count == 1


def test_unsupported_claims_are_not_counted_as_supported():
    result = evaluate_response_precision(
        supported_claims=["appointment date"],
        unsupported_claims=["invented diagnosis", "invented medication"],
    )

    assert result.supported_claim_count == 1
    assert result.verifiable_claim_count == 3
    assert result.precision == 1 / 3
