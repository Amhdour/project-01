# Schema Versioning Rules

## Version Format
- Schemas use semantic version format: `MAJOR.MINOR.PATCH`.
- `schema_version` is required in event payload envelopes.

## Compatibility Rules
- **Backward-compatible changes** (same MAJOR):
  - adding optional fields,
  - adding optional enum values that consumers may ignore,
  - tightening documentation without changing accepted instance shape.
- **Backward-incompatible changes** (MAJOR bump required):
  - removing or renaming required fields,
  - changing field types,
  - changing semantic meaning of existing required fields.

## Bump Rules
- **PATCH**: typo/docs/schema-description corrections with no accepted-instance change.
- **MINOR**: additive optional fields and non-breaking extensions.
- **MAJOR**: any contract-breaking structural or semantic change.

## Release Checklist
- [x] Update affected schema file `schema_version` values.
- [x] Add or refresh minimal example fixtures.
- [x] Ensure validation tests pass for all schema examples.
- [x] Document changes in `CHANGELOG.md`.
