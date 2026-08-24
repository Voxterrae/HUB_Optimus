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
- dry-run value;
- catalog version.

The approval flow must return a signed or otherwise trusted receipt containing
that exact plan hash. A changed parameter produces a different hash and makes
the old approval unusable.
