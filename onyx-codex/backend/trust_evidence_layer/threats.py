from __future__ import annotations

from dataclasses import replace

from trust_evidence_layer.types import EvidenceSource


def classify_threat_signals(answer_text: str, evidence_sources: list[EvidenceSource]) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    answer_l = answer_text.lower()

    injection_markers = ["ignore previous instructions", "system prompt", "override policy"]
    if any(marker in answer_l for marker in injection_markers):
        signals.append(
            {
                "threat_type": "PROMPT_INJECTION_ATTEMPT",
                "confidence": "HIGH",
            }
        )

    poisoning_markers = ["jailbreak", "fabricated", "poison", "do not trust policy"]
    poisoning_hits = sum(
        1
        for source in evidence_sources
        for marker in poisoning_markers
        if marker in source.snippet.lower()
    )
    if poisoning_hits:
        confidence = "HIGH" if poisoning_hits >= 2 else "MEDIUM"
        signals.append(
            {
                "threat_type": "EVIDENCE_POISONING_SUSPECTED",
                "confidence": confidence,
            }
        )

    return signals


def apply_threat_containment(
    evidence_sources: list[EvidenceSource],
    threat_signals: list[dict[str, str]],
) -> list[EvidenceSource]:
    has_poisoning = any(s["threat_type"] == "EVIDENCE_POISONING_SUSPECTED" for s in threat_signals)
    has_injection = any(s["threat_type"] == "PROMPT_INJECTION_ATTEMPT" for s in threat_signals)

    if not (has_poisoning or has_injection):
        return evidence_sources

    downgraded: list[EvidenceSource] = []
    for source in evidence_sources:
        new_confidence = max(0.0, source.confidence_weight - 0.3)
        downgraded.append(
            replace(
                source,
                trust_level="UNVERIFIED" if has_poisoning else source.trust_level,
                confidence_weight=new_confidence,
            )
        )
    return downgraded
