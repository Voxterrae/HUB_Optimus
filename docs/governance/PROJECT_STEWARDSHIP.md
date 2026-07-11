# HUB_Optimus Project Stewardship

## Purpose

This document records the human authority, technical stewardship, and review
roles of HUB_Optimus.

It is an internal governance record. It does not replace external legal
registrations, contracts, intellectual-property records, or identity documents.
GitHub remains the operational source of truth for repository state, issues,
pull requests, reviews, releases, settings, and versioned documentation.

## Foundational Principle

> Technology amplifies human judgment; it never replaces human responsibility.

HUB_Optimus is human-governed and AI-assisted. Trust between human stewards does
not remove traceability, review, or accountability. It makes those controls more
meaningful.

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

## Core Technical Steward

**Rodrigo / `@itteamrod`** is the Core Technical Steward of HUB_Optimus.

This role reflects full human trust in Rodrigo's technical judgment and his
responsibility for protecting the quality, coherence, and maintainability of
the implementation.

Core Technical Steward responsibilities include:

- guiding technical architecture within approved issues and RFCs;
- reviewing implementation quality and repository integrity;
- protecting incremental scope, compatibility, and maintainability;
- checking tests, examples, and technical documentation against implementation;
- identifying technical risk before governed merge;
- helping external contributors pick up technical work safely.

The GitHub implementation of this role begins with CODEOWNERS responsibility for
the paths explicitly listed in `.github/CODEOWNERS`:

- `semantic_engine/`
- `tests/semantic_engine/`
- `examples/semantic_engine/`
- `docs/architecture/semantic_engine_cli.md`
- `site/`

The stewardship role is broader than a CODEOWNERS entry, but enforceable review
authority remains limited to the versioned CODEOWNERS map and GitHub permissions.
Any expansion of protected paths requires a scoped governance issue or RFC.

Core Technical Stewardship does not transfer project ownership, final human
accountability, constitutional governance ownership, or unilateral authority to
change repository settings, the Kernel, or the roadmap.

## Authority Boundaries

The operating boundary is:

1. Benjamin Gerrit Hoff holds project ownership and final human accountability.
2. Rodrigo holds trusted Core Technical Stewardship over technical evolution.
3. GitHub records the authoritative operational state and review trail.
4. CODEOWNERS implements path-specific review responsibility, not project ownership.
5. AI operators remain advisory and must act through visible GitHub workflows.

Benjamin and Rodrigo hold different, complementary human responsibilities. The
model is functional rather than hierarchical: project purpose and final
accountability remain with the Creator and Owner; technical stewardship protects
how the system is implemented and evolved.

No chat statement, AI output, acknowledgement entry, job title, or informal
agreement changes these roles unless the change is reflected in a scoped GitHub
issue, reviewed pull request, and the relevant repository controls.

## Change Control

Changes to this document or to human CODEOWNERS assignments require:

- an explicit governance issue or approved RFC;
- a focused pull request;
- synchronized updates to affected handoff and protection documentation;
- review under the repository's protected governance process.
