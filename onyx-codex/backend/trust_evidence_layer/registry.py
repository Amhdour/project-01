from __future__ import annotations

from trust_evidence_layer.policy_registry import get_policy_definitions
from trust_evidence_layer.policy_registry import get_policy_version_change_log
from trust_evidence_layer.policy_registry import get_policy_versions
from trust_evidence_layer.risk_registry import get_active_risks
from trust_evidence_layer.storage.file_store import TraceFileStore
from trust_evidence_layer.system_claims import SystemBehaviorClaim
from trust_evidence_layer.system_claims import get_active_system_claims

_default_store = TraceFileStore()
_TRUSTED_TOOLS = {"search_docs"}


def get_default_store() -> TraceFileStore:
    return _default_store


def get_default_exporter():
    from trust_evidence_layer.audit_pack import AuditPackExporter

    return AuditPackExporter(_default_store)


def get_system_behavior_claims() -> list[SystemBehaviorClaim]:
    return get_active_system_claims()


def get_trusted_tools() -> set[str]:
    return set(_TRUSTED_TOOLS)


def get_policy_versions_map() -> dict[str, str]:
    return get_policy_versions()


def get_policy_registry() -> dict[str, object]:
    return get_policy_definitions()


def get_policy_change_log() -> list[dict[str, object]]:
    return get_policy_version_change_log()


def get_risk_registry():
    return get_active_risks()
