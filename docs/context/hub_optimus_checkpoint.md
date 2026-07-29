# HUB_Optimus — archived systemic checkpoint

Status: **historical snapshot (non-authoritative)**

This file preserves an early project checkpoint for traceability. It is not
updated at milestones and must not be used to determine current release,
runtime, CI, benchmark, scenario, phase, task, or deployment state.

Use the hierarchy in
[`docs/context/SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md), the current
language/canonical policy in [`STATUS.md`](STATUS.md), operational boundaries
in [`AI_HANDOFF.md`](AI_HANDOFF.md), and the explicit-commit
[capability ledger](../architecture/capability_status.md).

## Values recorded by the historical snapshot

| Property | Historical recorded value | Current authority |
| --- | --- | --- |
| Release | `v0.1.0` | Live GitHub Releases; external to this file |
| Runtime | `stable` | Applicable source, runtime contract, tests, and GitHub Checks at a named commit |
| CI | `passing` | Live GitHub Checks for the relevant commit or PR |
| Benchmarks | `active` | Versioned benchmark source, expected bytes, and their execution result |

None of the values above is a current attestation.

## Work recorded as completed at that time

- PR #109 was recorded as merged.
- A benchmark summary was recorded as visible in CI.
- `runtime_contract.md` was recorded as published.
- Scenario references 001–005 were recorded as integrated.

## Scenario references recorded at that time

| # | Name | Family |
| --- | --- | --- |
| 001 | Partial Ceasefire | Ceasefire Negotiation |
| 002 | Verified Ceasefire | Ceasefire Negotiation |
| 003 | Coalition Fracture | Coalition Stability |
| 004 | Shared Resource Drought | Shared Resource Conflict |
| 005 | Spain Diplomatic War Accusation | Domestic Political Pressure |

The current classification and existence of scenario material must be checked
against the baseline tree and
[`docs/scenarios/catalog.md`](../scenarios/catalog.md).

## Taxonomy families recorded at that time

- Ceasefire Negotiation
- Coalition Stability
- Shared Resource Conflict
- Domestic Political Pressure

## Documentary paths recorded at that time

```text
docs/scenarios/
  scenario_taxonomy.md
  scenario_template.md
  catalog.md
```

## Phase sequence recorded at that time

1. Phase 1 — reproducible runtime
2. Phase 2 — executable benchmarks
3. Phase 3 — CI observability
4. Phase 4 — behavioral diagnostics (then marked as active)

## Proposed follow-up recorded at that time

The snapshot named “Task 24 — structural drift analysis for benchmarks” and
“commit → push → PR”. These are historical notes, not an active assignment or
authorization.
