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

## Questions to investigate

- What is the agreement rate per family under seed 42?
- Does adding a mediator role measurably change convergence speed?
- At what `max_rounds` threshold does resource scarcity stop being
  failure-dominant?
- Do any scenarios produce the same negotiation history despite
  different initial configurations? (structural equivalence)

## Methodology notes

- All generated scenarios use seed-controlled randomness (default: 42).
- Telemetry is collected via `python tools/scenario_telemetry.py`.
- Results are written to `scenarios/telemetry.json` (per-scenario)
  and `scenarios/index.json` (aggregate).
- Both files are gitignored — regenerate locally as needed.
