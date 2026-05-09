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

Date: 2026-05-09
Source: Copilot execution for issue "clarify simulator capabilities vs. framework objectives"
Repo state: documentation-only PR on branch `copilot/issue-1-clarify-simulator-capabilities`
Last merged PR: #1578
Active issue: clarify implemented simulator capabilities versus planned/conceptual framework objectives
Decision made: clarify in documentation that only Layer 0 (core kernel) is implemented; Layers 1–3, integrity scoring, false-success detection, long-term stability scoring, cryptographic exchange, and corrective option generation are planned objectives
Reason: README.md and manifesto documents were overclaiming runtime capabilities not yet implemented in `hub_optimus_simulator.py` or `run_scenario.py`
Files changed:
- README.md (The simulator section)
- INTEGRITY_SCORING_SYSTEM.md (integration section — ES)
- INTEGRITY_SCORING_SYSTEM_EN.md (integration section — EN)
- TECHNICAL_MANIFESTO.md (sections 3 and 4 — ES)
- TECHNICAL_MANIFESTO_EN.md (sections 3 and 4 — EN)
- SIMULATION_README.md (intro paragraph and kyber reference — ES)
Validation:
- `python tools/check_mojibake.py` passed on all modified files
- `python -m pytest -q` passed, 46 tests
Risks: low; documentation-only change; no runtime, CI, schema, or benchmark changes
Next action: observe CI link-check results; no further changes unless signal appears
Out of scope:
- runtime changes
- CI changes
- benchmark changes
- schema changes
- roadmap changes
- LLM-as-judge
- dashboards
