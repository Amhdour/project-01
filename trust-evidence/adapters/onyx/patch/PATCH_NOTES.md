# Onyx Patch Notes Placeholder (v0.1)

## Minimal net LoC target
- Target patch footprint: **<= 80 net LoC** in core Onyx request path.
- Prefer single hook module import + callsites over broad refactors.
- Keep changes isolated to chat request orchestration and trust API bridge.

## Compatibility statement format
Use this format in every patch PR description/release note:

```text
Compatibility Statement:
- Onyx baseline: <git tag or commit>
- Adapter version: <version>
- Status: compatible | requires adjustment
- Notes: <breaking symbols/paths and mitigation>
```

## Patch hygiene
- No hardcoded sidecar endpoints or secrets; environment-driven only.
- Keep adapter calls non-blocking to user flow where possible (bounded retries only).
- If hook points move in upstream Onyx, update `mapping.md` with new callsites.
