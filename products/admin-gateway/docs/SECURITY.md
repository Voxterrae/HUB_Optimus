# Security model

## Fail-closed rules

1. Unknown operation IDs return `404`.
2. Unknown request properties are rejected.
3. Mutation requests default to `dry_run=true`.
4. Mutation execution requires an approval receipt bound to the exact plan hash.
5. The reference executor returns `503 EXECUTOR_NOT_CONFIGURED` until a tenant adapter is configured.
6. Arbitrary command text, script text, script paths and module names are not accepted by any API contract.
7. Secrets are referenced externally and never stored in the operation catalog.
8. Production identity is accepted only from the canonical EasyAuth client-principal header and must match the configured Entra tenant.
9. Catalog, planning, read execution and DryRun require `Optimus.Reader`; live mutation additionally requires `Optimus.Mutator`.

## Identity and authorization boundary

Azure App Service EasyAuth is the production authentication boundary. The API
decodes `X-MS-CLIENT-PRINCIPAL`, requires the `aad` provider, uses the immutable
Entra object ID as the subject, compares the mapped tenant claim with
`OPTIMUS_ENTRA_TENANT_ID`, and extracts roles only from the claim type named by
`role_typ`.

`X-MS-CLIENT-PRINCIPAL-ID`, `X-MS-CLIENT-PRINCIPAL-NAME` and
`X-OPTIMUS-ROLES` are not authorization inputs. Local simulation uses only
`X-OPTIMUS-DEV-PRINCIPAL` and `X-OPTIMUS-DEV-ROLES`, and only while
`OPTIMUS_DEV_MODE=true`.

The tenant deployment must configure EasyAuth to require authentication, use a
tenant-specific issuer, restrict allowed token audiences and scopes, and ensure
that clients cannot reach the application while bypassing EasyAuth. Decoding
the injected header is not a substitute for cryptographic token validation. If
that network and platform boundary cannot be guaranteed, the deployment must
validate token signature, issuer and audience in the application instead.

The application roles are additive:

- `Optimus.Reader` permits catalog discovery, planning, read operations and DryRun.
- `Optimus.Mutator` is additionally required for a mutation with `dry_run=false`.
- `Optimus.Mutator` does not silently imply `Optimus.Reader`.

## Recommended tenant controls

- Entra application with least-privilege application roles.
- Certificate-based or supported managed-identity authentication for unattended Exchange administration.
- Azure Key Vault for certificates and secrets.
- Azure Automation PowerShell 7.4 runtime with pinned module versions.
- Dataverse table permissions separating requester, approver and executor.
- Conditional Access and named locations as appropriate to the tenant.
- Private networking or access restrictions for the API where practical.
- Assign the separate `Optimus.Reader` and `Optimus.Mutator` application roles.

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
