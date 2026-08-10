# Security model

## Fail-closed rules

1. Unknown operation IDs return `404`.
2. Unknown request properties are rejected.
3. Mutation requests default to `dry_run=true`.
4. Gateway acceptance of a mutation requires a fresh approval receipt bound to the exact plan hash.
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

The only accepted signature profile is `hmac-sha256-lp-v1`. Its HMAC-SHA256
material is binary and has this exact form:

```text
ASCII("HUB_OPTIMUS_APPROVAL_RECEIPT") || 0x00 ||
LP(signature_profile) || LP(approval_id) || LP(plan_hash) ||
LP(approved_by) || LP(approved_at)
```

`LP(value)` is exactly four unsigned big-endian bytes containing the length of
the value's strict UTF-8 byte sequence, followed by those bytes. Lengths count
bytes, not characters or UTF-16 code units. There is no BOM, delimiter, field
count prefix, newline or trailing data: exactly five ordered fields follow the
domain. Values are signed after validation without implicit Unicode
normalization. The 29-byte domain prefix includes its final NUL byte, and
`signature_profile` is itself the first authenticated field.

`approved_at` is the UTC approval-decision time. Receipt JSON must supply an
RFC3339 date-time string with seconds and an explicit `Z` or numeric offset;
numeric epochs and numeric strings are rejected. Before framing, the timestamp
is converted to UTC and emitted with `+00:00`, never `Z`; seconds are always
present, zero fractional seconds are omitted, and a non-zero fraction uses
exactly six digits. Values that cannot be represented after conversion to UTC
are rejected. For example, `2026-08-10T19:00:00.123+02:00` is signed as
`2026-08-10T17:00:00.123000+00:00`.

The configured secret contributes its exact UTF-8 bytes: no trim or Base64
decoding is applied. Startup rejects secrets shorter than 32 UTF-8 bytes or
formed only from whitespace. This length floor does not prove entropy; generate
a random secret dedicated to this purpose in each tenant and environment. The
tenant signer service must construct the binary framing; a Power Automate
expression must not approximate byte lengths with UTF-16 string `length()`.

The receipt carries the lowercase 64-character hexadecimal HMAC. A missing or
unknown profile, malformed signature, or malformed receipt fails schema
validation with `422`. A schema-valid receipt with a cryptographic mismatch
returns the generic `403 APPROVAL_INVALID`. The legacy delimiter-joined format
has no fallback, negotiation or downgrade path.

An external signer can verify its implementation against this synthetic vector:

```text
secret: external-signing-vector-secret-32
signature_profile: hmac-sha256-lp-v1
approval_id: approval-vector-0001
plan_hash: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
approved_by: approver@example.com
approved_at input: 2026-08-10T19:00:00.123+02:00
approved_at signed: 2026-08-10T17:00:00.123000+00:00
field byte lengths: 17,20,64,20,32
material hex: 4855425f4f5054494d55535f415050524f56414c5f524543454950540000000011686d61632d7368613235362d6c702d763100000014617070726f76616c2d766563746f722d30303031000000406161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616161616100000014617070726f766572406578616d706c652e636f6d00000020323032362d30382d31305431373a30303a30302e3132333030302b30303a3030
HMAC: c6196583fde6c8d51e2c9f1539eecc9dc52e45d67067886b4a4a3962f2199598
```

This second vector proves that lengths are UTF-8 bytes rather than characters
or UTF-16 code units:

```text
secret: external-signing-vector-secret-32
signature_profile: hmac-sha256-lp-v1
approval_id: approval-vector-utf8-0001
plan_hash: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
approved_by: approuvé@example.com
approved_at input: 2026-08-10T17:00:00Z
approved_at signed: 2026-08-10T17:00:00+00:00
field byte lengths: 17,25,64,21,25
material hex: 4855425f4f5054494d55535f415050524f56414c5f524543454950540000000011686d61632d7368613235362d6c702d763100000019617070726f76616c2d766563746f722d757466382d30303031000000406262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626262626200000015617070726f7576c3a9406578616d706c652e636f6d00000019323032362d30382d31305431373a30303a30302b30303a3030
HMAC: 52a61cc8461620d8ca86891c7009cc9226c03bc75d1583c6fa4fe09bdeafe5d1
```

The gateway also rejects a receipt whose age exceeds
`OPTIMUS_APPROVAL_MAX_AGE_SECONDS` (900 seconds by default) or whose timestamp
is in the future. The setting must be an integer from 1 to 86400 seconds and
invalid values stop application startup. The exact expiry boundary is
inclusive: a receipt is valid through its configured maximum age and invalid
immediately afterward. Gateway and approval-service clocks must be synchronized.

Freshness limits indefinite reuse, but it is not single-use replay prevention.
A valid receipt can still be presented more than once inside its freshness
window until a durable, atomic receipt-consumption store is added.

The check occurs before gateway dispatch. A queued executor or runbook must
revalidate authority at its own trust boundary; this slice does not claim that
a later-running external job is covered by the earlier freshness decision.
