from __future__ import annotations

import re
from typing import Any

from trust_evidence_layer.system_claims import SystemBehaviorClaim
from trust_evidence_layer.system_claims import match_system_claim
from trust_evidence_layer.types import EvidenceSource

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"[a-zA-Z0-9]+")

_CONVERSATIONAL_PREFIXES = (
    "hi",
    "hello",
    "thanks",
    "thank you",
    "you're welcome",
    "how can i help",
)

_INTERPRETIVE_MARKERS = (
    "suggests",
    "likely",
    "recommend",
    "appears",
    "possibly",
    "probably",
    "seems",
)

_SYSTEM_MARKERS = (
    "system",
    "policy",
    "tool",
    "capability",
    "gate",
    "unknown",
    "response contract",
)

_DERIVED_PREFIXES = (
    "therefore",
    "thus",
    "hence",
    "as a result",
    "this means",
    "so ",
    "based on",
)


class ClaimType:
    FACTUAL = "FACTUAL"
    DERIVED = "DERIVED"
    INTERPRETIVE = "INTERPRETIVE"
    SYSTEM = "SYSTEM"


class VerificationStatus:
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"


class HallucinationMode:
    NO_EVIDENCE = "NO_EVIDENCE"
    CONTRADICTED = "CONTRADICTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    TOOL_UNTRUSTED = "TOOL_UNTRUSTED"


def split_claims(answer_text: str) -> list[str]:
    chunks = [c.strip() for c in _SENTENCE_SPLIT_RE.split(answer_text) if c.strip()]
    return chunks if chunks else ([answer_text.strip()] if answer_text.strip() else [])


def is_conversational_claim(claim: str) -> bool:
    lowered = claim.strip().lower()
    return lowered.startswith(_CONVERSATIONAL_PREFIXES)


def _keywords(text: str) -> set[str]:
    tokens = {t.lower() for t in _WORD_RE.findall(text)}
    return {t for t in tokens if len(t) >= 4}


def classify_claim_type(claim_text: str) -> str:
    lowered = claim_text.strip().lower()
    if lowered.startswith(_DERIVED_PREFIXES):
        return ClaimType.DERIVED
    if any(marker in lowered for marker in _INTERPRETIVE_MARKERS):
        return ClaimType.INTERPRETIVE
    if any(marker in lowered for marker in _SYSTEM_MARKERS):
        return ClaimType.SYSTEM
    return ClaimType.FACTUAL


def _check_contradiction(claim_text: str, snippet: str) -> bool:
    claim = claim_text.lower()
    text = snippet.lower()
    if " not " in claim and " not " not in text:
        return True
    if " not " not in claim and " not " in text:
        return True
    return False


def _find_lexical_matches(
    claim_text: str,
    evidence_sources: list[EvidenceSource],
    *,
    minimum_keyword_hits: int = 1,
) -> tuple[list[EvidenceSource], bool]:
    claim_l = claim_text.lower()
    claim_keywords = _keywords(claim_text)
    matches: list[EvidenceSource] = []
    contradicted = False

    for src in evidence_sources:
        snippet_l = src.snippet.lower()
        if claim_l in snippet_l:
            matches.append(src)
            contradicted = contradicted or _check_contradiction(claim_text, src.snippet)
            continue

        if claim_keywords:
            overlap = claim_keywords.intersection(_keywords(snippet_l))
            if len(overlap) >= minimum_keyword_hits:
                matches.append(src)
                contradicted = contradicted or _check_contradiction(claim_text, src.snippet)

    return matches, contradicted


def _verification_for_factual(matches: list[EvidenceSource]) -> tuple[str, str | None]:
    primary = [m for m in matches if m.trust_level == "PRIMARY"]
    secondary = [m for m in matches if m.trust_level == "SECONDARY"]
    if primary or len(secondary) >= 2:
        return VerificationStatus.SUPPORTED, None
    if matches and all(m.trust_level == "UNVERIFIED" for m in matches):
        return VerificationStatus.UNSUPPORTED, HallucinationMode.TOOL_UNTRUSTED
    if matches:
        return VerificationStatus.UNSUPPORTED, HallucinationMode.OUT_OF_SCOPE
    return VerificationStatus.UNSUPPORTED, HallucinationMode.NO_EVIDENCE


def _verification_for_interpretive(matches: list[EvidenceSource]) -> tuple[str, str | None]:
    if not matches:
        return VerificationStatus.UNSUPPORTED, HallucinationMode.NO_EVIDENCE
    trusted = [m for m in matches if m.trust_level in {"PRIMARY", "SECONDARY"}]
    if trusted:
        return VerificationStatus.PARTIAL, None
    return VerificationStatus.PARTIAL, HallucinationMode.TOOL_UNTRUSTED


def _severity(claim_type: str) -> str:
    if claim_type in {ClaimType.FACTUAL, ClaimType.SYSTEM}:
        return "HIGH"
    if claim_type == ClaimType.DERIVED:
        return "MEDIUM"
    return "LOW"


def enforce_claims(
    draft_answer_text: str,
    evidence_sources: list[EvidenceSource],
    *,
    system_claims: list[SystemBehaviorClaim],
) -> tuple[
    str,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, str]],
    list[str],
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, str]],
]:
    claims = split_claims(draft_answer_text)

    if not claims:
        metrics = {"num_claims_total": 0, "num_claims_unsupported": 0, "pct_suppressed": 0.0}
        return (
            "UNKNOWN: no answer content generated.",
            [],
            [],
            [],
            ["empty_draft_answer"],
            [],
            metrics,
            [],
        )

    output_lines: list[str] = []
    claim_records: list[dict[str, Any]] = []
    evidence_links: list[dict[str, Any]] = []
    claim_graph: list[dict[str, str]] = []
    failure_modes: list[str] = []
    hallucination_events: list[dict[str, Any]] = []
    system_claim_refs: list[dict[str, str]] = []

    supported_claim_ids: list[str] = []

    for idx, claim_text in enumerate(claims, start=1):
        claim_id = f"claim_{idx}"
        claim_type = classify_claim_type(claim_text)
        evidence_required = not is_conversational_claim(claim_text)

        matches, contradicted = _find_lexical_matches(claim_text, evidence_sources)
        source_ids = [m.id for m in matches]

        hallucination_mode: str | None = None

        if claim_type == ClaimType.SYSTEM:
            matched_system_claim = match_system_claim(claim_text, system_claims)
            if matched_system_claim:
                verification_status = VerificationStatus.SUPPORTED
                system_claim_refs.append(
                    {
                        "claim_id": claim_id,
                        "system_claim_id": matched_system_claim.system_claim_id,
                    }
                )
            else:
                verification_status = VerificationStatus.UNSUPPORTED
                hallucination_mode = HallucinationMode.OUT_OF_SCOPE
        elif claim_type == ClaimType.INTERPRETIVE:
            verification_status, hallucination_mode = _verification_for_interpretive(matches)
        elif claim_type == ClaimType.DERIVED:
            parents = supported_claim_ids[-2:] or supported_claim_ids[-1:]
            for parent in parents:
                claim_graph.append({"claim_id": claim_id, "derived_from": parent})
            if parents:
                verification_status = VerificationStatus.SUPPORTED
            else:
                verification_status = VerificationStatus.UNSUPPORTED
                hallucination_mode = HallucinationMode.OUT_OF_SCOPE
        else:
            verification_status, hallucination_mode = _verification_for_factual(matches)

        if contradicted and verification_status != VerificationStatus.SUPPORTED:
            hallucination_mode = HallucinationMode.CONTRADICTED

        if not evidence_required:
            verification_status = VerificationStatus.SUPPORTED
            hallucination_mode = None

        if verification_status in {VerificationStatus.SUPPORTED, VerificationStatus.PARTIAL}:
            if verification_status == VerificationStatus.PARTIAL:
                output_lines.append(f"PARTIAL: {claim_text}")
            else:
                output_lines.append(claim_text)
            supported_claim_ids.append(claim_id)
        else:
            output_lines.append(f"UNKNOWN: {claim_text}")
            failure_modes.append("unsupported_claim")

        if hallucination_mode is not None:
            failure_modes.append(hallucination_mode)
            hallucination_events.append(
                {
                    "event_type": "HALLUCINATION_SUPPRESSED",
                    "severity": _severity(claim_type),
                    "claim_id": claim_id,
                    "mode": hallucination_mode,
                }
            )

        claim_records.append(
            {
                "claim_id": claim_id,
                "claim_text": claim_text,
                "claim_type": claim_type,
                "evidence_required": evidence_required,
                "verification_status": verification_status,
            }
        )

        for source_id in source_ids:
            evidence_links.append({"claim_id": claim_id, "source_id": source_id})

    if not evidence_sources:
        failure_modes.append("no_supporting_evidence_found")

    total = len(claim_records)
    unsupported = sum(
        1 for claim in claim_records if claim["verification_status"] == VerificationStatus.UNSUPPORTED
    )
    metrics = {
        "num_claims_total": total,
        "num_claims_unsupported": unsupported,
        "pct_suppressed": round((unsupported / total), 4) if total else 0.0,
    }

    return (
        "\n".join(output_lines),
        claim_records,
        evidence_links,
        claim_graph,
        sorted(set(failure_modes)),
        hallucination_events,
        metrics,
        system_claim_refs,
    )
