# RFC: HUB_Optimus Evidence Bridge

**GitHub Authority + Dataverse Operational Ledger + OpenAI Read-Only Plugin v0.1**

## Status

Lifecycle: **Draft**.

Proposal issue: #1922.

Inspection baseline:

```text
repository: Voxterrae/HUB_Optimus
main: 5cb923c38e8ec0f45468c29268c79dcc3b06b822
mode: RFC_DRAFT_ONLY
Dataverse writes: 0
OpenAI production calls: 0
merge/deployment/publication writes: 0
```

This RFC is reviewable proposal text only. It is not accepted or ratified, does
not authorize implementation, and creates no permission to merge, deploy,
modify a tenant, expose an MCP endpoint, create an OpenAI production plugin, or
publish a result. The lifecycle registry reports evidence; it does not create
authority.

## 1. Decision summary

Define a bounded evidence bridge with four separate responsibilities:

```text
GitHub protected records and contracts
                |
                v
Dataverse private operational evidence ledger
                |
                v
HUB_Optimus Evidence Gateway MCP
                |
                v
OpenAI methodology Skill + read-only tools
                |
                v
Human-reviewed draft or evidence view
```

GitHub remains the authority for governance, versioned contracts, methodology,
capability declarations, tests, and implementation history. Dataverse may hold
private operational evidence records after separate authorization, but it does
not become an independent constitutional, methodological, or truth authority.
The model-facing MCP surface is owned by HUB_Optimus and exposes only a
sanitized, contract-bound projection. The OpenAI integration assists retrieval,
validation, provenance review, and structured drafting; it does not adjudicate
truth or replace human judgment.

The v0.1 product archetype is **tool-only and headless-first**. A custom widget,
Site tools/WebMCP integration, remote write surface, and public directory
submission are later and separately governed decisions.

## 2. Problem statement

The repository contains related but separate workstreams:

- draft PR #1879 proposes a tenant-neutral Optimus Evidence Lab Dataverse
  package and governed schema applicator;
- issue #1880 defines an isolated Global Graph foundation and a future
  read-only MCP boundary;
- issue #1881 controls the review order and safety gates for the open pull
  request portfolio;
- draft PR #1918 contains a disabled, private controlled-URL intake candidate;
- draft PR #1921 contains a browser-local, human-confirmed atomic-claim drafting
  candidate.

None of those records alone defines the end-to-end authority relationship among
GitHub, Dataverse, an evidence gateway, and an OpenAI plugin. Building directly
from the individual candidates could create:

- duplicate or incompatible evidence schemas;
- ambiguity about which system is authoritative;
- exposure of a broader Dataverse tool surface than the product requires;
- tenant GUID, personal-data, or internal-diagnostic leakage;
- repeated media reports being presented as independent corroboration;
- capability or truth claims that exceed the executable evidence;
- hidden coupling between draft branches;
- a public integration before rights, security, cost, and review gates close.

This RFC supplies the missing integration boundary without changing any of the
underlying candidates.

## 3. Goals

v0.1 is intended to:

1. establish one auditable authority chain from repository contract to
   operational record to model-facing result;
2. preserve explicit separation among source material, claims, evidence,
   inference, narrative analysis, and operational signal;
3. expose the smallest useful read-only MCP tool surface;
4. use stable public identifiers rather than tenant-specific identifiers;
5. bind every returned object to schema, methodology, source, hash, and
   repository-version provenance;
6. detect contract drift, stale projections, missing evidence, duplicates, and
   unresolved rights;
7. fail closed on ambiguity, authorization failure, unsafe input, or incomplete
   provenance;
8. require human review for any interpretation, memory promotion, publication,
   or consequential use;
9. remain reversible and provider-neutral at the domain-contract layer;
10. begin with synthetic fixtures and a private canary.

## 4. Explicit non-goals

v0.1 does not authorize or claim:

- automatic truth verification or a universal fact-checking authority;
- guilt, intent, credibility, reliability, peace, conflict, or actor scoring;
- prediction, persuasion, surveillance, sanctioning, enforcement, or autonomous
  decision-making;
- creation, update, deletion, schema mutation, file transfer, or skill
  management in Dataverse;
- direct exposure of the complete native Dataverse MCP surface to an OpenAI
  client;
- arbitrary URL retrieval, crawling, browser automation, paywall bypass, video
  transcription, OCR, or social-platform scraping;
- server-side persistence of case drafts submitted for validation;
- institutional memory promotion or model training;
- public OpenAI plugin submission, production hosting, OAuth configuration,
  billing activation, DNS, Site tools/WebMCP, or a custom widget;
- modification, stacking, acceptance, merge, deployment, or supersession of
  #1879, #1880, #1881, #1918, or #1921;
- a claim of affiliation, endorsement, ownership, or partnership with
  Microsoft, GitHub, OpenAI, or another third party.

## 5. Terms

**Authority plane**  
The protected GitHub records and live GitHub evidence that define governance,
contracts, versions, capability state, and change history within their stated
boundaries.

**Operational ledger**  
A private Dataverse deployment that may record governed operational evidence.
It is a ledger of operational state, not a source of constitutional authority or
automatic truth.

**Evidence Gateway**  
The HUB_Optimus-controlled MCP server that authenticates, authorizes, validates,
queries, sanitizes, and projects approved ledger and repository data.

**OpenAI plugin**  
The combined methodology Skill and MCP tool integration used by ChatGPT or a
compatible OpenAI host. In v0.1 it has no custom UI and no write tools.

**Case draft**  
A transient, unratified structure submitted for validation. Validation does not
store, publish, endorse, or convert it into canonical knowledge.

**Provenance chain**  
The bounded set of version, source, hash, relation, supersession, and review
records needed to explain where an object came from and what authority it does
or does not possess.

## 6. Source-of-truth and authority model

This RFC inherits, and does not modify, the repository's
[source-of-truth hierarchy](../context/SOURCE_OF_TRUTH.md), founder-authority
records, current owner handoff, and live GitHub controls.

For the Evidence Bridge, the operational precedence is:

1. applicable founder, ownership, and constitutional authority records at the
   controlling protected commit;
2. the exact GitHub `main` commit and live GitHub records within their own
   current boundaries;
3. canonical repository schemas, methodology documents, runtime contracts, and
   tests read together;
4. a Dataverse record whose contract and repository binding are current;
5. the Evidence Gateway projection of that record;
6. model-generated summaries, drafts, and explanations.

Rules:

- a lower layer cannot override a higher applicable layer;
- a Dataverse row without a recognized contract binding is not canonical;
- a plugin response is a derived view, not an authority record;
- a passing test proves only the behavior asserted by that test;
- a Draft RFC, open issue, open PR, chat statement, or model output does not
  authorize implementation or deployment;
- when two records conflict, retain both, apply the narrower higher-precedence
  evidence, and expose the conflict rather than silently selecting a preferred
  narrative;
- absence of evidence is not positive evidence of capability, truth, or
  permission;
- stale or unresolvable authority bindings fail closed as `CONTRACT_DRIFT` or
  `PROVENANCE_INCOMPLETE`.

## 7. Component responsibilities

### 7.1 GitHub authority plane

GitHub stores and versions:

- governance and founder-authority records;
- source-of-truth and capability declarations;
- methodology and epistemic-state definitions;
- JSON Schemas and stable public contract definitions;
- migration and rollback specifications;
- synthetic fixtures and evaluations;
- implementation source and tests;
- release manifests and content hashes;
- issues, PRs, reviews, checks, and decision evidence.

A Dataverse environment must not redefine these contracts independently. Each
operational projection must carry the exact repository commit and schema version
against which it was created or validated.

### 7.2 Dataverse operational ledger

After a separate gate authorizes it, Dataverse may record private operational
objects such as:

- case;
- immutable source snapshot or source receipt;
- atomic claim;
- claim-to-evidence relation;
- human review or attestation.

These are logical functions, not approved physical table names. Exact entities,
columns, choices, alternate keys, ownership, auditing, change tracking, delete
behavior, retention, and security roles must be derived from the reviewed
artifact in #1879 and confirmed against a fresh, authenticated, read-only
inspection of the intended environment.

This RFC performs no Dataverse inspection or mutation and reserves no schema
names or choice values.

### 7.3 HUB_Optimus Evidence Gateway

The Gateway is the product and policy boundary. It must:

- authenticate the caller and authorize each tool independently;
- use an explicit allowlist of readable object types, fields, filters, and
  relation depths;
- translate internal identifiers into stable public IDs;
- reject tenant IDs, environment IDs, raw GUIDs, secrets, tokens, personal data,
  private content, and unnecessary diagnostics from responses;
- validate all inputs and upstream responses against versioned contracts;
- bind responses to repository commit, schema version, methodology version, and
  source hashes;
- enforce query, result-count, byte, time, rate, and cost limits;
- preserve contradiction, uncertainty, supersession, and missing-evidence
  signals;
- expose no native schema, write, file, or administrative tools;
- fail closed when authorization, provenance, rights, or contract state is
  unresolved.

The Gateway may later use a reviewed Dataverse adapter internally. The public
MCP contract must remain independent of changing vendor tool names or broad
vendor capabilities.

### 7.4 OpenAI methodology Skill

The Skill provides the model-facing method and language constraints. It must
require the sequence:

```text
Reality -> Evidence -> Inference -> Narrative -> Operational Signal
```

It must also require that the model:

1. identify the source and its provenance;
2. separate atomic claims;
3. distinguish direct evidence, attribution, contradiction, context, and
   inference;
4. state missing evidence and uncertainty;
5. avoid counting duplicated reporting as independent corroboration;
6. avoid converting official attribution into a judicial or independently
   verified fact;
7. avoid converting a denial into an automatic refutation;
8. produce only a draft or review signal;
9. require a human decision before publication or consequential use.

The Skill cannot create authority, repair missing evidence, or override the
Gateway.

### 7.5 OpenAI host and optional UI

The v0.1 integration is useful without a widget. A later UI may be considered
only when structured comparison, inspection, editing, or confirmation materially
requires it. Any UI remains a view over the same tool contracts and cannot gain
additional authority or hidden write capability.

## 8. Public projection contract

### 8.1 Common fields

Every returned domain object must expose only the fields needed for the tool and
must be compatible with this minimum projection:

```text
public_id
object_type
schema_version
methodology_version
repository_commit_sha
source_id
source_type
source_captured_at
source_sha256
claim_text
claim_status
supporting_evidence_ids
contradicting_evidence_ids
missing_evidence
uncertainty_statement
review_state
review_authority
supersedes_id
human_review_required
```

Not every field applies to every object, but a tool must not synthesize a value
that the upstream record does not support. `null` or an explicit unresolved
state is preferable to plausible completion.

### 8.2 Epistemic states

The public contract must preserve these claim classes:

- `verified_fact`;
- `human_or_project_declaration`;
- `calculation_or_synthetic_observation`;
- `estimate_or_inference`;
- `proposal`;
- `unknown_or_unverified`.

An implementation may add narrower subtypes through a versioned contract, but
must not collapse declarations, estimates, or proposals into verified facts.
The state describes the evidence relationship recorded by the system; it is not
a universal truth verdict.

### 8.3 Relation types

The minimum relation vocabulary is:

- `supports`;
- `contradicts`;
- `attributes`;
- `contextualizes`;
- `supersedes`;
- `duplicate_of`.

Attribution means that a source states a claim. It is not independent
corroboration. Duplicate sources or repeated syndication must remain linked and
must not increase an evidence count merely through repetition.

### 8.4 Identity and immutability

- Public IDs are opaque, namespace-qualified, stable, and non-enumerable where
  practical.
- Dataverse GUIDs are never public identity.
- Source material is content-addressed by SHA-256 or a later explicitly
  versioned algorithm.
- A correction creates a new version and `supersedes_id`; it does not silently
  overwrite historical evidence.
- The complete object contract is bound to `repository_commit_sha`.
- Same public key plus identical content is `NO_OP`; same key plus different
  content is `CONFLICT` until reviewed.
- Missing, malformed, or unsupported hashes fail closed.

## 9. Dataverse access boundary

The OpenAI plugin must not connect directly to the complete native Dataverse MCP
surface in v0.1. Dataverse can expose capabilities broader than this product
needs, including administrative and mutating operations. The Gateway therefore
acts as a restrictive adapter and stable contract membrane.

Allowed upstream behavior for v0.1:

- bounded reads from specifically approved entities and fields;
- exact retrieval by an approved alternate or public key;
- bounded filtered queries;
- retrieval of review, provenance, and supersession relations;
- read-only health and contract-version checks.

Disallowed upstream behavior for v0.1:

- create, update, upsert, delete, associate, or disassociate;
- metadata discovery outside the allowlist;
- table, column, relationship, choice, or solution changes;
- file upload or download;
- skill creation, modification, or execution;
- arbitrary FetchXML, SQL, OData, or expression execution supplied by a model;
- cross-environment or cross-tenant fallback;
- exposure of service-principal, role, environment, solution, publisher, or
  internal table identifiers.

Microsoft licensing, metering, capacity, environment policy, DLP, Managed
Environment status, auditing, and client enablement are external mutable facts.
They must be inspected at the relevant gate and must not be inferred from this
RFC. The private canary requires a query budget, cost alarm, rate limit, and kill
switch before any live connection.

## 10. OpenAI plugin shape

v0.1 consists of:

1. a methodology Skill;
2. a remote HUB_Optimus MCP server;
3. no custom UI;
4. no direct OpenAI API call from the HUB_Optimus backend unless separately
   approved;
5. no Site tools/WebMCP surface;
6. no public submission.

The absence of a backend model call means that an OpenAI API key is not a v0.1
requirement. Authentication for the private MCP server remains an implementation
question and must use a separately reviewed mechanism; no client secret or token
belongs in repository files, browser JavaScript, tool results, or logs.

## 11. v0.1 MCP tools

All five tools are domain-read-only and must declare:

```text
readOnlyHint: true
destructiveHint: false
openWorldHint: false
idempotentHint: true
```

Annotations describe intended effects; they do not replace authentication,
authorization, validation, confirmation, or server-side enforcement.

| Tool | Purpose | Minimum input | Domain side effect |
| --- | --- | --- | --- |
| `search` | Search the approved closed corpus of cases, sources, claims, reviews, methodology, and capability records. | `query`, optional allowlisted `object_types`, bounded `limit`, optional cursor. | None. |
| `fetch` | Retrieve one exact object by stable public ID. | `public_id`, optional expected schema version. | None. |
| `validate_case_draft` | Validate a transient candidate against schema, provenance, epistemic, duplication, and review rules. | Versioned case draft within strict byte and record bounds. | None; no persistence or promotion. |
| `get_provenance_chain` | Return a bounded graph of sources, hashes, versions, relations, reviews, and supersession for one object. | `public_id`, bounded depth. | None. |
| `get_capability_status` | Report whether a named capability is implemented, prototype, Draft/RFC, not implemented, or unknown/unverified at a stated commit. | One or more bounded capability identifiers. | None. |

### 11.1 `search`

`search` uses a closed-domain index or query adapter. It does not browse the
internet, resolve a URL, execute arbitrary query text against Dataverse, or
return unrestricted raw source content. Results contain stable IDs, concise
snippets, object types, current review state, and provenance summaries. The
server enforces result and pagination bounds.

### 11.2 `fetch`

`fetch` returns one exact, authorized object and the minimum relations necessary
to interpret it. A request for an internal GUID, an object outside the allowlist,
or an object from another tenant must return a controlled error rather than
attempting discovery.

### 11.3 `validate_case_draft`

Validation is pure with respect to the domain ledger. It may return:

- schema errors;
- missing source or hash bindings;
- duplicate or ambiguous evidence;
- unsupported epistemic transitions;
- stale repository bindings;
- unresolved rights or review requirements;
- a normalized preview that remains non-canonical.

It must not save, publish, endorse, promote to memory, or silently repair the
submitted draft.

### 11.4 `get_provenance_chain`

The provenance chain is depth-, node-, edge-, and byte-bounded. Cycles,
dangling references, duplicate edges, unknown algorithms, or missing required
records are surfaced explicitly. The tool does not infer a missing chain.

### 11.5 `get_capability_status`

This tool reads a versioned capability record and returns one of:

```text
implemented
prototype
partially_implemented
accepted_not_implemented
draft_or_rfc
not_implemented
unknown_or_unverified
```

It must include the inspected repository commit and evidence paths. It prevents
a model from presenting a design objective, file name, draft PR, or green test
as a deployed capability.

## 12. Result envelope and controlled errors

A successful result uses a concise envelope:

```json
{
  "schema_version": "hub-optimus-evidence-bridge-result.v1",
  "request_id": "opaque-correlation-id",
  "repository_commit_sha": "40-hex-commit",
  "data": {},
  "warnings": [],
  "human_review_required": true
}
```

Large or sensitive widget-only payloads do not exist in v0.1. Future UI metadata
must never be used to hide facts that materially change the model's
interpretation.

Minimum controlled error codes:

```text
INVALID_INPUT
UNAUTHORIZED
FORBIDDEN
NOT_FOUND
RATE_LIMITED
RESULT_LIMIT_EXCEEDED
CONTRACT_DRIFT
PROVENANCE_INCOMPLETE
RIGHTS_UNRESOLVED
DUPLICATE_AMBIGUITY
UPSTREAM_UNAVAILABLE
UPSTREAM_TIMEOUT
INTERNAL_FAIL_CLOSED
```

Errors must not include tokens, connection strings, stack traces, tenant IDs,
raw GUIDs, private URLs, raw personal data, or unrestricted upstream responses.

## 13. Security, privacy, and rights

### 13.1 Trust boundary

All source text, claim text, annotations, imported metadata, tool arguments, and
model output are untrusted data. Instructions embedded in evidence are never
system or operator instructions. The server validates the request independently
of model narration.

### 13.2 Minimum controls

- least-privilege identity and per-tool authorization;
- strict input schemas with bounded strings, arrays, depth, and bytes;
- allowlisted entities, columns, relations, filters, and sort orders;
- no arbitrary query language supplied by the client;
- output minimization and field-level redaction;
- cross-tenant denial by construction;
- rate, concurrency, time, result, and cost limits;
- replay-safe, idempotent read handlers;
- audit correlation without raw source or prompt logging by default;
- secrets stored only in a reviewed server-side secret store;
- no anonymous public access in the private canary;
- fail-closed dependency and health checks;
- documented retention and deletion rules before real records are used;
- an independent kill switch.

### 13.3 Personal and sensitive data

The initial corpus is synthetic and contains no personal, health, biometric,
financial, precise-location, private-message, credential, or tenant data. A
later real-data gate must define lawful basis, purpose limitation, data
classification, retention, deletion, access review, export controls, and breach
handling. The absence of an explicit prohibition does not imply permission.

### 13.4 Rights boundary

Every source or artifact must carry an explicit rights or reuse state. Unresolved
rights produce `RIGHTS_UNRESOLVED` and block public redistribution or plugin
submission. This RFC does not resolve the relationship between historical open
materials and the current restricted-rights repository notice.

## 14. Threat model

| Threat | Required response |
| --- | --- |
| Prompt injection in source content | Treat as data; never execute or elevate embedded instructions. |
| Identifier enumeration or IDOR | Opaque public IDs, authorization before existence disclosure, bounded access. |
| Tenant or GUID leakage | Gateway translation and response-schema rejection. |
| Over-fetching | Field, object, relation, result, and byte allowlists. |
| Contract or schema drift | Exact version/commit binding; fail closed as `CONTRACT_DRIFT`. |
| Duplicate amplification | Content fingerprints and `duplicate_of`; no false corroboration count. |
| Provenance laundering | Preserve attribution and source type; no automatic promotion to verified fact. |
| Cross-tenant fallback | No implicit environment discovery or fallback. |
| Cost exhaustion | Per-user and global quotas, budget alarm, concurrency bound, kill switch. |
| Stale capability claims | `get_capability_status` bound to current evidence and explicit commit. |
| Hidden domain write through a read tool | Side-effect tests and denied write credentials for the v0.1 runtime identity. |
| Sensitive logs | Metadata-only telemetry by default; no raw evidence, prompt, secret, or PII logging. |

## 15. Observability and economics

The private canary must record, at minimum:

- opaque request/correlation ID;
- tool name and contract version;
- authenticated principal class, not unnecessary identity detail;
- repository commit and Dataverse adapter version;
- start/end time, latency, result count, response bytes, and controlled status;
- upstream dependency status;
- quota and budget counters;
- security denial category.

It must not record raw source text, complete prompts, secrets, private URLs, or
personal data by default. Alert thresholds, daily query budget, maximum canary
window, cost ceiling, and emergency stop procedure must be documented before a
live Dataverse connection.

## 16. Canary and evaluations

### 16.1 Sequence

1. static contract validation;
2. deterministic synthetic fixtures;
3. headless MCP tests with no Dataverse connection;
4. read-only Dataverse adapter test against synthetic or isolated records;
5. private OpenAI plugin canary;
6. sanitized real-case review only after separate authorization;
7. optional UI evaluation;
8. public-submission evaluation only after all earlier gates close.

### 16.2 Initial case pattern

`HO-DE-RU-20260903-001` may be represented first as a synthetic or sanitized
fixture that tests structure without asserting a geopolitical conclusion. A
later controlled case must prove that the system:

- distinguishes the existence of an incident from attribution of responsibility;
- distinguishes an official statement from independently reproducible evidence;
- records classified or unpublished evidence as an auditability limitation;
- records a denial as a counterclaim, not an automatic refutation;
- does not merge separate incidents without an evidenced relation;
- detects repeated reporting derived from one primary source;
- exposes missing evidence and uncertainty;
- produces no guilt score or automatic truth verdict;
- requires human review.

### 16.3 Positive evaluations

At minimum:

- exact fetch of an authorized synthetic object;
- bounded search returning deduplicated results;
- valid draft producing no persistence and no errors;
- contradiction and missing-evidence relations preserved;
- provenance chain resolves to exact hashes and versions;
- capability status distinguishes Draft from implemented;
- repeated identical requests produce no domain-state change.

### 16.4 Negative evaluations

At minimum:

- prompt injection embedded in a source;
- internal GUID, tenant ID, or unauthorized object request;
- malformed or oversized draft;
- arbitrary query-language injection;
- same public ID with conflicting content;
- missing hash or stale repository commit;
- unresolved reuse rights;
- attempted create, update, delete, publish, or URL-fetch action;
- cross-tenant access attempt;
- result-volume and rate-limit exhaustion.

No public submission may rely only on these RFC examples. Submission test cases
must be derived from the final hosted implementation and current official
requirements.

## 17. Rollout gates

| Gate | Action | Exit condition |
| --- | --- | --- |
| G0 — RFC record | Review this documentation proposal. | Owner-reviewed decision record; Draft text alone opens no implementation gate. |
| G1 — Dataverse inspection | Fresh authenticated, read-only inspection of the intended DEV environment. | Environment, solution, publisher, entities, keys, roles, auditing, policies, licensing, metering, and write count evidenced. |
| G2 — Evidence Lab review | Complete the separately governed review of #1879. | Exact package, idempotency, rollback, privacy, and Dataverse review accepted through its own process. |
| G3 — Projection contract | Freeze public IDs, fields, states, errors, hashes, and drift rules. | Versioned schema and synthetic fixtures reviewed; no GUID, secret, or PII exposure. |
| G4 — Headless Gateway | Implement the five tools against synthetic data. | Security and contract tests pass; domain write credentials absent; no UI. |
| G5 — Private plugin canary | Connect a private OpenAI client for a bounded window. | Authentication, quotas, cost, logs, kill switch, provenance, and zero domain writes verified. |
| G6 — Controlled real data | Use a separately authorized sanitized case. | Rights, privacy, retention, human review, and deletion controls evidenced. |
| G7 — Optional UI | Add a decoupled inspection widget only if justified. | Tool-only path remains complete; UI adds no hidden authority or writes. |
| G8 — Public submission | Prepare a new review package. | Production MCP, verified identity/domain, support, privacy, terms, rights, regional availability, and current submission tests complete. |

Each gate requires its own current evidence and explicit authorization. Passing a
later technical test cannot retroactively accept this RFC or an earlier gate.

## 18. Dependency and non-interference map

| Record | Relevance | This RFC's boundary |
| --- | --- | --- |
| #1879 | Candidate Dataverse Evidence Lab package and applicator. | Reference only; no modification, stacking, inspection, mutation, acceptance, merge, or deployment. |
| #1880 | Candidate governed evidence foundation and read-only MCP principles. | Reuse compatible boundaries; do not alter its product scope or files. |
| #1881 | Current owner-facing portfolio review ledger. | Its execution order and global safety gates remain controlling. |
| #1918 | Controlled authenticated URL intake candidate. | Excluded from v0.1; no arbitrary URL tool or dependency. |
| #1921 | Human-confirmed atomic-claim drafting candidate. | Potential future input producer; not required, modified, or accepted here. |

Implementation must start from a current reviewed `main`, not from one of these
draft branches, unless a later issue explicitly authorizes a dependency and
records the exact commit.

## 19. Acceptance criteria for this RFC PR

- [ ] Only `docs/rfc/hub_optimus_evidence_bridge.md`,
      `docs/rfc/registry.v1.json`, and the minimum registry test adjustment are
      changed.
- [ ] Lifecycle is `Draft`; owner, ratifier, decision PR, and implementation PRs
      remain unset.
- [ ] The registry covers the new RFC exactly once.
- [ ] Registry lifecycle counts remain explicit and unratified.
- [ ] No runtime, application schema, workflow, site, infrastructure, secret,
      tenant, permission, ruleset, or capability-ledger change is included.
- [ ] No Dataverse, Azure, AWS, OpenAI API, deployment, merge, or publication
      action is executed.
- [ ] No personal data, tenant identifier, credential, private source, or
      proprietary third-party content is added.
- [ ] Links and UTF-8 checks pass.
- [ ] Hosted required checks are complete before any merge decision.
- [ ] The PR states why AI handoff files are unchanged.

## 20. Future implementation acceptance criteria

A later implementation PR must additionally demonstrate:

- exact reviewed contracts and synthetic fixtures;
- no domain write credentials or code paths in the read-only runtime;
- authorization before existence disclosure;
- strict schemas and bounded outputs;
- deterministic deduplication and provenance behavior;
- contract-drift and fail-closed tests;
- prompt-injection, identifier, query, cross-tenant, rate, and cost tests;
- zero secrets, tenant IDs, raw GUIDs, and personal data in outputs;
- auditable zero-write canary evidence;
- current-head review and rollback instructions;
- no capability, deployment, affiliation, or truth claim beyond direct evidence.

## 21. Risks and mitigations

**Authority drift**  
Mitigation: exact commit binding, explicit precedence, and fail-closed status.

**Schema/vendor drift**  
Mitigation: stable HUB_Optimus public contract and an internal versioned adapter.

**Data leakage**  
Mitigation: allowlists, field minimization, output validation, opaque IDs, and
synthetic-first testing.

**Prompt injection**  
Mitigation: untrusted-content boundary and independent server-side validation.

**Narrative overclaiming**  
Mitigation: explicit epistemic states, capability-status tool, missing-evidence
fields, and mandatory human review.

**Duplicate corroboration**  
Mitigation: fingerprints, source lineage, and `duplicate_of` relations.

**Unexpected cost or availability**  
Mitigation: live licensing inspection, budgets, quotas, alarms, bounded canary,
and kill switch.

**Premature coupling to draft work**  
Mitigation: non-interference map and implementation from reviewed `main` only.

## 22. Open questions

The RFC cannot resolve these without later evidence:

- exact Dataverse physical schema and alternate keys after #1879 review;
- intended DEV environment and solution/publisher readiness;
- authentication mechanism and scopes for the private MCP server;
- hosting, region, network, DLP, audit, retention, and deletion policy;
- Microsoft licensing, capacity, metering, and budget for the intended client;
- whether any real case may contain personal or sensitive data;
- source-reuse and redistribution rights for the initial corpus;
- final OpenAI organization identity, verified domain, support, privacy, terms,
  and publication regions;
- whether a UI materially improves review after the tool-only canary;
- whether Site tools/WebMCP should remain separate or share a later contract.

Unknowns remain blockers, not implicit permission.

## 23. Rollback

The RFC PR is documentation-only. Rollback is a pure revert of the RFC file,
registry entry, and associated test-count adjustment. The issue and PR remain as
historical evidence. Revert does not modify Dataverse, delete operational data,
change an external integration, or authorize an alternative architecture.

## 24. Internal references

- [Source-of-truth hierarchy](../context/SOURCE_OF_TRUTH.md)
- [Founder Ownership and Authority Charter](../governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md)
- [Current AI handoff](../context/AI_HANDOFF.md)
- [RFC lifecycle](README.md)
- [Ingestion and Evidence Intake Boundary](ingestion_evidence_intake_boundary.md)
- [Operator Controlled URL Intake](operator_controlled_url_intake.md)
- #1879
- #1880
- #1881
- #1918
- #1921
- #1922

## 25. External primary references

- [OpenAI plugin concepts](https://developers.openai.com/plugins/concepts/plugins)
- [OpenAI tool planning](https://developers.openai.com/plugins/plan/tools)
- [OpenAI MCP server construction](https://developers.openai.com/plugins/build/mcp-server)
- [OpenAI plugin security and privacy](https://developers.openai.com/plugins/guides/security-privacy)
- [OpenAI plugin submission](https://developers.openai.com/plugins/deploy/submission)
- [Microsoft Dataverse MCP server](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/data-platform-mcp)
- [Microsoft Dataverse MCP tool updates](https://learn.microsoft.com/en-us/power-platform/release-plan/2026wave1/data-platform/improve-dataverse-mcp-server-quality-updated-tools)

## 26. Decision record

```text
lifecycle: Draft
proposal_issue: 1922
record_pr: null
decision_pr: null
implementation_prs: []
owner: null
ratifier: null
implementation_authorized: no
deployment_authorized: no
public_submission_authorized: no
```

A later decision must identify the exact reviewed head, owner, ratifier, accepted
scope, rejected scope, implementation gates, and supersession effects. Until
then, the correct operational state is **proposal recorded; no authority
created**.
