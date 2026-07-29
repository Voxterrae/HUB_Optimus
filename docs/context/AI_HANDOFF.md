# HUB_Optimus AI Handoff

This file records operational handoff state for ChatGPT/Codex repo execution.
GitHub remains the source of truth; chat summaries are advisory unless reflected in issues, PRs, commits, or repo docs.

## Operating Discipline

- Release: use GitHub Releases as source of truth.
- Current branch and active assignment: use the active GitHub issue or PR.
- CI status: use GitHub Checks on the active PR as source of truth.
- Default loop: observe -> detect -> decide -> act.
- Default rule: no build without signal.

## Current Constraints

- No big rewrites.
- No roadmap edits without RFC or approved issue.
- Runtime contract must remain stable unless explicitly scoped.
- Small PRs only.
- Keep source-of-truth conflicts resolved by `docs/context/STATUS.md`.

## PowerShell Tooling Boundary

- Mutation-capable PowerShell utilities are preview-only unless the operator
  supplies `-Apply`.
- They are limited to Git-tracked, non-link paths inside the detected repository.
- Their current support status is provisional/manual and requires PowerShell 7
  plus Git.
- The dedicated `PowerShell tooling` CI job must fail when `pwsh` 7 is missing
  and must execute the temporary-repository behavior tests. Local or generic
  pytest runs without `pwsh` report those tests as skipped; a skip is not
  certification.
- Do not describe PowerShell behavior as CI-verified from repository code or a
  local result alone. Only a green dedicated job on the reviewed PR is evidence
  for the behavior covered on its Ubuntu runner; Windows and macOS remain
  unverified by that job.

## Human Stewardship and Technical Review Boundary

- Benjamin Gerrit Hoff is the creator, project owner, primary human steward, and final human-accountability layer of HUB_Optimus.
- `@Voxterrae` is the GitHub repository identity used for administration under that human authority.
- Rodrigo / `@itteamrod` is the trusted Core Technical Steward of HUB_Optimus.
- The GitHub enforcement of Rodrigo's role remains limited to paths explicitly assigned in `.github/CODEOWNERS` and requires Write collaborator access.
- Core Technical Stewardship does not imply project co-ownership, final human accountability, constitutional governance ownership, or unilateral repository-settings authority.
- AI operators must read `docs/governance/PROJECT_STEWARDSHIP.md` and must not infer authority beyond versioned GitHub records.
- Foundational principle: technology amplifies human judgment; it never replaces human responsibility.

## Governance Intelligence Boundary

Issue #1694 and PR #1695 are the ratification record for the canonical Governance Intelligence protocol.

Operational boundary:

- The canonical protocol lives at `docs/governance/GOVERNANCE_INTELLIGENCE.md` and is active through the reviewed merge record of PR #1695.
- Governance Intelligence requires explicit separation of claim, evidence, inference, uncertainty, narrative amplification, and operational relevance.
- Chat messages, hidden prompts, conversation memory, model output, and external AI reviews remain advisory until represented in versioned GitHub artifacts.
- No model family, model version, provider, or hidden control path may ratify governance, override repository evidence, approve its own work, or merge its own governance change.
- Model capability may improve analytical depth; it does not increase governance authority.
- Human accountability remains mandatory for ratification, publication, escalation, and sensitive use.
- `docs/rfc/constitutional_governance_ai_regulatory_boundary.md` remains a separate Draft RFC and is not accepted or superseded by this ratification.

## Handoff Update Discipline

Update this file only when the scoped issue or PR changes operational handoff state, including:

- operational state
- active priorities
- architecture
- governance posture
- runtime, CI, or benchmark posture
- contributor handoff requirements

Do not update this file for narrowly scoped translation, typo, link, formatting, or parity-only PRs unless the issue or PR explicitly requires it.

If this file is not updated, say why in the PR body.

## Current Recommended Action

Return to controlled observation. Act only when a new regression, architecture ambiguity, contributor friction, documentation drift, CI/runtime signal, governance risk, or explicit user request is recorded in GitHub.

## PR Enrichment Helper Boundary

Issue #1762 keeps `tools/pr_pro.py` as a supported, optional helper for an
existing PR. It is not a PR creator, merge authority, or authentication
provider.

Operational boundary:

- Write mode requires an existing PR target and the GitHub CLI.
- The helper uses the caller's existing authentication and scopes; it does
  not create, persist, exchange, or expand tokens.
- Failed GitHub or required local diff commands return non-zero and cannot
  emit the success status.
- `--dry-run` invokes no GitHub commands and performs no GitHub mutation.
- The active workflow file, not this helper or chat context, determines
  whether scheduled maintenance invokes it.

## Python Packaging Boundary

Issue #1763 records drift between the documented Python minimum, executable
syntax, bootstrap checks, and the dependency files. The scoped correction
in PR #1776 establishes:

- supported Python is 3.11 or newer;
- `requirements.txt` is the runtime tier and contains `jsonschema`;
- `requirements-dev.txt` includes the runtime tier and adds `pytest`;
- `python scripts/bootstrap.py --runtime-only` installs/checks runtime
  dependencies and executes the supported scenario CLI smoke test;
- the default bootstrap remains the development path and fails when tests or
  frozen benchmarks fail rather than printing an ambiguous ready state.

The runtime-only install path has been verified in a newly created virtual
environment without development requirements.

## Maintenance Drift Boundary

Issue #1788 replaces branch-producing scheduled maintenance with a read-only
drift check on trusted `main`.

Operational boundary:

- the scheduled workflow has only `contents: read` permission and persists no
  checkout credentials;
- it creates no GitHub App token, commit, branch, pull request, or remote ref;
- the legacy maintenance helper runs only inside an isolated copy of committed
  `HEAD`;
- proposed changes fail the check and appear in the GitHub Actions step
  summary; they are never applied to the source checkout;
- retiring historical maintenance branches remains a separate audited action
  and is not authorized or performed by the scheduled drift check.

## Simulator Isolation Boundary

Issue #1755 records a verified mismatch between the runtime contract and the
simulation kernel: seeded runs used module-global random state, repeated runs
accumulated history, and previously returned results exposed the simulator's
mutable history.

PR #1770 restores the documented boundary:

- one run-local `random.Random` instance drives all built-in actor policies;
- seeded execution does not mutate caller-global random state;
- each `run()` starts with empty run history;
- returned history is a snapshot rather than live simulator state;
- changed seed-42 benchmark bytes are reviewed and frozen explicitly.

Laboratory observations derived from the previous random stream require
separate regeneration under issue #1775; they are not silently rewritten by
the runtime correction.

## Boundary Search Integrity Boundary

Issue #1754 and PR #1774 record that the laboratory boundary tool treated
non-monotonic observations as monotonic and could collapse runner errors into
ordinary failures. The scoped correction establishes:

- `rounds_min` retains binary search because a larger round budget preserves
  the deterministic execution prefix;
- `actors_min` enumerates actor counts 1–6 because actor count changes the
  random stream and role-sensitive policies can lose success at a larger
  count;
- `threshold_max` enumerates thresholds 1–5 because success checks exact
  equality and can fail between successful values;
- actor and threshold state maps are retained with seed, policy, and method
  provenance;
- runner or result errors are explicit probe errors, not failed simulations;
- verification re-enumerates each complete axis, including reported `None`
  extrema, rather than checking only an adjacent value.

The boundary section of `docs/lab_state.md` is regenerated from the isolated
simulator. Other mutation, gradient, and frontier observations remain
historical until issue #1775 regenerates them.

## Telemetry Input Boundary

Issue #1757 records that malformed scenario files could crash telemetry or
be subtracted from multiple aggregate categories. The scoped correction
in PR #1771 restores the following behavior:

- every discovered input receives exactly one processing outcome:
  `agreement`, `no_agreement`, `parse_error`, `schema_error`, or
  `runtime_error`;
- malformed JSON roots, invalid UTF-8, schema errors, and runner-output
  errors are recorded per file without stopping safe collection;
- aggregate counts remain non-negative and sum to the discovered total;
- exit `0` means complete collection, exit `2` means outputs were written
  with one or more partial data errors, and exit `1` means fatal setup or
  output failure;
- the canonical generated seed-42 set remains 60/60 runtime-complete with
  55 agreements, 5 no-agreements, and average convergence round 1.8.

## Mobile Intake Storage Boundary

Issue #1759 records that the mobile helper wrote raw claims to a non-ignored
repository-root file without stable classification or retention guidance.

PR #1777 restores the following boundary:

- default raw mobile intake is stored under the git-ignored
  `.local/intake/` directory;
- on supported POSIX systems, the protected default path is traversed and
  opened through no-follow directory descriptors, eliminating parent-path
  check-to-open races;
- platforms without those descriptor primitives fail closed for the protected
  default and require an explicit operator-managed `--output` path;
- every opened output descriptor must reference a regular file; the protected
  default additionally requires a single link, rejecting FIFOs, devices,
  sockets, and hard-linked targets before permission or content changes;
- the default directory/file and newly created custom files use private POSIX
  permissions where supported; an existing custom file retains its operator-set
  permissions;
- appends restore a missing LF boundary before writing the next JSONL record;
- option-like argv claims are accepted without being echoed by parser errors;
- each record carries schema version, intake ID, capture time, source,
  classification, verification status, and publication status;
- raw intake remains unverified, local-only material and is never promoted or
  published automatically;
- `--output` permits an explicit operator-managed path with a warning;
- the operator remains responsible for classification, access, retention,
  backup, and deletion.

No encryption, managed confidential storage, evidence verification, or
multi-writer locking is claimed.

## Semantic CaseInput Integrity Boundary

- Issue #1756 defines the versioned `CaseInput v1` contract as the combination
  of the structural JSON Schema in
  `semantic_engine/contracts/case_input.schema.json` and the complete Python
  validator `semantic_engine.contracts.case_input.validate_case_input`.
- Schema-only validation is structural pre-validation, not complete contract
  conformance: uniqueness and cross-record reference integrity are enforced by
  the Python validator.
- The Semantic Engine CLI rejects unknown fields, duplicate claim/evidence IDs,
  and evidence references to undeclared claims with controlled JSON-path
  errors.
- `metadata` is the only open extension object, remains preserved in output,
  and is opaque rather than executable or authoritative.
- Input `decision_trace` and `audit_log` are forbidden; they remain output-only
  engine records.
- Operator `/analyze` handoff and the local API reach the same contract through
  `hub-core analyze`; browser-local draft rendering remains a non-authoritative
  preview.
- Missing, unreadable, invalid UTF-8, invalid JSON, and contract-invalid inputs
  fail through the CLI's controlled error channel without a traceback.
- This change adds no evaluator, scoring, model judge, or autonomous conclusion.

## Meta-learning Follow-up

- `.github/copilot-instructions.md` currently identifies `v1_core/workflow/05_meta_learning.md` as the meta-learning update location.
- Other meta-learning copies or link targets require canonical/parity/legacy classification in a separate PR.
- Do not consolidate or delete meta-learning files in this handoff/status discipline PR.

## Do Not Do

- Do not touch runtime unless an issue explicitly says so.
- Do not add LLM-as-judge yet.
- Do not replace byte-for-byte benchmark guard.
- Do not add dashboards, semantic scoring, or new metrics without approved issue scope.
- Do not treat chat-only decisions as roadmap changes.

## Historical AI Sync Blocks

The entries below are retained as historical execution notes. They are not current branch, PR, issue, or priority state.

### AI Sync Block

Date: 2026-07-08
Source: Copilot Coding Agent execution for GitHub issue #1690
Repo state: local branch for RFC/github-platform-strategy
Branch: rfc/github-platform-strategy
Active issue: #1690
Decision made: add RFC-only GitHub platform strategy document
Reason: issue #1690 requests a governed, traceable record of which GitHub platform capabilities HUB_Optimus should adopt now, next, later, or avoid — grounded in current repository evidence
Files changed:
- docs/rfc/github_platform_strategy.md
- docs/context/AI_HANDOFF.md
Validation:
- `python tools/check_mojibake.py docs/rfc/github_platform_strategy.md` passed
- `git diff --check -- docs/rfc/github_platform_strategy.md` passed
- `python tools/check_mojibake.py docs/context/AI_HANDOFF.md` passed
- `git diff --check -- docs/context/AI_HANDOFF.md` passed
Risks: documentation-only; no runtime, CI, benchmark, schema, settings, or security claim changes
Next action: review RFC content and open follow-up issues only after explicit approval
Out of scope:
- runtime changes
- CI changes
- benchmark changes
- schema changes
- GitHub Settings mutation
- GitHub Organization migration
- Copilot/GitHub App automation
- dashboards
- LLM-as-judge
- roadmap changes

### AI Sync Block

Date: 2026-05-24
Source: Codex execution for GitHub issue #1589
Repo state: local branch `docs/capability-status-table`
Branch: `docs/capability-status-table`
Active issue: #1589
Decision made: add a capability status table and correct benchmark/drift rows to match implemented runner behavior
Reason: issue #1589 requests a source-backed table to avoid overpromising or under-reporting current runtime behavior
Files changed:
- docs/architecture/capability_status.md
- docs/context/AI_HANDOFF.md
Validation:
- `python tools/check_mojibake.py docs/architecture/capability_status.md` passed
- `git diff --check -- docs/architecture/capability_status.md` passed
- `python tools/check_mojibake.py docs/context/AI_HANDOFF.md` passed
- `git diff --check -- docs/context/AI_HANDOFF.md` passed
Risks: documentation-only; table wording must remain conservative and source-backed
Next action: review table wording against issue #1589 and PR #1580 before opening a PR
Out of scope:
- runtime changes
- CI changes
- benchmark changes
- schema changes
- roadmap changes
- multilingual docs
- crypto implementation
- dependency additions

### AI Sync Block

Date: 2026-05-24
Source: Codex execution for RFC branch `rfc/post-quantum-control-plane`
Repo state: local RFC branch
Branch: rfc/post-quantum-control-plane
Active issue: none provided in task
Decision made: add RFC-only post-quantum control plane planning document
Reason: explicit user request for a governed RFC covering artifact signing, sealed exchange, node identity, quorum access, auditability, and crypto-agility
Files changed:
- docs/rfc/post_quantum_control_plane.md
- docs/context/AI_HANDOFF.md
Validation:
- `python tools/check_mojibake.py docs/rfc/post_quantum_control_plane.md` passed
- `git diff --check -- docs/rfc/post_quantum_control_plane.md` passed
- `python tools/check_mojibake.py docs/context/AI_HANDOFF.md` passed
- `git diff --check -- docs/context/AI_HANDOFF.md` passed
Risks: documentation-only; no runtime, CI, benchmark, schema, dependency, or production security claim changes
Next action: review RFC scope and open follow-up issues only after explicit approval
Out of scope:
- crypto implementation
- runtime changes
- CI changes
- benchmark changes
- schema changes
- roadmap changes
- dashboards
- LLM-as-judge

### AI Sync Block

Date: 2026-05-08
Source: Codex execution for GitHub issue #1577
Repo state: governance protocol merged to main
Branch at the time: see active GitHub issue or PR; `main` is the source of truth after merge
Merged PR for this historical block: #1578
Active issue at the time: none
Decision made: add persistent repo-level handoff protocol for ChatGPT/Codex sync
Reason: align AI work through GitHub state instead of fragile chat-memory synchronization
Files changed:
- AGENTS.md
- docs/context/AI_HANDOFF.md
Validation:
- `git diff --check` passed
- `python tools/check_mojibake.py AGENTS.md docs/context/AI_HANDOFF.md` passed
- `python -m pytest -q` passed, 42 tests
Risks: low; documentation-only change
Next action: observe CI and collaborator friction; open scoped issue only when signal appears
Out of scope:
- runtime changes
- CI changes
- benchmark changes
- schema changes
- roadmap changes
- LLM-as-judge
- dashboards

## Governance RFC handoff — constitutional governance and AI regulatory boundary

PR #1628 introduces a draft RFC defining HUB_Optimus constitutional governance and AI regulatory boundary posture.

Operational meaning:
- HUB_Optimus is framed as an evidence-structured analysis and governance system, not an autonomous enforcement, censorship, surveillance, or persuasion system.
- Future regulated, high-risk, automated, or externally exposed capabilities require explicit RFC review before implementation.
- High-risk downstream use triggers include consequential decisions about people, surveillance/profiling, political persuasion, automated moderation/enforcement, and legal/regulatory bypass risk.
- This PR is documentation-only and does not authorize runtime, CI, schema, benchmark, roadmap, licensing, IP, ingestion, dashboard, scoring, or provider changes.

Review note:
- The RFC lives under docs/rfc/ to avoid creating governance translation mirror drift under docs/governance/.
