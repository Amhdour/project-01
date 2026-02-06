from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from trust_evidence_layer.attestation import generate_attestation_artifact
from trust_evidence_layer.redaction import redact_text
from trust_evidence_layer.registry import get_policy_registry
from trust_evidence_layer.registry import get_risk_registry
from trust_evidence_layer.registry import get_system_behavior_claims
from trust_evidence_layer.risk_registry import as_dicts as risks_as_dicts
from trust_evidence_layer.storage.file_store import TraceFileStore
from trust_evidence_layer.storage.legal_hold_store import LegalHoldStore
from trust_evidence_layer.system_claims import as_dicts


class AuditPackExporter:
    def __init__(self, store: TraceFileStore) -> None:
        self.store = store

    @staticmethod
    def _hash_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _hash_obj(obj: dict[str, Any]) -> str:
        payload = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _sanitize_summary(text: str, max_len: int = 220) -> str:
        compact = " ".join(text.split())
        return compact[:max_len]

    def _build_chain_of_custody_narrative(
        self,
        *,
        response: dict[str, Any],
        context: dict[str, Any],
        artifacts_hashes: dict[str, str],
    ) -> str:
        decision = response.get("decision_record", {})
        claims = decision.get("claims", [])
        suppressed = [c for c in claims if c.get("verification_status") == "UNSUPPORTED"]

        summary_source = response.get("answer_text") or ""
        summary = self._sanitize_summary(str(summary_source))

        evidence_links = decision.get("evidence_links", [])
        policy_checks = decision.get("policy_checks", [])
        failure_modes = decision.get("failure_modes", [])
        jc = response.get("evidence_bundle_user", {}).get("retrieval_metadata", {}).get("jurisdiction_compliance", {})

        lines = [
            "# Chain of Custody Narrative",
            "",
            "## User Request Summary (sanitized)",
            f"- {summary}",
            "",
            "## Claims asserted vs suppressed",
            f"- total_claims: {len(claims)}",
            f"- suppressed_claims: {len(suppressed)}",
        ]
        for claim in suppressed:
            lines.append(f"- suppressed: {claim.get('claim_id')} -> {claim.get('claim_text')}")

        lines.extend(["", "## Evidence flow (source -> claim)"])
        for link in evidence_links:
            lines.append(f"- {link.get('source_id')} -> {link.get('claim_id')}")

        lines.extend(["", "## Policy decisions applied"])
        for policy in policy_checks:
            lines.append(
                f"- {policy.get('policy_id')}: passed={policy.get('passed')} version={policy.get('version')} details={policy.get('details')}"
            )

        lines.extend(["", "## Jurisdiction Compliance"])
        lines.append(f"- allowed_jurisdictions: {jc.get('allowed_jurisdictions', [])}")
        lines.append(f"- accepted_evidence_count: {len(jc.get('accepted_evidence', []))}")
        lines.append(f"- rejected_evidence_count: {len(jc.get('rejected_evidence', []))}")

        lines.extend(["", "## Failure modes encountered"])
        for mode in failure_modes:
            lines.append(f"- {mode}")

        lines.extend(["", "## Artifact hash references"])
        for name, digest in sorted(artifacts_hashes.items()):
            lines.append(f"- {name}: {digest}")

        lines.extend(["", "## Context summary", f"- request_metadata: {json.dumps(context.get('request_metadata', {}), sort_keys=True)}"])
        return "\n".join(lines) + "\n"

    def export_audit_pack(self, trace_id: str, output_dir: str | Path | None = None) -> Path:
        record = self.store.load(trace_id)
        if record.get("trace_id") != trace_id:
            raise ValueError("Trace ID mismatch in stored record")

        response = record.get("response")
        context = record.get("context")
        retention = record.get("retention")
        replay_inputs = record.get("replay_inputs")
        if (
            not isinstance(response, dict)
            or not isinstance(context, dict)
            or not isinstance(retention, dict)
            or not isinstance(replay_inputs, dict)
        ):
            raise ValueError("Stored trace record is malformed")

        if record.get("response_hash") != self._hash_obj(response):
            raise ValueError("Response hash mismatch in stored record")
        if record.get("context_hash") != self._hash_obj(context):
            raise ValueError("Context hash mismatch in stored record")
        if record.get("replay_inputs_hash") != self._hash_obj(replay_inputs):
            raise ValueError("Replay inputs hash mismatch in stored record")

        out_dir = Path(output_dir or self.store.base_dir) / f"audit_{trace_id}"
        out_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, Path] = {}

        def dump(name: str, payload: Any) -> None:
            files[name] = out_dir / name
            files[name].write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))

        dump("final_response.json", response)
        dump("decision_record.json", response.get("decision_record", {}))
        dump("evidence_sources.json", response.get("evidence_bundle_user", {}).get("sources", []))
        dump("retrieval_metadata.json", response.get("evidence_bundle_user", {}).get("retrieval_metadata", {}))
        dump("policy_evaluation_results.json", response.get("decision_record", {}).get("policy_checks", []))
        dump("incident_events.json", response.get("decision_record", {}).get("incidents", []))
        dump("raw_context_minimal.json", context)
        dump("retention_metadata.json", retention)
        dump("replay_inputs.json", replay_inputs)
        dump("system_claims_snapshot.json", as_dicts(get_system_behavior_claims()))
        dump("risk_register_snapshot.json", risks_as_dicts(get_risk_registry()))
        dump(
            "jurisdiction_compliance.json",
            response.get("evidence_bundle_user", {}).get("retrieval_metadata", {}).get("jurisdiction_compliance", {}),
        )
        dump(
            "policy_registry_snapshot.json",
            {
                key: {
                    "policy_id": val.policy_id,
                    "description": val.description,
                    "scope": val.scope,
                    "version": val.version,
                    "acceptance_tests": val.acceptance_tests,
                    "enforced_by": val.enforced_by,
                }
                for key, val in get_policy_registry().items()
            },
        )

        attestation_path = generate_attestation_artifact(
            output_dir=out_dir,
            tests_executed=["pytest -q backend/trust_evidence_layer/tests"],
        )
        files["attestation_artifact.json"] = attestation_path

        artifact_hashes = {name: self._hash_file(path) for name, path in files.items()}
        unredacted_narrative = self._build_chain_of_custody_narrative(
            response=response,
            context=context,
            artifacts_hashes=artifact_hashes,
        )
        narrative, _ = redact_text(unredacted_narrative)
        files["chain_of_custody.md"] = out_dir / "chain_of_custody.md"
        files["chain_of_custody.md"].write_text(narrative)
        artifact_hashes["chain_of_custody.md"] = self._hash_text(narrative)

        if retention.get("legal_hold"):
            LegalHoldStore().store_unredacted(
                trace_id=trace_id,
                unredacted_answer=str(response.get("answer_text", "")),
                unredacted_evidence=response.get("evidence_bundle_user", {}).get("sources", []),
                unredacted_narrative=unredacted_narrative,
            )

        manifest = {
            "trace_id": trace_id,
            "retention": retention,
            "narrative_hash": artifact_hashes["chain_of_custody.md"],
            "artifacts": artifact_hashes,
        }
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))

        zip_path = out_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name, path in files.items():
                zf.write(path, arcname=name)
            zf.write(manifest_path, arcname="manifest.json")

        return zip_path
