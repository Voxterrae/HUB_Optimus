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

<<<<<<< HEAD
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
=======
## Human Stewardship and Technical Review Boundary

- Benjamin Gerrit Hoff is the creator, project owner, primary human steward, and final human-accountability layer of HUB_Optimus.
- `@Voxterrae` is the GitHub repository identity used for administration under that human authority.
- Rodrigo / `@itteamrod` is the trusted Core Technical Steward of HUB_Optimus.
- The GitHub enforcement of Rodrigo's role remains limited to paths explicitly assigned in `.github/CODEOWNERS` and requires Write collaborator access.
- Core Technical Stewardship does not imply project co-ownership, final human accountability, constitutional governance ownership, or unilateral repository-settings authority.
- AI operators must read `docs/governance/PROJECT_STEWARDSHIP.md` and must not infer authority beyond versioned GitHub records.
- Foundational principle: technology amplifies human judgment; it never replaces human responsibility.
>>>>>>> origin/main

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
