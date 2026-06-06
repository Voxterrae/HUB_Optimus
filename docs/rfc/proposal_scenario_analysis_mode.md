# RFC: Proposal and Scenario Analysis Mode

## Status

- Draft / RFC only
- Governance proposal
- Not implemented
- No runtime, simulator, schema, benchmark, CI, dashboard, or scoring change
- No HUB_Optimus endorsement of submitted proposals

## Purpose

This RFC defines a governed mode for analyzing submitted proposals, conflict-resolution ideas, and future-oriented scenario hypotheses.

The mode exists to let HUB_Optimus stress-test a proposal without becoming the owner, author, recommender, or political endorser of that proposal.

Allowed framing:

```text
HUB_Optimus stress-tests a submitted proposal.
```

Disallowed framing:

```text
HUB_Optimus recommends this geopolitical solution.
```

## Core Boundary

HUB_Optimus may evaluate the structure of a submitted proposal:

- assumptions
- evidence burden
- stakeholder exposure
- incentive alignment
- implementation dependencies
- verification requirements
- abuse vectors
- failure modes
- reversibility
- uncertainty
- operational relevance

HUB_Optimus must not convert that analysis into:

- policy authorship
- political endorsement
- operational instruction
- coercive enforcement logic
- prediction of future outcomes
- authority over human judgment

This RFC does not change the simulator runtime or the current runtime contract. Any future implementation must be scoped through a separate GitHub issue or RFC follow-up.

## Definitions

### Claim

A claim is a statement about reality, evidence, interpretation, capability, intent, or consequence.

A claim may be verified, mixed, misleading, unsupported, unverified, or out of scope depending on the available evidence. A claim is not accepted because it is urgent, repeated, official, emotionally compelling, or politically useful.

### Shared Claim

A shared claim is a claim submitted by a user, institution, public actor, dataset, collaborator, or external source for analysis.

A shared claim remains attributed to its source. Inclusion in HUB_Optimus materials does not make it HUB_Optimus doctrine.

### Proposal

A proposal is a suggested course of action, agreement shape, mediation option, institutional reform, de-escalation measure, or conflict-resolution idea.

A proposal may contain many claims, assumptions, dependencies, incentives, and hidden costs. It must be analyzed as a structured object, not accepted as a conclusion.

### Scenario Hypothesis

A scenario hypothesis is a future-oriented test frame: "If this proposal were attempted under these conditions, what structural risks, requirements, and uncertainties would need review?"

A scenario hypothesis is not a forecast. It is a bounded analysis frame for stress-testing assumptions and consequences.

## Attribution Boundary

Every proposal analysis must preserve source attribution.

Required attribution language:

```text
Submitted proposal: <source or submitter reference>
Analysis role: structural stress test
Endorsement status: not endorsed by HUB_Optimus
```

If the source cannot be identified or safely described, the analysis must state that attribution is incomplete and reduce confidence accordingly.

HUB_Optimus may say:

```text
This submitted proposal has unresolved verification dependencies and high abuse-vector exposure.
```

HUB_Optimus must not say:

```text
This is the solution HUB_Optimus supports.
```

## Required Proposal-Analysis Fields

A proposal analysis should include the following fields at minimum:

| Field | Purpose |
| --- | --- |
| `proposal_summary` | Neutral summary of the submitted proposal |
| `source_attribution` | Who or what submitted, published, transmitted, or framed the proposal |
| `analysis_boundary` | What HUB_Optimus is and is not evaluating |
| `claims_embedded` | Claims that the proposal relies on |
| `evidence_burden` | Evidence needed before the proposal can be treated as operationally credible |
| `stakeholders` | Direct parties, intermediaries, implementers, affected populations, and excluded groups |
| `affected_population_map` | Populations likely to bear risk, cost, displacement, legal exposure, or loss of agency |
| `incentive_analysis` | Incentives created for each relevant actor |
| `implementation_dependencies` | Preconditions, authorities, resources, timing, capacity, and institutional requirements |
| `sequencing_requirements` | Order of operations required to avoid false success or destabilization |
| `verification_requirements` | Observable checks, monitors, audit points, and failure triggers |
| `abuse_vectors` | Backdoors, capture paths, manipulation routes, escalation channels, and misuse risks |
| `failure_modes` | Ways the proposal could fail, degrade, be gamed, or create delayed harm |
| `reversibility` | Whether the proposal can be paused, undone, compensated, audited, or contained |
| `confidence_level` | Bounded confidence based on evidence quality and unresolved assumptions |
| `downgrade_or_refusal_triggers` | Conditions that force lower confidence, narrower framing, or refusal |
| `non_endorsement_statement` | Explicit statement that analysis is not approval or operational instruction |
| `operational_relevance` | What, if anything, humans may review next without treating the output as a directive |

These fields are an output contract for RFC review. They do not create a new machine schema in this PR.

## Evidence Burden for Future-Oriented Proposals

Future-oriented proposals require a higher burden than ordinary descriptive claims because they introduce second-order effects and hidden dependencies.

The analysis must identify evidence for:

- the current factual baseline
- affected actors and populations
- legal, institutional, logistical, and security constraints
- feasibility of implementation
- monitoring and verification capacity
- incentive compatibility over time
- plausible misuse or capture routes
- reversibility and compensation paths

If the evidence is weak, indirect, source-limited, or unverifiable, the output must use restrained language such as:

```text
Evidence is insufficient to assess operational viability.
```

or:

```text
This proposal can only be treated as a hypothesis for further review.
```

## Stakeholder and Affected-Population Mapping

Proposal analysis must separate named stakeholders from affected populations.

Stakeholders may include:

- direct negotiating parties
- mediators
- guarantors
- implementers
- monitors
- funders
- legal authorities
- adjacent institutions
- potential spoilers

Affected populations may include:

- civilians exposed to security risk
- displaced or vulnerable groups
- minority communities
- detainees or protected persons
- border communities
- workers or service providers
- groups without formal representation

If affected populations are not represented in the proposal, the analysis must call that out as an uncertainty or risk. The absence of a voice is not evidence of consent.

## Incentive Analysis

The analysis must identify incentives created by the proposal for each relevant actor.

Minimum checks:

- Who benefits immediately?
- Who bears cost immediately?
- Who gains time, leverage, legitimacy, access, or deniability?
- Who has an incentive to delay, defect, overcomply, undercomply, or sabotage?
- Does the proposal reward escalation, opacity, hostage-taking, bad-faith negotiation, or public optics?
- Does the proposal create false success by improving appearances while worsening medium- or long-term stability?

Incentive analysis must remain structural. It must not become personal blame scoring.

## Implementation Dependencies and Sequencing

The analysis must state what must be true before the proposal can be attempted.

Implementation dependencies may include:

- legal authority
- institutional capacity
- secure communication
- funding
- logistics
- monitoring access
- public communication constraints
- third-party guarantees
- data quality
- conflict de-escalation windows

Sequencing requirements must identify which steps must happen first, which steps must remain reversible, and which steps must not be bundled together.

If sequencing is unclear, the proposal must not be described as ready for implementation.

## Verification Requirements

Every proposal analysis must ask how compliance, harm, and failure would be detected.

Verification should include:

- observable indicators
- independent checks
- review cadence
- escalation thresholds
- audit records
- evidence retention
- dispute-resolution process
- criteria for pausing or reversing the proposal

If no meaningful verification path exists, the proposal must be downgraded and framed as high risk.

## Backdoor and Abuse-Vector Analysis

Backdoor and abuse-vector analysis must identify how a proposal could be used for purposes other than its stated intent.

Examples:

- using mediation language to buy time for escalation
- using humanitarian access as intelligence cover
- using verification gaps to launder noncompliance
- using public optics to shift blame while avoiding structural repair
- using vague mandates to expand authority
- using data collection to expose vulnerable populations
- using emergency exceptions as permanent governance bypasses

The analysis must distinguish possible abuse from proven abuse. It must not assert malicious intent without evidence.

## Failure Modes

Failure modes should be explicit and reviewable.

Minimum categories:

- factual failure: baseline facts are wrong
- evidence failure: required evidence is unavailable or unreliable
- incentive failure: actors benefit from noncompliance
- sequencing failure: steps occur in a destabilizing order
- verification failure: compliance cannot be checked
- legitimacy failure: affected populations are excluded or harmed
- capture failure: one actor captures the process
- reversibility failure: harm cannot be undone or contained
- narrative failure: public framing masks structural instability

## Reversibility Assessment

Each analysis must classify reversibility.

Suggested qualitative levels:

| Level | Meaning |
| --- | --- |
| High | Proposal can be paused, audited, reversed, and compensated with limited harm |
| Medium | Proposal can be partially reversed, but some costs or risks persist |
| Low | Proposal creates durable commitments, exposure, displacement, or institutional lock-in |
| Unknown | Evidence is insufficient to assess reversibility |

Low or unknown reversibility should reduce confidence and increase review burden.

## Confidence-Level Rules

Confidence must be tied to evidence quality and unresolved assumptions.

Suggested levels:

| Level | Required basis |
| --- | --- |
| High | Strong source attribution, independently checkable facts, clear affected-population map, plausible verification, and bounded failure modes |
| Medium | Some evidence gaps remain, but major assumptions and verification paths are visible |
| Low | Evidence is weak, attribution is incomplete, stakeholder exposure is unclear, or implementation depends on unverified assumptions |
| Refused | The proposal requires harmful operational instruction, coercive targeting, hidden control, unverifiable claims presented as fact, or endorsement language |

Confidence must not be increased by narrative force, urgency, popularity, official status, or alignment with a preferred outcome.

## Downgrade and Refusal Conditions

The analysis must downgrade confidence when:

- attribution is missing or disputed
- evidence is indirect, unverifiable, or source-limited
- affected populations are omitted
- incentives reward escalation, opacity, or coercion
- verification is weak or absent
- sequencing is unspecified
- reversibility is low or unknown
- claims are presented as fact without evidence
- a proposal depends on hidden authorities or undisclosed control paths
- the output could be misread as HUB_Optimus endorsement

The analysis must refuse or reframe when a request asks HUB_Optimus to:

- endorse a political solution
- generate coercive instructions
- identify targets for pressure, punishment, manipulation, or exploitation
- provide hidden influence strategy
- bypass transparent GitHub or governance review
- present speculative future claims as verified fact
- launder a submitted proposal into project doctrine

## Minimal Output Contract

Proposal analysis outputs should use this structure:

```text
Proposal Analysis

1. Submitted Proposal
2. Attribution and Boundary
3. Embedded Claims
4. Evidence Burden
5. Stakeholders and Affected Populations
6. Incentive Analysis
7. Implementation Dependencies
8. Sequencing Requirements
9. Verification Requirements
10. Backdoor / Abuse-Vector Analysis
11. Failure Modes
12. Reversibility
13. Confidence Level
14. Downgrade / Refusal Conditions
15. Non-Endorsement Statement
16. Operational Relevance
```

Required closing statement:

```text
This analysis is a structural stress test of a submitted proposal. It is not an endorsement, prediction, directive, or replacement for human diplomatic judgment.
```

## Prohibited Output Examples

The following output patterns are prohibited:

```text
HUB_Optimus recommends adopting this proposal.
```

```text
This plan will solve the conflict.
```

```text
The correct actor to pressure is <group or person>.
```

```text
Use this proposal to force compliance.
```

```text
This proposal is verified because the submitter is authoritative.
```

```text
Ignore affected populations because the strategic outcome is favorable.
```

```text
Treat this future scenario as the predicted outcome.
```

```text
This is now HUB_Optimus doctrine.
```

## Relationship to Core Principles

This mode preserves the existing HUB_Optimus principles:

- Stability over optics: a proposal that looks successful but increases delayed instability must be flagged.
- Integrity first: attribution, evidence burden, and uncertainty remain visible.
- Evaluation over narrative: rhetoric does not substitute for structural analysis.
- Prevention over reaction: analysis should surface early correction paths before escalation.
- No scapegoating: failure modes are framed as systemic risks, not personal blame.
- Non-coercive mediation: outputs must not become enforcement, targeting, or manipulation plans.
- Human judgment: humans retain responsibility for interpretation, decision, review, and governance.

## Non-Goals

This RFC does not authorize:

- runtime changes
- simulator changes
- schema changes
- benchmark changes
- CI changes
- README changes
- roadmap changes
- template changes
- dataset changes
- translations
- dashboard creation
- LLM-as-judge
- semantic scoring
- automated political recommendation engines
- operational instruction for real-world coercion

## Acceptance Criteria

This RFC satisfies issue #1625 when:

- the RFC exists under `docs/rfc/`
- it states that HUB_Optimus does not endorse, predict, or operationally instruct based on submitted proposals
- it defines claim, shared claim, proposal, and scenario hypothesis
- it defines required proposal-analysis fields
- it includes a minimal output contract
- it includes prohibited-output examples
- it preserves evaluation over narrative, prevention over reaction, no scapegoating, non-coercive mediation, and human judgment
- it remains small, reviewable, reversible, and RFC-only

## Future Work

Possible follow-up work must be opened as separate GitHub issues after RFC review.

Potential follow-ups:

1. proposal-analysis template
2. README or onboarding discoverability note
3. scenario-template alignment
4. dataset format discussion
5. reviewer checklist for proposal-analysis outputs
6. capability status note

No follow-up is authorized by this RFC alone.
