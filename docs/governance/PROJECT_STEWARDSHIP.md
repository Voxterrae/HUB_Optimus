# HUB_Optimus Project Stewardship

## Purpose

This document records the human authority and technical review roles of
HUB_Optimus.

It is an internal governance record. It does not replace external legal
registrations, contracts, intellectual-property records, or identity documents.
GitHub remains the operational source of truth for repository state, issues,
pull requests, reviews, releases, settings, and versioned documentation.

## Creator, Project Owner, and Primary Human Steward

**Benjamin Gerrit Hoff** is the creator, project owner, and primary human
steward of HUB_Optimus.

He is the human origin and final-accountability layer of the project. His
responsibilities include:

- defining the project's purpose and long-term direction;
- holding final human accountability for constitutional governance;
- approving changes to ownership, protected authority, and core architecture;
- preserving the boundary between human judgment and machine assistance;
- ensuring that repository decisions remain visible and traceable through
  GitHub.

AI systems may assist with analysis, drafting, implementation, and review. They
do not own HUB_Optimus and cannot replace its human accountability layer.

## Repository Identity and Administration

`@Voxterrae` is the GitHub repository identity through which HUB_Optimus is
administered.

The account represents repository administration under the authority of
Benjamin Gerrit Hoff. It is not a separate project owner or an autonomous
governance actor.

## Scoped Technical CODEOWNER

**Rodrigo / `@itteamrod`** is a scoped Technical CODEOWNER for the interface and
Semantic Engine areas explicitly listed in `.github/CODEOWNERS`:

- `semantic_engine/`
- `tests/semantic_engine/`
- `examples/semantic_engine/`
- `docs/architecture/semantic_engine_cli.md`
- `site/`

Within those paths, the role includes:

- reviewing technical coherence and maintainability;
- checking tests, examples, and documentation against implementation;
- protecting incremental scope and compatibility;
- providing a human technical review before governed merge.

This scoped role does not grant project co-ownership, Kernel authority,
constitutional governance ownership, repository-settings authority, or review
authority outside the paths listed in `.github/CODEOWNERS`.

## Authority Boundaries

The operating boundary is:

1. Benjamin Gerrit Hoff holds project ownership and final human accountability.
2. GitHub records the authoritative operational state.
3. CODEOWNERS grants path-specific review responsibility, not project ownership.
4. AI operators remain advisory and must act through visible GitHub workflows.

No chat statement, AI output, acknowledgement entry, job title, or informal
agreement changes these roles unless the change is reflected in a scoped GitHub
issue, reviewed pull request, and the relevant repository controls.

## Change Control

Changes to this document or to human CODEOWNERS assignments require:

- an explicit governance issue or approved RFC;
- a focused pull request;
- synchronized updates to affected handoff and protection documentation;
- review under the repository's protected governance process.
