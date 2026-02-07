# API

## GET `/trust/audit-packs/{trace_id}`

Downloads the generated audit pack as a zip attachment.

- Authorization: Bearer JWT with `trust:audit:read`
- Response:
  - `200 OK`
  - `Content-Type: application/zip`
  - `Content-Disposition: attachment; filename="audit_pack_{trace_id}.zip"`
  - Body: binary zip stream containing audit artifacts (including `manifest.json` and event files such as `incident_events.json`)

Notes:
- The endpoint returns the zip content directly and does **not** expose server filesystem paths in JSON.
