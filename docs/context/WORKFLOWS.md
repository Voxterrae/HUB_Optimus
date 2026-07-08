# WORKFLOWS - CI and automation

This document tracks the automation surface currently present under
`.github/workflows`. The workflow YAML files are the source of truth for
exact behavior.

## Local validation baseline

Run these checks before opening or merging code changes:

```powershell
python tools/check_mojibake.py v1_core docs README.md CONTRIBUTING.md
python -m pytest -q
```

For scenario runtime changes, also run:

```powershell
python run_scenario.py example_scenario.json --seed 42
python benchmarks/run_benchmarks.py --summary-file out/benchmark_summary.md
```

For merge, deploy, or automation decisions, refresh traceability:

```powershell
powershell -ExecutionPolicy Bypass -File tools/trace_repo.ps1
```

## Workflow inventory

### ci.yml

- Triggers:
  - `pull_request`
  - `push` to `main`
- Permissions: `contents: read`
- Jobs:
  - `pytest`: installs `requirements-dev.txt`, runs the mojibake guard, runs narrative consistency, then `python -m pytest -q`.
  - `benchmarks`: non-blocking benchmark pack with `continue-on-error: true`.
- Writes to repo: no.

### link-check.yml

- Triggers:
  - `push`
  - `pull_request`
  - `workflow_dispatch`
- Permissions: `contents: read`
- Job:
  - Runs Lychee against `README.md`, `CONTRIBUTING.md`, `docs/CONTRIBUTING.md`, and `docs/**/*.md`.
- Writes to repo: no.

### kernel-guard.yml

- Triggers:
  - `pull_request` events: opened, synchronize, reopened, labeled, unlabeled.
- Permissions: `contents: read`
- Job:
  - Runs `tools/kernel_guard.py` against the pull request diff.
  - Allows explicit override only when the PR has the `allow-kernel-change` label.
- Writes to repo: no.

### pr-safety-check.yml

- Triggers:
  - `pull_request` events: opened, synchronize, reopened, edited.
- Permissions: `contents: read`
- Job:
  - Classifies PR path risk as LOW, MEDIUM, or HIGH.
  - High-risk paths include runtime, schema, workflows, CODEOWNERS, `v1_core/languages/`, and governance docs.
- Writes to repo: no.

### pr-quarantine.yml

- Triggers:
  - `pull_request_target` events: opened, synchronize, reopened.
- Permissions:
  - `contents: read`
  - `issues: write`
  - `pull-requests: write`
- Job:
  - For first-time external fork PRs, adds `needs-maintainer-review` and comments on the PR.
  - Does not checkout or execute PR code.
- Writes to repo: no; writes labels/comments on PRs.

### repo_maintenance_bot.yml

- Triggers:
  - `workflow_dispatch` with `mode` and `allow_kernel_changes` inputs.
  - weekly schedule: Monday 06:15 UTC.
- Permissions:
  - `contents: write`
  - `pull-requests: write`
  - `issues: write`
- Job:
  - Skips cleanly when `GH_APP_ID` or `GH_APP_PRIVATE_KEY` are missing.
  - Creates a maintenance branch, runs `tools/maintenance_bot.py`, runs `tools/kernel_guard.py`, commits changes, pushes the branch, opens a PR, then runs `tools/pr_pro.py`.
- Writes to repo: yes, only through an explicit maintenance PR branch.

### repo-health-summary.yml

- Triggers:
  - weekly schedule: Monday 08:00 UTC.
  - `workflow_dispatch`
- Permissions:
  - `contents: read`
  - `issues: write`
- Job:
  - Collects repository health metrics with `gh`.
  - Posts a summary comment to issue `#93`.
- Writes to repo: no; writes issue comments.

### pages.yml

- Triggers:
  - `push` to `main` when `site/**` or `pages.yml` changes.
  - `workflow_dispatch`
- Permissions:
  - `contents: read`
  - `pages: write`
  - `id-token: write`
- Job:
  - Publishes the static `site/` directory to GitHub Pages.
- Writes to repo: no; deploys Pages artifact.

## Change rule

Any change under `.github/workflows/` must update this document in the same PR,
or the PR body must explicitly explain why no documentation update is needed.
