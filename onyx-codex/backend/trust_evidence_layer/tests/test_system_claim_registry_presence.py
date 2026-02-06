from trust_evidence_layer.registry import get_system_behavior_claims


def test_system_claim_registry_presence() -> None:
    claims = get_system_behavior_claims()
    assert claims
    first = claims[0]
    assert first.system_claim_id
    assert first.scope
    assert first.enforced_by
    assert first.evidence
    assert first.version
