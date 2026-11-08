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

### optimus-admin-gateway.yml

- Triggers:
  - `push` to `main` when the Admin Gateway package or this workflow changes;
  - `pull_request` for the same paths;
  - `workflow_dispatch`.
- Permissions: `contents: read`.
- Job `python-contract`:
  - installs the package with its development dependencies on Python 3.11;
  - runs the complete product test suite;
  - treats the Starlette legacy-TestClient deprecation as an error.
  - verifies that the package manifest exactly matches the tracked Git-index
    bytes for the Admin Gateway package and its workflow.
- Job `powershell-contract`:
  - parses every Admin Gateway PowerShell asset with PowerShell's language parser;
  - self-tests an executable-AST guard that allows inert strings and comments
    while rejecting direct dynamic-execution calls;
  - rejects a non-safe DryRun default;
  - runs the versioned Pester safety contracts with `Invoke-Pester -CI`.
- Writes to repo: no.

### native-pilot-windows.yml

- Trigger: `workflow_dispatch` only, with a required immutable 40-hex
  `candidate_sha` from this repository and a closed `test_suite` choice:
  `bootstrap-process` (default), `identity-cng` or `identity-http`.
- Permissions: `contents: read`; the reviewed checkout Action does not persist
  credentials. No named secrets, write token, upload or deployment is used.
- One disposable GitHub-hosted `windows-2022` job (20-minute timeout):
  - validates the input before checkout, verifies exact HEAD and binds all
    native-pilot source/manifest/lockfile bytes to that candidate;
  - verifies explicit x64 MinGW `gcc`, `ar` and `dlltool` paths and metadata;
  - installs exact Rust `1.99.0-x86_64-pc-windows-gnu`, Clippy and rustfmt on
    the runner, with isolated Cargo/Rustup state and cleared compiler overrides;
  - fetches locked dependencies once, then runs the selected suite offline:
    exactly 36 `bootstrap_process::` tests (30 token and 6 parent), or the exact
    eight reviewed `identity::tests::` names, or exactly those eight plus seven
    reviewed `approval_https::tests::` names for `identity-http`; then Clippy with
    `--all-targets -- -D warnings` and `rustfmt --check --edition 2024 src/lib.rs`;
  - requires all selected tests to execute with 0 failed and 0 ignored, and
    verifies unchanged source and Cargo.lock hashes afterward; filtered tests
    from other modules provide no acceptance;
  - for `identity-http`, requires the HTTP driver already `Running` immediately
    before both test inventory and execution, and still `Running` afterward,
    including on failure. It refuses stopped/unavailable states and issues no
    service start/stop/configuration command. These reads are not atomic and
    cannot exclude external state changes between observation and `HttpInitialize`;
  - captures CNG/HTTP test stdout/stderr in runner process memory and publishes only
    the allowlisted inventory, recognized test statuses, exit code and counts.
    Raw vectors, key/resource identifiers and failure output are not printed or uploaded;
  - records candidate/workflow SHAs, runner/tool versions, SHA-256 inputs and
    actual outcomes in the job log/summary. Skipped or incomplete validation
    cannot produce PASS.
- The CNG selection requires a separately reviewed exact candidate containing
  `src/identity.rs`. It creates real persistent test keys in the disposable
  runner account's Microsoft Software KSP, including an owned export-policy
  control. Tests delete their exact owned keys and verify failed reopening;
  runner disposal is the remaining boundary after cancellation or process loss.
  No existing keys are enumerated or deleted. Run only under the exact approved
  source/profile scope. Raw CNG output is ephemeral and is not retained as an
  artifact; a failed run may need a separately scoped private diagnostic.
- The combined `identity-http` suite requires a separately reviewed candidate
  containing `src/identity.rs` and `src/approval_https.rs`; the exact inventory
  must contain only their fifteen expected tests before any are executed.
  It repeats CNG under the candidate's changed manifest/module graph and creates
  only owned API-v2 sessions, anonymous non-inheritable queues and empty URL
  groups. No URL registration, queue binding, HTTP I/O, listener, certificate,
  URLACL or TLS acceptance is included. Explicit cleanup failures fail the tests;
  Drop is best-effort and failed cleanup may persist until process exit.
- Eight internal CNG passes do not prove independent Node interoperability,
  production MSVC compatibility, TPM/biometric protection, same-user isolation
  or protected enrollment.
- Writes to repo: no. This is candidate-specific hosted evidence, not laptop
  account-context certification, remote-device enrollment or release authority.
  The manual workflow must reach the default branch before dispatch; merging
  it does not run native validation or make this job a required branch check.

### optimus-windows-smoke.yml

- Trigger: manual `workflow_dispatch` on protected `main` only, in the public
  source repository with exact repository and owner-account guards.
- Permissions: `contents: read`; immutable checkout Action, no persisted checkout
  credentials, artifact uploads or caches. The source input confirms a literal
  reviewed commit; exact HEAD/tree and clean checkout are checked separately.
- Runner: Windows 2022, 15-minute job limit, existing SDK **10.0.403** without
  installation/fallback. Less than one GiB free RAM or occupied loopback17831
  blocks execution without stopping existing processes or listeners.
- Native coverage: complete C# TLS suite and all 22 identity cases, production
  suites/publications and real packaged-service acceptance. Their actual totals
  and cleanup must come from the exact-source receipt, not historical counts.
- The independent three-minute WPF step builds with visible diagnostics, then
  runs the 13 reviewed search handler/state scenarios with captured runtime
  output. Every named case must occur once, the exact final summary must occur
  once and last, and exit/failure/block markers must agree. Only curated case
  outcomes and provenance enter its separate report and always-run summary.
- WPF cases use synthetic HTTP, owned temporary settings and an invisible HWND;
  they require an interactive disposable runner with no default Optimus profile.
  The product window is not shown and its engine/host are not initialized.
- Issue #2151 scopes one later execution with `gui=false`; these WPF cases run
  independently of that optional GUI input. Visible GUI, physical keyboard/focus,
  assistive technology, provider relevance and distribution remain separate.
  Missing, blocked, skipped or timed-out evidence never establishes acceptance.
- Record workflow SHA, product SHA/tree and run/attempt separately. The workflow
  does not create a new required PR-head check, activate a provider or distribute
  the product. OWNER_AUTHORITY_HANDOFF remains controlling and unchanged.

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

### retire-maintenance-branches.yml

- Trigger: `workflow_dispatch` only. Merge, push, pull request, and schedule
  events cannot activate it.
- Inputs:
  - `mode`, defaulting to `dry-run`;
  - the exact approved live `main` SHA;
  - the manifest-derived confirmation sentence, required by the tool only for
    `execute`.
- Dry-run permissions: `contents: read` and `pull-requests: read`.
- Execute permissions, scoped only to the execute job:
  - `contents: write` for the single atomic ref deletion;
  - `issues: write` to record verified post-cleanup counts in issue `#1788`.
  - `pull-requests: read` for both preflight and postflight head checks.
- Both paths verify a clean checkout whose dispatch SHA, input SHA, checked-out
  SHA, `origin/main`, and live `main` agree. They restore and verify the
  versioned standalone bundle, compare complete REST and Git branch
  inventories, and reject moved, protected, PR-backed, missing, or newly added
  maintenance refs.
- Execute additionally requires the exact confirmation emitted by dry-run,
  performs an atomic Git push dry-run, refreshes every live guard, and then
  submits one `git push --atomic` with 881 exact leases and deletion refspecs.
  There is no batching or non-atomic fallback.
- Writes to repo content: no. The execute path can delete only the exact 881
  remote refs in the issue #1788 manifest and comments its structured outcome;
  successful outcomes include verified post-counts. Merging the workflow does
  not run it.

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
  - PR and issue counts request up to 10,001 records so counts through the
    explicit 10,000-item audit ceiling are exhaustive. A failed CLI/API call,
    invalid JSON response, or result above that ceiling stops the run without
    publishing a partial or plausible-zero snapshot.
  - Remote branch refs are collected once and a failed `git ls-remote` also
    stops the run instead of being represented as zero maintenance branches.
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
