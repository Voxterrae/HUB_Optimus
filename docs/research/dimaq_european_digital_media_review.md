# DIMAQ / European Digital Media Manual Review Matrix

Issue: #1647

Status: documentation-only / manual analytical aid / not implemented.

Use this matrix to review material about programmatic advertising, privacy,
attribution, analytics, digital strategy, or the European media ecosystem. It
structures questions; it does not verify a claim, determine truth, or authorize
an action.

DIMAQ, IAB, industry standards, provider material, and other sector frameworks
may be recorded as sources or framing. They are not HUB_Optimus
source-of-truth authority merely because this matrix records them.

This matrix follows the boundaries in:

- [`epistemic_analysis_modes.md`](../rfc/epistemic_analysis_modes.md), which
  requires one declared mode before evaluation; and
- [`ingestion_evidence_intake_boundary.md`](../rfc/ingestion_evidence_intake_boundary.md),
  which establishes that intake is not verification.

Complete one matrix manually for one declared analysis mode. Preserve source
wording and provenance where possible. If the mode is unclear, stop and request
clarification instead of blending modes.

## Source-Laundering Guard

Passing material through this matrix does not strengthen its evidence tier,
confirm its authenticity, or endorse the source. A standard, certification,
trade-body publication, platform report, vendor metric, screenshot, or repeated
claim remains material to inspect, not proof of the underlying assertion.

Record separately:

- what the source directly states or shows;
- what another actor claims the source means;
- what the reviewer infers; and
- what remains unverified, unavailable, or contested.

Do not promote a claim because it uses legal, technical, commercial, or
institutional language. Do not treat the matrix output as a legal conclusion,
privacy assessment, compliance determination, or truth verdict.

## Manual Review Matrix

### 1. Input

- Source or reference:
- Access or publication date:
- Actor, author, or organization:
- Domain:
- Jurisdiction claimed or potentially relevant:
- Language:
- Source type and provenance:
- Material actually inspected:
- Material unavailable or only described:
- Declared analysis mode:

Choose exactly one:

- `claim_record`: a bounded assertion about reality, evidence, capability,
  intent, an event, or a causal effect. Keep the six-part epistemic
  decomposition in section 9.
- `proposal_analysis`: a submitted strategy, plan, intervention, or future
  option. Record it as a proposal, not an endorsed recommendation; stress-test
  its assumptions, effects, dependencies, and failure modes.
- `conflict_analysis`: a broad multi-actor system, tension, or contested
  ecosystem. Keep actors, interests, evidence zones, uncertainty zones, and
  narrative pressures distinct; do not collapse the system into one claim.

These are conceptual manual review labels, not implemented automatic
classification or analysis capabilities.

Mode selected and reason:

### 2. Claim / Proposal / Conflict Scope

- What exactly is asserted, proposed, or placed within scope?
- What wording is copied from the source, and what wording is the reviewer's?
- Is the material factual, strategic, legal, technical, commercial,
  reputational, or a combination?
- Is the item compound and therefore in need of separate review records?
- What time period, population, market, channel, or decision does it concern?
- What would make the item inspectable, testable, or comparable?

For `proposal_analysis`, keep the submitted proposal separate from claims used
to justify it. For `conflict_analysis`, list bounded claims separately rather
than treating the entire ecosystem as one proposition.

### 3. Programmatic

- Does the material concern automated media buying or selling?
- Which buyers, sellers, platforms, intermediaries, or inventory sources are
  named, and which remain hidden?
- What transparency is claimed, by whom, and on what evidence?
- Are fraud, brand safety, suitability, supply-chain, auction, identity, or CTV
  concerns raised?
- Are measurements independently inspectable or supplied only by an interested
  actor?
- What relevant process, fee, dependency, or data path remains unexplained?

### 4. Privacy / GDPR

- Is personal data said to be collected, inferred, shared, matched, retained,
  or deleted?
- Is consent, a CMP, TCF, a cookie mechanism, or another preference signal
  mentioned?
- Is a lawful-basis, controller, processor, purpose, minimization, retention,
  or data-subject-rights claim made?
- Is the statement legal, technical, operational, or commercial?
- What jurisdiction and processing context does the source actually identify?
- Which points require review by a qualified legal or privacy professional?

This section records privacy and GDPR-related claims and missing evidence. It
does not decide whether GDPR applies, whether consent is required or valid,
whether a lawful basis exists, or whether conduct is compliant.

### 5. Attribution

- What conversion, outcome, or business result is claimed?
- Is causality asserted, or is the evidence only correlational?
- What attribution model, window, identity method, or counterfactual is
  assumed?
- Is incrementality tested? If so, is the design inspectable?
- Could channel overlap, selection, missing consent, modeled data, or reporting
  incentives affect the result?
- What evidence could strengthen, weaken, or reverse the attribution claim?

### 6. Analytics

- Which metrics are used, and how are they defined?
- Are values observed, modeled, sampled, estimated, extrapolated, or inferred?
- What population, denominator, date range, geography, and exclusions apply?
- Could consent gaps, blockers, platform restrictions, data loss, or
  deduplication affect coverage?
- Are uncertainty, error bars, methodology changes, and missing data visible?
- Could selective reporting, survivorship, optimization, or commercial bias
  affect the presentation?

### 7. Digital Strategy

- What business or public-interest objective is claimed?
- Which audience, channel, market, journey, or funnel stage is involved?
- Are the stated KPIs aligned with that objective?
- What assumptions, dependencies, trade-offs, and second-order effects are
  unstated?
- Which actors benefit, pay, lose visibility, or carry implementation risk?
- For a proposal, what failure modes and stop conditions require review?

### 8. European Media Ecosystem

- Which public, commercial, civil-society, standards, platform, publisher,
  advertiser, agency, technology, or audience actors are relevant?
- Which actors benefit, and which carry legal, financial, reputational,
  operational, or evidential risk?
- Is regulation relevant as a claim, a constraint, or contextual framing?
- Are standards or sector frameworks used as inspectable evidence, as
  self-description, or only as persuasive framing?
- Are cross-border, language, market, media-plurality, or platform-dependency
  differences material?
- What conflicting interests or unavailable perspectives must remain visible?

### 9. HUB_Optimus Decomposition

Complete every field. `None identified`, `no evidence provided`, or `no action
justified` is preferable to omission or invented certainty.

- Claim: the specific bounded assertion being reviewed. In
  `proposal_analysis`, include only claims supporting or opposing the proposal;
  do not relabel the proposal itself as a `claim_record`.
- Evidence: inspectable material supporting, weakening, or contextualizing the
  claim, including provenance and limitations.
- Inference: reasoning that goes beyond the evidence, with assumptions and
  plausible alternatives made explicit.
- Uncertainty: information that is unknown, contested, incomplete, unavailable,
  or not independently checked.
- Narrative amplification: framing, repetition, urgency, authority appeal,
  selective omission, or certainty compression that may exceed the evidence.
  Identifying amplification does not prove the claim false.
- Operational relevance: the bounded consequence for the review, including an
  explicit no-action result when no valid signal exists.

For `conflict_analysis`, repeat the six fields for each bounded claim that
materially affects the system map. Do not use one aggregate verdict for all
actors or evidence zones.

### 10. Decision

Select one or more manual routing outcomes and record the reason:

- No action.
- Needs evidence.
- Needs qualified legal/privacy review.
- Needs source comparison.
- Suitable for private notes only.
- Suitable for a future RFC or issue only if a visible GitHub signal exists.

Decision reason:

Reviewer:

Review date:

The decision is a review-routing note, not an automated action, recommendation,
legal conclusion, compliance verdict, or authorization to implement.

## Non-Goals

This matrix does not add, authorize, or claim:

- runtime, simulator, schema, benchmark, CI, or dependency changes;
- scoring, dashboards, crawlers, monitoring, automated ingestion, or provider
  integrations;
- automated mode classification, verification, recommendation, or
  truth adjudication;
- access to advertising platforms, CMPs, analytics systems, personal data, or
  private media systems;
- legal advice, GDPR applicability or compliance conclusions, or replacement
  of qualified legal/privacy review;
- treating DIMAQ, IAB, industry standards, certifications, provider reports, or
  trade-body materials as authoritative project truth; or
- publication of confidential, client-sensitive, personal, security-sensitive,
  or otherwise non-public material in GitHub.

Any implementation, automation, data collection, legal conclusion, or
externally exposed use requires its own explicit GitHub scope and
human-accountable review.
