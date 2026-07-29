# RFC: Enterprise Boundary

## Status

Draft / RFC-only / not accepted / not implemented.

Parent issue: #1634

The proposal text was recorded by PR #1635. That merge did not accept the
proposal, authorize an enterprise product, or create commercial or operational
authority.

## Purpose

Record a proposed separation between the public HUB_Optimus Core and any
future downstream enterprise configuration without changing the current
runtime, governance, rights, or deployment state.

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

## Decision and implementation record

- Decision PR: not recorded.
- Owner: not recorded.
- Ratifier: not recorded.
- Implementation PRs: none recorded.
- Current capability: no enterprise product is present in this repository.

These missing records are deliberate unknowns, not implicit approvals.

## Acceptance boundary

This RFC can move beyond `Draft` only through a separate human decision record
that identifies scope, owner, ratifier, rights, security boundaries, deployment
evidence, and implementation gates. A merge of this file alone is insufficient.

## Risks

- treating a downstream configuration as authority over Core;
- presenting planned commercial or security capabilities as implemented;
- introducing a semantic fork that no longer matches repository truth;
- inferring deployment, licensing, or customer readiness from proposal text.

## Validation

- python tools/check_mojibake.py docs/rfc/enterprise_boundary.md
- git diff --check -- docs/rfc/enterprise_boundary.md

## AI_HANDOFF.md update

Not updated. This is an RFC-only documentation record and does not change
operational handoff state, runtime posture, CI posture, benchmark posture, or
contributor handoff requirements.
