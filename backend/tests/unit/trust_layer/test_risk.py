from trust_layer.risk import HallucinationRiskFlag
from trust_layer.risk import detect_hallucination_risk_flags


def test_no_evidence_used_and_out_of_scope_flags() -> None:
    flags, warnings = detect_hallucination_risk_flags(
        answer="The capital is definitely Atlantis according to records.",
        citation_count=0,
        evidence_count=0,
        retrieval_scores=[],
    )

    assert HallucinationRiskFlag.NO_EVIDENCE_USED.value in flags
    assert HallucinationRiskFlag.OUT_OF_SCOPE.value in flags
    assert len(warnings) >= 2


def test_low_retrieval_score_flag() -> None:
    flags, warnings = detect_hallucination_risk_flags(
        answer="Based on documents, the answer is 42 with caveats.",
        citation_count=2,
        evidence_count=3,
        retrieval_scores=[0.1, 0.2, 0.25],
        low_retrieval_score_threshold=0.3,
    )

    assert HallucinationRiskFlag.LOW_RETRIEVAL_SCORE.value in flags
    assert any("Average retrieval score" in warning for warning in warnings)


def test_no_flags_for_well_supported_answer() -> None:
    flags, warnings = detect_hallucination_risk_flags(
        answer="The policy states employees receive 20 days of leave annually.",
        citation_count=2,
        evidence_count=2,
        retrieval_scores=[0.82, 0.77],
    )

    assert flags == []
    assert warnings == []
