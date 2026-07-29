# Lab State

Scientific memory for the HUB_Optimus exploration laboratory.

This document captures what the system has learned from running
synthetic scenarios — not code changes, but **behavioural observations**.

Update this file when telemetry reveals a new pattern or when a
previously observed pattern changes after a code modification.

All empirical sections in this document were regenerated for issue #1775 from
commit `af89e420efb7b60eb95867b840ebeaf23dd989b6`, after the simulator
isolation (#1770), boundary-search correction (#1774), and generation-manifest
correction (#1779) were merged. Exact commands, tool and artifact hashes, and
the old-to-new result ledger are recorded in
[`docs/lab_regeneration_1775.md`](lab_regeneration_1775.md).

Labels used below:

- **Verified result** means a direct observation in a hashed raw artifact.
- **Inference** means a bounded interpretation of verified results.
- **Hypothesis** means an explanation not tested by this regeneration.
- **Uncertainty** states what the sampled evidence does not establish.

---

## Current state

| Metric | Value |
|---|---|
| Generator families | 3 (info_asymmetry, resource_scarcity, incentive_misalignment) |
| Generated scenarios | 60 (seed 42) |
| Passed runtime | 60 |
| Parse failures | 0 |
| Runtime failures | 0 |
| Schema violations | 0 |
| Agreements reached | 39 |
| No agreement | 21 |
| Avg convergence round (agreements) | 2.26 |

### Per-family breakdown

| Family | Scenarios | Agreements | No agreement | Agreement rate |
|---|---|---|---|---|
| info_asymmetry | 20 | 20 | 0 | 100% |
| incentive_misalignment | 20 | 16 | 4 | 80% |
| resource_scarcity | 20 | 3 | 17 | 15% |

### Mobile Ingest (Termux)

Capture an unverified raw claim from a mobile terminal into the private local
intake area:

```bash
python tools/mobile_ingest.py "AI regulation in Europe is accelerating"
```

Or via stdin:

```bash
echo "AI regulation in Europe is accelerating" | python tools/mobile_ingest.py
```

The default file is `.local/intake/mobile_ingest.jsonl`. The directory is
git-ignored and created with private permissions where the platform supports
them. A different operator-managed path may be selected explicitly:

```bash
python tools/mobile_ingest.py --output /private/path/mobile.jsonl "raw claim"
```

On POSIX systems with no-follow directory-descriptor support, the default path
is traversed and opened relative to verified directory descriptors. This keeps
parent-component replacement from redirecting a write outside the repository.
The protected default fails closed on platforms without those primitives,
including standard Windows Python builds; use an explicit operator-managed
`--output` path there.

New files use mode `0600` and the protected default intake directory uses
`0700` where POSIX modes are supported. Appending to an existing custom file
preserves its operator-defined mode. Existing custom JSONL files must be
readable as well as writable so the helper can restore a missing LF record
boundary before appending.

Every opened output must be a regular file. The protected default also requires
the file to have exactly one link, so FIFOs, devices, sockets, and hard-linked
default targets fail closed before permissions or content can change. An
explicit custom path remains operator-managed but is still required to be a
regular file.

Claim text beginning with `-` is accepted without being treated as an unknown
option or echoed by an argument-parser error. Use `--` before a claim that is
exactly `--output`, `-h`, or `--help`.

Every record is classified `private_raw_intake`, remains `unverified`, and has
`local_only` publication status. Intake is not evidence validation, analysis,
or project truth, and the tool never publishes or promotes records
automatically.

The operator is responsible for data classification, access, retention, secure
backup, and deletion. Do not enter credentials or secrets. Regulated,
client-confidential, or otherwise sensitive content requires an approved
private process. Existing root-level `mobile_ingest.jsonl` files are not moved
or deleted automatically; review and dispose of any such legacy local file
manually.

The helper does not provide encryption, managed confidential storage,
multi-process locking, retention automation, or backup. Operators must
serialize concurrent writers and remain responsible for access, retention,
backup, and deletion.

## Observed patterns

**Verified results:**

- Resource scarcity is the least successful generated family in this run:
  3/20 agreements. Its 17 no-agreements span every generated round budget:
  6 at `max_rounds=1`, 5 at `max_rounds=2`, and 6 at `max_rounds=3`.
- Information asymmetry records 20/20 agreements for these 20 generated
  scenarios at seed 42. This is a sampled result, not an “always converges”
  guarantee.
- Incentive misalignment records 16/20 agreements. Its four no-agreements
  occur with three actors and round budgets of 2 or 3.
- Of the 39 agreements, 25 converge in rounds 1–2; the remaining 14 converge
  in rounds 3, 4, or 6. The mean among agreements is 2.26.

**Inference:** in this generated corpus and seed, the combination of short
budgets and exact-equality thresholds is associated with substantially lower
resource-scarcity agreement than the other two families.

**Uncertainty:** one simulator seed and 20 generated cases per family do not
estimate a real-world agreement probability or establish that the family label
causes the difference.

---

## Mutation sweep (stability boundary discovery)

Mutation testing varies **one parameter at a time** on representative
base scenarios to map the stability boundaries of the simulator.

Tools:

```bash
python tools/scenario_mutator.py
python tools/scenario_telemetry.py \
  --scenario-dir scenarios/mutations --seed 42
```

The sweep covers three axes and 62 mutations from three representative bases.
All 62 inputs passed runtime processing; parse, schema, and runtime error
counts are zero. The no-agreement counts below do not include processing
errors.

### Sweep summary

| Axis | Mutations | Agreements | No agreement | Agreement rate |
|---|---|---|---|---|
| threshold (offer 1–5) | 15 | 14 | 1 | 93% |
| rounds (max_rounds 1–10) | 30 | 28 | 2 | 93% |
| actors (count 1–6) | 17 | 15 | 2 | 88% |
| **Total** | **62** | **57** | **5** | **92%** |

### No-agreement outcomes (all 5)

| Scenario | Axis | Key parameter | Reason |
|---|---|---|---|
| resource_scarcity_021_actors_1 | actors | actors=1 | No match within 3 rounds |
| resource_scarcity_021_actors_2 | actors | actors=2 | No match within 3 rounds |
| info_asymmetry_001_rounds_1 | rounds | max_rounds=1 | First match occurs at round 2 |
| resource_scarcity_021_rounds_1 | rounds | max_rounds=1 | First match occurs at round 2 |
| info_asymmetry_001_threshold_4 | threshold | offer=4 | No exact match within 4 rounds |

### Result, inference, and uncertainty

**Verified result:** one actor is successful for the information-asymmetry and
incentive-misalignment bases at seed 42; resource scarcity first succeeds at
three actors. There is no family-independent “minimum viable actor count” in
this sweep.

**Verified result:** incentive misalignment succeeds with one round, while the
other two bases first succeed with two. There is no common minimum reliable
budget of three rounds in this sweep.

**Verified result:** threshold mutation can produce a no-agreement outcome:
`info_asymmetry_001` fails at threshold 4 but succeeds at threshold 5. Exact
equality makes the threshold axis non-monotonic.

**Inference:** actor count is non-worsening for these three bases at seed 42,
but the seed-11 biased-policy counterexample in the boundary section prevents a
general monotonic claim.

**Uncertainty:** this is a one-at-a-time sweep of one generated base per family.
Interactions between axes are reported separately below; they cannot be
inferred from this table.

---

## Boundary search (automatic instability discovery)

`rounds_min` uses binary search because increasing `max_rounds` preserves
the deterministic execution prefix. `actors_min` enumerates 1–6 because
changing actor count changes subsequent random values, and
`threshold_max` enumerates 1–5 because success uses exact equality.

For actor count and threshold, “minimum” and “maximum” mean the extrema of
the successful values actually enumerated. They do not imply that every
larger or smaller value also succeeds.

Tool: `python tools/scenario_boundary_search.py --seeds 42,99,7,123,256`

Provenance: generated bases use generator seed 42; probes use the listed
seeds and the simulator-default policy. The scenarios are synthetic
runtime observations, not real-world predictions.

### Single-seed boundaries (seed 42)

| Family | rounds_min | actors_min | threshold_max |
|---|---|---|---|
| incentive_misalignment | 1 | 1 | 5 |
| info_asymmetry | 2 | 1 | 5 |
| resource_scarcity | 2 | 3 | 5 |

### Multi-seed consensus (worst-case across 5 seeds)

| Family | rounds_min | actors_min | threshold_max |
|---|---|---|---|
| incentive_misalignment | **4** | **2** | 5 |
| info_asymmetry | **5** | **3** | **4** |
| resource_scarcity | **3** | **4** | 5 |

### Key findings from multi-seed analysis

1. **Single-seed results are insufficient.** Seed 42 records
   `info_asymmetry` at `rounds_min=2`, while seed 99 records 5.

2. **`info_asymmetry` has the largest sampled round minimum.** Across
   these five seeds its consensus is 5 rounds and 3 actors, and it is
   the only family whose sampled `threshold_max` falls below 5.

3. **`resource_scarcity` has the largest sampled actor minimum.**
   Seed 256 records `actors_min=4`.

4. **Actor and threshold extrema are not monotonic guarantees.** Every
   value is retained in `actors_probe_states` or
   `threshold_probe_states`; the extrema are summaries of that evidence.

5. **These findings are seed- and policy-specific simulator results.**
   They do not establish external stability, causality, or prediction.

### Per-seed detail

| Family | Seed 42 | Seed 99 | Seed 7 | Seed 123 | Seed 256 |
|---|---|---|---|---|---|
| info_asymmetry rounds | 2 | **5** | 1 | 1 | 1 |
| info_asymmetry actors | 1 | **3** | 1 | 1 | 1 |
| info_asymmetry threshold | 5 | 5 | 5 | **4** | **4** |
| resource_scarcity rounds | 2 | 1 | 2 | **3** | **3** |
| resource_scarcity actors | 3 | 2 | 2 | 3 | **4** |
| incentive_misalignment rounds | 1 | **4** | 1 | 1 | 1 |
| incentive_misalignment actors | 1 | **2** | 1 | 1 | 1 |

---

## Boundary verification

After finding boundaries, automated verification re-enumerates every
value in each axis. It compares the reported minimum or maximum with the
extremum recomputed from the full state map, including valid `None`
results when every probe fails.

Tool: `python tools/scenario_boundary_search.py --seeds 1,42,123 --verify`

### Reproducibility test (seeds 1, 42, 123)

| Family | Seed 1 | Seed 42 | Seed 123 | Consensus |
|---|---|---|---|---|
| incentive_misalignment rounds | 2 | 1 | 1 | **2** |
| incentive_misalignment actors | 1 | 1 | 1 | 1 |
| incentive_misalignment threshold | 5 | 5 | 5 | 5 |
| info_asymmetry rounds | 2 | 2 | 1 | **2** |
| info_asymmetry actors | 1 | 1 | 1 | 1 |
| info_asymmetry threshold | 5 | 5 | 4 | **4** |
| resource_scarcity rounds | 1 | 2 | 3 | **3** |
| resource_scarcity actors | 1 | 3 | 3 | **3** |
| resource_scarcity threshold | 5 | 5 | 5 | 5 |

### Verification result: ALL PASSED

All per-seed extrema verified against fresh exhaustive state maps.

### Discovery: non-monotonic axes

With seed 2 and the simulator-default policy, both
`info_asymmetry_001` and `resource_scarcity_021` record threshold states:

`success, success, success, failure, success`

With seed 11 and the biased policy, `incentive_misalignment_041` records
actor states:

`failure, failure, success, success, success, failure`

The first sequence has `threshold_max=5`; the second has
`actors_min=3`. Binary search cannot recover either extremum reliably,
which is why those axes are enumerated.

---

## Convergence gradient

Measures the convergence round at each parameter value, producing
behavioural curves instead of binary pass/fail.

Tool: `python tools/scenario_boundary_search.py --seed 42 --gradient`

### Rounds axis (seed 42)

| Family | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 | R9 | R10 |
|---|---|---|---|---|---|---|---|---|---|---|
| incentive_misalignment | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 |
| info_asymmetry | X | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 |
| resource_scarcity | X | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 |

**Verified result:** once a base has enough budget to reach its first match,
adding rounds does not change that match round. This follows the preserved
execution prefix for a fixed seed and actor set.

### Actors axis (seed 42)

| Family | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| incentive_misalignment | R3 | R2 | R1 | R1 | R1 | R1 |
| info_asymmetry | R3 | R2 | R1 | R1 | R1 | R1 |
| resource_scarcity | X | X | R3 | R2 | R2 | R2 |

**Verified result:** convergence is non-worsening as actors increase for these
three seed-42 curves. Resource scarcity still converges at round 2, not round
1, with 5–6 actors.

**Uncertainty:** actor count changes the random stream. The biased-policy,
seed-11 sequence below succeeds at actors 3–5 and fails at 6, so this sampled
curve is not a monotonicity guarantee.

### Threshold axis (seed 42)

| Family | T=1 | T=2 | T=3 | T=4 | T=5 |
|---|---|---|---|---|---|
| incentive_misalignment | R1 | R2 | R1 | R4 | R3 |
| info_asymmetry | R1 | R2 | R2 | X | R4 |
| resource_scarcity | R1 | R1 | R1 | R3 | R2 |

**Verified result:** the threshold curves are non-monotonic. In particular,
information asymmetry fails at T=4 while succeeding at T=5.

**Inference:** the ordering reflects the exact offer sequence sampled by the
fixed seed, not an ordered notion of threshold difficulty.

**Uncertainty:** this run does not test whether averaging over a declared seed
distribution would remove, preserve, or transform the non-monotonicity.

---

## Two-axis stability frontier

Two-axis mapping probes the full grid for parameter pairs, producing
stability matrices that show the exact shape of the boundary surface
instead of projecting it onto single axes.

Tool: `python tools/scenario_frontier.py --policy uniform --seeds 1,42,123`

### Actors × rounds (seed 42)

`incentive_misalignment`:

| actors \ rounds | 1 | 2 | 3 | 4–10 |
|---|---|---|---|---|
| 1 | X | X | R3 | R3 |
| 2 | X | R2 | R2 | R2 |
| 3–6 | R1 | R1 | R1 | R1 |

`info_asymmetry` has the identical seed-42 matrix.

`resource_scarcity`:

| actors \ rounds | 1 | 2 | 3 | 4 | 5–7 | 8–10 |
|---|---|---|---|---|---|---|
| 1 | X | X | X | X | X | R8 |
| 2 | X | X | X | R4 | R4 | R4 |
| 3 | X | X | R3 | R3 | R3 | R3 |
| 4–6 | X | R2 | R2 | R2 | R2 | R2 |

### Threshold × rounds (seed 42)

`incentive_misalignment`:

| threshold \ rounds | 1 | 2 | 3 | 4 | 5–10 |
|---|---|---|---|---|---|
| 1 | R1 | R1 | R1 | R1 | R1 |
| 2 | X | R2 | R2 | R2 | R2 |
| 3 | R1 | R1 | R1 | R1 | R1 |
| 4 | X | X | X | R4 | R4 |
| 5 | X | X | R3 | R3 | R3 |

`info_asymmetry`:

| threshold \ rounds | 1 | 2 | 3 | 4 | 5 | 6–10 |
|---|---|---|---|---|---|---|
| 1 | R1 | R1 | R1 | R1 | R1 | R1 |
| 2 | X | R2 | R2 | R2 | R2 | R2 |
| 3 | X | R2 | R2 | R2 | R2 | R2 |
| 4 | X | X | X | X | X | R6 |
| 5 | X | X | X | R4 | R4 | R4 |

`resource_scarcity`:

| threshold \ rounds | 1 | 2 | 3–10 |
|---|---|---|---|
| 1 | R1 | R1 | R1 |
| 2 | R1 | R1 | R1 |
| 3 | R1 | R1 | R1 |
| 4 | X | X | R3 |
| 5 | X | R2 | R2 |

### Seed sensitivity summary

The table reports verified stable-cell counts, not probabilities.

| Family | Plane | Seed 1 | Seed 42 | Seed 123 |
|---|---|---:|---:|---:|
| incentive_misalignment | actors×rounds | 55/60 | 57/60 | 59/60 |
| info_asymmetry | actors×rounds | 55/60 | 57/60 | 59/60 |
| resource_scarcity | actors×rounds | 59/60 | 45/60 | 42/60 |
| incentive_misalignment | threshold×rounds | 48/50 | 44/50 | 43/50 |
| info_asymmetry | threshold×rounds | 46/50 | 40/50 | 39/50 |
| resource_scarcity | threshold×rounds | 49/50 | 47/50 | 45/50 |

### Result, inference, and uncertainty

**Verified result:** information asymmetry and incentive misalignment share the
same actors/rounds matrix under all three sampled uniform-policy seeds. This
follows from their representative bases having the same threshold and receiving
the same actor mutations on this plane; it does not make the families generally
equivalent.

**Verified result:** the `(actors=1, rounds=1)` cell fails for every family and
each of the three sampled seeds. Resource scarcity is not fully stable at seed
1; it records 59/60 stable cells.

**Verified result:** the seed-42 threshold/rounds matrices are non-monotonic.
For information asymmetry, threshold 4 first succeeds at round 6 while
threshold 5 first succeeds at round 4.

**Verified result:** at seed 1, `threshold=1` first succeeds at round 1 for
incentive misalignment, round 2 for information asymmetry, and round 1 for
resource scarcity. The previous unqualified statement that it requires five
rounds is not reproduced by the regenerated matrices.

**Inference:** actor count and round budget can compensate for one another in
parts of the sampled matrices, but “hyperbolic” and “seed-invariant” are
retracted as general descriptions. Resource-scarcity stable area changes from
59/60 to 42/60 across the declared seeds.

**Uncertainty:** these are two-dimensional slices. They do not establish the
full three-axis surface, monotonicity outside the sampled cells, or a
distribution over seeds.

---

## Policy comparative frontier

Compares two negotiation policies (uniform vs biased) by running
full two-axis frontier sweeps under identical seeds and measuring
how the stability geometry changes.

Tools and independent cross-check:

```bash
python tools/scenario_frontier.py --policy uniform --seeds 1,42,123
python tools/scenario_frontier.py --policy biased --seeds 1,42,123
python tools/scenario_frontier_compare.py \
  --policy-a uniform --policy-b biased --seeds 1,42,123
```

### Representative-base roles

The frontier executes one generated base per family, not all 60 generated
scenarios.

| Base | negotiator | hardliner | mediator |
|---|---|---|---|
| info_asymmetry_001 | 2 | 0 | 0 |
| resource_scarcity_021 | 4 | 0 | 0 |
| incentive_misalignment_041 | 2 | 1 | 0 |

The implemented biased policy changes offer ranges for hardliners to `[3,5]`
and mediators to `[2,4]`; negotiators remain `[1,5]`. The information-asymmetry
and resource-scarcity bases contain only negotiators and produce identical raw
matrices under both policies. All changed cells below are in
`incentive_misalignment_041`.

### Incentive misalignment: actors × rounds

| Seed | Uniform stable | Biased stable | Δ area | Avg round Δ |
|---|---|---|---|---|
| 1 | 55/60 | 56/60 | +1 | −0.17 |
| 42 | 57/60 | 56/60 | −1 | +0.17 |
| 123 | 59/60 | 59/60 | 0 | 0.00 |
| **mean area delta** | | | **0.0** | |

Only the actors=3 row shifts: seed 1 changes `rounds_min` from 2 to 1,
seed 42 changes it from 1 to 2, and seed 123 is unchanged.

### Incentive misalignment: threshold × rounds

| Seed | Uniform stable | Biased stable | Δ area | Avg round Δ |
|---|---|---|---|---|
| 1 | 48/50 | 48/50 | 0 | 0.00 |
| 42 | 44/50 | 44/50 | 0 | −0.10 |
| 123 | 43/50 | 43/50 | 0 | 0.00 |
| **mean area delta** | | | **0.0** | |

Equal area does not mean identical geometry. Seed 1 moves the T=1 boundary
from round 1 to 2 and T=3 from round 2 to 1. Seed 42 moves T=3 from 1 to 2,
T=4 from 4 to 5, and T=5 from 3 to 1. Seed 123 is unchanged.

### Result, inference, hypothesis, and uncertainty

**Verified result:** biased policy does not produce a consistent sampled-area
improvement. Its actors/rounds gains and losses cancel to a mean delta of zero;
threshold/rounds area is unchanged for all three seeds.

**Verified result:** changed cells can redistribute while total stable area is
constant. Stable-area delta alone is therefore insufficient to characterize
geometry.

**Inference:** the selective effect is consistent with the role-to-offer
mapping because only the representative base containing a hardliner changes.
This regeneration did not isolate role as a causal intervention.

**Hypothesis:** a threshold-aware policy could alter these trade-offs. No such
policy is implemented or tested here.

**Uncertainty:** three seeds and one incentive-misalignment base do not support
a general claim that biased policy improves or harms negotiation stability.

---

## Questions to investigate

- ~~What is the agreement rate per family under seed 42?~~ Answered by
  manifest-verified base telemetry: 20/20 information asymmetry, 16/20
  incentive misalignment, and 3/20 resource scarcity.
- Does adding a mediator role measurably change convergence speed?
- ~~At what `max_rounds` threshold does resource scarcity stop being
  failure-dominant?~~ For the current `resource_scarcity_021` base,
  seed 42 records `rounds_min=2`; sampled seeds reach 3.
- Do any scenarios produce the same negotiation history despite
  different initial configurations? (structural equivalence)
- ~~Does the mutation stability map change under different seeds?~~
  Answered: yes. No single sampled seed is worst on every family and
  axis; per-seed state maps must remain available with the consensus.
- ~~What is the full bifurcation frontier: the set of (actors, rounds,
  threshold) triples that separate agreement from failure?~~
  Partially answered: 2D slices (actors×rounds, threshold×rounds)
  are mapped. The full 3D surface is not computed.
- Can adversarial seed search find the single worst-case seed
  automatically?
- ~~Do boundary extrema survive verification?~~ Answered: all per-seed
  extrema for seeds 1, 42, and 123 matched fresh exhaustive state maps.
- ~~Does convergence accelerate with more rounds?~~ Answered: no.
  Convergence round is fixed once past the boundary. Extra rounds are
  unused.
- ~~Can adding actors remove a previous success?~~ Answered for the
  biased policy: seed 11 succeeds at actors 3–5 and fails at actor 6
  for `incentive_misalignment_041`.
- ~~**How does the stability frontier change under a different
  negotiation policy?**~~ Partially answered for uniform versus biased:
  mean stable-area delta is 0.0 on both sampled planes. Only the
  incentive-misalignment base changes, and some boundary rows shift despite
  unchanged area. More policies, bases, and seeds remain untested.
- Can a declared seed-sampling design support estimates rather than a list of
  selected deterministic cases?

## Methodology notes

- The complete provenance ledger, command sequence, executable-input hashes,
  artifact hashes, and old-to-new comparison are in
  [`docs/lab_regeneration_1775.md`](lab_regeneration_1775.md).
- The regenerated corpus uses generator seed 42 and exactly 60 scenarios.
- Each generation writes `scenarios/generated/generation_manifest.json`
  with a content-addressed run identifier, the exact current file set, and
  SHA-256 hashes. By default stale generator-owned files are reported and
  retained; `--clean` removes only immediate
  `<family>/<family>_<number>.json` paths outside the new manifest.
- Scenario files and the manifest are staged before publication. A reported
  staging, backup, write, or publish failure restores the prior generated set
  and manifest. CLI generation requires `--count` greater than zero.
- Telemetry is collected via `python tools/scenario_telemetry.py`.
- Telemetry auto-detects and verifies the generation manifest, selects only
  its declared files, executes isolated snapshots of the exact bytes whose
  hashes were verified, and records the generation run identifier. Use
  `--manifest FILE` to select an explicit generated run; directories without
  a manifest remain supported as legacy scans without generation provenance.
  Recursive legacy scans exclude only the root `generation_manifest.json`;
  nested valid scenarios with that filename remain inputs.
- Mutation sweeps use `python tools/scenario_mutator.py` in a fresh output
  directory. The mutator does not publish a manifest or remove old files, so
  its exact 62-file corpus is checked by a deterministic tree hash before
  telemetry.
- Base and mutation telemetry outputs are preserved outside Git by hash; the
  default output names are `telemetry.json` and `index.json`.
- Boundary search uses binary search only for rounds and exhaustive
  enumeration for actors and threshold.
- Boundary verification via `--verify` re-enumerates each complete axis.
- Convergence gradient via `--gradient` flag (measures convergence
  round at each parameter value).
- Boundary results go to `scenarios/boundaries.json`.
- Two-axis frontier mapping via `python tools/scenario_frontier.py`.
- Frontier results go to `scenarios/frontiers/` (gitignored).
- Policy comparative frontier via
  `python tools/scenario_frontier_compare.py`.
- Comparison results go to `scenarios/frontiers/comparisons/`
  (gitignored).
- Uniform and biased raw frontier matrices are generated and preserved
  separately because frontier filenames do not contain the policy and are
  overwritten by the next policy run.
- A separate post-check found zero `status=error` probe cells in both raw
  policy sets. Reapplying `compare_frontiers()` to those raw sets reproduced
  all six comparison JSON objects exactly.
- Generated, mutation, boundary, frontier, and comparison files are
  gitignored — regenerate locally.
