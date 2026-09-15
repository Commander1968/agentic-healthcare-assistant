from app.evaluation.persisted_response_precision import evaluate_persisted_response_precision


def test_missing_persisted_log_returns_zero_result(tmp_path):
    missing_log = tmp_path / "not-created.jsonl"
    result = evaluate_persisted_response_precision(missing_log)

    assert result.supported_claim_count == 0
    assert result.verifiable_claim_count == 0
    assert result.excluded_claim_count == 0
    assert result.precision == 0.0
    assert result.supported_claims == []
    assert result.unsupported_claims == []
    assert result.excluded_claims == []
    assert "No persisted semantic-evaluation records" in result.evaluation_basis
