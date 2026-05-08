# AGENTS.md - HUB_Optimus

You are Codex working on HUB_Optimus.

## Source of Truth

GitHub Issues, Pull Requests, Project board state, and repository docs are the only source of truth.
Chat summaries are advisory unless reflected in GitHub or committed repo docs.

## Operating Rules

- No big rewrites.
- No surprise architecture changes.
- No roadmap edits without an approved RFC or issue.
- One problem equals one small, reversible PR.
- Prefer measurable increments.
- Keep runtime behavior stable unless explicitly scoped.
- Do not mix unrelated feature, refactor, docs, and cosmetic cleanup.
- Do not touch runtime, CI, benchmarks, schemas, or kernel/governance contracts unless the issue explicitly asks for it.
- If repeated mistakes appear, update this file with the stable rule instead of repeating the same correction in chat.

## Required Reading

Before changing files, read:

1. `README.md`
2. `docs/context/AI_HANDOFF.md`
3. `docs/context/STATUS.md`, if present
4. `docs/architecture/runtime_contract.md`, if present
5. The relevant GitHub issue or Pull Request

If a required file is missing, state that explicitly and continue with the smallest safe scope.

## Default Output Format

- Decision
- Scope
- Files changed
- Acceptance criteria
- Validation
- Risks
- AI_HANDOFF.md update
- Next PR recommendation

## Current Strategic Bias

Prefer observability, benchmark clarity, CI visibility, and controlled drift detection.
Do not introduce LLM-as-judge, dashboards, semantic scoring, roadmap changes, or runtime contract changes unless explicitly approved in GitHub.

## Handoff Discipline

After meaningful work, update `docs/context/AI_HANDOFF.md` with:

- What changed
- Which issue or PR justified it
- What validation ran
- What remains pending
- What should not be done yet
- The next recommended action
