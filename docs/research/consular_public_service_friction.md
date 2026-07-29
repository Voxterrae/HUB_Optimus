# Consular Public-Service Friction Claim Intake Criteria

Issue: #1644

Status: research intake / documentation-only / not implemented.

This note defines a manual intake standard for claims about public-service
friction under diplomatic representation. It helps reviewers preserve a
bounded claim, its evidence, the inference drawn from that evidence, remaining
uncertainty, possible narrative amplification, and operational relevance.

Recording a claim does not verify it. Admitting a record does not establish
misconduct, a service failure, a general pattern, or institutional
responsibility.

## Scope And Separation

This intake covers citizen-facing consular services delivered by a diplomatic
or consular representation, such as passport renewal, identity documents,
visas, certificates, and emergency assistance.

It remains separate from
`docs/research/foreign_resident_identity_process_friction.md`. That document
covers host-country NIE, TIE, extranjeria, appointment, and fee-payment
processes. Neither document creates a shared taxonomy or executable parent
model. A future approved RFC would be required to combine them.

The Operator currently exposes only the generic source type
`public-service-friction`. This note does not extend that type, add a consular
source type, verify Operator input, or create an Operator, API, Semantic
Engine, or runtime capability.

## Explicit Boundary

This document does not authorize or implement:

- scraping, crawling, monitoring, or automated collection;
- browser, email, phone, social-media, or connector automation;
- dashboards, country rankings, service rankings, or comparative league
  tables;
- scoring, weighted evidence, automated pattern detection, or LLM-as-judge;
- truth adjudication, legal conclusions, diplomatic findings, or public
  accusations;
- publication of names, identity data, correspondence, case references, or
  other personal data;
- runtime, Operator, API, Semantic Engine, schema, CI, benchmark, fixture,
  deployment, or roadmap changes.

It also does not create a complaint channel, case-management commitment,
response-time commitment, escalation service, or obligation for HUB_Optimus to
investigate a submitted claim.

## Intake Principle

Intake is not verification. Every admitted record must keep these six layers
visible:

| Layer | Intake question | Required treatment |
| --- | --- | --- |
| Claim | What exactly is asserted? | Record a bounded statement without accepting it. |
| Evidence | What inspectable material supports, contradicts, or contextualizes the claim? | Preserve source type, provenance, relevance, and limitations. |
| Inference | What reasoning moves beyond the evidence? | Label the reasoning and its assumptions explicitly. |
| Uncertainty | What remains unknown, contested, missing, or unverifiable? | State gaps and plausible alternatives. |
| Narrative amplification | Where may frustration or generalization exceed the evidence? | Record the mechanism and risk without treating it as proof that the claim is false. |
| Operational relevance | Why might the bounded case matter for public-service reliability? | Record a limited research signal or `no action justified`. |

Evidence that weakens or contradicts a claim must remain in the record.
Repetition, urgency, institutional prestige, or the number of testimony-only
reports does not promote evidence to a stronger tier.

## Minimum Admissibility

A real claim record is admissible for manual research intake only when all of
the following are true:

1. The claim concerns a named service category and at least one alleged
   friction mode from this document.
2. The claim is bounded to a case, period, channel, or published pattern. It
   does not turn one experience into a country-wide or institution-wide
   conclusion.
3. The jurisdiction is present at a public-safe level. The represented country,
   consular post, or exact city may be redacted or generalized when it could
   identify a person.
4. At least one attributable evidence item or testimony item is described with
   its source type, provenance, relevance, limitations, and evidence tier.
5. Claim, evidence, inference, uncertainty, narrative amplification, and
   operational relevance are separate and non-empty. `No corroborating
   evidence provided` is valid only when an attributable testimony item is
   recorded as Tier D. `No inference justified` or `no action justified` are
   also valid explicit values.
6. The record has an evidence tier and a non-verdict claim status.
7. The privacy checklist is complete before any material is committed to
   public GitHub.
8. The wording reports an allegation or documented event precisely. It does
   not accuse a named person, office, provider, or state of misconduct beyond
   the reviewed evidence.

Testimony-only material may be admitted only as a Tier D weak signal. It must
remain `unverified`, must not be presented as verified fact, and must not
support a public accusation or generalized conclusion.

A record is not admissible when:

- personal or confidential data has not been removed;
- the only statement is vague, compound, or impossible to bound;
- the assertion has no attributable source context or testimony provenance;
- a screenshot, copied message, model summary, or social post is represented
  as proof of the underlying event;
- the evidence was obtained through unauthorized access or collection;
- a placeholder, hypothetical example, or generated text is presented as a
  real case;
- the record requires publishing a private document in order to be
  intelligible.

Inadmissible material must not be copied into the repository. A reviewer may
record only a public-safe rejection reason, without retaining the material.

## Evidence Tiers

Evidence tiers classify the available material; they do not return a true or
false verdict.

### Tier A - Strong Public Or Official Evidence

Examples include:

- ombudsman decisions;
- court or administrative decisions;
- parliamentary, audit, or official oversight reports;
- official complaint outcomes;
- official confirmations of a service-standard breach.

Tier A can support the bounded finding stated by the source. It does not prove
that the finding applies to another person, post, period, or jurisdiction.

### Tier B - Direct Case Evidence

Examples include reviewer-inspected, public-safe redacted artifacts or
verifiable redacted derivatives such as:

- redacted receipts or case references;
- redacted appointment confirmations;
- redacted email delivery failures or written deadline communications;
- redacted call logs;
- redacted complaint submissions and responses;
- redacted collection or ready-for-pickup notices.

Tier B may support a specific case when provenance, relevance, and redaction
are adequate. A case number or screenshot alone does not establish causality,
intent, or a wider pattern.

A statement that a direct artifact exists remains Tier D until an identified
reviewer has inspected the artifact or a verifiable redacted derivative. A
public-safe description of restricted evidence is review metadata, not a
publicly inspectable substitute for that evidence. The record must disclose
that access limitation.

### Tier C - Press Or Structured Public Reporting

Examples include:

- reputable media reporting;
- NGO or civil-society reports;
- professional-association reports;
- public institutional statements that are not direct case findings.

Tier C may establish that a concern has been publicly reported. It is not
direct proof that a particular local case occurred as alleged.

### Tier D - Weak Signal Or Testimony Only

Examples include:

- social-media posts;
- forum posts;
- public reviews;
- anecdotal testimony without supporting documents;
- screenshots with unclear provenance or context.

Tier D is usable only as an initial signal for manual pattern observation. It
is not verified fact. Multiple Tier D items do not become Tier C, B, or A by
volume alone.

### Assigning A Record Tier

Each evidence item keeps its own tier. `record_evidence_tier` is the strongest
tier directly relevant to the bounded claim, with A strongest and D weakest.
It must not be raised by evidence that is merely contextual or concerns a
different case. It must always be read together with `relation_to_claim`; a
Tier A item that contradicts a claim does not make that claim "Tier A." Mixed
and contradictory evidence remains listed item by item.

## Initial Friction Taxonomy

The taxonomy classifies what is alleged. Applying a label does not establish
that the failure occurred.

- `status_visibility_gap`: the person cannot determine the current case status
  or the next expected status transition.
- `communication_failure`: an official phone, email, web, or written channel
  is allegedly unavailable, fails, or receives no usable response.
- `deadline_breach`: an official or documented service window is allegedly
  exceeded without adequate notice or resolution.
- `appointment_access_failure`: the person allegedly cannot obtain a necessary
  appointment through the stated process within the relevant period.
- `unnecessary_physical_presence`: an in-person visit is allegedly avoidable or
  caused by missing status or channel information.
- `unclear_escalation_path`: the available complaint or escalation route is
  absent, conflicting, or not discoverable from the reviewed information.
- `document_retention_risk`: an identity or travel document is allegedly held
  without a clear status, return path, or mitigation for time-sensitive use.
- `third_party_outsourcing_gap`: responsibility or handoff between a consular
  post and an external service provider is allegedly unclear or fails.
- `emergency_response_gap`: urgent consular assistance is allegedly
  unavailable, delayed, or unclear. Intake of such a claim is not an emergency
  service and must not delay contact with competent authorities.
- `conflicting_information`: official web, email, phone, provider, or
  in-person guidance allegedly gives incompatible next steps.

## Manual `claim_record` Template

The following YAML is a research form, not an executable repository schema,
runtime contract, or accepted Operator payload.

```yaml
record_type: claim_record
template_version: consular_public_service_friction.v1
domain: public_service_friction_under_diplomatic_representation
case_id: consular-friction-YYYY-NNN
synthetic_placeholder: true

jurisdiction:
  country_represented: ""
  consular_post_city_or_generalized_area: ""
  host_country: ""

service_type: "passport | id_card | visa | certificate | emergency_assistance | other"

claim:
  text: ""
  claimant_role: "affected_person | representative | observer | public_report | unknown"
  claim_date_or_period: "YYYY-MM-DD | date range | unknown"
  scope_limit: ""

alleged_failure_modes:
  - status_visibility_gap
  - communication_failure
  - deadline_breach
  - appointment_access_failure
  - unnecessary_physical_presence
  - unclear_escalation_path
  - document_retention_risk
  - third_party_outsourcing_gap
  - emergency_response_gap
  - conflicting_information

timeline:
  request_date: "YYYY-MM-DD | unknown"
  promised_or_expected_window: ""
  followup_dates: []
  visit_dates: []
  resolved_date: "YYYY-MM-DD | unresolved | unknown"

citizen_cost:
  travel_cost: "unknown | redacted"
  time_cost: "unknown | redacted"
  lost_trip_or_deadline: "unknown | true | false"
  employment_or_legal_risk: "unknown | true | false"
  other: []

evidence_items:
  - evidence_id: E1
    tier: "A | B | C | D"
    kind: "official_outcome | direct_case_record | public_report | testimony | other"
    public_safe_reference: ""
    provenance: ""
    relation_to_claim: "supports | contradicts | contextualizes"
    limitations: ""

record_evidence_tier: "A | B | C | D"
claim_status: "unverified | partially_supported | documented | resolved | disputed"

inference:
  text: ""
  assumptions: []
  alternative_explanations: []

uncertainty:
  unknowns: []
  evidence_needed: []

narrative_amplification:
  risk: "low | medium | high"
  mechanism: ""

operational_relevance:
  bounded_signal: ""

privacy_redactions:
  personal_names_removed: false
  passport_and_identity_numbers_removed: false
  case_receipt_and_appointment_numbers_removed: false
  phone_email_and_addresses_removed_or_masked: false
  travel_and_visit_detail_generalized_if_identifying: false
  minors_health_and_legal_detail_removed_or_generalized: false
  screenshots_and_document_metadata_reviewed: false
  named_staff_and_private_parties_removed: false

manual_review:
  reviewed_by: ""
  reviewed_on: "YYYY-MM-DD"
  admissible: false
  public_safe: false
  review_notes: ""
```

`claim_status` remains non-authoritative:

- `unverified`: intake has not established the bounded claim;
- `partially_supported`: reviewed evidence supports only part of the bounded
  claim;
- `documented`: direct or official evidence documents the bounded event, not a
  wider causal or institutional conclusion;
- `resolved`: the reported service need ended or was addressed, without
  deciding every contested claim;
- `disputed`: material contradiction remains visible.

The template defaults `synthetic_placeholder` to `true` and every privacy
check, `admissible`, and `public_safe` to `false`. Only a human reviewer may
change the placeholder flag to `false` or a privacy check to `true` after
inspecting the proposed public record. Operational relevance records a bounded
signal only; it never selects or authorizes a next step.

## Privacy And Redaction

Public GitHub may contain only public-safe material. Before a record is
committed, remove or safely generalize:

- personal names, initials, signatures, faces, and voices;
- passport, identity-card, visa, certificate, case, receipt, appointment, and
  complaint numbers;
- addresses, phone numbers, email addresses, account identifiers, QR codes,
  barcodes, and document metadata;
- exact travel, visit, employment, legal, health, or family details that could
  re-identify a person;
- information concerning minors or vulnerable persons;
- names of consular staff, contractors, witnesses, or private intermediaries;
- private correspondence and document images.

Redaction must happen before a file enters the public repository. Deleting or
masking data in a later commit is not a sufficient publication strategy
because Git history may retain it.

When a post or city plus service date could identify a person, generalize the
location and period. A public official source may be cited when it is relevant,
lawfully accessible, and needed for provenance, but quote only the minimum
necessary content and preserve its scope and date.

The public record may describe that an identified reviewer inspected a
redacted artifact and record the review date. That description is review
metadata, not publicly inspectable direct evidence, and must disclose the
access limitation. It must not embed a private artifact, a secret storage
address, or a reversible identifier. Raw evidence requires an authorized
private process outside this public documentation note.

## Anonymized Structural Placeholders

The examples below are synthetic structural placeholders. They are not factual
claims, evidence, dataset rows, or findings about any consular post. They must
not be copied into a dataset with `synthetic_placeholder: false`.

Placeholder 1 shows the complete review boundary. Placeholders 2 and 3 are
deliberately abbreviated, non-admissible fragments; a real record would have
to complete every required template and review field. Their
`illustrated_evidence_tier_if_real_and_reviewed` fields are explanatory only
and are not part of the `claim_record` template.

### Placeholder 1 - Barcelona-Area Passport-Renewal Signal

```yaml
record_type: claim_record
template_version: consular_public_service_friction.v1
domain: public_service_friction_under_diplomatic_representation
case_id: consular-friction-placeholder-001
synthetic_placeholder: true
jurisdiction:
  country_represented: redacted_or_not_supplied
  consular_post_city_or_generalized_area: Barcelona area
  host_country: Spain
service_type: passport
claim:
  text: "Synthetic example of testimony alleging that an expected delivery window passed, remote contact did not produce a usable response, and an in-person visit did not resolve the status."
  claimant_role: affected_person
  claim_date_or_period: unknown
  scope_limit: "One anonymized alleged experience only."
alleged_failure_modes:
  - status_visibility_gap
  - communication_failure
  - deadline_breach
  - unnecessary_physical_presence
  - unclear_escalation_path
evidence_items: []
illustrated_evidence_tier_if_real_and_reviewed: D
record_evidence_tier: not_applicable_synthetic_placeholder
claim_status: not_applicable_synthetic_placeholder
inference:
  text: "No case or institutional inference is justified; the placeholder only tests the form."
  assumptions: []
  alternative_explanations: []
uncertainty:
  unknowns:
    - "All case facts, dates, communications, status, and resolution."
  evidence_needed:
    - "A real record would require public-safe provenance and manual review."
narrative_amplification:
  risk: high
  mechanism: "One alleged experience could be generalized into a claim about a post or represented country."
operational_relevance:
  bounded_signal: "Template coverage test only."
privacy_redactions:
  personal_names_removed: true
  passport_and_identity_numbers_removed: true
  case_receipt_and_appointment_numbers_removed: true
  phone_email_and_addresses_removed_or_masked: true
  travel_and_visit_detail_generalized_if_identifying: true
  minors_health_and_legal_detail_removed_or_generalized: true
  screenshots_and_document_metadata_reviewed: true
  named_staff_and_private_parties_removed: true
manual_review:
  reviewed_by: ""
  reviewed_on: "YYYY-MM-DD"
  admissible: false
  public_safe: true
  review_notes: "Placeholder only; not eligible as evidence."
```

### Placeholder 2 - How Inspected Tier B Evidence Would Be Bounded

```yaml
case_id: consular-friction-placeholder-002
synthetic_placeholder: true
service_type: certificate
claim:
  text: "Placeholder claim that written instructions and the available appointment path conflicted."
  scope_limit: "One hypothetical case and one stated period."
alleged_failure_modes:
  - appointment_access_failure
  - conflicting_information
evidence_items: []
illustrated_evidence_tier_if_real_and_reviewed: B
record_evidence_tier: not_applicable_synthetic_placeholder
claim_status: not_applicable_synthetic_placeholder
inference:
  text: "No factual inference is permitted from a synthetic placeholder."
uncertainty:
  unknowns:
    - "All facts and whether any instructions actually conflicted."
narrative_amplification:
  risk: medium
  mechanism: "A channel mismatch could be described as a systemic service failure."
operational_relevance:
  bounded_signal: "Demonstrates the scope limit that would apply if real Tier B evidence were inspected."
```

### Placeholder 3 - How A Tier A Official Outcome Would Be Bounded

```yaml
case_id: consular-friction-placeholder-003
synthetic_placeholder: true
service_type: other
claim:
  text: "Placeholder claim matching the bounded finding of a hypothetical official complaint outcome."
  scope_limit: "Only the event, service, period, and finding stated in that outcome."
alleged_failure_modes:
  - deadline_breach
evidence_items: []
illustrated_evidence_tier_if_real_and_reviewed: A
record_evidence_tier: not_applicable_synthetic_placeholder
claim_status: not_applicable_synthetic_placeholder
inference:
  text: "No factual inference is permitted from a synthetic placeholder."
uncertainty:
  unknowns:
    - "All facts and whether an official outcome exists."
narrative_amplification:
  risk: low
  mechanism: "A bounded finding could be expanded beyond its jurisdiction or period."
operational_relevance:
  bounded_signal: "Demonstrates the scope limit that would apply if a real Tier A outcome were reviewed."
```

## Activation Thresholds

```text
1 admissible case  -> initial signal; manual record only
3-5 cases          -> preliminary pattern; manually reviewed mini-dataset candidate
5-10 cases         -> comparative analysis candidate if genuinely multi-source
10+ cases          -> RFC candidate only if multi-source and cross-jurisdictional
approved RFC       -> only then consider separately scoped tooling or module design
```

Counts alone never activate a new capability. Records must be admissible,
independently reviewed, sufficiently distinct, and public-safe. Duplicate
reports, copied narratives, multiple posts derived from one source, and
synthetic placeholders do not count as independent cases.

Reaching a threshold does not authorize scraping, monitoring, a dashboard,
scoring, ranking, runtime work, schema work, public accusations, or
publication. It only permits a human reviewer to propose the next GitHub issue
or RFC.

## Manual Review And Validation

All content validation is manual. Repository encoding or formatting checks do
not verify a claim.

For each proposed record, a human reviewer must:

1. confirm that the record is a `claim_record`, not a proposal or broad
   conflict analysis;
2. decompose compound claims into separately reviewable statements;
3. confirm that every evidence item is lawfully available, public-safe, and
   assigned a conservative tier;
4. check that supporting, contextual, and contradictory evidence remains
   distinguishable;
5. check that inference does not repeat the claim as a fact;
6. state unknowns and plausible alternative explanations;
7. inspect narrative-amplification risk and bound operational relevance;
8. complete privacy redaction before Git staging;
9. record the human reviewer and date; and
10. reject or return the record when any admissibility requirement is unmet.

Manual acceptance tests for this note:

- The Barcelona-area placeholder represents the alleged passport-renewal
  signal without a name, represented country, passport number, case reference,
  contact detail, exact date, or factual finding.
- It labels Tier D only as the classification an analogous real,
  testimony-only item could receive after review; the placeholder itself has
  no evidence tier or claim status and produces no institutional conclusion.
- The Tier B and Tier A placeholders demonstrate the form without embedding
  evidence, changing a schema, or creating a runtime capability.
- The foreign-resident identity-process intake remains a separate research
  track.
- No section promises investigation, monitoring, response, resolution, or
  operational service.

## Acceptance Criteria

This note is complete when reviewers can:

- decide whether a future consular-friction record is admissible without
  making a true/false verdict;
- assign evidence tiers A-D without laundering testimony into stronger
  evidence;
- preserve claim, evidence, inference, uncertainty, narrative amplification,
  and operational relevance as separate layers;
- extend the manual template without exposing personal data; and
- identify that any future automation or implementation requires a separate
  approved GitHub issue or RFC.

The change remains one reversible documentation file. It creates no
operational commitment or executable behavior.
