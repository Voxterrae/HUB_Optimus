# RFC: HERMES PWA Interface Boundary

## Status

Draft / RFC-only / not implemented.

This RFC defines the boundary for HERMES as a future PWA interface for operating HUB_Optimus Semantic Engine.

This RFC does not authorize HERMES implementation, frontend work, backend API work, authentication, billing, S3 storage, dashboards, vector search, scoring expansion, provider integrations, runtime changes, CI changes, schema changes, benchmark changes, or enterprise deployment.

Parent issue: #1634

## Roadmap execution (issues-first)

Implementation planning is tracked in:

- `docs/rfc/hermes_pwa_gate_issue_pack.md`

This keeps the RFC as boundary documentation and defers all UI/frontend/backend implementation until gate issues are opened, reviewed, and approved.

## Decision

HERMES must be an interface, not semantic authority.

HERMES may allow users to create cases, submit claims, attach evidence, run approved Semantic Engine operations, view structured outputs, inspect audit trails, and export reports.

HERMES must not define truth, scoring, evidence hierarchy, governance, source authority, or Core logic.

## Why this RFC exists

The project needs a future interface, but interface work can easily become the center of gravity.

This RFC prevents HERMES from drifting into:

- hidden scoring;
- dashboard-first product design;
- UI-defined semantics;
- model-first judging;
- unsupported truth verdicts;
- enterprise authority outside the Core;
- unclear source provenance;
- private configuration overriding governance.

Core rule:

> HERMES operates HUB_Optimus. HERMES does not define HUB_Optimus.

## Definitions

### HERMES

A future Progressive Web App interface for operating HUB_Optimus Semantic Engine.

### Semantic Engine

The executable translation of HUB_Optimus Core into contracts, normalizers, evaluators, scoring policies, audit logs, and decision traces.

### Core

The GitHub-versioned source of truth for governance, contracts, RFCs, epistemic separation, and operating boundaries.

### Interface action

A user-facing action in HERMES, such as creating a case, submitting a claim, attaching evidence, requesting analysis, viewing output, or exporting a report.

### Semantic authority

The authority to define what counts as valid logic, evidence hierarchy, scoring, governance, or output structure.

HERMES does not have semantic authority.

## Allowed HERMES capabilities

Future HERMES work may include, after separate approved issues/RFCs:

- case creation;
- claim submission;
- evidence attachment;
- document metadata entry;
- URL/reference entry;
- analysis execution through approved Semantic Engine endpoints;
- structured result display;
- audit trail display;
- decision trace display;
- export to Markdown, JSON, or PDF;
- user role display;
- review queue display;
- status labels such as raw, unreviewed, needs evidence, reviewed;
- source provenance display;
- uncertainty display;
- client workspace navigation in enterprise deployments.

## Prohibited HERMES capabilities

HERMES must not:

- define Core logic;
- redefine source-of-truth hierarchy;
- hide scoring logic inside UI;
- convert claims into verified facts;
- display unsupported truth verdicts;
- override Semantic Engine contracts;
- bypass audit logging;
- bypass human review gates;
- perform autonomous surveillance;
- implement persuasion, targeting, enforcement, or censorship workflows;
- expose confidential/client/patent-sensitive data publicly;
- become the only place where decisions are recorded;
- replace GitHub source-of-truth for project governance.

## Required interface principles

HERMES must preserve:

- claim / evidence / inference / uncertainty / narrative amplification / operational signal separation;
- source provenance;
- evidence tier visibility;
- review status visibility;
- uncertainty visibility;
- auditability;
- reversibility;
- exportability;
- no hidden authority;
- no silent model judgment.

## Screen boundary

Potential screens may include:

- Case List;
- Case Detail;
- Claim Intake;
- Evidence Intake;
- Analysis Result;
- Audit Trail;
- Decision Trace;
- Export;
- Review Queue;
- Settings / Workspace Configuration.

These screens are not authorized by this RFC. They are listed only to define future boundary expectations.

## Case creation boundary

Case creation may collect:

- case title;
- summary;
- domain;
- jurisdiction;
- language;
- confidentiality classification;
- operator;
- timestamp;
- initial claim or evidence reference.

Case creation must not assign truth, liability, legality, or final risk by itself.

## Claim and evidence UI boundary

The UI may support structured entry of claims and evidence.

It must clearly distinguish:

- raw claim;
- source shown;
- evidence item;
- evidence tier;
- verification status;
- uncertainty notes;
- transformation notes.

The UI must not hide weak evidence behind strong visual styling.

## Result display boundary

HERMES may display Semantic Engine outputs.

Result display must preserve the output contract and show:

- claim;
- evidence;
- inference;
- uncertainty;
- narrative amplification where applicable;
- operational signal;
- confidence/risk/severity only when approved by Core-defined policy;
- audit reference.

HERMES must not rewrite results into stronger claims than the engine produced.

## Dashboard boundary

Dashboards are high risk because they can create false authority.

Any future dashboard must:

- show source and uncertainty;
- avoid vanity metrics;
- avoid unsupported rankings;
- avoid hidden scoring;
- avoid replacing detailed analysis;
- link every metric to auditable records.

No dashboard is authorized by this RFC.

## AI provider boundary

If HERMES uses AI providers in the future, provider use must be explicit, logged, and governed by the AI / LLM Provider Independence RFC.

HERMES must distinguish:

- user input;
- provider-generated draft;
- engine output;
- human review;
- final exported result.

Provider output must not appear as final authority without review.

## Enterprise boundary

Enterprise HERMES deployments may include private workspaces, access control, client configuration, and data retention rules.

Enterprise HERMES must not:

- redefine Core logic;
- create client-private semantic doctrine;
- hide provider-specific behavior;
- leak client data to public GitHub;
- store confidential data without approved deployment and retention boundaries.

## Security and privacy boundary

Before implementation, HERMES requires separate RFCs/issues covering:

- authentication;
- authorization;
- session handling;
- secrets;
- data storage;
- audit logs;
- client isolation;
- export controls;
- deletion;
- retention;
- incident response;
- accessibility;
- privacy review.

No such implementation is authorized here.

## API dependency boundary

HERMES should not call ad-hoc logic.

HERMES should operate through approved Semantic Engine/API contracts.

Before HERMES implementation, the API boundary must define:

- input contract;
- output contract;
- error behavior;
- audit behavior;
- versioning;
- authentication;
- rate limits;
- logging;
- rollback behavior.

## Export boundary

Future exports may include:

- Markdown;
- JSON;
- PDF;
- evidence index;
- audit trail summary;
- decision trace summary.

Exports must preserve uncertainty, evidence tiers, and source provenance.

Exports must not convert draft analysis into certified conclusions.

## Governance requirements for future HERMES PRs

Any future HERMES PR must include:

- screen or component scope;
- data contract used;
- source-of-truth impact;
- privacy/confidentiality impact;
- security impact;
- audit behavior;
- accessibility impact where applicable;
- validation plan;
- rollback plan;
- explicit statement that HERMES does not define semantic authority.

## Implementation gates

No implementation is authorized by this RFC.

Before HERMES implementation begins, separate approved issues/RFCs must define or defer:

1. API boundary.
2. Authentication and authorization.
3. Data storage and retention.
4. Audit trail display.
5. Case and claim contracts.
6. Evidence intake contract.
7. Export contract.
8. Enterprise workspace boundary if enterprise is involved.
9. Provider use boundary if AI providers are used.
10. Security and privacy review.

## Out of scope

- HERMES implementation.
- Frontend framework choice.
- API implementation.
- Authentication.
- Authorization.
- Billing.
- S3 storage.
- Vector search.
- Dashboards.
- Provider integrations.
- Runtime changes.
- CI changes.
- Schema changes.
- Benchmark changes.
- Enterprise deployment.
- LLM-as-judge.
- Semantic scoring changes.
- Commercial launch.

## Acceptance criteria

This RFC is acceptable when:

- It defines HERMES as interface only.
- It explicitly denies HERMES semantic authority.
- It defines allowed and prohibited interface capabilities.
- It preserves claim/evidence/inference/uncertainty separation.
- It defines dashboard and result-display risks.
- It requires separate API/security/privacy issues before implementation.
- It preserves GitHub Core as source of truth.
- It avoids authorizing frontend implementation.

## Validation

For this documentation-only RFC:

```bash
python tools/check_mojibake.py docs/rfc/hermes_pwa_interface_boundary.md
git diff --check -- docs/rfc/hermes_pwa_interface_boundary.md
```

## Risk