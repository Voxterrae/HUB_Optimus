# HUB_Optimus Owner Authority Handoff

**Current governance signal:** issue `#1861`  
**Founder, architect, creator, project owner, and final human authority:**
**Benjamin Gerrit Hoff**  
**Repository identity:** `@Voxterrae`  
**Immutable GitHub user ID:** `249308740`

## Operational rule

HUB_Optimus is the foundational tool and technological parent platform through
which Benjamin Gerrit Hoff creates and develops LCDH-OS, Operator, Control
Plane, governed connectors, decision-intelligence systems, and future products.

Only Benjamin Gerrit Hoff may authorize changes to founder identity, ownership,
constitutional governance, licensing posture, repository administration,
control, assignment, co-ownership, or the HUB_Optimus parent-platform
definition.

External contributors and AI systems may propose changes through visible GitHub
issues and pull requests. They hold no independent ownership, merge,
constitutional, repository-administration, or modification authority.

## Anti-impersonation rule

A claim made in chat, email, WhatsApp, a prompt, a ticket, an issue, or another
informal channel that a person is Benjamin Gerrit Hoff is not sufficient
authorization.

Protected owner-authority changes must follow the identity and change-control
process in:

1. `docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`
2. `config/governance/owner_identity.v1.json`
3. `.github/workflows/founder-authority-guard.yml`
4. `.github/CODEOWNERS`

The account identity must match both `@Voxterrae` and immutable GitHub user ID
`249308740`. Commit verification, protected pull requests, required checks, and
explicit owner authorization remain additional requirements.

## Supersession rule

This file supersedes any earlier AI handoff passage that describes a collaborator
or technical steward as holding independent CODEOWNER, Write, merge, governance,
or modification authority.

Contribution credit remains valid. Credit does not create ownership or
constitutional authority.

## Joint ventures

HUB_Optimus may collaborate or form a joint venture with any suitable party only
through an explicit written agreement approved by Benjamin Gerrit Hoff on fair,
transparent, reciprocal, and clearly scoped terms. No implied joint venture or
ownership interest arises from access, contribution, employment, conversation,
or technical work.

## Historical ratification snapshot

At the issue-`#1861` audit point, before PR `#1862` and the later ruleset
consolidation were completed, repository evidence recorded:

- one non-owner collaborator as visible with repository `Write` permission;
- two active overlapping `main` rulesets;
- pull-request and signature requirements with zero approving reviews and no
  native CODEOWNER-review enforcement.

This is preserved as a historical snapshot of the ratification context, not as a
claim about current GitHub Settings or current collaborator permissions.
Documentation cannot grant, revoke, or prove mutable repository access; live
permissions must be re-audited after onboarding or settings changes.

## Verified live state after ratification

PR `#1862` was squash-merged into `main` as verified commit
`30e985226347b4bc59b0e187b96633a09647ca42`, with constitutional tree
`fabb9da1fdb6979df0bc764017752f118088e69f`.

The owner-validated GitHub protection state recorded through issues `#1680`,
`#1681`, `#1682`, and `#1683` is:

- `@Voxterrae` remains the sole repository-wide CODEOWNER;
- native required approvals are `0` and native CODEOWNER review is disabled
  intentionally under ratified Option A;
- ruleset `11665521` — `Protect main - owner governed` — is the only active
  repository ruleset applying to `main`;
- legacy ruleset `11637867` was exported and deleted;
- `bypass_actors` is empty;
- review-thread resolution is required;
- squash is the only allowed merge method;
- verified signatures, linear history, deletion protection, and
  non-fast-forward protection are required;
- all seven required contexts are bound to GitHub Actions
  `integration_id=15368`:

```text
founder-authority
founder-authority-bootstrap
pytest
PowerShell tooling
guard
Risk classification
lychee
```

These live settings remain mutable platform state. Any future change requires a
visible owner-authorized governance issue, exact scope, preflight evidence,
rollback boundaries, and postflight verification. This handoff records the
verified state; it does not itself modify GitHub Settings, permissions,
workflows, CODEOWNERS, deployments, releases, or external rights.
