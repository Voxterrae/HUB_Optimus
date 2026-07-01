# RFC: Ingestion and Evidence Intake Boundary

## Status

Draft / RFC-only / not implemented.

This RFC defines how HUB_Optimus may intake claims, text, URLs, screenshots, documents, PDFs, evidence records, mobile notes, and future connector outputs.

This RFC does not authorize crawler infrastructure, automated scraping, browser automation, OCR pipelines, provider integrations, API work, HERMES work, S3 storage, vector search, scoring, runtime changes, CI changes, schema changes, benchmark changes, or enterprise deployment.

Parent issue: #1634

## Decision

HUB_Optimus ingestion must be controlled, evidence-aware, and non-authoritative.

Ingestion may collect, normalize, classify, and prepare material for analysis.

Ingestion must not decide truth, assign final verification, perform autonomous surveillance, execute uncontrolled crawling, bypass access controls, or convert screenshots/social posts into facts without evidence decomposition.

## Why this RFC exists

HUB_Optimus increasingly handles claims from chats, screenshots, social posts, public articles, local documents, and mobile intake.

Without a boundary, ingestion could drift into:

- uncontrolled scraping;
- automated truth adjudication;
- privacy-invasive collection;
- source laundering;
- unreviewed evidence promotion;
- client data leakage;
- crawler-first architecture;
- narrative amplification.

The system needs a stable rule:

> Intake is not verification.

## Definitions

### Claim

A statement that asserts something about reality, responsibility, causality, risk, intent, legality, performance, identity, or operational relevance.

### Evidence

Material that may support, weaken, contextualize, or contradict a claim.

Evidence can include:

- primary source documents;
- official statements;
- reputable reporting;
- public records;
- screenshots;
- contracts;
- policies;
- datasets;
- logs;
- correspondence;
- user-provided context.

### Intake

The act of receiving raw material into HUB_Optimus.

### Normalization

The conversion of raw material into structured fields, such as claim text, source shown, date, evidence tier, domain, jurisdiction, uncertainty, and notes.

### Verification

A later review process that evaluates evidence quality, source reliability, contradiction, uncertainty, and operational relevance.

Verification is not the same as ingestion.

### Source laundering

Treating a weak, indirect, or unclear source as stronger evidence because it passed through the system.

Example:

> screenshot from unknown account -> dataset record -> treated as confirmed fact

This is prohibited.

## Core rule

> Ingestion collects material. Evaluation separates claim, evidence, inference, uncertainty, narrative amplification, and operational signal.

## Allowed intake sources

Future intake may include, after separate approved issues or RFCs where needed:

- manual text entry;
- mobile terminal notes;
- screenshots provided by the user;
- public URLs provided by the user;
- PDFs and documents provided by the user;
- public datasets;
- public government or institutional pages;
- client-provided documents in private enterprise deployments;
- email or workspace connector outputs if authorized;
- controlled source lists;
- structured case forms.

## Prohibited intake behavior

Ingestion must not:

- run uncontrolled crawlers;
- bypass paywalls, authentication, robots, or access controls;
- scrape private platforms without authorization;
- collect personal data without a lawful and explicit purpose;
- perform surveillance or profiling;
- infer identities from images or private data;
- treat viral content as verified;
- hide source uncertainty;
- overwrite original source context;
- convert claims into conclusions;
- enrich data with hidden provider assumptions;
- store confidential/client material in public GitHub;
- expose credentials, secrets, or private documents;
- build autonomous monitoring without a condition-watch RFC or approved issue.

## Evidence tiering

Intake may label evidence tier conservatively.

Allowed evidence tier concepts:

- primary;
- official_secondary;
- reputable_press;
- advocacy;
- user_provided;
- screenshot;
- unknown.

Tiering is not verification.

A screenshot may be evidence of what was shown to the user, but not proof that the underlying claim is true.

A URL may identify a source, but not prove accuracy.

A user-provided document may be relevant, but still requires provenance and review.

## Required intake metadata

Where possible, intake records should preserve:

- intake_id;
- intake_timestamp;
- intake_operator;
- source_type;
- source_shown;
- original_reference;
- claim_text;
- evidence_summary;
- evidence_tier;
- jurisdiction if known;
- language if known;
- verification_status;
- uncertainty_notes;
- privacy_classification;
- confidentiality_classification;
- transformation_notes.

## Privacy and confidentiality classification

Before storing or publishing intake material, classify it as:

- public-safe;
- personal-data;
- client-sensitive;
- confidential;
- patent-sensitive;
- security-sensitive;
- commercial-sensitive.

Public GitHub may only receive public-safe material.

Client-sensitive, confidential, patent-sensitive, or security-sensitive material requires private intake and review.

## Mobile intake boundary

Mobile intake may capture raw claims quickly.

A mobile intake record is raw material, not evidence validation.

Mobile intake should preserve:

- claim;
- timestamp;
- source context if known;
- raw status;
- operator/device context where appropriate.

Mobile intake must not become automatic publication or automatic verification.

## Screenshot boundary

Screenshots must be handled cautiously.

A screenshot may support:

- that a user saw a statement;
- that a platform displayed content;
- that a narrative exists;
- that a claim should be triaged.

A screenshot does not automatically prove:

- the claim is true;
- the source is authentic;
- the date is accurate;
- the image is unedited;
- the context is complete.

## URL boundary

A URL may be ingested as a reference.

URL intake must preserve:

- URL;
- retrieval date if fetched;
- visible title if available;
- source domain;
- source type;
- whether content was actually fetched or merely referenced.

URL intake must not assume the content is stable, complete, or accurate.

## Document/PDF boundary

Documents may be ingested when provided or authorized.

Document intake should preserve:

- filename or reference;
- source;
- date received;
- document type;
- page/section reference where possible;
- confidentiality class;
- extraction notes;
- whether text was parsed, summarized, or manually reviewed.

Do not publish private documents to public GitHub.

## Connector boundary

Future connectors may ingest email, calendar, Slack, drive files, websites, or enterprise systems only after explicit authorization and scoped implementation.

Connector intake must define:

- permission scope;
- data minimization;
- retention;
- audit logging;
- user consent;
- confidentiality handling;
- error behavior;
- deletion/export behavior.

No connector is authorized by this RFC.

## Automated collection boundary

Automated collection requires a separate RFC or approved issue.

Before any automation, define:

- source list;
- collection frequency;
- legal/terms boundary;
- privacy impact;
- rate limits;
- storage location;
- deduplication;
- failure mode;
- human review gate;
- stop condition.

Default rule:

> No crawler without source boundary, legal review, privacy review, and human review gate.

## Claim record boundary

A structured claim record may be created from intake.

A claim record should not overstate certainty.

Acceptable statuses include:

- raw;
- unreviewed;
- unsupported;
- mixed;
- verified;
- rejected;
- needs_evidence;
- counsel_review_needed;
- confidential_intake_needed.

Only evidence-backed review may promote a claim beyond raw/unreviewed.

## Output boundary

Intake outputs may include:

- raw intake record;
- normalized claim draft;
- evidence candidate list;
- source summary;
- uncertainty notes;
- privacy/confidentiality classification;
- review queue entry.

Intake outputs must not include:

- final truth verdict;
- legal conclusion;
- autonomous enforcement action;
- public accusation;
- production scoring;
- hidden model judgment.

## Enterprise implication

Enterprise ingestion may include private documents and client systems, but only inside private deployments with access control, audit logging, retention rules, and confidentiality classification.

Enterprise intake must not flow into public GitHub unless redacted and explicitly approved as public-safe.

## AI provider boundary

AI tools may help normalize or summarize intake only when data classification permits.

Do not send confidential, client-sensitive, patent-sensitive, personal, credential, or security-sensitive material to external AI providers without explicit approval.

AI-generated extraction is advisory and must preserve uncertainty.

## Governance requirements for future intake PRs

Any future intake PR must include:

- source type;
- allowed inputs;
- prohibited inputs;
- privacy classification;
- confidentiality classification;
- storage location;
- validation plan;
- human review gate;
- failure behavior;
- deletion/export considerations if applicable;
- explicit statement that intake does not verify truth.

## Implementation gates

No implementation is authorized by this RFC.

Before building ingestion tooling beyond minimal manual/raw intake, a separate issue or RFC must define:

- input source;
- data contract;
- privacy impact;
- confidentiality impact;
- evidence tier rules;
- validation checks;
- storage location;
- audit requirements;
- human review workflow;
- output contract.

## Out of scope

- Runtime changes.
- CI changes.
- Schema changes.
- Benchmark changes.
- API work.
- HERMES work.
- S3 storage.
- Vector search.
- OCR pipeline.
- Browser automation.
- Web crawler.
- Provider integrations.
- Enterprise deployment.
- Authentication.
- Billing.
- LLM-as-judge.
- Truth adjudication.
- Legal advice.
- Surveillance or profiling workflows.

## Acceptance criteria

This RFC is acceptable when:

- It states that intake is not verification.
- It defines claim, evidence, intake, normalization, and verification.
- It prohibits uncontrolled crawling and source laundering.
- It defines allowed source categories.
- It defines metadata expected from intake.
- It protects privacy/confidentiality.
- It defines screenshot, URL, document, connector, and mobile boundaries.
- It requires separate issues/RFCs before implementation.
- It preserves GitHub as source of truth without storing private evidence publicly.

## Validation

For this documentation-only RFC:

```bash
python tools/check_mojibake.py docs/rfc/ingestion_evidence_intake_boundary.md
git diff --check -- docs/rfc/ingestion_evidence_intake_boundary.md
```

## Risk