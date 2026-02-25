# WORKFLOWS - CI and Automation

This document reflects the workflows currently present in `.github/workflows`.
Source of truth is the workflow YAML in the repository.

## ci.yml
- Trigger:
  - `pull_request`
  - `push` on `main`
- What it checks:
  - Installs dev dependencies from `requirements-dev.txt`
  - Runs mojibake guard: `python tools/check_mojibake.py`
  - Runs test suite: `python -m pytest -q`
- How to run locally:
  1. `python -m pip install --upgrade pip`
  2. `python -m pip install -r requirements-dev.txt`
  3. `python tools/check_mojibake.py`
  4. `python -m pytest -q`

## link-check.yml
- Trigger:
  - `push`
  - `pull_request`
  - `workflow_dispatch`
- What it checks:
  - Repository/debug listing for link targets
  - Markdown links via `lycheeverse/lychee-action@v1` with:
    - `README.md`
    - `CONTRIBUTING.md`
    - `docs/CONTRIBUTING.md`
    - `docs/**/*.md`
- How to run locally:
  1. `lychee --no-progress --verbose README.md CONTRIBUTING.md docs/CONTRIBUTING.md docs/**/*.md`

## repo_maintenance_bot.yml
- Trigger:
  - `workflow_dispatch` with inputs:
    - `mode`: `hygiene`, `i18n`, `full`
    - `allow_kernel_changes`: `false`, `true`
  - `schedule`: `15 6 * * *`
  - `pull_request` (paths):
    - `docs/**`
    - `v1_core/**`
    - `.github/workflows/**`
    - `tools/**`
- What it checks/does:
  - Skips cleanly when `GH_APP_ID` or `GH_APP_PRIVATE_KEY` are missing
  - Creates GitHub App token
  - Creates maintenance branch and runs:
    - `python tools/maintenance_bot.py <mode>`
    - `python tools/kernel_guard.py <allow_kernel_changes>`
  - Commits/pushes changes and opens PR
  - Runs `python tools/pr_pro.py`
- How to run locally:
  1. `python tools/maintenance_bot.py full`
  2. `python tools/kernel_guard.py --help`
  3. `python tools/kernel_guard.py`
- Notes:
  - Full automation path requires GitHub App secrets and `gh` auth.

## kernel-guard.yml
- Trigger:
  - `pull_request` events:
    - `opened`
    - `synchronize`
    - `reopened`
    - `labeled`
    - `unlabeled`
- What it checks:
  - Reads override label `allow-kernel-change`
  - Runs diff-based kernel guard against base/head refs:
    - without override: `python tools/kernel_guard.py --base-ref origin/<base> --head-ref <sha>`
    - with override label: adds `--allow-kernel-changes`
- How to run locally:
  1. `git fetch --no-tags --prune --depth=1 origin main`
  2. `python tools/kernel_guard.py --base-ref origin/main --head-ref HEAD`
  3. Optional override: `python tools/kernel_guard.py --base-ref origin/main --head-ref HEAD --allow-kernel-changes`

## Change rule
Any change under `.github/workflows` must update this file in the same PR.
