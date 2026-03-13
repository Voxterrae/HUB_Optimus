# Scenario Catalog

This index tracks the hand-maintained scenarios currently committed to the
repository.

Scope notes:

- Include canonical scenarios and benchmarks committed to Git.
- Exclude translated mirrors of the same scenario.
- Exclude generated artifacts under `scenarios/generated/`,
  `scenarios/mutations/`, and other derived outputs.

---

| Scenario | Family | Status | Description |
|---|---|---|---|
| [`example_scenario`](../../example_scenario.json) | Ceasefire Negotiation | example | Simple partial ceasefire input used to demonstrate the simulator CLI |
| [`ceasefire_basic`](../../benchmarks/scenarios/ceasefire_basic.json) | Ceasefire Negotiation | benchmark | Simple bilateral ceasefire negotiation with compatible objectives |
| [`ceasefire_fragile`](../../benchmarks/scenarios/ceasefire_fragile.json) | Ceasefire Negotiation | benchmark | Ceasefire with external mediation and limited rounds, used as a fragile convergence case |
| [`ceasefire_failure`](../../benchmarks/scenarios/ceasefire_failure.json) | Ceasefire Negotiation | benchmark | Hardline negotiation breakdown with no feasible settlement space |
| [`scenario_001_partial_ceasefire`](../../v1_core/workflow/scenario_001_partial_ceasefire.md) | Ceasefire Negotiation | workflow reference | Narrative reference scenario showing an unverifiable ceasefire as destabilizing |
| [`scenario_002_verified_ceasefire`](../../v1_core/workflow/scenario_002_verified_ceasefire.md) | Ceasefire Negotiation | workflow reference | Narrative reference scenario showing a verified ceasefire as stabilizing |
| [`scenario_003_coalition_fracture`](../../v1_core/workflow/scenario_003_coalition_fracture.md) | Coalition Stability | experimental | External negotiation constrained by an internal coalition veto player |

---

## How to extend this table

When adding a new scenario:

1. Add one row for the canonical scenario file.
2. Reuse the primary family from
   [scenario_taxonomy.md](scenario_taxonomy.md).
3. Choose one status:
   `example`, `benchmark`, `workflow reference`, or `experimental`.
4. Keep the description to one sentence focused on the diplomatic dynamic.

If a scenario evolves from experimental to benchmark status, update this table
in the same pull request that freezes or promotes it.
