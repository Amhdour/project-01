from __future__ import annotations

from enum import Enum


class HallucinationRiskFlag(str, Enum):
    NO_EVIDENCE_USED = "NO_EVIDENCE_USED"
    LOW_RETRIEVAL_SCORE = "LOW_RETRIEVAL_SCORE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


def _has_claim_like_answer(answer: str) -> bool:
    stripped = answer.strip()
    if not stripped:
        return False
    # Low-cost heuristic: non-trivial natural language output
    return len(stripped.split()) >= 5


def detect_hallucination_risk_flags(
    *,
    answer: str,
    citation_count: int,
    evidence_count: int,
    retrieval_scores: list[float],
    low_retrieval_score_threshold: float = 0.3,
) -> tuple[list[str], list[str]]:
    """Return (risk_flags, trust_warnings) based on existing retrieval/generation signals."""
    flags: list[str] = []
    warnings: list[str] = []

    has_claims = _has_claim_like_answer(answer)
    has_answer = bool(answer.strip())

    if has_claims and citation_count == 0 and evidence_count == 0:
        flags.append(HallucinationRiskFlag.NO_EVIDENCE_USED.value)
        warnings.append("Answer appears claim-like but has no linked citations or evidence.")

    if evidence_count == 0 and has_answer:
        flags.append(HallucinationRiskFlag.OUT_OF_SCOPE.value)
        warnings.append("Answer produced despite empty retrieval context.")

    if retrieval_scores:
        avg_score = sum(retrieval_scores) / len(retrieval_scores)
        if avg_score < low_retrieval_score_threshold:
            flags.append(HallucinationRiskFlag.LOW_RETRIEVAL_SCORE.value)
            warnings.append(
                f"Average retrieval score ({avg_score:.3f}) is below threshold ({low_retrieval_score_threshold:.3f})."
            )

    return flags, warnings
