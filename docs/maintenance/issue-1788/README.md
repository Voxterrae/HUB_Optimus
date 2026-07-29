# Issue #1788 audited maintenance branch retirement

This directory is the durable recovery record for the stale numbered
`chore/maintenance-*` branches audited under issue
[#1788](https://github.com/Voxterrae/HUB_Optimus/issues/1788). Merging these
files does **not** delete a branch. The associated workflow is manual-only and
defaults to a read-only audit.

## Fixed audit

The inventory was refreshed on 2026-07-29 at 18:48:19 UTC from both
`git ls-remote --heads origin` and the GitHub branches API:

- 1,060 remote branches in total;
- 887 branches under `chore/maintenance-*`;
- 884 branches matching `^chore/maintenance-[0-9]+$`;
- 881 exact retirement candidates;
- no candidate marked protected;
- no candidate used as an open pull-request head;
- candidate tip dates from 2026-03-09T13:49:10Z through
  2026-05-11T07:32:39Z, all strictly before the explicit
  2026-05-12T00:00:00Z cutoff.

The counts are an observation, not an execution precondition for unrelated
branch names. At execution time the complete maintenance namespace must still
be exactly the 881 manifest candidates plus these six semantic exclusions:

| Excluded branch | Audited tip |
|---|---|
| `chore/maintenance-19` | `5d7a61840c56671323a9c4f579d6f41d91a16b80` |
| `chore/maintenance-21` | `97b8476749c62b2a2a19645a6fe2b28c70d883a1` |
| `chore/maintenance-25` | `03fcc983f00dcdfaae7fa765dea72ca67e18dd4d` |
| `chore/maintenance-D` | `3198ce3e641ac14a4b1767b4f40b2e9d23d5a421` |
| `chore/maintenance-bot-v2` | `008c3fb78d805b8e35fb721e4659bcb4277b271d` |
| `chore/maintenance-workflow-fix` | `40983c1bd2b4dc5c3f5bc11810b63c79f64e4d28` |

Any missing, added, or moved maintenance ref requires a new audit. A changed
candidate protection state or any open PR with a candidate head also blocks
execution.

## Recovery evidence

`maintenance-branches.manifest.v1.json` records every candidate name, exact tip
SHA, tree SHA, commit time, cutoff result, protection observation, and PR
observation.

`maintenance-branches.bundle` is a standalone Git bundle containing complete
history for all 881 candidate heads under their original
`refs/heads/chore/maintenance-*` names:

- size: 957,017 bytes;
- SHA-256:
  `3d896c256061c2d0435c2acd26a36d24a7895053207a375690cd07d05681b3b3`;
- refs: 881;
- prerequisites: none;
- object hash: SHA-1;
- canonical head-list SHA-256:
  `77d1310f63ee4f38681c370703484ad8747e8df3d8dd87cb81eec72e19137270`.

The canonical head list is serialized in manifest branch-name order as one
`<tip_sha><SPACE>refs/heads/<branch><LF>` record per candidate. Relative to
the manifest's source base commit, the bundle adds 897 historical objects: 861
commits, 34 trees, and two reviewed blobs. The two blobs are an old telemetry
collector and a VS Code settings file; no credential material was found in
that bounded blob review.

A versioned bundle is preferable here to an Actions artifact, which expires,
or a GitHub Release, which would introduce a release tag outside the issue
boundary. Its size is below 1 MB.

Verify and restore it into an empty local bare repository:

```bash
sha256sum docs/maintenance/issue-1788/maintenance-branches.bundle
git bundle list-heads \
  docs/maintenance/issue-1788/maintenance-branches.bundle
git clone --bare \
  docs/maintenance/issue-1788/maintenance-branches.bundle \
  /tmp/hub-optimus-maintenance-recovery.git
git --git-dir=/tmp/hub-optimus-maintenance-recovery.git \
  fsck --full --strict --no-dangling
```

The clone is a local recovery copy only. Recreating remote refs from it is a
separate write operation requiring its own explicit approval.

## Guarded operation

`.github/workflows/retire-maintenance-branches.yml` has only
`workflow_dispatch`; merge, push, PR, and schedule events cannot activate it.
Its `dry-run` choice is the default and retains `contents: read`.

A dry-run:

1. verifies that the manifest and bundle are committed in a clean checkout;
2. restores the bundle into an empty bare repository and runs strict `fsck`;
3. requires dispatch SHA, checkout, input SHA, and live `main` to agree;
4. requires the exact canonical GitHub fetch/push URL and rejects multiple
   push destinations, Git URL rewrites, and Git environment redirects;
5. compares complete REST and Git branch inventories;
6. verifies all 881 exact leases, the six exclusions, branch protection, the
   explicit cutoff, and every open PR;
7. emits the exact execution confirmation without invoking Git
   `receive-pack`.

The `execute` choice has a separately scoped ephemeral `GITHUB_TOKEN` with
`contents: write` and `issues: write`. It additionally requires the exact
confirmation from the dry-run, performs an identical atomic Git push dry-run,
refreshes all guards, then submits one real `git push --atomic` containing 881
deletion refspecs and 881 exact `--force-with-lease` constraints. There is no
batching or non-atomic fallback. If GitHub rejects the atomic request or its
size, the workflow stops.

After the real push, the tool always queries REST and Git again—even when the
transport returned an error, because an acknowledgement can be lost after the
server commits an update. It accepts success only when every candidate is
absent, every pre-existing non-candidate retains its SHA, and no candidate head
appears in the refreshed open-PR inventory. The structured outcome is then
added to issue #1788; a successful outcome includes verified post-counts.

## Limits

- Git ref leases close the ref-movement race, and GitHub enforces protection
  at deletion time. Open-PR state has no transactional Git lease; an open PR
  created in the final interval between the second API check and the atomic
  push is the remaining race. Run during a brief repository ref/PR-head change
  freeze. A concurrent non-candidate ref movement does not come from this
  push, but deliberately makes postflight `inconsistent` and requires review.
- `git push --dry-run` does not execute every server-side hook. The real push
  can still be rejected; the operation deliberately has no fallback.
- A postflight API/network outage after a real push leaves status unknown. Use
  the manifest and bundle to inspect state; do not rerun until the remote
  inventory is known.
- This package does not change runtime, kernel, schemas, benchmarks, website,
  governance, tags, non-maintenance branches, or active PR branches.
