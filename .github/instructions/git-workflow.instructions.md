---
applyTo: "**"
---

# Git Workflow Discipline

## Branch Management
- Close the current branch (commit → push → PR) before starting work on another.
- Never leave staged files in limbo across branch switches.
- If a branch switch is unavoidable, use `git stash` but always re-verify staging after `git stash pop` — stash does not reliably preserve the index.

## Separation of Concerns
- Each branch and PR has a single purpose. Do not mix documentation changes with functional changes.
- Scenario content, infrastructure docs, and runtime changes go in separate PRs.

## Commit Messages
- Use conventional commit prefixes: `feat:`, `docs:`, `fix:`, `chore:`, `test:`.
- Keep the subject line concise and descriptive.
- Example: `feat: add scenario-004 shared resource`

## Pull Request Structure
Every PR body must include:
- **Summary** — what changed
- **Why** — rationale
- **Scope** — affected files/areas
- **Non-goals** — what this PR intentionally does not do

## State Verification
- Run `git status` before committing to confirm exactly what is staged.
- Run `git status` after any stash, checkout, or restore operation to verify state.
- Report output before proceeding to the next step.

## Sequencing
- Execute operations one at a time: stage → verify → commit → push → PR.
- Do not batch multiple unrelated changes into a single commit.
- Stop and report after each step when instructed to do so.

## No Scope Creep
- Do not add improvements, refactors, or cleanup beyond the requested change.
- If you notice something worth fixing, note it for a separate branch — do not fold it in.
