# HUB_Optimus AI Handoff

This file is the living bridge between ChatGPT PM/Tech Lead work and Codex repo execution.
GitHub remains the source of truth; chat context only matters when it is reflected in issues, PRs, or repo docs.

## Current System State

- Release: use GitHub Releases as source of truth.
- Last merged PR: #1578, `docs: add AI handoff protocol for ChatGPT/Codex sync`.
- Current branch: see active GitHub issue or PR; `main` is the source of truth after merge.
- CI status: use GitHub Checks on the active PR as source of truth.
- Active issue: none; use GitHub Issues/Project board for current assignment.
- Current priority: observe -> detect -> decide -> act; no build without signal.

## Recent Decisions

- Decision: synchronize ChatGPT and Codex through GitHub state, not through unsynchronized chat memory.
- Reason: repository files, issues, and PRs are reviewable, durable, and reproducible.
- Date: 2026-05-08.
- Source: GitHub issue #1577 and ChatGPT PM handoff summary.

## Current Constraints

- No big rewrites.
- No roadmap edits without RFC or approved issue.
- Runtime contract must remain stable unless explicitly scoped.
- Small PRs only.
- Keep source-of-truth conflicts resolved by `docs/context/STATUS.md`.

## Next Recommended Action

No action until CI, collaborator friction, regression, or user request creates a concrete signal.

## Do Not Do

- Do not touch runtime unless an issue explicitly says so.
- Do not add LLM-as-judge yet.
- Do not replace byte-for-byte benchmark guard.
- Do not add dashboards, semantic scoring, or new metrics without approved issue scope.
- Do not treat chat-only decisions as roadmap changes.

## AI Sync Block

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

## AI Sync Block

Date: 2026-05-08
Source: Codex execution for GitHub issue #1577
Repo state: governance protocol merged to main
Branch: see active GitHub issue or PR; `main` is the source of truth after merge
Last merged PR: #1578
Active issue: none
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
