# STATUS

## Canonical languages policy (v1)

`v1_core/` (normative spec):
- Canonical (source of truth): `es`
- Parity reference: `en`

`docs/` (onboarding and navigation):
- Priority languages: `es`, `de`, `en`
- Progressive languages: `ca`, `fr`, `ru`
- Partial/planned: `he`, `zh`

Rule: when repository docs disagree, this file wins.

## Batch update - 2026-02-22

- [x] Align language source-of-truth repo-wide (`STATUS` policy applied in README/docs/copilot instructions)
- [x] Close #49: update `.github/copilot-instructions.md` to match STATUS and repo rules
- [x] Create `docs/context/PROJECT_OVERVIEW.md` (MVP + no-go zones)
- [x] Create `docs/context/GLOSSARY.md` (15+ terms)
- [x] Fix ES docs duplication: `docs/es/03_try_a_scenario.md` is now a real guided scenario page
- [x] Update kernel guard with protected prefixes: added `tools/kernel_guard.py` and CI PR check
- [x] Harden `.github/workflows/repo_maintenance_bot.yml` for missing secrets (clean skip path)
- [x] Link-check green and local run documented in `docs/context/WORKFLOWS.md`
- [x] Scenario validation schema + fail-fast added to `run_scenario.py`
- [x] Minimal smoke test for `example_scenario.json` added (`tests/test_run_scenario_cli.py`)

## Verification snapshot

- Tests: `python -m pytest -q` -> 13 passed
- Link-check: `lychee --config .github/lychee.toml README.md CONTRIBUTING.md docs/**/*.md v1_core/**/*.md` -> 0 errors
