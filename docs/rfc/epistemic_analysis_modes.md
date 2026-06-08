# RFC: Epistemic Analysis Modes

## Status

- Draft / RFC only
- Governance proposal
- Not implemented
- Tracks issue #1630
- No runtime, schema, dataset, fixture, benchmark, CI, dashboard, scoring, or LLM-as-judge change

## Purpose

This RFC defines generic analytical input modes before evaluation occurs.

The goal is to prevent HUB_Optimus from mixing concrete claims, submitted proposals, and broad conflict systems into a single output contract.

Core rule:

```text
Every analytical input must declare its analysis mode before evaluation.
```

Spanish reference:

```text
Toda entrada analitica debe declarar su modo antes de ser evaluada.
```

## Relationship to Existing Work

This RFC does not replace existing work.

- Issue #1547 defines the current `claim_record` dataset/schema lane for narrative-risk claim triage.
- Issue #1625 and `docs/rfc/proposal_scenario_analysis_mode.md` define the proposal/scenario analysis boundary.
- Issue #1630 requests the generic mode taxonomy that keeps those lanes distinct before future implementation work.

## Mode Selection Rule

An input must be classified before evaluation:

```text
input_text -> declared_mode -> mode-specific validation -> mode-specific output
```

If the mode is unclear, the analysis must stop and request clarification or use a constrained framing. It must not silently blend modes.

The first supported conceptual modes are:

1. `claim_record`
2. `proposal_analysis`
3. `conflict_analysis`

## Modes

### `claim_record`

Use `claim_record` for concrete assertions about reality, evidence, interpretation, capability, intent, speech, events, or causal effects.

Example inputs:

```text
X happened.
Y said Z.
This policy caused this effect.
```

Use this mode when the input asks whether a statement is supported, unsupported, uncertain, amplified, or operationally relevant.

Do not use this mode when the input is primarily a proposed intervention, a future plan, a mediation option, or a broad conflict-system review.

Expected output fields:

- `claim`
- `evidence`
- `inference`
- `uncertainty`
- `narrative_amplification`
- `operational_relevance`

Boundary:

`claim_record` must not turn a claim into project doctrine, truth adjudication from a weak source, or an instruction to act.

### `proposal_analysis`

Use `proposal_analysis` for solutions, plans, hypotheses, interventions, policy proposals, mediation options, or future-oriented scenario ideas.

Example inputs:

```text
If actor A did X, Y could happen.
One solution would be Z.
This plan would reduce the conflict.
```

Use this mode when the input asks how a submitted proposal should be stress-tested for assumptions, consequences, dependencies, and failure modes.

Do not use this mode when the input is only a factual claim, a request to verify an event, or a broad conflict-system review without a specific proposal.

Expected output fields:

- `proposal`
- `assumptions`
- `intended_effects`
- `second_order_effects`
- `failure_modes`
- `affected_actors`
- `uncertainty`
- `operational_relevance`

Boundary:

`proposal_analysis` must preserve non-endorsement. HUB_Optimus may stress-test a submitted proposal, but must not present it as a recommendation, prediction, directive, or political solution owned by HUB_Optimus.

### `conflict_analysis`

Use `conflict_analysis` for broad conflict systems, crises, multi-actor tensions, escalation dynamics, or narrative/evidence separation across a complex situation.

Example inputs:

```text
Analyze conflict X.
Evaluate the dynamics between A and B.
Separate narrative, evidence, and uncertainty in a crisis.
```

Use this mode when the input requires a system-level map of actors, interests, evidence zones, uncertainty zones, escalation risks, de-escalation factors, and operational relevance.

Do not use this mode when the input is only a single concrete claim or a specific proposed solution. Do not introduce a concrete conflict fixture in this RFC.

Expected output fields:

- `conflict_scope`
- `actors`
- `interests`
- `evidence_zones`
- `uncertainty_zones`
- `narrative_pressures`
- `escalation_risks`
- `deescalation_factors`
- `operational_relevance`

Boundary:

`conflict_analysis` must remain generic until a separate issue or PR authorizes concrete fixtures. It must not smuggle in Russia-Ukraine, Israel-Gaza, or any other specific conflict case as part of the taxonomy PR.

## Future Tooling Direction

This RFC does not build tooling. It only reserves conceptual space for possible future internal components:

1. `mode_classifier` - decides which mode the input belongs to.
2. `mode_validator` - verifies that the input satisfies the declared mode contract.
3. `mode_renderer` - produces the correct output shape for the declared mode.

Possible future flow:

```text
input_text -> mode_classifier -> claim_record | proposal_analysis | conflict_analysis
mode_validator -> analysis_engine -> mode_renderer
```

Any tooling must be proposed in a separate GitHub issue or RFC follow-up.

## Non-Goals

This RFC does not add, authorize, or require:

- runtime changes
- simulator changes
- schema changes
- benchmark changes
- CI changes
- dataset changes
- fixture changes
- concrete conflict cases
- Russia-Ukraine content
- Israel-Gaza content
- scoring
- dashboards
- LLM-as-judge
- semantic adjudication
- automated recommendation engines
- roadmap changes
- changes to `docs/architecture/runtime_contract.md`

## Acceptance Criteria

This RFC satisfies issue #1630 when:

- it defines the three initial modes: `claim_record`, `proposal_analysis`, and `conflict_analysis`;
- it explains when to use each mode;
- it explains when not to use each mode;
- it defines expected output fields for each mode;
- it explicitly blocks concrete conflict fixtures in this PR;
- it explicitly blocks runtime, CI, schema, scoring, dashboard, and LLM-as-judge changes;
- it remains small, reviewable, reversible, and RFC-only.

## Future Work

Possible follow-up work must be opened as separate GitHub issues after this RFC is reviewed.

Suggested sequence:

1. `docs: add mode selection guidance`
2. `scenarios: add generic conflict_analysis fixture template`
3. `scenarios: add concrete conflict_analysis fixture`

No follow-up is authorized by this RFC alone.
