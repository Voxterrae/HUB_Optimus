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

The Founder Ownership and Authority Charter entered protected main in
`30e985226347b4bc59b0e187b96633a09647ca42`, linked to issue `#1861`.
It remains present at the integration checkpoint
`main@260666ce9cdeb7a1b3daf43ba550da549d98f3ce` and identifies:

- **Benjamin Gerrit Hoff** as founder, architect, creator, project owner, and
  final human authority of HUB_Optimus;
- `@Voxterrae`, immutable GitHub user ID `249308740`, as the repository identity
  used under that authority;
- HUB_Optimus as the foundational tool and technological parent platform through
  which Benjamin Gerrit Hoff develops LCDH-OS and the wider ecosystem.

Presence of the Charter on `main` does not by itself change the
machine-readable ratification state. The current
`config/governance/owner_identity.v1.json` remains
`RATIFICATION_PROPOSED`, hardware-backed owner-key enrollment remains pending,
and PR `#1896` is the separate open proposal to change that record. No operator
may describe the identity record as `RATIFIED` unless the exact protected
change, live required checks, explicit owner record, and applicable
cryptographic gate are all satisfied. Draft PR `#1862` is historical proposal
provenance rather than the current merge gate.

## CODEOWNERS and review policy

`@Voxterrae` is the sole proposed repository-wide CODEOWNER. CODEOWNERS records
review responsibility and owner authority; it does not itself grant legal
ownership or mutate GitHub permissions.

Native CODEOWNER approval must not be configured as a required gate while the
sole CODEOWNER is also the author of owner-created pull requests, because an
author cannot provide the required approval to their own pull request. The
approved policy for this proposal is instead:

- protected-path pull requests and every commit in them must be owner-authored;
- all commits must be verified;
- non-owner general contributions require an explicit `@Voxterrae` approval
  bound to the current head;
- comment-only reviews do not revoke an existing approval, while a later
  change-request or dismissal does;
- all required checks and conversations must be complete before merge;
- force-push and deletion protections remain in place.

Live rulesets and collaborator permissions are repository settings. This draft
changes neither. They require a separate authenticated owner action and fresh
audit evidence.

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

The proposed Founder Authority Guard executes trusted policy from the protected
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

The adapter merged through PR `#1907` at
`5cb923c38e8ec0f45468c29268c79dcc3b06b822` publishes `founder-authority`
on the exact pull-request head and revalidated live test-merge candidate.
A missing, pending, cancelled, or failed check is not approval. The active
ruleset requires both `founder-authority` and `founder-authority-bootstrap`
from GitHub Actions integration `15368`. This records the observed mechanism,
not a dedicated trusted publisher: issue `#1906` remains open for publisher
identity and exact-authorization hardening. PR `#1919` introduced the separate
shadow-only App canary at `dc16281fe91d255939bf017798e5924ab52e0e7c`.
It remains non-required and does not change the required-check source.

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

## Project intelligence surface

Governance issue `#1901` and PR `#1903` define a new repository-intelligence
surface without expanding the executable runtime or changing `/operator/`.
Future operators must treat these artifacts as one synchronized snapshot:

- analysis baseline: `main@30e985226347b4bc59b0e187b96633a09647ca42`,
  tree `fabb9da1fdb6979df0bc764017752f118088e69f`;
- knowledge graph: `obsidian-HUB_Optimus/`;
- structured browser model: `site/obsidian-HUB_Optimus/system.json` plus declared
  fragments;
- static Pages route: `/obsidian-HUB_Optimus/`;
- update contract: `obsidian-HUB_Optimus/98_META/Update Protocol.md`;
- focused validation: `python -m pytest -q
  tests/test_project_intelligence_site.py`;
- public-route validation: `python -m pytest -q
  tests/test_public_site_links_and_contrast.py`;
- JavaScript syntax validation: `node --check
  site/obsidian-HUB_Optimus/app-graph.js` and `node --check
  site/obsidian-HUB_Optimus/app.js`.

The Obsidian notes and browser explorer must remain derived from the same model
and preserve `CONFIRMED`, `INFERRED`, and `UNKNOWN` distinctions. A future
architecture-relevant change requires a model delta, affected-note updates,
web-model synchronization, focused tests, and normal protected review.

Until the exact reviewed PR is merged and the Pages workflow plus served URLs
are inspected, source presence proves neither production publication nor the
live state of `/`, `/operator/`, or `/obsidian-HUB_Optimus/`. Repository state,
Pages deployment state, and externally served bytes remain separate claims.


## Project intelligence v1.1 release channels

Issue #1912 and existing PR #1913 reconcile the graph-search, impact-focus,
zoom/pan, and evidence-bound learning increment with protected main. The stable
route is /obsidian-HUB_Optimus/; /obsidian-HUB_Optimus-v1.1/ is its complete byte
alias. The frozen /obsidian-HUB_Optimus-v1.0/ recovery route preserves verified
historical Git bytes recorded in site/obsidian-release-channels.v1.json.
These retained public release channels are intentional, not disposable duplicates.

The semantic model remains a dated observation of main@30e985226347b4bc59b0e187b96633a09647ca42.
The inventory and delta in this integration describe protected main@c7d08b78d38148ffc6f84b9f2dd8541149d224ff.
They do not claim automatic freshness or certify live external infrastructure.
Regeneration uses tools/project_intelligence/repository_intelligence.py with an
explicit reviewed source commit; synchronize the v1.1 alias after updating stable
assets. Run the Project Intelligence site, v1.1, release-channel, and public-route
tests, then inspect the actual deployment run and served bytes. Browser graph
interaction does not execute the Python simulator or enable URL retrieval.

## EC2 validation-log attestation

The implementation in PR #1857 binds every newly validated production release
state to the complete validation log SHA-256 and its final non-empty result.
Preflight, deployment and rollback reject replaced, truncated or result-divergent
logs using one no-follow regular-file snapshot, canonical UTF-8/LF text and
mode 0600. Explicit legacy schemas retain their documented compatibility.
This code integration does not certify a deployed host or authorize the blocked
operation in #1831; dependency, locking and recovery hardening remain separate.

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
