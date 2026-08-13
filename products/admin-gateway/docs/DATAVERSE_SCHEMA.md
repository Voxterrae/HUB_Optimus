# Dataverse schema plan

## Boundary

This document defines the tenant-neutral Dataverse metadata contract for the
Optimus Admin Gateway. It does not authorize metadata creation. The reviewed
plan is non-applying and contains no tenant, environment, organization, user or
mailbox identifiers.

The private deployment process must bind this contract to an explicitly
approved non-production environment and must fail closed if the solution,
publisher, prefix, version or current component count differs from the approved
preflight.

## Canonical solution identity

```text
Publisher unique name:  HUB_Optimus
Customization prefix:   opt
Choice value prefix:    88483
Solution unique name:   OptimusAdminGateway
Solution version:       0.1.0.0
Source package type:    Unmanaged
Base language:          English / 1033
```

## Design decisions

- Tables and columns are created environment-first through reviewed metadata
  APIs and are then exported and unpacked. New metadata is never authored by
  hand in solution XML.
- Every custom name uses the verified `opt` publisher prefix.
- Regular string columns use `Key` rather than an `Id` suffix. Dataverse creates
  identifier and navigation names for lookups; avoiding `Id` suffixes prevents
  future collisions.
- Alternate-key values are limited to `A-Z`, `a-z`, digits, `.`, `_` and `-`.
  Characters that are problematic in alternate-key URLs are rejected before
  persistence.
- All custom date-time columns explicitly use `UserLocal` with
  `DateAndTime`. Dataverse stores these timestamps as UTC and renders them for
  the current user.
- Global choice values are explicit and publisher-scoped. Labels are never used
  as executable filters.
- Audit is enabled at table level and on critical scalar state fields. Large
  JSON payload columns are not duplicated into platform audit history.
- Change tracking is enabled for controlled downstream synchronization.
- All parent-child delete behavior is `Restrict`; every other cascade behavior
  is `NoCascade`.
- Retention is tenant-configured. Version 0.1 does not silently delete
  administration records or metadata.

## Global choices

| Choice | Values |
| --- | --- |
| `opt_adminrisk` | Low `884830000`, Medium `884830001`, High `884830002` |
| `opt_adminrequeststate` | Requested `884831000` through Cancelled `884831010` |
| `opt_adminapprovaldecision` | Approved `884832000`, Rejected `884832001` |
| `opt_adminjobstate` | Queued `884833000` through Cancelled `884833004` |

## Tables

### `opt_adminrequest`

User-owned request record containing the exact operation key, normalized
parameters, deterministic plan digest, idempotency key, requester identity,
catalog version, risk and approval/execution state.

The normalized parameter JSON is capped at 131,072 characters. It may contain
tenant-private operational parameters, but never tokens, passwords,
certificate private keys or unredacted mailbox content.

### `opt_adminapproval`

User-owned, append-only approval or rejection record bound to one request and
one exact plan digest. The receipt JSON is capped at 32,768 characters.

### `opt_adminjob`

Organization-owned executor job state. Only a sanitized output summary is
stored in Dataverse; full runbook evidence remains in the private evidence
store. The summary is capped at 131,072 characters.

### `opt_adminevent`

Organization-owned, append-only audit event with an event key, correlation key,
actor key, timestamp, sanitized payload and SHA-256 payload digest. The payload
is capped at 65,536 characters.

## Relationships

```text
Admin Request 1 ── * Admin Approval   required; delete Restrict
Admin Request 1 ── * Admin Job        required; delete Restrict
Admin Request 1 ── * Admin Event      optional; delete Restrict
Admin Job     1 ── * Admin Event      optional; delete Restrict
```

Assign, merge, reparent, share and unshare do not cascade.

## Deterministic dry-run

`python scripts/build-dataverse-schema-plan.py` verifies that the committed plan
matches the contract. `--write` is reserved for reviewed source changes.

The plan contains 60 non-executable actions:

```text
1  target solution/publisher verification
4  global choices
4  tables with primary name columns
41 scalar columns
4  alternate keys
4  restrictive relationships
1  publish step
1  post-check and unmanaged export step
```

The plan records what an authorized apply phase would do, but:

```text
apply = false
tables created = 0
rows created = 0
merge = false
deployment = false
```

`dataverse/pac/Test-OptimusDataverseSchemaPlan.ps1` performs a private,
read-only target preflight with PAC. It calls only `pac env who` and
`pac env fetch`, verifies the solution baseline and current component count,
and stores the environment binding outside the repository.

## Future apply gate

A later apply operation requires a separate explicit authorization tied to:

- the exact Git commit and contract hash;
- the exact dry-run plan hash;
- the exact environment URL and environment ID;
- the expected current solution component count;
- a tested check-first implementation;
- export evidence before and after mutation;
- a rollback decision recorded before the first metadata write.

Before any business row exists, a failed non-production metadata transaction
may remove only the newly created components in reverse order after exporting
evidence. After business data exists, automatic metadata deletion is
prohibited; recovery uses a reviewed solution upgrade/data migration or an
environment backup and restore.

## Prepared idempotent applicator

The apply implementation is now present as reviewed source but remains
unexecuted. `scripts/apply-dataverse-schema.py` provides four modes:

```text
offline review  public hash and contract verification only
inspect         live read-only comparison; missing metadata => WOULD_CREATE
apply           separately authorized metadata creation
rollback        zero-row, journal-bound reverse-order recovery only
```

The PowerShell entry point is
`dataverse/pac/Invoke-OptimusDataverseSchemaApply.ps1`. Apply requires a private
apply authorization derived from `dataverse/apply/authorization.template.json`,
an exact environment URL and ID, a token file, a pre-apply unmanaged export and
an explicit evidence directory. Authorization is mode-specific, has a unique
ID, expires no more than four hours after approval, and binds the base commit,
contract hash, plan hash, published applicator commit and current
solution-component count. All private files and evidence must remain outside
the repository.

The check-first implementation first scans the complete declared model with
writes disabled, rechecks the target boundary, then performs the reviewed
phases in order with propagation barriers after tables, scalar columns and
alternate keys. Each created metadata ID is journaled immediately. Exact
existing metadata is reused; any partial or conflicting definition fails
closed. All component creates use the `MSCRM.SolutionUniqueName` header.
Metadata-cache and throttling responses use bounded retries; alternate-key
indexes are polled until numeric `Active` status 2. A no-change rerun does not
republish customizations.

Rollback uses the separate
`dataverse/apply/rollback-authorization.template.json`. It requires the exact
apply-journal SHA-256, target solution, environment and applicator commit,
exports before and after recovery, verifies all target tables have zero rows,
deletes only allowlisted journal entries in reverse phase order and publishes
once after deletion.

No apply command is invoked by CI or by the PR publication step. The first live
metadata write still requires a separate authorization tied to the then-current
applicator commit and private target evidence.


## Effective solution membership for table subcomponents

Dataverse can represent a table as a root solution component with
`RootComponentBehavior = 0` (`Include Subcomponents`). In that state, a column,
alternate key, relationship, or relationship-created lookup can be part of the
exported solution through the table root even when no direct child
`solutioncomponent` row exists.

The applicator therefore accepts either:

1. a direct solution-component record for the exact metadata ID and component
   type; or
2. exact metadata that belongs to a contract table whose table root is in
   `OptimusAdminGateway` with `RootComponentBehavior = 0`.

The second path is fail-closed: table roots with behavior `1` (`Do not include
subcomponents`), behavior `2` (`Include as shell only`), missing table roots,
wrong parent tables, or metadata drift remain fatal. Every accepted path is
written to the evidence journal as `DIRECT_SOLUTION_COMPONENT` or
`INCLUDED_VIA_TABLE_ROOT`.

Rollback remains journal-bound and reverse ordered. Child columns, keys, and
relationships recorded by a completed apply are deleted before their table
roots. A partial apply journal containing only table roots may be recovered by
deleting those roots, but the private rollback procedure must verify zero rows,
absence of all effective subcomponents, a zero final solution-component count,
and pre/post rollback exports.
