from __future__ import annotations

import json
from pathlib import Path


def _validate(instance, schema, path="$"):
    schema_type = schema.get("type")
    if "oneOf" in schema:
        for option in schema["oneOf"]:
            try:
                _validate(instance, option, path)
                return
            except AssertionError:
                continue
        raise AssertionError(f"{path}: no oneOf option matched")

    if "const" in schema:
        assert instance == schema["const"], f"{path}: expected const {schema['const']!r}"
    if "enum" in schema:
        assert instance in schema["enum"], f"{path}: expected enum {schema['enum']!r}"

    if schema_type == "object":
        assert isinstance(instance, dict), f"{path}: expected object"
        required = schema.get("required", [])
        for key in required:
            assert key in instance, f"{path}: missing required key {key}"

        props = schema.get("properties", {})
        addl = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                _validate(value, props[key], f"{path}.{key}")
            else:
                assert addl is not False, f"{path}: additional property {key} not allowed"

    elif schema_type == "array":
        assert isinstance(instance, list), f"{path}: expected array"
        if "minItems" in schema:
            assert len(instance) >= schema["minItems"], f"{path}: expected minItems {schema['minItems']}"
        item_schema = schema.get("items")
        if item_schema:
            for idx, item in enumerate(instance):
                _validate(item, item_schema, f"{path}[{idx}]")

    elif schema_type == "string":
        assert isinstance(instance, str), f"{path}: expected string"
        if "minLength" in schema:
            assert len(instance) >= schema["minLength"], f"{path}: expected minLength {schema['minLength']}"

    elif schema_type == "integer":
        assert isinstance(instance, int) and not isinstance(instance, bool), f"{path}: expected integer"
        if "minimum" in schema:
            assert instance >= schema["minimum"], f"{path}: expected minimum {schema['minimum']}"

    elif schema_type == "number":
        assert isinstance(instance, (int, float)) and not isinstance(instance, bool), f"{path}: expected number"

    elif schema_type == "null":
        assert instance is None, f"{path}: expected null"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_examples_validate_against_schemas() -> None:
    base = Path("trust-evidence/sidecar/schemas")
    schemas = [
        "turn_start",
        "retrieval_batch",
        "tool_call",
        "tool_result",
        "citations_resolved",
        "turn_final",
        "policy_decision",
        "integrity_checkpoint",
        "contract_response",
    ]
    for name in schemas:
        schema = _load_json(base / f"{name}.json")
        example = _load_json(base / "examples" / f"{name}.example.json")
        _validate(example, schema)


def test_required_fields_enforced() -> None:
    base = Path("trust-evidence/sidecar/schemas")
    schema = _load_json(base / "turn_start.json")
    example = _load_json(base / "examples" / "turn_start.example.json")
    example.pop("trace_id")
    try:
        _validate(example, schema)
        raise AssertionError("expected required field failure")
    except AssertionError as e:
        assert "trace_id" in str(e)
