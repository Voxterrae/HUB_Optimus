# Laboratory Evidence Regeneration — Issue #1775

This ledger records the complete regeneration requested by GitHub issue
[#1775](https://github.com/Voxterrae/HUB_Optimus/issues/1775). It binds the
ignored raw laboratory outputs to an exact repository state without committing
the bulk artifacts.

The observations are synthetic executions of the prototype simulator. They are
not external-world evidence, forecasts, policy recommendations, or proof of
causality.

## Epistemic labels

- **Verified result:** read directly from a hashed output produced by the
  commands below.
- **Inference:** a bounded interpretation of one or more verified results.
- **Hypothesis:** a proposed explanation that this regeneration did not test.
- **Uncertainty:** a known limit on what the sampled results establish.

## Source and execution environment

| Item | Recorded value |
|---|---|
| GitHub issue | `#1775` |
| Base commit | `af89e420efb7b60eb95867b840ebeaf23dd989b6` |
| Included prerequisite corrections | `#1770`, `#1774`, `#1779` |
| Python | `3.12.13` |
| `jsonschema` | `4.26.0` |
| Generator seed/count | `42` / `60` |
| Generation run ID | `sha256:cab1baacc6cd3494487a59dd3f75ca9584dc872e8b3b3ec65dbd822f9bf0de92` |
| Base policy | simulator default (`uniform`) |
| Frontier comparison | `uniform` versus `biased` |

The commit identifies the version of every tracked input. The additional tool
hashes below make the executable inputs independently checkable.

| Executable input | SHA-256 |
|---|---|
| `tools/scenario_generator/generate_scenarios.py` | `e2e0a6920b4a118c1d4ecf7b33c9da6e66a9b71421a81e071ba68caf6941a5e4` |
| `tools/scenario_telemetry.py` | `7cea59644f345204cee10d9993ffba6b35a22fda2e5ade125063278977488fdb` |
| `tools/scenario_mutator.py` | `13725cb0f4ee04ecbc00365210d22c52384e5bfce680465394cfc2186ee9cf91` |
| `tools/scenario_boundary_search.py` | `7994cdd84ea44c6968a8e9de685ce1062fd2b7c94cec96e33e543b9c0fd7acfd` |
| `tools/scenario_frontier.py` | `17426087f530de64dab1e4b1ef279b61b2bfbee0b452e0b562f7be1f49e2e3eb` |
| `tools/scenario_frontier_compare.py` | `19b274a3cb613b95f0e1bf2e9d464b9ddb9ca2db00ad01e89082caf430013592` |
| `run_scenario.py` | `9beb5a41a6850bebe2b7a9df78498047d55309af429ab53a54112368cefdbea2` |
| `hub_optimus_simulator.py` | `df00f950f12c08a76a6f54769818313712a9ef292b6f463485a96ca5fa0553bb` |
| `scenario.schema.json` | `983aa24429c302cff706d26c95c77306e5b44c0b91f9736c9251543a4259bde6` |

## Commands

Run from the repository root at the recorded base commit. The execution used a
new worktree whose ignored generated and mutation directories contained no
prior JSON. `LAB1775_OUT` is a local, untracked evidence directory; changing
that path does not change the JSON bytes.

```bash
export LAB1775_OUT=/tmp/huboptimus-issue1775-evidence-af89e420
mkdir -p "$LAB1775_OUT"

python tools/scenario_generator/generate_scenarios.py \
  --count 60 --seed 42 --clean

python tools/scenario_telemetry.py \
  --scenario-dir scenarios/generated \
  --manifest scenarios/generated/generation_manifest.json \
  --output-dir "$LAB1775_OUT/base_telemetry" \
  --seed 42

test -z "$(
  find scenarios/mutations -type f ! -name '.gitignore' -print -quit
)"
python tools/scenario_mutator.py
python tools/scenario_telemetry.py \
  --scenario-dir scenarios/mutations \
  --output-dir "$LAB1775_OUT/mutation_telemetry" \
  --seed 42

python tools/scenario_boundary_search.py --seeds 42,99,7,123,256
cp scenarios/boundaries.json \
  "$LAB1775_OUT/boundaries_multi_42_99_7_123_256.json"

python tools/scenario_boundary_search.py --seeds 1,42,123 --verify
cp scenarios/boundaries.json \
  "$LAB1775_OUT/boundaries_verified_1_42_123.json"

python tools/scenario_boundary_search.py --seed 42 --gradient
cp scenarios/boundaries.json \
  "$LAB1775_OUT/boundaries_gradient_seed_42.json"

python tools/scenario_boundary_search.py --seed 2
cp scenarios/boundaries.json "$LAB1775_OUT/boundaries_seed_2.json"

python tools/scenario_boundary_search.py --seed 11 --policy biased
cp scenarios/boundaries.json \
  "$LAB1775_OUT/boundaries_seed_11_biased.json"

python tools/scenario_frontier.py --policy uniform --seeds 1,42,123
mkdir -p "$LAB1775_OUT/frontiers_uniform"
cp scenarios/frontiers/actors_rounds_seed_*.json \
  scenarios/frontiers/threshold_rounds_seed_*.json \
  "$LAB1775_OUT/frontiers_uniform/"

python tools/scenario_frontier.py --policy biased --seeds 1,42,123
mkdir -p "$LAB1775_OUT/frontiers_biased"
cp scenarios/frontiers/actors_rounds_seed_*.json \
  scenarios/frontiers/threshold_rounds_seed_*.json \
  "$LAB1775_OUT/frontiers_biased/"

python tools/scenario_frontier_compare.py \
  --policy-a uniform --policy-b biased --seeds 1,42,123
mkdir -p "$LAB1775_OUT/comparisons"
cp scenarios/frontiers/comparisons/*.json \
  "$LAB1775_OUT/comparisons/"
```

`scenario_mutator.py` creates inputs but does not execute them. The second
telemetry command is therefore the execution step for the 62-mutation sweep.
It also does not clean its output. The empty-directory precondition prevents a
retained file from entering the deliberately legacy/unmanifested scan; the
exact corpus hash is recorded below.

## Artifact hashes

SHA-256 is calculated over the exact file bytes. The generated manifest already
contains the relative path and SHA-256 of all 60 generated scenarios, so its
hash plus its content-addressed run ID binds the complete base corpus.

| Artifact | SHA-256 |
|---|---|
| `scenarios/generated/generation_manifest.json` | `ea38278890342747012101a5b43bff5a76b6179e75174b83e94acee31816bc6b` |
| base `index.json` | `45e4c2410f5aaedb1ece9e319e48e5320e58b6649035f9b8c7954becbb188fa9` |
| base `telemetry.json` | `8cf13232ba0ce5cb0f3a166ef0e2b26ff7c89d163caa8576a516bdd8b6f9e5a5` |
| mutation corpus tree | `2860bae222764811c92f6399610b4f61243a23edc28f321a2cf8086ba738d5ca` |
| mutation `index.json` | `25703233a983cf98d5b6af169ab621ffae7cbb2b8d457315b28abbdd9bea2ba9` |
| mutation `telemetry.json` | `36ee3e9325016f8806552620a0b79ceb938d1dc41fab404c020ff945a1ca7042` |
| boundaries, seeds `42,99,7,123,256` | `e6aec87a6aef206b303deb11c6551ef27f7dbaffdbab5cca6e9c05e971538edc` |
| boundaries + verification, seeds `1,42,123` | `ce2a21bc31e8647050b42e5b60a3a37a54e29dea0467fa9c872fec09862cb3af` |
| boundaries + gradient, seed `42` | `ca0f85988b54e835493198607e0c1a17fe3ca858fbae38743d0b0838a51dd0d9` |
| boundaries, seed `2`, default policy | `414150ff65d5de27849d47adbcb15b903680cce8c1cbf9861239a11db8185a1a` |
| boundaries, seed `11`, biased policy | `b06faf1614b6433ea156bde30271db0bd83ea2141e1733fd45a173b1cb0af3f4` |
| uniform `actors_rounds_seed_1.json` | `e02a16fc603d70c524e98c66b8eeeeb1d756adf03f8561ccc235b61d3d6a1199` |
| uniform `actors_rounds_seed_42.json` | `d94134dbdef8b8ba7941539c7cf254144dd88b14f524701ea812f4b7bf3d6dc2` |
| uniform `actors_rounds_seed_123.json` | `87fff707484840d6398ca38f31bc88f586430300326bc1aaa26978be7ad59404` |
| uniform `threshold_rounds_seed_1.json` | `7ec14d4afec24625bb841c0eb430f0780963f9c69c7a5a117a31a4e5d124496c` |
| uniform `threshold_rounds_seed_42.json` | `72330d2b3e8ce71964f4b0128d116e539cd0d630e09eccf087a5fb7526975ce8` |
| uniform `threshold_rounds_seed_123.json` | `410a3160b5a2fd2e64a4a703f4545d76d04ca7acfb2b8dfaa0a6c84c1bbbc005` |
| biased `actors_rounds_seed_1.json` | `9fe0408c91fa486e2644a14e8a8e1c1fada21c86c1b691c4e476c35bf22f4efe` |
| biased `actors_rounds_seed_42.json` | `6740e45003aa452b0bd9c69ada126bcc3888dcc86b052b81c3b69a5ad855390e` |
| biased `actors_rounds_seed_123.json` | `87fff707484840d6398ca38f31bc88f586430300326bc1aaa26978be7ad59404` |
| biased `threshold_rounds_seed_1.json` | `165d3a220beb6c03874b59bee78ff1f803fd914dcb9d0fd5f472b7c3f9bc4c0d` |
| biased `threshold_rounds_seed_42.json` | `8e6e1c45e823ee01b6c1878c333b153bbc8ed9dacecf82bd80e7b015bde0858e` |
| biased `threshold_rounds_seed_123.json` | `410a3160b5a2fd2e64a4a703f4545d76d04ca7acfb2b8dfaa0a6c84c1bbbc005` |
| comparison, actors/rounds, seed `1` | `d2be106649a62dd898dfe28c46dcaf6513c2bfa3b58afb9ba12ec4835a76d942` |
| comparison, actors/rounds, seed `42` | `954ca0e80d88f7d39c06551d673b555c3e5ebb93c5080b84bb0b08b8615946d8` |
| comparison, actors/rounds, seed `123` | `b2fc8c46dcaf7a5689aa4885fbf407448b21549e46126e3d3e99e0e6ae5aa901` |
| comparison, threshold/rounds, seed `1` | `5ae8ea3cc3dc2b99b0db6b2329a7ff555d97548f1121fca5ce7408ee92ca85b9` |
| comparison, threshold/rounds, seed `42` | `ed408c3ba7128fa519ef938f5f79b36c9beddffd0cade7b4dc8ec7a7524c687b` |
| comparison, threshold/rounds, seed `123` | `049254e19c47a12d7399851cd2d015476b401b3285d7b8ec5ab2b6adb0e124cf` |

The mutation corpus tree hash is reproducible with relative paths:

```bash
(
  cd scenarios/mutations
  find . -type f -name '*.json' -print0 \
    | sort -z \
    | xargs -0 sha256sum \
    | sha256sum
)
```

## Old-to-new result ledger

All “previous” values below are statements previously published in
`docs/lab_state.md`. The pre-isolation raw outputs did not have a complete
commit/tool/artifact ledger, so they cannot be reconstructed or certified
1:1. “Regenerated” values are verified results from the hashed artifacts
above.

| Observation | Previous | Regenerated |
|---|---:|---:|
| Base agreements | 55/60 | 39/60 |
| Base no-agreements | 5/60 | 21/60 |
| Average convergence round among agreements | 1.8 | 2.26 |
| Information-asymmetry agreements | 20/20 | 20/20 |
| Incentive-misalignment agreements | 19/20 | 16/20 |
| Resource-scarcity agreements | 16/20 | 3/20 |
| Actor mutations | 15/17 | 15/17 |
| Round mutations | 27/30 | 28/30 |
| Threshold mutations | 15/15 | 14/15 |
| Total mutations | 57/62 | 57/62 |
| Seed-1 `threshold=1` first-success round | 5 rounds (published without a family qualifier) | incentive: 1; information: 2; resource: 1 |
| Policy comparison, actors/rounds mean area delta | +5.7 cells | 0.0 cells |
| Policy comparison, threshold/rounds mean area delta | +2.0 cells | 0.0 cells |

### Retracted interpretations

The regenerated evidence does not support these former statements:

- base resource-scarcity no-agreements occur only at `max_rounds=1`;
- one actor is structurally broken across the representative bases;
- threshold mutation alone never produces a sampled no-agreement;
- seed 1 makes `threshold=1` require five rounds;
- more actors monotonically improve convergence as a general rule;
- the actors/rounds frontier is seed-invariant or adequately described as
  universally hyperbolic;
- the biased policy expands sampled stability area on average.

The replacement results and bounded interpretations are in
[`docs/lab_state.md`](lab_state.md).

## Error and verification checks

**Verified result:** all 27 per-seed boundary extrema in the
`1,42,123 --verify` run passed fresh exhaustive verification.

**Verified result:** telemetry reported zero parse, schema, and runtime errors
for both the 60-scenario base set and the 62-mutation set.

**Verified result:** an independent replay into new generated, telemetry, and
mutation directories reproduced the generation-manifest hash, both base
telemetry hashes, the mutation-corpus tree hash, and both mutation-telemetry
hashes byte for byte.

**Verified result:** an independent scan of the 12 separately preserved
uniform and biased raw frontier matrices found zero cells with
`"status": "error"`. Consequently, this execution contains no frontier probe
error that could be counted as an unstable cell.

**Verified result:** `compare_frontiers()` was reapplied to each matching pair
of preserved uniform and biased raw matrices. All six recomputed dictionaries
equal the six hashed comparison JSON objects exactly.

This second check is required because the comparison artifacts contain metrics,
not the underlying cell statuses. Scanning comparison JSON for `"error"` would
not certify its internal probes.

The check used the repository's comparison function against the preserved raw
matrices:

```bash
PYTHONPATH=tools python - "$LAB1775_OUT" <<'PY'
import json
import sys
from pathlib import Path

from scenario_frontier_compare import compare_frontiers

root = Path(sys.argv[1])
errors = []
for policy in ("uniform", "biased"):
    for path in sorted((root / f"frontiers_{policy}").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for family, entry in data["families"].items():
            for row, cells in entry["matrix"].items():
                for column, cell in cells.items():
                    if cell["status"] == "error":
                        errors.append((policy, path.name, family, row, column))
assert not errors, errors

for plane in ("actors_rounds", "threshold_rounds"):
    for seed in (1, 42, 123):
        uniform = json.loads(
            (root / "frontiers_uniform" / f"{plane}_seed_{seed}.json")
            .read_text(encoding="utf-8")
        )
        biased = json.loads(
            (root / "frontiers_biased" / f"{plane}_seed_{seed}.json")
            .read_text(encoding="utf-8")
        )
        recorded = json.loads(
            (root / "comparisons"
             / f"uniform_vs_biased_{plane}_seed_{seed}.json")
            .read_text(encoding="utf-8")
        )
        assert compare_frontiers(
            uniform, biased, "uniform", "biased"
        ) == recorded
PY
```

## Inference and remaining uncertainty

**Inference:** the isolated run-local random stream materially changes the
sampled laboratory results, while the generator corpus itself remains bound to
the same seed-42 manifest. That explains why evidence regeneration was
necessary; it does not by itself establish that one stream is more realistic.

**Uncertainty:** frontier JSON files do not embed the repository commit,
generation manifest, or policy name, and policy runs overwrite the same
filenames. This versioned ledger supplies the binding through separate copies,
the exact command sequence, and artifact hashes. Outputs from a different
command sequence must not be compared under these hashes.

**Uncertainty:** base telemetry covers the canonical 60 generated scenarios.
Mutation, boundary, gradient, and frontier sweeps cover three generated
representative scenarios, a small declared seed set, two toy policies, and
exact-equality success. They do not establish population statistics, external
validity, causal effects, or predictive performance.

**Hypothesis:** wider seed sampling may change stable-area and policy-delta
summaries. This regeneration did not test a seed distribution and makes no
claim about expected behavior over seeds.
