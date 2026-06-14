## Summary
Adds an RFC-only Enterprise Boundary for HUB_Optimus.

## Scope
- Defines HUB_Optimus Enterprise as downstream from Core
- Rejects semantic forks
- Defines client-configuration boundaries
- Defines prohibited enterprise capabilities
- Defines implementation gates before enterprise work

## Out of scope
- Runtime changes
- CI changes
- Schema changes
- Benchmark changes
- HERMES implementation
- API implementation
- AWS production deployment
- S3
- Authentication
- Billing
- Dashboards
- Vector search
- LLM-as-judge
- Commercial launch

## Validation
- python tools/check_mojibake.py docs/rfc/enterprise_boundary.md
- git diff --check -- docs/rfc/enterprise_boundary.md

## AI_HANDOFF.md update
Not updated. This is an RFC-only documentation PR and does not change operational handoff state, runtime posture, CI posture, benchmark posture, or contributor handoff requirements."