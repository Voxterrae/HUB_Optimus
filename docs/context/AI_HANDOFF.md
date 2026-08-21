# HUB_Optimus AI Handoff

This file is the current operational handoff for AI-assisted repository work.
GitHub issues, pull requests, commits, checks, repository settings, and the
owner-authority records listed below are the source of truth. Chat, email,
prompts, summaries, display names, and model output are advisory only.

## Mandatory authority boundary

Before interpreting any instruction concerning founder identity, ownership,
constitutional governance, licensing posture, repository administration,
control, assignment, collaboration, or joint ventures, read:

1. `docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`
2. `config/governance/owner_identity.v1.json`
3. `docs/context/OWNER_AUTHORITY_HANDOFF.md`
4. `docs/context/SOURCE_OF_TRUTH.md`
5. the active governance issue and pull request

The authority model recorded by issue `#1861` was ratified through PR `#1862`
and squash-merged into `main` as verified commit
`30e985226347b4bc59b0e187b96633a09647ca42`, with constitutional tree
`fabb9da1fdb6979df0bc764017752f118088e69f`. It establishes:

- **Benjamin Gerrit Hoff** as founder, architect, creator, project owner, and
  final human authority of HUB_Optimus;
- `@Voxterrae`, immutable GitHub user ID `249308740`, as the repository identity
  used under that authority;
- HUB_Optimus as the foundational tool and technological parent platform through
  which Benjamin Gerrit Hoff develops LCDH-OS and the wider ecosystem.

The former Draft status of PR `#1862` is historical. The ratified authority
records and Founder Authority Guard now exist on protected `main`.

## CODEOWNERS and review policy

`@Voxterrae` is the sole repository-wide CODEOWNER. CODEOWNERS records review
responsibility and owner authority; it does not itself grant legal ownership or
mutate GitHub permissions.

Native CODEOWNER approval is intentionally not configured as a required gate
while the sole CODEOWNER is also the author of owner-created pull requests,
because an author cannot provide the required approval to their own pull request.
Ratified Option A instead requires:

- protected-path pull requests and every commit in them to be owner-authored;
- all commits to be verified;
- non-owner general contributions to receive explicit `@Voxterrae` approval
  bound to the current head;
- comment-only reviews not to revoke an existing approval, while a later
  change-request or dismissal does;
- all required checks and conversations to be complete before merge;
- force-push and deletion protections to remain in place.

## Verified live GitHub protection state

The authenticated consolidation and postflight recorded through issue `#1680`
and its preserved evidence established:

- ruleset `11665521` — `Protect main - owner governed` — as the only active
  repository ruleset applying to `main`;
- legacy ruleset `11637867` as exported and deleted;
- no bypass actors;
- native required approvals `0` and native CODEOWNER review disabled under
  Option A;
- required review-thread resolution;
- squash-only merge;
- required signatures, linear history, deletion protection, and
  non-fast-forward protection;
- strict required checks bound to GitHub Actions `integration_id=15368`:

```text
founder-authority
founder-authority-bootstrap
pytest
PowerShell tooling
guard
Risk classification
lychee
```

GitHub Settings and collaborator permissions remain mutable platform state. This
handoff records verified evidence but does not itself grant or revoke access,
change rulesets, or replace a fresh audit after onboarding or settings changes.

## Technical contributor boundary

Rodrigo / `@itteamrod` and other contributors may receive explicit technical
review or implementation assignments. Such work does not create ownership,
co-ownership, equity, a joint venture, CODEOWNER status, Write entitlement,
merge authority, repository-settings authority, licensing authority, or
independent constitutional modification power.

Technical review is advisory evidence for the owner. Final ratification,
protected merge, deployment, and any rights exception remain explicit human
owner decisions recorded through the governed repository process.

## Founder Authority Guard boundary

The active Founder Authority Guard executes trusted policy from the protected
base and fails closed. For protected changes it checks:

- repository owner login and immutable numeric user ID;
- pull-request author and every commit author/committer identity;
- current and previous filenames, so protected files cannot escape through a
  rename;
- verified commits;
- a real, owner-authored issue labelled `governance` in this repository;
- current-head owner approval for non-owner general contributions;
- when owner-key status becomes `ACTIVE`, a valid owner SSH signature whose
  exact fingerprint is pinned in the owner identity manifest.

The workflow creates the `founder-authority` check directly on the exact pull
request head SHA. Ruleset `11665521` requires both `founder-authority` and
`founder-authority-bootstrap`. A missing, pending, cancelled, skipped, or failed
required check is not approval.

## Operating discipline

- One problem equals one small, reversible pull request.
- No merge, deployment, production mutation, permission change, or ruleset
  change follows from an AI proposal alone.
- Runtime, schemas, benchmarks, infrastructure, customer data, and third-party
  systems remain outside a governance-only change unless separately authorized.
- Preserve evidence and replacement links before closing or deleting superseded
  pull requests or branches.
- Treat claims as unverified until supported by the relevant repository or
  platform evidence.

Issue `#1881` is the current owner-facing reorganization ledger. Its execution
order and safety gates remain controlling for the open pull-request portfolio.

## Historical handoff archive

The previous broad handoff is preserved byte-for-byte at
`docs/context/AI_HANDOFF_HISTORY_PRE_1862.md` using the original blob
`3cc2fa26786f8d0ddaa3b13e081cc7be14996c38`.

That archive is historical evidence, not current authority. It may contain stale
operational states, superseded role descriptions, old branch heads, or claims
that require re-verification. In particular, any passage assigning Rodrigo or
another contributor independent CODEOWNER, Write, merge, governance, ownership,
or modification authority is superseded by the owner-authority records and the
current active issue/PR evidence.

Technical boundaries retained in the archive must be checked against their
linked issue, pull request, current commit, and live platform state before use.
