import json

from trust_evidence_layer.cli import dry_run
from trust_evidence_layer.cli import validate_policy


def test_validate_policy_bundle(tmp_path):
    bundle = {
        "bundle_version": "1.0.0",
        "policies": [{"policy_id": "p1", "version": "1.0", "description": "d"}],
    }
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(bundle))
    validate_policy(str(path))


def test_dry_run_returns_contract(tmp_path):
    bundle = {
        "bundle_version": "1.0.0",
        "policies": [{"policy_id": "p1", "version": "1.0", "description": "d"}],
    }
    bpath = tmp_path / "policy.json"
    bpath.write_text(json.dumps(bundle))

    fixture = {
        "draft_answer_text": "hello",
        "retrieved_evidence": [{"id": "doc-1", "snippet": "hello"}],
        "context": {},
    }
    ipath = tmp_path / "input.json"
    ipath.write_text(json.dumps(fixture))

    result = dry_run(str(ipath), str(bpath))
    assert result["contract_version"] == "1.0"
    assert "audit_pack_ref" in result
