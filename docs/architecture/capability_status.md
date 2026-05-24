# Capability Status

This table separates implemented repository capabilities from planned or explicitly out-of-scope work. It is a descriptive audit aid for issue #1589, not a roadmap or implementation plan.

| Capability | Status | Source | Notes |
| --- | --- | --- | --- |
| Scenario schema validation | Implemented | `docs/architecture/runtime_contract.md`; `scenario.schema.json`; `tests/test_run_scenario_cli.py` | The CLI validates scenario JSON against the schema before runtime execution. |
| Deterministic simulator runtime | Implemented | `docs/architecture/runtime_contract.md`; `hub_optimus_simulator.py`; `run_scenario.py`; `tests/test_run_scenario_cli.py` | Seeded runs produce deterministic JSON output for the current prototype behavior. |
| Benchmark byte-level comparison | Implemented | `benchmarks/run_benchmarks.py`; `benchmarks/expected/`; `docs/architecture/runtime_contract.md` | The runner compares benchmark output byte-for-byte and exits non-zero on mismatch. The CI benchmark job is currently non-blocking. |
| Structural drift diagnostics | Implemented | `benchmarks/run_benchmarks.py` | The benchmark runner compares outcome/status, rounds, and actor count and classifies differences by severity. |
| Blocking benchmark CI gate | Not implemented | `.github/workflows/ci.yml` | The benchmark job runs in CI but uses `continue-on-error: true`. |
| CI summary / visibility | Implemented | `.github/workflows/ci.yml`; `docs/architecture/runtime_contract.md` | CI writes narrative consistency and benchmark summaries to `GITHUB_STEP_SUMMARY`. |
| Multilingual documentation | Implemented | `README.md`; `docs/context/STATUS.md` | Documentation structure exists across priority, progressive, and stub languages; `v1_core/languages/es/` remains canonical for v1. |
| Narrative-risk claim triage | Implemented | `tools/check_narrative_consistency.py`; `tests/test_narrative_consistency.py`; `tests/test_geopolitical_claim_packs.py`; `.github/workflows/ci.yml` | Implemented as deterministic dataset/schema consistency checks, not truth adjudication or LLM-as-judge. |
| Post-quantum control plane | Planned / RFC | `docs/rfc/post_quantum_control_plane.md` | RFC-only planned control layer around artifacts; not simulator runtime behavior. |
| ML-KEM sealed exchange | Not implemented | `docs/rfc/post_quantum_control_plane.md` | Allowed as a future standardized primitive reference only. |
| ML-DSA artifact signing | Not implemented | `docs/rfc/post_quantum_control_plane.md` | Allowed as a future standardized primitive reference only. |
| SLH-DSA long-lived signature option | Not implemented | `docs/rfc/post_quantum_control_plane.md` | Allowed as a future standardized primitive reference only. |
| Custom cryptographic algorithms | Explicitly out of scope | `docs/rfc/post_quantum_control_plane.md` | The RFC prohibits custom cryptographic primitives. |
