"""Portable Trust & Evidence contract package."""

from trust_layer.events import TrustContext
from trust_layer.events import TrustEvent
from trust_layer.interface import TrustLayer
from trust_layer.risk import detect_hallucination_risk_flags
from trust_layer.hook_utils import run_trust_hook_safe
from trust_layer.types import EvidenceItem
from trust_layer.types import GenerationTrace
from trust_layer.types import RetrievalTrace
from trust_layer.types import TrustReport

__all__ = [
    "EvidenceItem",
    "GenerationTrace",
    "RetrievalTrace",
    "TrustReport",
    "TrustEvent",
    "TrustContext",
    "TrustLayer",
    "run_trust_hook_safe",
    "detect_hallucination_risk_flags",
]
