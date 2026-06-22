# Foreign-Resident Identity-Process Friction Intake Criteria

Issue: #1645

Status: research intake / documentation-only / not implemented.

This document defines intake criteria for claims about foreign-resident
identity-process friction. The first pilot signal is Spain NIE / TIE /
extranjeria appointment and payment friction.

This document is not a verdict that any specific office, locality, official,
or intermediary acted improperly. It defines how reviewers can classify claims
without turning intake into verification.

This track remains separate from issue #1644 unless a future approved RFC
defines a shared parent taxonomy.

## Boundary

This document does not authorize:

- scraping;
- appointment automation;
- appointment checkers;
- appointment checking bots;
- queue circumvention;
- unofficial appointment acquisition tactics;
- dashboards;
- scoring;
- LLM-as-judge;
- public accusations;
- runtime changes;
- CI changes;
- benchmark changes;
- schema changes;
- roadmap changes;
- publication of personal data.

Public reports of appointment resale, bot activity, fraud, or scarcity may be
recorded as pattern evidence. They are not proof that a specific local case
involved fraud, resale, bots, or misconduct.

## Intake Purpose

The intake purpose is to preserve the distinction between:

- claim: what is asserted;
- evidence: what supports, weakens, or contextualizes the claim;
- inference: what a reviewer derives from the evidence;
- uncertainty: what remains unknown;
- narrative amplification: where frustration or broad generalization may exceed
  the evidence;
- operational relevance: why the case may matter for public-service reliability.

Reviewers classify admissibility and evidence strength. They do not make a
true/false verdict at intake.

## Admissibility Criteria

A record is admissible when it can be stated without personal data and includes
at least:

- the identity process involved, such as NIE, TIE, EU citizen certificate,
  non-resident certificate, appointment access, or fee payment;
- the alleged friction mode;
- the jurisdictional context, such as Spain, province, or locality, with office
  details omitted or generalized when needed for privacy;
- the evidence type and evidence tier;
- separate fields for claim, evidence, inference, and uncertainty;
- a privacy classification showing that names, ID numbers, appointment codes,
  addresses, and payment identifiers are removed.

Testimony-only records are admissible only as weak signal. They must not be
treated as verified fact.

## Failure Taxonomy

- `appointment_access_failure`: a person cannot obtain a timely official
  appointment through official channels.
- `status_visibility_gap`: a person cannot verify whether appointment
  availability, payment state, or processing status is progressing.
- `deadline_breach`: actual waiting time conflicts with an official deadline,
  published service expectation, or time-sensitive dependency.
- `payment_channel_friction`: required fee payment is difficult, unavailable, or
  unclear through expected channels.
- `paper_based_payment_dependency`: the process depends on printed documents,
  in-person bank handling, or paper forms.
- `unclear_admin_ownership`: responsibility is unclear among Police,
  extranjeria, delegation/subdelegation, consulate, bank, or another actor.
- `inconsistent_office_guidance`: web, office, bank, phone, or written
  instructions conflict or leave the required next step unclear.
- `unofficial_intermediary_pressure`: scarcity or confusion pushes the person
  toward paid intermediaries.
- `fraud_or_resale_risk`: public reporting or case evidence indicates risk of
  black-market appointments, bots, false appointments, resale, or scams.
- `unnecessary_physical_presence`: avoidable in-person visits are required or
  caused by unclear appointment, payment, or status instructions.
- `newcomer_dependency_gap`: a new resident needs the identifier for work,
  housing, banking, registration, contracts, or other basic setup but cannot
  access the process reliably.
- `digital_exclusion`: the flow excludes or burdens users lacking certificates,
  printers, Spanish bank access, language fluency, or digital fluency.

## Evidence Tiers

### Tier A - Strong official or adjudicated evidence

Examples:

- ombudsman decisions;
- court or administrative decisions;
- parliamentary, audit, or official oversight reports;
- official complaint outcomes;
- official statistics on appointment availability, backlog, service-standard
  breach, or processing times.

Tier A supports a stronger pattern assessment, but still does not prove every
local claim.

### Tier B - Direct case evidence

Examples:

- redacted appointment screenshots;
- redacted official receipts or case references;
- redacted fee-payment forms or bank rejection/acceptance records;
- written office instructions;
- email or SMS notices with personal data removed;
- call logs or complaint records.

Tier B can support a specific case record when provenance and redaction are
adequate.

### Tier C - Press or structured public reporting

Examples:

- reputable media coverage;
- professional association reports;
- NGO or civil-society reports;
- public institutional statements;
- documented public reporting on appointment scarcity, resale, bots, or fraud.

Tier C may support pattern relevance. It must not be used as proof that a
specific local case involved the reported abuse.

### Tier D - Weak signal / testimony only

Examples:

- social media posts;
- forum posts;
- reviews;
- anecdotal testimony without documents;
- unverified screenshots with unclear provenance.

Tier D may be used for pattern detection only. It is not verified fact.

## `claim_record` Template

```yaml
record_type: claim_record
domain: foreign_resident_identity_process_friction
case_id: foreign-id-friction-YYYY-NNN
pilot_signal: spain_nie_tie_extranjeria
host_country: Spain
region_or_province: ""
locality_or_office_generalized: ""
service_type: "NIE | TIE | EU citizen certificate | non-resident certificate | appointment | fee_payment | other"
admin_owner: "Police | Oficina de Extranjeria | Delegacion/Subdelegacion del Gobierno | bank | consulate | unknown"
claim_summary: ""
claim:
  text: ""
  claimant_role: "affected_person | advisor | observer | public_report | unknown"
  claim_date: "YYYY-MM-DD | unknown"
alleged_failure_modes:
  - appointment_access_failure
  - status_visibility_gap
  - deadline_breach
  - payment_channel_friction
  - paper_based_payment_dependency
  - unclear_admin_ownership
  - inconsistent_office_guidance
  - unofficial_intermediary_pressure
  - fraud_or_resale_risk
  - unnecessary_physical_presence
  - newcomer_dependency_gap
  - digital_exclusion
timeline:
  first_attempt_date: "YYYY-MM-DD | unknown"
  appointment_request_dates: []
  appointment_received_date: "YYYY-MM-DD | unavailable | unknown"
  payment_attempt_dates: []
  office_visit_dates: []
  resolved_date: "YYYY-MM-DD | unresolved | unknown"
citizen_cost:
  travel_cost: "unknown | redacted"
  time_cost: "unknown | redacted"
  missed_work_or_housing_deadline: false
  employment_or_contract_risk: false
  banking_or_property_delay: false
  unofficial_payment_pressure: false
  other: []
evidence:
  official_pages: []
  redacted_appointment_screenshots: []
  redacted_fee_payment_documents: []
  redacted_email_or_notice_records: []
  call_logs: []
  complaint_records: []
  public_reports: []
  testimony: []
evidence_tier: "A | B | C | D"
claim_status: "raw | unverified | partially_supported | documented | resolved | disputed"
inference: ""
uncertainty: ""
narrative_amplification_risk: "low | medium | high"
operational_relevance: ""
privacy_redactions:
  names_removed: true
  nie_tie_passport_numbers_removed: true
  addresses_removed_or_masked: true
  appointment_codes_removed: true
  bank_payment_identifiers_removed: true
  phone_email_removed_or_masked: true
  exact_office_detail_generalized_if_needed: true
notes: ""
```

## Privacy And Redaction Rules

Public GitHub records must be public-safe. Do not publish:

- names or initials that could identify the person;
- NIE, TIE, passport, certificate, appointment, receipt, or expediente numbers;
- exact addresses, phone numbers, email addresses, or account identifiers;
- appointment barcodes, QR codes, payment identifiers, or bank references;
- unredacted screenshots or documents;
- accusations against named officials, offices, intermediaries, or private
  persons;
- private legal, immigration, banking, housing, or employment documents.

Use generalized geography when needed. For example, "Girona province" or
"Lloret de Mar area" may be enough if naming an exact office would make the
case identifiable.

## Activation Thresholds

```text
1 case       -> initial signal; manual record only
3-5 cases    -> preliminary pattern; internal mini-dataset candidate
5-10 cases   -> comparative analysis candidate if multi-source
10+ cases    -> RFC candidate only if multi-source and cross-locality
RFC approved -> only then consider tooling or module design
```

Activation never authorizes scraping, appointment monitoring, appointment
automation, queue circumvention, dashboards, scoring, runtime changes, CI
changes, benchmark changes, schema changes, or public accusations.

## Example Records

### Example 1 - Lloret de Mar area appointment and payment friction placeholder

```yaml
domain: foreign_resident_identity_process_friction
case_id: foreign-id-friction-2026-001-placeholder
pilot_signal: spain_nie_tie_extranjeria
host_country: Spain
region_or_province: Girona
locality_or_office_generalized: Lloret de Mar area
service_type: "NIE appointment and fee_payment"
admin_owner: "unknown"
claim_summary: "A foreign resident reports difficulty obtaining an official appointment and completing the fee-payment step without local procedural help."
claim:
  text: "The person could not complete the appointment and payment flow smoothly through official channels."
  claimant_role: affected_person
  claim_date: unknown
alleged_failure_modes:
  - appointment_access_failure
  - status_visibility_gap
  - payment_channel_friction
  - paper_based_payment_dependency
  - unclear_admin_ownership
  - inconsistent_office_guidance
  - newcomer_dependency_gap
evidence:
  official_pages: []
  redacted_appointment_screenshots: []
  redacted_fee_payment_documents: []
  public_reports: []
  testimony:
    - "Anonymized testimony only; no personal data retained."
evidence_tier: D
claim_status: raw
inference: "The case can be recorded as an initial weak signal for intake design."
uncertainty: "No official record, screenshot, receipt, complaint outcome, appointment availability data, deadline evidence, or physical-visit evidence is attached."
narrative_amplification_risk: medium
operational_relevance: "Shows whether the intake template can represent a local Spain NIE friction signal without personal data."
privacy_redactions:
  names_removed: true
  nie_tie_passport_numbers_removed: true
  addresses_removed_or_masked: true
  appointment_codes_removed: true
  bank_payment_identifiers_removed: true
  phone_email_removed_or_masked: true
  exact_office_detail_generalized_if_needed: true
notes: "Not a verified finding and not proof of local fraud, resale, or misconduct."
```

### Example 2 - Public report pattern evidence placeholder

```yaml
domain: foreign_resident_identity_process_friction
case_id: foreign-id-friction-2026-002-placeholder
pilot_signal: spain_nie_tie_extranjeria
host_country: Spain
region_or_province: multi-locality
locality_or_office_generalized: generalized
service_type: appointment
admin_owner: "Police | Oficina de Extranjeria | unknown"
claim_summary: "Public reporting describes appointment scarcity, resale, bots, or fraud risk around extranjeria appointments."
claim:
  text: "Appointment scarcity can create pressure toward unofficial intermediaries and fraud risk."
  claimant_role: public_report
  claim_date: unknown
alleged_failure_modes:
  - appointment_access_failure
  - unofficial_intermediary_pressure
  - fraud_or_resale_risk
evidence:
  public_reports:
    - "Placeholder for reputable public reporting; do not paste copyrighted text or personal data."
evidence_tier: C
claim_status: unverified
inference: "The report may support pattern relevance for the taxonomy."
uncertainty: "The report does not prove that any specific local case involved resale, bots, fraud, or misconduct."
narrative_amplification_risk: high
operational_relevance: "Helps reviewers separate pattern evidence from proof of a specific case."
privacy_redactions:
  names_removed: true
  nie_tie_passport_numbers_removed: true
  addresses_removed_or_masked: true
  appointment_codes_removed: true
  bank_payment_identifiers_removed: true
  phone_email_removed_or_masked: true
  exact_office_detail_generalized_if_needed: true
notes: "Use as pattern evidence only."
```

### Example 3 - Direct redacted case evidence placeholder

```yaml
domain: foreign_resident_identity_process_friction
case_id: foreign-id-friction-2026-003-placeholder
pilot_signal: spain_nie_tie_extranjeria
host_country: Spain
region_or_province: redacted_or_generalized
locality_or_office_generalized: redacted_or_generalized
service_type: fee_payment
admin_owner: bank
claim_summary: "A person reports that the required fee-payment flow could not be completed through the expected channel."
claim:
  text: "The payment channel created avoidable friction before the identity appointment."
  claimant_role: affected_person
  claim_date: unknown
alleged_failure_modes:
  - payment_channel_friction
  - paper_based_payment_dependency
  - inconsistent_office_guidance
  - unnecessary_physical_presence
  - digital_exclusion
evidence:
  redacted_fee_payment_documents:
    - "Placeholder for redacted Modelo 790 Codigo 012 payment evidence."
  testimony:
    - "Short anonymized context."
evidence_tier: B
claim_status: partially_supported
inference: "Direct redacted payment evidence may support the existence of payment-channel friction in this case."
uncertainty: "The record does not establish whether the friction was local, temporary, bank-specific, systemic, or whether any in-person step was avoidable."
narrative_amplification_risk: low
operational_relevance: "Shows how direct evidence can be classified without publishing payment identifiers."
privacy_redactions:
  names_removed: true
  nie_tie_passport_numbers_removed: true
  addresses_removed_or_masked: true
  appointment_codes_removed: true
  bank_payment_identifiers_removed: true
  phone_email_removed_or_masked: true
  exact_office_detail_generalized_if_needed: true
notes: "No unredacted bank, identity, appointment, or address data may be committed."
```

## Acceptance Criteria

This intake document is acceptable when:

- reviewers can classify a NIE / TIE / extranjeria friction claim without making
  a true/false verdict;
- the record template preserves claim, evidence, inference, uncertainty,
  narrative amplification, and operational relevance;
- testimony-only claims are marked as Tier D weak signal, not verified fact;
- the Lloret de Mar pilot signal can be represented without personal data;
- public reports of appointment resale or fraud are treated as pattern evidence,
  not proof of a specific local case;
- the document remains documentation-only and reversible.

## Validation

For this documentation-only intake document:

```bash
python tools/check_mojibake.py docs/research/foreign_resident_identity_process_friction.md
git diff --check -- docs/research/foreign_resident_identity_process_friction.md
```
