# Dataverse schema applicator

This directory documents the separately gated metadata-apply mechanism for
`OptimusAdminGateway`. The committed applicator is **source only**: CI parses
and tests it but never supplies an authorization file, a Dataverse token, an
environment identity or the `-Apply` switch.

## Immutable source binding

```text
Authorized base commit: 4aab546e503e7bb2fda253eb0b20741b25b13a47
Contract SHA-256:       ad0275c652f8877c2fc091dcdf66c8ab5fea6db3b2d4b64e847e17716c549d1d
Plan SHA-256:           dd1a4c4d2ab24f224172bb8f87f6c89d89f09e86ea36cc3886e8551d12751a06
Solution:               OptimusAdminGateway
Initial components:     0
```

The private authorization also binds `applicatorCommit` to the exact published
commit being executed, carries a unique authorization GUID, and expires no more
than four hours after approval. Any mismatch fails before the first metadata
write. Completed authorizations, tokens, journals, exports and evidence are
rejected when their paths resolve inside the repository.

## Modes

`Invoke-OptimusDataverseSchemaApply.ps1` has four explicit modes:

1. **Offline review** — default; verifies only the public contract and hashes.
2. **Inspect** — executes the existing PAC read-only target preflight and then
   compares live metadata with the public contract. Missing components are
   reported as `WOULD_CREATE`; no metadata is written.
3. **Apply** — requires `-Apply`, an expiring private authorization file, the
   exact environment URL and ID, an access-token file, a pre-apply export and
   an empty target solution. Every create request carries
   `MSCRM.SolutionUniqueName: OptimusAdminGateway`.
4. **Rollback** — requires a distinct `ROLLBACK_METADATA` authorization bound
   to the exact apply-journal SHA-256, environment, solution and applicator
   commit. It verifies that all four target tables contain zero rows, exports
   before recovery, deletes only allowlisted components recorded as created by
   that run in reverse order, publishes once, and exports again.

Create apply authorization from `authorization.template.json` and rollback
authorization from `rollback-authorization.template.json`. Never commit a
completed authorization, access token, export, environment identity, user
identity, journal or evidence directory.

## Check-first and phase ordering

The Python applicator first queries the complete declared model with writes
disabled, then rechecks the solution/component boundary immediately before
mutation. An exact match is reused; a partial or conflicting match fails
closed. The reviewed phase order is:

```text
verify target solution and component count
create or reuse global choices
create or reuse tables and primary names
wait for metadata propagation
create or reuse scalar columns
wait for metadata propagation
create or reuse alternate keys and poll indexes to Active
wait for metadata propagation
create or reuse restrictive relationships/lookups
publish once
export and verify the unmanaged solution
```

Transient Dataverse metadata-cache and service-throttling responses are retried
with bounded backoff. The journal is written after every successful create so
a later recovery decision is based on actual metadata IDs, not assumptions.

## Rollback boundary

Before any business row exists, a separately authorized rollback may remove
only components created by the recorded run. Once any target table contains a
row, automatic metadata deletion is prohibited. Recovery then requires an
environment backup/restore or a reviewed solution upgrade and data migration.
