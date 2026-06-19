# RFC: Judicial Transparency Audit Framework

## Status

- Draft / RFC only
- Governance proposal
- Not implemented
- Tracks issue #1641
- No runtime, schema, dataset, fixture, benchmark, CI, dashboard, scoring, crawler, connector, or LLM-as-judge change
- No legal advice
- No public accusation workflow

## Purpose

This RFC defines a neutral forensic audit framework for complex judicial processes where evidence, public communication, and legal admissibility may diverge.

Initial reference domain:

- EncroChat
- Sky ECC
- ANOM
- encrypted-platform evidence cases
- cross-border evidence transfer
- public court communication
- the Halle an der Saale EncroChat macroprocess reference

The goal is not to decide guilt, innocence, institutional misconduct, or conspiracy.

The goal is to preserve traceability:

```text
what was claimed -> what evidence exists -> what is inferred -> what remains uncertain -> what is operationally relevant
```

Spanish reference:

```text
lo afirmado -> evidencia disponible -> inferencia -> incertidumbre -> relevancia operativa
```

## Core Boundary

HUB_Optimus may analyze judicial transparency structurally.

HUB_Optimus must not:

- assign guilt or innocence;
- accuse living persons without official court sources;
- infer protected identities;
- publish private or victim-sensitive material;
- treat missing public information as proof of wrongdoing;
- treat judicial admissibility as proof of complete transparency;
- perform surveillance, profiling, doxxing, or targeting;
- bypass access controls, paywalls, confidentiality duties, or court restrictions;
- provide legal advice;
- convert a public narrative into project doctrine.

Core rule:

```text
Auditability is not guilt adjudication.
```

Spanish reference:

```text
La auditabilidad no es adjudicacion de culpabilidad.
```

## Relationship to Existing Work

This RFC extends existing governance boundaries without replacing them.

- `docs/rfc/epistemic_analysis_modes.md` defines mode separation before evaluation.
- `docs/rfc/ingestion_evidence_intake_boundary.md` defines controlled, evidence-aware intake.
- `docs/rfc/proposal_scenario_analysis_mode.md` defines non-endorsement and structural stress testing.

This RFC adds a specialized judicial-transparency lens for cases where legal process, evidence collection, cross-border transfer, press visibility, and public trust intersect.

## Analysis Mode

Suggested conceptual mode:

```text
judicial_transparency_audit
```

Use this mode when the input asks for a neutral review of:

- evidence origin;
- legal authority;
- chain of custody;
- cross-border transfer;
- admissibility;
- defense contradiction;
- publication and redaction;
- preservation of public-safe metadata;
- unresolved transparency gaps.

Do not use this mode when the input is only:

- a single factual claim;
- a request for legal strategy;
- a request to identify protected persons;
- a request to expose private evidence;
- a request to prove a preselected conspiracy;
- a request to endorse a law-enforcement narrative.

## Forensic Layers

A judicial transparency audit should separate the following layers.

### 1. Event and Proceeding Identification

Minimum fields:

- proceeding_id;
- jurisdiction;
- court or authority;
- public case reference, if available;
- date range;
- proceeding status;
- public-safe summary;
- source references.

Purpose:

```text
Identify the process before evaluating the process.
```

### 2. Evidence Collection

Questions:

- What type of evidence is referenced?
- Which authority collected it?
- What technical method is publicly described?
- What is known from official sources?
- What remains classified, redacted, sealed, or unavailable?

Boundary:

Technical collection details must remain public-source based. This RFC does not authorize forensic reverse engineering, operational intrusion analysis, or replication of law-enforcement methods.

### 3. Legal Authority Chain

Questions:

- Which authority authorized the original collection?
- Which court, prosecutor, or agency is named publicly?
- Which legal instrument enabled transfer or later use?
- Was later national use reviewed by a court?
- Did higher courts review admissibility or rights issues?

Output should distinguish:

- documented authority;
- reported authority;
- defense allegation;
- unresolved authority gap.

### 4. Chain of Custody and Data Handling

Questions:

- Where did the evidence move?
- Which institutions handled it?
- Was the transfer cross-border?
- Was a joint investigation team, judicial cooperation channel, or agency platform involved?
- Is there public information on integrity controls, hashes, logs, or access records?

Boundary:

If custody details are not public, mark them as unavailable. Do not fill the gap with speculation.

### 5. Selection and Exclusion

Questions:

- Which subset of material reached the proceeding?
- Which material was excluded, redacted, or not publicly discussed?
- Are selection criteria known?
- Could public visibility differ by charge type, jurisdiction, victim protection, or press policy?

Operational point:

```text
The visible case set may not equal the captured evidence universe.
```

This is a transparency gap, not proof of misconduct by itself.

### 6. Admissibility

Questions:

- Was the evidence admitted?
- Was admissibility challenged?
- Which court decided the issue?
- What was the stated reasoning?
- Was the decision final, appealed, or still open?

Boundary:

Admissibility means a court allowed use of evidence under the applicable process. It does not automatically prove complete transparency, perfect collection, or absence of institutional error.

### 7. Contradiction and Defense Review

Questions:

- Could the defense challenge origin, integrity, attribution, and context?
- Were technical details available enough for meaningful contradiction?
- Did the court address defense objections?
- Did any ruling require exclusion, limitation, or reduced weight?

This layer is central because evidence that cannot be meaningfully challenged may weaken procedural legitimacy even when the public narrative appears strong.

### 8. Public Communication and Redaction

Questions:

- What did the court or authority publish?
- What did press reporting add or omit?
- Were protected persons, minors, victims, or private third parties involved?
- Were names, dates, locations, or details redacted?
- Is the redaction legally justified, privacy-protective, or unexplained?

Core rule:

```text
Transparency does not require exposing protected people or private evidence.
It requires a reviewable reason why information is public, redacted, sealed, or unavailable.
```

### 9. Preservation and Reproducibility

Questions:

- Are public URLs preserved?
- Is the access date recorded?
- Are official sources preferred over commentary?
- Are indirect claims linked back to primary sources where possible?
- Can another reviewer reproduce the source path?

Public GitHub may store only public-safe metadata and source references. It must not store private evidence, protected identities, confidential documents, or sensitive investigative material.

## Claim Decomposition Contract

Every substantive statement in this mode should be classified as one of:

- `fact_documented`
- `allegation`
- `court_reasoning`
- `defense_argument`
- `institutional_statement`
- `press_report`
- `inference`
- `uncertainty`
- `narrative_amplification`
- `operational_relevance`

Required output sections:

```text
Claim
Evidence
Inference
Uncertainty
Narrative amplification
Operational relevance
```

No claim may be promoted from allegation or inference to documented fact without a cited source tier that supports it.

## Source Tiers

Use conservative source tiers.

| Tier | Meaning |
| --- | --- |
| `official_primary` | Judgment, court order, official court press release, legislation, official agency record |
| `official_secondary` | Agency summary, institutional press release, official explanatory note |
| `judicial_database` | Public decision database or case-law portal |
| `reputable_press` | Professional reporting with identifiable source path |
| `academic_analysis` | Scholarly or legal analysis with citations |
| `defense_claim` | Claim by defense counsel, accused party, or advocacy source |
| `user_provided` | User-submitted text, link, screenshot, or context |
| `unknown` | Source unclear, incomplete, or not yet checked |

Tiering is not verification.

## Minimal Record Shape

A public-safe audit record may use this conceptual shape:

```yaml
record_id: jtaf_YYYY_shortname
mode: judicial_transparency_audit
status: draft | reviewed | unresolved | archived
jurisdiction: unknown | EU | DE | FR | NL | BE | ES | UK | other
proceeding_reference: public-safe court or source reference
source_tier: official_primary | official_secondary | judicial_database | reputable_press | academic_analysis | defense_claim | user_provided | unknown
claim:
evidence:
inference:
uncertainty:
narrative_amplification:
operational_relevance:
privacy_classification: public-safe | personal-data | protected-person | confidential | security-sensitive
publication_boundary:
traceability_links:
review_notes:
```

This is not a machine schema. Any schema, fixture, dataset, or validator must be proposed separately.

## Auditability Metrics

Suggested human-review metrics, scored 0-5 only in future approved work:

- `source_traceability`: Can a reviewer reach the original source?
- `authority_traceability`: Is the authorizing legal authority visible?
- `custody_visibility`: Is evidence movement between institutions visible?
- `selection_visibility`: Is it clear why the public case subset exists?
- `contradiction_visibility`: Is defense challenge visible?
- `redaction_explainability`: Are redactions or gaps explained?
- `public_safe_reproducibility`: Can the public record be reviewed without exposing protected material?

This RFC does not authorize scoring implementation.

## Reference Case Boundary

EncroChat, Sky ECC, ANOM, Kinahan-related references, and Halle an der Saale macroprocess materials may be used as public-source test references only after separate follow-up issues or PRs.

Any concrete case record must:

- preserve presumption of innocence where applicable;
- cite official court or agency sources where possible;
- avoid naming living persons unless already named in official public records and necessary to the audit;
- avoid private personal details;
- avoid protected victim detail;
- mark press-only details as press reporting, not court fact;
- separate proceedings from broader narratives.

## Transparency Target

Incorrect target:

```text
100 percent public disclosure of all evidence.
```

Correct target:

```text
100 percent auditable traceability with lawful redaction and public-safe metadata.
```

Meaning:

- something exists or is marked unavailable;
- the holder or authority is identified where public;
- the reason for redaction, sealing, or uncertainty is recorded where known;
- gaps remain visible instead of being hidden or filled by narrative.

## Governance Requirements

Any future PR under this lane must state:

- source boundary;
- jurisdiction boundary;
- privacy classification;
- publication boundary;
- evidence tier rules;
- human review gate;
- protected-person handling;
- non-accusation language;
- validation plan;
- explicit non-goals.

## Non-Goals

This RFC does not authorize:

- runtime changes;
- simulator changes;
- schema changes;
- benchmark changes;
- CI changes;
- dataset creation;
- fixture creation;
- automated crawling;
- OCR pipeline;
- connector work;
- dashboard creation;
- semantic scoring;
- LLM-as-judge;
- legal advice;
- investigative targeting;
- identity inference;
- publication of private evidence;
- publication of protected victim details;
- claims that missing public data proves wrongdoing;
- claims that admissibility proves full institutional transparency.

## Acceptance Criteria

This RFC satisfies issue #1641 when:

- it defines `judicial_transparency_audit` as a conceptual mode;
- it states that auditability is not guilt adjudication;
- it defines forensic layers from event identification to preservation;
- it preserves claim/evidence/inference/uncertainty separation;
- it defines conservative source tiers;
- it defines a public-safe minimal record shape;
- it defines auditability metrics as future human-review concepts only;
- it protects privacy, protected persons, and confidential material;
- it explicitly blocks runtime, CI, schema, dataset, fixture, crawler, dashboard, scoring, and LLM-as-judge changes;
- it remains small, reviewable, reversible, and RFC-only.

## Validation

For this documentation-only RFC:

```bash
python tools/check_mojibake.py docs/rfc/judicial_transparency_audit_framework.md
git diff --check -- docs/rfc/judicial_transparency_audit_framework.md
```

## Future Work

Possible follow-up work must be opened as separate GitHub issues after RFC review.

Suggested sequence:

1. `docs: add judicial transparency audit template`
2. `research: add public-source index for encrypted-platform cases`
3. `research: add Halle/Saale public-source case note`
4. `docs: add reviewer checklist for judicial transparency audit records`
5. `schema: discuss public-safe audit record shape`

No follow-up is authorized by this RFC alone.
