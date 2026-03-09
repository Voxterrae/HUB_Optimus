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

## Boundary search (automatic instability discovery)

Binary search finds the exact stability boundary for each axis on
each family with O(log N) probes instead of exhaustive sweeps.

Tool: `python tools/scenario_boundary_search.py --seeds 42,99,7,123,256`

### Single-seed boundaries (seed 42)

| Family | rounds_min | actors_min | threshold_max |
|---|---|---|---|
| incentive_misalignment | 2 | 1 | 5 |
| info_asymmetry | 3 | 2 | 5 |
| resource_scarcity | 1 | 2 | 5 |

### Multi-seed consensus (worst-case across 5 seeds)

| Family | rounds_min | actors_min | threshold_max |
|---|---|---|---|
| incentive_misalignment | **3** | **2** | 5 |
| info_asymmetry | **4** | **2** | **4** |
| resource_scarcity | **3** | **4** | 5 |

### Key findings from multi-seed analysis

1. **Single-seed results are optimistic.** Seed 42 showed
   resource_scarcity stable at actors=2; but seed 99 requires actors=4.
   Single-seed boundaries are necessary but not sufficient.

2. **info_asymmetry is confirmed most fragile.** Needs 4 rounds AND
   2+ actors AND threshold ≤ 4. It is the only family where threshold
   constrains stability.

3. **resource_scarcity shifts from most resilient to most demanding
   in actor count.** Seed 99 pushes actors_min to 4 — the highest of
   any family. The previous observation (resilient at rounds=1) was
   seed-dependent.

4. **Threshold is nearly always unconstrained.** Only info_asymmetry
   at seed 99 shows threshold_max < 5. The random policy's uniform
   distribution over [1, 5] makes threshold failures rare except under
   tight round budgets.

5. **Seed 99 is the most adversarial seed tested.** It shifts
   boundaries for all three families, revealing that seed 42 was a
   particularly lenient RNG path.

### Per-seed detail

| Family | Seed 42 | Seed 99 | Seed 7 | Seed 123 | Seed 256 |
|---|---|---|---|---|---|
| info_asymmetry rounds | 3 | 1 | 3 | **4** | 3 |
| info_asymmetry actors | 2 | 1 | 2 | 2 | 2 |
| info_asymmetry threshold | 5 | **4** | 5 | 5 | 5 |
| resource_scarcity rounds | 1 | **3** | 1 | 1 | 1 |
| resource_scarcity actors | 2 | **4** | 2 | 1 | 1 |
| incentive_misalignment rounds | 2 | 1 | 2 | **3** | 2 |
| incentive_misalignment actors | 1 | 1 | 2 | 2 | 2 |

---

## Boundary verification

After finding boundaries, automated verification confirms consistency:
boundary converges, boundary-1 fails (or boundary+1 fails for max).

Tool: `python tools/scenario_boundary_search.py --seeds 1,42,123 --verify`

### Reproducibility test (seeds 1, 42, 123)

| Family | Seed 1 | Seed 42 | Seed 123 | Consensus |
|---|---|---|---|---|
| incentive_misalignment rounds | 3 | 2 | 3 | **3** |
| incentive_misalignment actors | 2 | 1 | 2 | **2** |
| incentive_misalignment threshold | 5 | 5 | 5 | 5 |
| info_asymmetry rounds | 4 | 3 | 4 | **4** |
| info_asymmetry actors | 2 | 2 | 2 | 2 |
| info_asymmetry threshold | None | 5 | 5 | 5 |
| resource_scarcity rounds | 1 | 1 | 1 | 1 |
| resource_scarcity actors | 1 | 2 | 1 | **2** |
| resource_scarcity threshold | None | 5 | 5 | 5 |

### Verification result: ALL PASSED

All per-seed boundaries verified: each seed's own boundaries are
consistent (boundary passes, boundary−1 fails).

### Discovery: axis coupling

Seed 1 produces `threshold=None` for info_asymmetry and
resource_scarcity. This does NOT mean threshold is unconstrained —
it means the base scenario's `max_rounds` is insufficient for seed 1's
RNG path, so threshold testing inherits the round failure. The axes
are coupled: threshold stability depends on the base scenario's round
budget.

This is a structural property of single-axis boundary search. A full
bifurcation frontier (multi-axis) would decouple this.

---

## Convergence gradient

Measures the convergence round at each parameter value, producing
behavioural curves instead of binary pass/fail.

Tool: `python tools/scenario_boundary_search.py --gradient`

### Rounds axis (seed 42)

| Family | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 |
|---|---|---|---|---|---|---|---|---|---|---|
| incentive_misalignment | X | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 |
| info_asymmetry | X | X | R3 | R3 | R3 | R3 | R3 | R3 | R3 | R3 |
| resource_scarcity | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 |

**Key pattern:** Once past the boundary, convergence round is fixed.
Adding more rounds does NOT accelerate convergence — the system
converges as fast as the RNG allows, then ignores remaining budget.

### Actors axis (seed 42)

| Family | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| incentive_misalignment | R5 | R3 | R2 | R2 | R1 | R1 |
| info_asymmetry | X | R3 | R2 | R2 | R1 | R1 |
| resource_scarcity | X | R2 | R2 | R1 | R1 | R1 |

**Key pattern:** More actors = monotonically faster convergence.
Consistent with P ≈ 1−(4/5)^N model. At 5+ actors, all families
converge in round 1. No counter-intuitive "more actors hurts
convergence" detected (yet).

### Threshold axis (seed 42)

| Family | T=1 | T=2 | T=3 | T=4 | T=5 |
|---|---|---|---|---|---|
| incentive_misalignment | R1 | R1 | R2 | R1 | R2 |
| info_asymmetry | R1 | R1 | R3 | R2 | R2 |
| resource_scarcity | R1 | R1 | R2 | R1 | R1 |

**Key pattern:** Threshold gradient is non-monotonic. T=3 is
consistently harder than T=4 or T=5 for this seed. This is a
RNG-path artifact: the random policy's sequence of offers happens to
match some thresholds faster than others. This non-monotonicity would
disappear with averaging across many seeds.

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
- ~~Does the mutation stability map change under different seeds?~~
  Answered: yes, significantly. Seed 99 is adversarial; seed 42 is
  lenient. Multi-seed consensus required for reliable boundaries.
- What is the full bifurcation frontier: the set of (actors, rounds,
  threshold) triples that separate agreement from failure?
- Can adversarial seed search find the single worst-case seed
  automatically?
- ~~Do boundaries survive verification (boundary−1 fails)?~~ Answered:
  all per-seed boundaries verified consistent with seeds 1, 42, 123.
- ~~Does convergence accelerate with more rounds?~~ Answered: no.
  Convergence round is fixed once past the boundary. Extra rounds are
  unused.
- Does the "more actors hurts convergence" phenomenon emerge under
  adversarial seeds or different scenario families?
- Can multi-axis boundary search (varying 2+ parameters simultaneously)
  decouple the axis coupling observed with seed 1?

## Methodology notes

- All generated scenarios use seed-controlled randomness (default: 42).
- Telemetry is collected via `python tools/scenario_telemetry.py`.
- Mutation sweeps via `python tools/scenario_mutator.py`.
- Results are written to `scenarios/telemetry.json` (per-scenario)
  and `scenarios/index.json` (aggregate).
- Mutation results go to `scenarios/mutations/` with per-axis subdirs.
- Boundary search via `python tools/scenario_boundary_search.py`.
- Boundary verification via `--verify` flag (confirms boundary−1 fails).
- Convergence gradient via `--gradient` flag (measures convergence
  round at each parameter value).
- Boundary results go to `scenarios/boundaries.json`.
- Generated, mutation, and boundary files are gitignored — regenerate
  locally.
