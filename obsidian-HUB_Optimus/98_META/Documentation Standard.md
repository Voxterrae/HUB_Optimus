---
type: "meta-standard"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "meta"
  - "documentation"
  - "standard"
---

# Documentation Standard

## Principle

Document the system that emerges from files, then map each concept back to source. Do not replace architecture with a directory listing.

## Required Component Sections

- Purpose
- Responsibilities
- Runtime Behaviour
- Inputs
- Outputs
- Dependencies
- Consumers
- Data
- APIs
- Failure Modes
- Security
- Tests
- Deployment
- Source Files
- Related Components

## Evidence Language

- `CONFIRMED`: direct evidence.
- `INFERRED`: explicit inference.
- `UNKNOWN`: insufficient or external evidence.

## Status Language

Only use statuses in [[Status Definitions]].

## Wikilinks

Use the same concept name in:

1. Obsidian note title;
2. `system.json` y sus fragmentos declarados;
3. Web explorer;
4. Source Map.

Avoid duplicate note stems and ambiguous links.

## Source Paths

Use repository-relative paths. Do not copy secrets, credentials, personal data or private operational payloads.

## Drift

When code and documentation differ, preserve:

```markdown
## Documentation Drift

Documentation states:
Code currently shows:
Likely current truth:
Evidence:
```

## Baseline

Every update must change the commit/tree in [[Repository Analysis]] and the structured model together.
