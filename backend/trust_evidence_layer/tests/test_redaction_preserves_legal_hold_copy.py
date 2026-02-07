import json
from pathlib import Path

from trust_evidence_layer.gate import TrustEvidenceGate
from trust_evidence_layer.storage.legal_hold_store import LegalHoldStore


def test_redaction_preserves_legal_hold_copy(tmp_path: Path, monkeypatch) -> None:
    store = LegalHoldStore(base_dir=tmp_path)
    monkeypatch.setattr("trust_evidence_layer.gate.LegalHoldStore", lambda: store)

    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text="john.doe@example.com",
        retrieved_evidence=[{"id": "x", "snippet": "john.doe@example.com"}],
        context={"chat_session_id": "p2", "message_id": 2, "legal_hold": True},
    )

    target = tmp_path / f"{response.trace_id}_unredacted.json"
    assert target.exists()
    payload = json.loads(target.read_text())
    assert "john.doe@example.com" in payload["answer_text"]
