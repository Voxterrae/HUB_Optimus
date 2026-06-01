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

No action until CI, collaborator friction, regression, or user request creates a concrete signal.

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
Branch: `rfc/post-quantum-control-plane`
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
