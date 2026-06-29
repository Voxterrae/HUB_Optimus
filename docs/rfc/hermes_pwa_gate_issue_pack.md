# HERMES PWA Gate Issue Pack (RFC execution, no implementation)

## Status

Draft / planning-only / documentation-only.

This file operationalizes `docs/rfc/hermes_pwa_interface_boundary.md` into explicit gate issues and one first PR scope.

It does not authorize frontend, backend, runtime, CI, schema, benchmark, dashboard, provider integration, or deployment work.

## Decision

HERMES execution remains gated.

No implementation starts until the gate issues below are opened, reviewed, and explicitly approved.

## Gate issue set

### Gate 1 — API boundary contract

- **Issue title:** `HERMES Gate 1: API boundary contract for Semantic Engine access`
- **Objective:** define interface-to-engine request/response, errors, audit behavior, versioning, rollback boundaries, and compatibility policy.
- **Required output:** RFC/contract document under `docs/architecture/` and linked from the HERMES RFC.
- **Acceptance criteria:**
  - input contract documented;
  - output contract documented;
  - error behavior documented;
  - audit behavior documented;
  - versioning and rollback behavior documented;
  - explicit statement that HERMES has no semantic authority.
- **Non-goals:** endpoint implementation, UI, provider logic.

### Gate 2 — Authentication and authorization boundary

- **Issue title:** `HERMES Gate 2: authentication and authorization boundary`
- **Objective:** define authN/authZ model and trust boundaries for HERMES access.
- **Required output:** RFC/contract document.
- **Acceptance criteria:**
  - actor classes and permission model documented;
  - session and token lifecycle boundaries documented;
  - denial/error behavior documented;
  - audit logging obligations documented;
  - no hidden authority paths.
- **Non-goals:** identity provider implementation.

### Gate 3 — Data storage and retention boundary

- **Issue title:** `HERMES Gate 3: storage, deletion, and retention boundary`
- **Objective:** define where case/claim/evidence metadata can be stored and how retention/deletion applies.
- **Required output:** RFC/contract document.
- **Acceptance criteria:**
  - data classes and sensitivity labels documented;
  - retention and deletion policy boundaries documented;
  - confidentiality and isolation boundaries documented;
  - audit trace retention documented.
- **Non-goals:** production storage integration.

### Gate 4 — Audit trail display boundary

- **Issue title:** `HERMES Gate 4: audit trail and decision trace display boundary`
- **Objective:** define what audit and trace data the interface must show and what cannot be suppressed.
- **Required output:** display contract specification.
- **Acceptance criteria:**
  - provenance display rules documented;
  - uncertainty visibility rules documented;
  - review status visibility rules documented;
  - no bypass of human review gates.
- **Non-goals:** dashboard implementation.

### Gate 5 — Case and claim contract

- **Issue title:** `HERMES Gate 5: case and claim input contract`
- **Objective:** define case creation and claim intake fields with explicit non-authority limits.
- **Required output:** contract specification.
- **Acceptance criteria:**
  - required/optional case fields documented;
  - claim status lifecycle documented;
  - prohibition on assigning truth/liability/finality at intake documented;
  - contract maps to claim/evidence/inference separation.
- **Non-goals:** intake UI build.

### Gate 6 — Evidence intake contract

- **Issue title:** `HERMES Gate 6: evidence intake and tier visibility contract`
- **Objective:** define evidence item structure, tier labels, verification state, and transformation notes.
- **Required output:** contract specification.
- **Acceptance criteria:**
  - evidence object contract documented;
  - tier and verification state model documented;
  - transformation and provenance notes required;
  - prohibition on visual overstatement of weak evidence documented.
- **Non-goals:** file upload pipeline implementation.

### Gate 7 — Export contract

- **Issue title:** `HERMES Gate 7: export boundary for markdown/json/pdf outputs`
- **Objective:** define allowed export formats and mandatory preserved fields.
- **Required output:** export contract specification.
- **Acceptance criteria:**
  - export payload boundaries documented;
  - required uncertainty/provenance/tier preservation documented;
  - prohibition on converting draft analysis into certified conclusion documented;
  - audit reference inclusion documented.
- **Non-goals:** renderer implementation.

### Gate 8 — Enterprise workspace boundary (conditional)

- **Issue title:** `HERMES Gate 8: enterprise workspace boundary (if enterprise scope is activated)`
- **Objective:** define client/workspace isolation without redefining Core logic.
- **Required output:** boundary addendum.
- **Acceptance criteria:**
  - workspace isolation and access control boundaries documented;
  - explicit ban on client-private semantic doctrine documented;
  - data leak prevention boundary documented.
- **Non-goals:** enterprise deployment.

### Gate 9 — Provider-use boundary (conditional)

- **Issue title:** `HERMES Gate 9: provider-use boundary (if AI providers are used)`
- **Objective:** bind any provider usage to governed, logged, reviewable behavior.
- **Required output:** provider-use addendum aligned with `docs/rfc/ai_llm_provider_independence.md`.
- **Acceptance criteria:**
  - explicit labeling of provider draft vs engine output vs human review;
  - logging and audit requirements documented;
  - prohibition on provider output as final authority documented.
- **Non-goals:** provider integration.

### Gate 10 — Security and privacy review gate

- **Issue title:** `HERMES Gate 10: security and privacy review before implementation`
- **Objective:** define pre-implementation security/privacy checklist and mandatory approvals.
- **Required output:** review checklist + approval workflow.
- **Acceptance criteria:**
  - threat surface documented;
  - privacy impact items documented;
  - incident response obligations documented;
  - explicit go/no-go gate documented.
- **Non-goals:** penetration testing execution.

## First scoped PR statement (after Gate 1 approval)

- **PR title:** `docs: draft HERMES API boundary contract (gate 1 only)`
- **PR objective:** documentation-only API boundary contract draft for interface-to-engine behavior.
- **PR scope:**
  - add one contract document under `docs/architecture/`;
  - link it from `docs/rfc/hermes_pwa_interface_boundary.md`;
  - no runtime or interface implementation.
- **PR non-goals:**
  - no frontend code;
  - no backend endpoint implementation;
  - no auth/storage/provider integration;
  - no dashboard work;
  - no CI/schema/benchmark/runtime changes.
- **PR acceptance checklist (mapped to RFC requirements):**
  - [ ] contract preserves claim/evidence/inference/uncertainty/operational-signal separation;
  - [ ] provenance, auditability, reversibility, and review visibility are explicit;
  - [ ] hidden scoring and unsupported truth verdicts are explicitly prohibited;
  - [ ] HERMES semantic non-authority is explicitly stated;
  - [ ] privacy/security impact section included;
  - [ ] validation and rollback plan included.

## Sequencing policy

- Gates 1-7 are mandatory before any HERMES implementation PR.
- Gates 8-9 are mandatory only if enterprise/provider scope is activated.
- Gate 10 is mandatory immediately before implementation authorization.

## Validation (for this file)

```bash
python tools/check_mojibake.py docs/rfc/hermes_pwa_gate_issue_pack.md
git diff --check -- docs/rfc/hermes_pwa_gate_issue_pack.md
```
