# TRACEABILITY - repo snapshot protocol

## Purpose
Provide a single command that captures the repo state and automation surface
area before any analysis, merge, or deploy decision.

## Command
- Run: `powershell -ExecutionPolicy Bypass -File tools/trace_repo.ps1`
- Output: `docs/context/TRACEABILITY_SNAPSHOT.md`

## What the snapshot includes
- Timestamp and repo root path.
- Git branch, HEAD, remotes, recent commits.
- Working tree status and diff stats (staged and unstaged).
- Full contents of `.github/workflows` files.
- Top-level inventory of files and folders.

## Discipline rules
- Update the snapshot before asking for merge/deploy guidance.
- If automation changes are detected, record them in `docs/context/STATUS.md`.
