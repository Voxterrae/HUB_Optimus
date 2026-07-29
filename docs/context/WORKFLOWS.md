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
  - weekly schedule only: Monday 06:15 UTC.
- Permissions: `contents: read`.
- Job:
  - Verifies that the credential-free checkout is clean and exactly matches
    the scheduled `main` commit.
  - Runs `tools/maintenance_bot.py` only inside an isolated copy of committed
    `HEAD`, compares that candidate with an untouched baseline, and publishes
    a GitHub Actions step summary.
  - Exits non-zero with the proposed paths when drift exists or when the check
    cannot complete safely.
- Writes to repo: no. It creates no token, commit, branch, pull request, or
  remote ref. Existing branch retirement is a separate, explicitly audited
  operation under issue `#1788`.

### `tools/pr_pro.py` support boundary

- Status: supported as an optional helper for enriching an existing PR with
  governed labels and a changed-file summary. It does not create or merge PRs
  and is not an authentication or authorization boundary.
- Write mode requires the GitHub CLI and uses only the authentication and
  token scopes already supplied by the caller. The tool does not create,
  exchange, persist, or expand tokens.
- Every failed `gh` operation is terminal and returns a non-zero status. A
  success message is emitted only after all required label, edit, and comment
  operations succeed.
- `--dry-run` performs the local Git diff and prints the planned target,
  labels, and comment. It does not invoke `gh` and therefore performs no
  GitHub read or write.
- The versioned workflow file remains authoritative for whether a workflow
  invokes this optional helper. No current workflow invokes it. A draft PR or
  chat statement does not change the active workflow.

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

## External Action update review

Every external `uses:` reference must use a reviewed, full 40-character commit
SHA followed by the corresponding upstream release as an inline comment:

```yaml
uses: owner/action@0123456789abcdef0123456789abcdef01234567 # v1.2.3
```

Dependabot proposes GitHub Actions updates weekly. It must not auto-merge them.
For each proposed update, a human reviewer must:

1. confirm the exact release tag and commit in the upstream Action repository;
2. review the upstream release notes and the diff from the currently approved
   version, including `action.yml`, runtime changes, inputs, and permissions;
3. confirm that the workflow keeps its existing permissions and intended
   inputs, then update both the SHA and inline version comment;
4. update the reviewed allowlist in `tests/test_workflow_action_pins.py`;
5. run the complete test suite and let the affected workflows execute in the
   pull request before approval.

An unknown Action, mutable tag, unreviewed SHA, missing version comment, or
permission expansion requires explicit review and must not be merged solely
because Dependabot proposed it.
