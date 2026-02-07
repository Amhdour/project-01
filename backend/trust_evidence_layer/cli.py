from __future__ import annotations

import argparse
import json
from pathlib import Path

from trust_evidence_layer.gate import TrustEvidenceGate


def _load(path: str) -> dict:
    p = Path(path)
    text = p.read_text()
    if p.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:
            raise RuntimeError("PyYAML is required for yaml policy bundles") from e
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("bundle must be an object")
    return data


def validate_policy(bundle_path: str) -> None:
    bundle = _load(bundle_path)
    if "bundle_version" not in bundle or "policies" not in bundle:
        raise ValueError("invalid bundle: missing bundle_version or policies")
    if not isinstance(bundle["policies"], list):
        raise ValueError("invalid bundle: policies must be an array")
    for policy in bundle["policies"]:
        if not isinstance(policy, dict):
            raise ValueError("invalid policy entry")
        for field in ("policy_id", "version", "description"):
            if field not in policy:
                raise ValueError(f"invalid policy entry missing {field}")


def dry_run(input_path: str, bundle_path: str) -> dict:
    validate_policy(bundle_path)
    fixture = _load(input_path)
    gate = TrustEvidenceGate()
    response = gate.gate_response(
        draft_answer_text=str(fixture.get("draft_answer_text", "")),
        retrieved_evidence=fixture.get("retrieved_evidence", []),
        context=fixture.get("context", {}),
    )
    return response.to_ordered_dict()


def main() -> None:
    parser = argparse.ArgumentParser(prog="tel")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate-policy")
    p_validate.add_argument("bundle")

    p_dry = sub.add_parser("dry-run")
    p_dry.add_argument("--input", required=True)
    p_dry.add_argument("--policy", required=True)

    args = parser.parse_args()
    if args.command == "validate-policy":
        validate_policy(args.bundle)
        print("OK")
    elif args.command == "dry-run":
        print(json.dumps(dry_run(args.input, args.policy), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
