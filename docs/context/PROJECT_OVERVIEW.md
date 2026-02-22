# PROJECT OVERVIEW - HUB_Optimus

## Elevator pitch
HUB_Optimus is an integrity-first evaluation framework for diplomatic and institutional scenarios.
It helps teams compare declared agreements against verifiable structure (incentives, sequencing, and monitoring).
Primary users are policy analysts, mediation teams, and technical maintainers building repeatable scenario reviews.

## MVP scope (current)
- Evaluate scenario markdown files with a deterministic CLI (`python -m hub_optimus evaluate ...`).
- Produce machine-readable JSON and human-readable markdown reports.
- Maintain multilingual onboarding/governance docs with link-check and CI guardrails.

## No-go zones (do not expand into)
- No prediction engine or probabilistic forecasting claims.
- No coercive enforcement, sanctions tooling, or authority automation.
- No personal blame frameworks; analysis stays structural.
- No rewriting legacy (`legacy/`) to retrofit v1 narratives.

## Architecture (high level)
- Kernel logic (`hub_optimus/`): parsing, schema checks, trust-layer classification.
- Scenario runner (`run_scenario.py`, `hub_optimus_simulator.py`): JSON scenario simulation loop.
- Documentation (`docs/`, `v1_core/`): onboarding, governance, scenario templates, examples.
- Automation (`.github/workflows/`, `tools/`): CI tests, link checks, maintenance scripts.

## Key folders
- `hub_optimus/`: evaluator package and CLI entrypoints.
- `v1_core/`: active kernel language specs and scenario workflow.
- `docs/`: onboarding and governance mirrors by language.
- `tests/`: smoke and behavior tests for CLI/evaluation logic.
- `tools/`: repository maintenance and policy guard scripts.

## Runtime model
- Local:
  - `python -m hub_optimus evaluate v1_core/workflow/scenario_001_partial_ceasefire.md`
  - `python run_scenario.py --scenario example_scenario.json --seed 42`
- CI:
  - `pytest` for test gates
  - Lychee link check for markdown integrity
  - Workflow guards for sensitive/kernel-adjacent path changes

## Source-of-truth policy
- When docs disagree, `docs/context/STATUS.md` wins.
- For v1 core specs: Spanish (`v1_core/languages/es/`) is canonical.
- English (`v1_core/languages/en/`) is a parity reference and must stay synchronized.
