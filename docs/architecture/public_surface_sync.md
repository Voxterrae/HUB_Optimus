# Public surface and Sites synchronization boundary

Status: foundation contract for review under issue #1888. This document does not authorize merge, deployment, publication, access changes, tenant mutation, or external transport.

## Purpose

HUB_Optimus needs one truthful product-status boundary between the governed repository and its presentation surfaces. The public portfolio and the protected Sites mirror must show only claims supported by reviewed evidence, while still making important draft work discoverable without describing it as released or deployed.

The canonical authority is:

```text
Voxterrae/HUB_Optimus
```

GitHub Pages and the protected OpenAI Sites project are presentation surfaces. Neither may redefine repository state.

## Verified baseline on 2026-08-16

- reviewed `main`: `30e985226347b4bc59b0e187b96633a09647ca42`;
- public evidence baseline used by document routes: `8426b08e5f88b650c4d79e41d3ce3afd7d42746b`;
- latest verified GitHub Pages run: `31957372253`, conclusion `success`;
- GitHub Pages uploads the static `site/` directory;
- the portfolio in `site/index.html` is manually maintained;
- the last verified protected Sites mirror is version 8 from `main@b64203fc8c784fd50053872767b179d97f451cc1`;
- the Sites mirror is therefore not current with the reviewed `main` baseline.

A successful GitHub Pages run proves that the selected static artifact was deployed. It does not prove that manually maintained portfolio claims include every recent issue or draft pull request.

## Canonical flow

```text
reviewed repository evidence
        ↓
human-reviewed capability registry
        ↓
validated static portfolio
        ↓
merged canonical site tree
        ↓
GitHub Pages deployment
        ↓
separate deterministic Sites mirror synchronization
```

Unreviewed issues and pull requests do not enter the public surface automatically. Automation may validate an approved registry, but it must not decide that a draft is released, deployed, production-ready, authorized, endorsed, or safe.

## Capability registry

The v1 registry lives at:

```text
site/data/capability-registry.v1.json
```

Its schema lives beside it. Each component records:

- a stable component identifier;
- a lifecycle state;
- whether its evidence is merged, a draft pull request, a draft stack, or an open issue;
- the public section in which it may appear;
- whether a public artifact or public runtime exists;
- whether production is deployed;
- production-write and live-external-transport claims;
- exact GitHub evidence;
- a human-readable claim boundary.

The registry is intentionally static and human-reviewed in v1. A future generator may consume it, but no generator may infer product state directly from labels, titles, mergeability, check status, branch names, or chat instructions.

## Presentation rules

### What exists today

A component may appear under **What exists today** only when:

1. its source status is `merged`;
2. it has an exact evidence path;
3. its visible wording matches the recorded lifecycle and execution fields;
4. any deployment limitation is visible rather than implied away.

A merged repository prototype may be public without being a production runtime. Those are separate claims.

### In development

Draft pull requests, draft stacks, and issue-only foundations may appear only under a visibly separate **In development** surface. They must not use language such as:

- live;
- released;
- production-ready;
- deployed;
- connected;
- enabled;
- partner or endorsed;
- automatically publishing;
- operating on real tenant or customer data;

unless a separate reviewed record proves that exact statement.

### Hidden or restricted work

Private identifiers, protected URLs, tenant details, credentials, certificates, customer information, private evidence, unpublished source snapshots, authorization receipts, and operational logs do not belong in the public registry or site.

## Current truthful treatment of recent work

- **Optimus Admin Gateway** remains a draft PR stack. Private Sandbox recovery evidence does not authorize production deployment, connector activation, or another tenant mutation.
- **Optimus Evidence Lab** remains a draft offline package. It is not a production deployment or a public runtime.
- **HUB_Optimus Connect — xAI and X Foundation** remains a disabled draft boundary. It has no credentials, live calls, automatic publication, or partnership claim.
- **Optimus Global Graph** remains issue-only under #1880. It has no implementation, person-level graph, Dataverse mutation, public API, public globe integration, or Sites deployment.

## GitHub Pages boundary

`.github/workflows/pages.yml` currently triggers when selected site, documentation, brand, or workflow paths change, but it uploads only `site/`.

Consequences:

- a documentation-only merge can redeploy unchanged site bytes;
- a successful deployment does not mean the portfolio was regenerated;
- current product status must be changed through a reviewed site/registry change;
- draft branches and pull requests must never deploy to the canonical public domain through this path.

## Protected Sites mirror boundary

The Sites project is a mirror and prototyping surface, not the canonical product repository. Synchronization must occur only after the relevant canonical site change is reviewed and merged.

A synchronization receipt must record:

- canonical repository;
- exact merged commit;
- exact `site/` tree;
- complete path and content-hash inventory;
- build and lint results;
- routing and provenance tests;
- saved Sites version;
- access level;
- visual QA actually performed;
- limitations not exercised by the available browser.

Saving a Sites version does not authorize public access. Widening access or publishing a different Sites endpoint requires a separate owner decision.

## Required checks

Repository checks for this boundary must fail when:

- a public portfolio component has no registry entry;
- component IDs or evidence records are duplicated;
- a draft or issue-only component claims a released artifact, public runtime, production deployment, production writes, or live external transport;
- an in-development component is silently placed under **What exists today**;
- the registry evidence SHA differs from the site document-route evidence SHA;
- the protected Sites mirror is described as current when its recorded source differs from reviewed `main`;
- evidence leaves the canonical GitHub repository;
- private identifiers or secret-like fields enter the registry.

## Update procedure

1. Open or identify the governing issue.
2. Inspect the exact merged, draft, and issue evidence.
3. Update the registry on a dedicated branch.
4. Update public markup only when the desired presentation change is explicitly in scope.
5. Run registry, public-portfolio, link, locale, accessibility-proxy, encoding, and repository tests.
6. Review wording for deployment and authorization overclaim.
7. Merge only through the protected owner/human boundary.
8. Confirm the GitHub Pages artifact and source SHA.
9. Synchronize Sites separately from the exact merged tree.
10. Record provenance and QA without overwriting historical evidence.

## Rollback

Before merge, close the draft pull request or delete its branch. No public rollback is required because no canonical deployment occurred.

After a canonical merge, revert the exact site/registry commit through a reviewed pull request and let GitHub Pages deploy the reverted `site/` tree. The protected Sites mirror must then be resynchronized as a new retained version; historical versions and receipts must not be rewritten.

## Foundation-slice limitation

The first PR under #1888 adds the registry, schema, documentation, and validation only. It deliberately does not modify `site/index.html`, translations, styles, JavaScript, the Pages workflow, the protected Sites project, or any runtime. The visible portfolio remains unchanged until a separate reviewed presentation slice consumes the registry.
