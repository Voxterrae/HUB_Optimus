# Runtime Contract — HUB_Optimus Architecture

This document describes the technical architecture of the HUB_Optimus simulation runtime: how scenarios flow through the system, what guarantees exist, and how each layer protects correctness.

---

## System layers

```text
┌─────────────────────────────────────────────┐
│  scenario.json          (user input)        │
└────────────────┬────────────────────────────┘
                 │ validates against
┌────────────────▼────────────────────────────┐
│  scenario.schema.json   (contract)          │
│  JSON Schema Draft 2020-12, strict          │
└────────────────┬────────────────────────────┘
                 │ accepted by
┌────────────────▼────────────────────────────┐
│  run_scenario.py        (CLI runner)        │
│  fail-fast validation, deterministic output │
└────────────────┬────────────────────────────┘
                 │ delegates to
┌────────────────▼────────────────────────────┐
│  hub_optimus_simulator  (kernel)            │
│  Scenario → Actor → Simulator → result      │
└────────────────┬────────────────────────────┘
                 │ produces
┌────────────────▼────────────────────────────┐
│  .result.json           (deterministic out) │
│  UTF-8, sorted keys, 2-space indent, LF    │
└─────────────────────────────────────────────┘
```

---

## Schema contract

File: `scenario.schema.json`

- **Draft:** 2020-12
- **`additionalProperties: false`** at root and role level — no extra fields accepted
- **Pattern constraints:** `".*\\S.*"` on `title`, `description`, and role `name`/`role` fields (rejects whitespace-only strings)
- **Minimums:** `minLength: 1` on strings, `minItems: 1` on roles, `minimum: 1` on `max_rounds`
- **Required fields:** `title`, `description`, `roles`, `success_criteria`, `max_rounds`

The schema is the single source of input truth. No validation logic lives outside it.

---

## CLI runner

File: `run_scenario.py`

### Input handling
- Reads scenario JSON → validates against schema → rejects with `[schema-error]` prefix
- File/path errors → rejects with `[input-error]` prefix
- All rejections use **exit code 2** (constant `INPUT_ERROR_EXIT_CODE`)
- Write failures (permissions, bad path, disk full) → caught as `OSError`, reported cleanly

### Output guarantees
- Format: `json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"`
- Encoding: UTF-8
- Line endings: LF (enforced by `.gitattributes` in expected files)
- Deterministic: same `--seed` value produces byte-identical output

---

## Simulation kernel

File: `hub_optimus_simulator.py`

### Components
- **`Scenario`** — data container loaded from validated JSON
- **`Actor`** — wraps a role with a policy function; default policy: `{"offer": random.randint(1, 5)}`
- **`Simulator`** — executes rounds, passes per-round `Random` instance to each actor, checks `success_criteria`

### Determinism
- `Simulator.run(seed=N)` creates `random.Random(seed)` — isolated from global state
- Each actor receives the same `Random` instance per round
- The number of actors directly affects the RNG sequence (adding/removing an actor changes all subsequent random values)

### Success condition
- `check_success()` returns `True` if **any** actor's action dict contains a key-value pair matching **any** entry in `success_criteria`
- Result dict: `{"status": "success"|"failure", "rounds": int, "history": [...], "detail": str}`

---

## Test layers

### Unit/integration tests (pytest)

| File | Coverage |
|---|---|
| `tests/test_smoke.py` | Basic happy path |
| `tests/test_run_scenario_cli.py` | CLI contract: happy path, determinism, error modes, schema guard |
| `tests/test_regression_runner.py` | Whitespace rejection, additional properties, write errors, output format |
| `tests/test_check_mojibake.py` | Mojibake detection: clean files, known patterns, directory recursion |

### Benchmarks

| Scenario | Design | Expected outcome |
|---|---|---|
| `ceasefire_basic` | 2 negotiators, offer:5, 5 rounds | Success (round 2) |
| `ceasefire_fragile` | 2 negotiators + mediator, offer:5, 3 rounds | Success (round 2) |
| `ceasefire_failure` | 2 hardliners, offer:99 (unreachable), 3 rounds | Failure (3/3) |

All benchmarks use **seed 42** and compare byte-for-byte against frozen expected outputs in `benchmarks/expected/`.

---

## CI pipeline

| Job | Purpose | Blocking? |
|---|---|---|
| **pytest** | Run all tests + mojibake guard | Yes |
| **Benchmarks** | Run benchmark pack, publish summary | No (`continue-on-error: true`) |
| **Kernel Guard** | Protect kernel file integrity | Yes |
| **Link Check** | Validate documentation links (Lychee) | Yes |

---

## Governance layer

- **CODEOWNERS** gates kernel, governance, CI, and simulator files behind `@Voxterrae` review
- **Issue forms** enforce structured intake (bug, docs, scenario, RFC)
- **PR template** requires scope check, kernel coherence, and quality checklist
- **Blank issues disabled** — all contributions flow through forms

---

## Encoding contract

- All markdown files: UTF-8, no BOM
- Mojibake guard (`tools/check_mojibake.py`) scans `docs/` and `v1_core/` for:
  - U+FFFD replacement characters
  - Double-encoded UTF-8 patterns (latin capital letter sequences typical of CP-1252 misinterpretation)
  - Smart punctuation mojibake (curly quote and dash sequences from double encoding)
  - Double-encoded Cyrillic
- Line endings: LF everywhere (`.gitattributes`)
