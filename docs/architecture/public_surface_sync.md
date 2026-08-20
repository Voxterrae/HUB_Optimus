# Public surface and Sites synchronization boundary

Status: foundation contract for review under issue #1888. This document records the operating boundary; it does not by itself authorize merge, GitHub Pages deployment, Sites publication, access changes, tenant mutation, or external transport.

## Purpose

HUB_Optimus needs one truthful product-status boundary between the governed repository and its presentation surfaces. The public portfolio and the protected Sites mirror must show only claims supported by reviewed evidence, while still making important draft work discoverable without describing it as released or deployed.

The canonical authority is:

```text
Voxterrae/HUB_Optimus
```

GitHub Pages and the protected OpenAI Sites project are presentation surfaces. Neither may redefine repository state.

## Reviewed observations

The registry is a dated observation, not a self-referential claim that it already knows the SHA of the commit that will eventually contain it.

Observed and rechecked on 21 August 2026:

- source baseline: `main@30e985226347b4bc59b0e187b96633a09647ca42`;
- public evidence baseline used by document routes: `8426b08e5f88b650c4d79e41d3ce3afd7d42746b`;
- GitHub Pages observation: run `31957372253`, source `30e985226347b4bc59b0e187b96633a09647ca42`, conclusion `success`, observed on 16 August 2026;
- GitHub Pages uploads the static `site/` directory;
- the portfolio in `site/index.html` is manually maintained;
- protected Sites observation: version 8 from `main@b64203fc8c784fd50053872767b179d97f451cc1`, observed on 30 July 2026;
- the protected Sites mirror did not match the source baseline at the time of review.

A successful GitHub Pages run proves that the selected static artifact was deployed. It does not prove that manually maintained portfolio claims include every recent issue or draft pull request.

The fields `source_baseline_sha`, `observed_run_id`, `observed_source_sha`, and `observed_at` deliberately describe evidence already observed. They must not be renamed or presented as the future merged commit, the current run forever, or a post-merge receipt.

## Canonical flow

```text
reviewed repository evidence
        ↓
human-reviewed capability registry
        ↓
validated exact pull-request head
        ↓
owner-signed reconstruction or squash
        ↓
explicit owner merge decision
        ↓
GitHub Pages deployment and receipt
        ↓
separate presentation update, when authorized
        ↓
separate deterministic Sites mirror synchronization
```

Unreviewed issues and pull requests do not enter the public surface automatically. Automation may validate an approved registry, but it must not decide that a draft is released, deployed, production-ready, authorized, endorsed, or safe.

## Capability registry

The v1 registry lives at:

```text
site/data/capability-registry.v1.json
```

Its Draft 2020-12 JSON Schema lives beside it. Each component records:

- a stable component identifier;
- a lifecycle state;
- whether its evidence is merged, a draft pull request, a draft stack, or an open issue;
- the public section in which it may appear;
- whether it is currently listed;
- whether a static public surface exists;
- whether a browser runtime exists;
- whether a production service is deployed;
- production-write and live-external-transport claims;
- exact GitHub evidence;
- a human-readable claim boundary.

The registry is intentionally static and human-reviewed in v1. A future generator may consume it, but no generator may infer product state directly from labels, titles, mergeability, check status, branch names, or chat instructions.

The schema must independently reject invalid cross-field combinations. Repository tests supplement the schema by binding evidence references to their exact commit, pull-request, or issue URL.

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

- **Optimus Admin Gateway** remains the exact draft PR stack #1870–#1873 plus #1875–#1876. Private Sandbox recovery evidence does not authorize production deployment, connector activation, or another tenant mutation.
- **Optimus Evidence Lab** remains draft PR #1879 and an offline package boundary. It is not a production deployment or a public runtime.
- **HUB_Optimus Connect — xAI and X Foundation** remains draft PR #1877 and a disabled provider boundary. It has no credentials, live calls, automatic publication, or partnership claim.
- **Optimus Global Graph** remains issue-only under #1880. It has no implementation, person-level graph, Dataverse mutation, public API, public globe integration, or Sites deployment.

## GitHub Pages boundary

`.github/workflows/pages.yml` triggers when selected site, documentation, brand, or workflow paths change, but it uploads only `site/`.

Consequences:

- a documentation-only merge can redeploy unchanged site bytes;
- a merge that changes `site/data/**` deploys those new public files even when visible HTML is unchanged;
- a successful deployment does not mean the portfolio was regenerated;
- current product status must be changed through a reviewed site/registry change;
- draft branches and pull requests must never deploy to the canonical public domain through this path.

Because this foundation PR changes both `site/**` and `docs/**`, merging it will trigger GitHub Pages. The future owner merge decision must explicitly acknowledge and authorize that deployment consequence. The resulting run must be validated and recorded before the work proceeds. Until that separate decision exists, the PR remains draft and no deployment is authorized.

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

- the registry or schema is not valid Draft 2020-12 JSON Schema;
- a public portfolio component has no registry entry;
- component IDs or evidence records are duplicated;
- evidence type, reference, and URL identity do not agree;
- a draft or issue-only component claims a public browser runtime, production deployment, production writes, or live external transport;
- an in-development component is silently placed under **What exists today**;
- the registry evidence SHA differs from the site document-route evidence SHA;
- the protected Sites observation is described as matching when its recorded source differs from the source baseline;
- an observed pre-merge SHA or run is represented as the future merged SHA or post-merge receipt;
- evidence leaves the canonical GitHub repository;
- private identifiers or secret-like fields enter the registry.

## Update procedure

1. Open or identify the governing issue.
2. Inspect the exact merged, draft, and issue evidence.
3. Update the registry on a dedicated branch.
4. Validate the schema itself and validate the registry against it with format checking.
5. Bind every evidence type, reference, and URL to the same identity.
6. Update public markup only when the desired presentation change is explicitly in scope.
7. Run registry, public-portfolio, link, locale, accessibility-proxy, encoding, and repository tests.
8. Review wording for deployment and authorization overclaim.
9. Reconstruct the exact approved tree through the verified owner-signing boundary.
10. Merge only after the owner decision explicitly covers the Pages side effect.
11. Confirm the GitHub Pages artifact, source SHA, run, and public files.
12. Synchronize Sites separately from the exact merged tree.
13. Record provenance and QA without overwriting historical evidence.

## Rollback

Before merge, close the draft pull request or delete its branch. No public rollback is required because no canonical deployment occurred.

After a canonical merge, revert the exact site/registry commit through a reviewed pull request and let GitHub Pages deploy the reverted `site/` tree. The protected Sites mirror must then be resynchronized as a new retained version; historical versions and receipts must not be rewritten.

## Foundation-slice limitation

The first PR under #1888 adds the registry, schema, documentation, and validation only. It does not modify `site/index.html`, translations, styles, JavaScript, the Pages workflow, the protected Sites project, or any runtime. The visible portfolio remains unchanged until a separate reviewed presentation slice consumes the registry.

The registry and schema are nevertheless public files under `site/data/` after an authorized merge. That non-visible deployment is an explicit effect, not an implication that the presentation update or Sites synchronization has already occurred.
