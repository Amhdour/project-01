import json
from pathlib import Path

from trust_evidence_layer.attestation import generate_attestation_artifact


def test_attestation_artifact_generation(tmp_path: Path) -> None:
    path = generate_attestation_artifact(
        output_dir=tmp_path,
        tests_executed=["pytest -q backend/trust_evidence_layer/tests"],
    )
    payload = json.loads(path.read_text())
    assert "system_claims" in payload
    assert "policies" in payload
    assert "risk_register" in payload
    assert "tests_executed" in payload
    assert "last_evaluation_timestamp" in payload
