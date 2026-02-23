# PROJECT OVERVIEW - HUB_Optimus

## What it is
HUB_Optimus is an integrity-first evaluation framework for diplomatic and institutional scenarios.
It compares declared commitments against verifiable structure: incentives, sequencing, and monitoring.

## Who it is for
- Policy analysts
- Mediation and negotiation teams
- Repository maintainers building reproducible scenario reviews

## MVP definition (current release target)
- Evaluate scenario markdown with deterministic CLI commands.
- Produce machine-readable JSON and human-readable markdown outputs.
- Keep docs and governance navigable with automated link and test checks.
- Block unsafe edits in protected kernel/governance paths unless explicitly authorized.

## Out of scope (no-go zones)
- Prediction engines or probabilistic forecasting claims.
- Automated coercive enforcement or sanctions logic.
- Personal blame scoring; analysis remains structural and evidence-driven.
- Legacy rewrites to force-fit old content into v1.

## Architecture at a glance
- `hub_optimus/`: evaluator package and CLI behavior.
- `run_scenario.py` and `hub_optimus_simulator.py`: scenario execution loop.
- `v1_core/`: active kernel language specs and workflow scenarios.
- `docs/`: onboarding and governance documentation.
- `.github/workflows/` and `tools/`: CI checks and maintenance automation.

## Success metrics (MVP)
- `pytest` passes on every `pull_request` and `push` to `main`.
- Link-check reports zero broken links on docs touched by PRs.
- Invalid scenario input fails fast with stable exit code and clear error message.
- Example scenario smoke test runs in CI without network dependencies.
- Source-of-truth policy remains consistent in onboarding and contribution docs.

## Operating constraints
- Source-of-truth for policy conflicts is `docs/context/STATUS.md`.
- For `v1_core/languages/`, Spanish (`es`) is canonical and English (`en`) is parity reference.
- Changes should ship as small PRs with one objective each.
