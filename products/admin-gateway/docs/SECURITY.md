# Security model

## Fail-closed rules

1. Unknown operation IDs return `404`.
2. Unknown request properties are rejected.
3. Mutation requests default to `dry_run=true`.
4. Mutation execution requires an approval receipt bound to the exact plan hash.
5. The reference executor returns `503 EXECUTOR_NOT_CONFIGURED` until a tenant adapter is configured.
6. Arbitrary command text, script text, script paths and module names are not accepted by any API contract.
7. Secrets are referenced externally and never stored in the operation catalog.

## Recommended tenant controls

- Entra application with least-privilege application roles.
- Certificate-based or supported managed-identity authentication for unattended Exchange administration.
- Azure Key Vault for certificates and secrets.
- Azure Automation PowerShell 7.4 runtime with pinned module versions.
- Dataverse table permissions separating requester, approver and executor.
- Conditional Access and named locations as appropriate to the tenant.
- Private networking or access restrictions for the API where practical.
- Separate read and mutation application roles.

## Approval binding

The plan hash is computed from canonical JSON containing:

- operation ID;
- validated parameters;
- mutation flag;
- risk level;
- catalog version.

The execution-mode flag `dry_run` is excluded from this semantic plan hash.
The planned read-only planning flow must compute the intended mutation plan
without executing it. The same reviewed plan hash must remain stable when an
approved request later changes `dry_run` from `true` to `false`.

The approval flow must return a signed or otherwise trusted receipt containing
that exact plan hash. Changing an operation, semantic parameter, mutation flag,
risk level or catalog version invalidates the receipt. Changing execution mode
alone grants no authority: execution still requires the matching valid receipt,
an authorized caller and a configured executor. The implementation slice must
prove both a stable planning-to-execution hash and rejection of changed plans
before it can be integrated.
