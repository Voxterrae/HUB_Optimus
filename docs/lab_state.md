# Lab State

Scientific memory for the HUB_Optimus exploration laboratory.

This document captures what the system has learned from running
synthetic scenarios — not code changes, but **behavioural observations**.

Update this file when telemetry reveals a new pattern or when a
previously observed pattern changes after a code modification.

---

## Current state

| Metric | Value |
|---|---|
| Generator families | 3 (info_asymmetry, resource_scarcity, incentive_misalignment) |
| Generated scenarios | 60 (seed 42) |
| Passed runtime | 60 |
| Runtime failures | 0 |
| Schema violations | 0 |
| Agreements reached | 55 |
| No agreement | 5 |
| Avg convergence round | 1.8 |

### Per-family breakdown

| Family | Scenarios | Agreements | Failures | Agreement rate |
|---|---|---|---|---|
| info_asymmetry | 20 | 20 | 0 | 100% |
| incentive_misalignment | 20 | 19 | 1 | 95% |
| resource_scarcity | 20 | 16 | 4 | 80% |

## Observed patterns

- **Resource scarcity scenarios are failure-prone by design.** Tight
  round limits (1–3) combined with high thresholds (4–5) make agreement
  unlikely under the default random-offer policy. 4 of 20 scenarios
  fail to reach agreement — all with `max_rounds=1`.
- **Information asymmetry scenarios always converge.** Moderate
  thresholds (3–5) and more rounds (3–7) give the random policy enough
  chances to hit the target. 20/20 reach agreement.
- **Incentive misalignment scenarios have variable actor counts.**
  The optional mediator role means some scenarios have 2 actors and
  others have 5, creating a wider behavioural spread. 19/20 converge;
  the one failure has only 2 rounds available.
- **Convergence is fast.** Average convergence at round 1.8 means
  most agreements happen in rounds 1–2, even in scenarios with 5+
  rounds available. The random policy's uniform distribution over
  [1, 5] makes a match probable early.

---

## Mutation sweep (stability boundary discovery)

Mutation testing varies **one parameter at a time** on representative
base scenarios to map the stability boundaries of the simulator.

Tool: `python tools/scenario_mutator.py` (3 axes, 62 mutations from
3 bases, seed 42).

### Sweep summary

| Axis | Mutations | Agreements | Failures | Agreement rate |
|---|---|---|---|---|
| threshold (offer 1–5) | 15 | 15 | 0 | 100% |
| rounds (max_rounds 1–10) | 30 | 27 | 3 | 90% |
| actors (count 1–6) | 17 | 15 | 2 | 88% |
| **Total** | **62** | **57** | **5** | **92%** |

### Failures (all 5)

| Scenario | Axis | Key parameter | Reason |
|---|---|---|---|
| info_asymmetry_001_actors_1 | actors | actors=1 | Single actor never matches threshold |
| resource_scarcity_021_actors_1 | actors | actors=1 | Single actor never matches threshold |
| incentive_misalignment_041_rounds_1 | rounds | max_rounds=1 | Needs 2 rounds, only 1 available |
| info_asymmetry_001_rounds_1 | rounds | max_rounds=1 | Needs 3 rounds, only 1 available |
| info_asymmetry_001_rounds_2 | rounds | max_rounds=2 | Needs 3 rounds, only 2 available |

### Discovered boundaries

1. **actors=1 is structurally broken.** With a single actor, the
   probability of matching the threshold drops from ~N×20% per round
   to ~20% per round. info_asymmetry and resource_scarcity bases fail;
   incentive_misalignment barely survives (converges at round 5 of 5).
   **Minimum viable actor count: 2.**

2. **max_rounds<3 creates fragile scenarios.** Two out of three families
   need at least 2 rounds to converge. info_asymmetry consistently needs
   round 3. Below that budget, failure is deterministic for that base.
   **Minimum reliable round budget: 3.**

3. **Threshold alone never causes failure.** All 15 threshold mutations
   converge. The uniform random policy over [1, 5] makes every threshold
   value reachable within the available rounds. Lower thresholds (1–2)
   converge faster (round 1), higher thresholds (3–5) may need round 2–3.

4. **More actors accelerate convergence monotonically.** With 5+
   actors, all three bases converge in round 1. The probability of at
   least one actor matching the threshold in a single round increases
   with actor count: P ≈ 1 - (4/5)^N.

5. **resource_scarcity is the most resilient family.** Converges at
   rounds=1 for any threshold, but still fails at actors=1.
   **info_asymmetry is the most fragile** — needs 3 rounds AND 2+ actors.

### Convergence gradient (actor axis, seed 42)

| Base | 1 actor | 2 actors | 3 actors | 4 actors | 5 actors | 6 actors |
|---|---|---|---|---|---|---|
| info_asymmetry_001 | ✗ | R3 | R2 | R2 | R1 | — |
| resource_scarcity_021 | ✗ | R2 | R2 | R1 | R1 | R1 |
| incentive_misalignment_041 | R5 | R3 | R2 | R2 | R1 | R1 |

### Convergence gradient (rounds axis, seed 42)

| Base | R1 | R2 | R3 | R4 | R5 | R6–R10 |
|---|---|---|---|---|---|---|
| info_asymmetry_001 | ✗ | ✗ | R3 | R3 | R3 | R3 |
| resource_scarcity_021 | R1 | R1 | R1 | R1 | R1 | R1 |
| incentive_misalignment_041 | ✗ | R2 | R2 | R2 | R2 | R2 |

---

## Questions to investigate

- ~~What is the agreement rate per family under seed 42?~~ Answered by
  base telemetry.
- Does adding a mediator role measurably change convergence speed?
- ~~At what `max_rounds` threshold does resource scarcity stop being
  failure-dominant?~~ Answered: resource_scarcity converges even at
  rounds=1 (threshold=4 with seed 42). It's fragile only at actors=1.
- Do any scenarios produce the same negotiation history despite
  different initial configurations? (structural equivalence)
- Does the mutation stability map change under different seeds?
- What is the full bifurcation frontier: the set of (actors, rounds,
  threshold) triples that separate agreement from failure?

## Methodology notes

- All generated scenarios use seed-controlled randomness (default: 42).
- Telemetry is collected via `python tools/scenario_telemetry.py`.
- Mutation sweeps via `python tools/scenario_mutator.py`.
- Results are written to `scenarios/telemetry.json` (per-scenario)
  and `scenarios/index.json` (aggregate).
- Mutation results go to `scenarios/mutations/` with per-axis subdirs.
- Generated and mutation files are gitignored — regenerate locally.
