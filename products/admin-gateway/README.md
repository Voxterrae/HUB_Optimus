# Optimus Admin Gateway

A tenant-neutral, governed administration module for **HUB_Optimus**.

This reference API validates allowlisted Microsoft 365 administration plans for future Copilot Studio, Power Platform and mobile clients. The API, operation catalog and tests are executable locally. The default executor performs DryRun only; live tenant execution remains unconfigured and requires the reviewed follow-up slices.

## Product/client boundary

- The generic gateway, contracts, operation catalog, tests and templates are part of **HUB_Optimus**. Ownership and final authority follow the [Founder Ownership and Authority Charter](../../docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md), which identifies **Benjamin Gerrit Hoff** as the project owner; this module creates no competing ownership record.
- **Client tenants** retain control of their private identities, mailbox addresses, tenant IDs, connection references, approvals, logs and evidence.
- The first pilot tenant is represented only by a private client overlay outside the public product repository.

See `docs/CLIENT_BOUNDARY.md`.

## Safety defaults

- Read-only planning is the default.
- Mutation operations require `dry_run=false`, a matching approved plan receipt and a configured executor.
- Arbitrary command text and arbitrary script paths are rejected.
- Alternate-key identifiers reject characters that are unsafe in Dataverse alternate-key URLs.
- Tenant secrets and certificates are external to the package.
- The reference executor intentionally fails closed until a deployment adapter is configured.

## Quick start

Run from this product directory. The API starts on localhost; production identity
requires the EasyAuth boundary described in `docs/SECURITY.md`.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
python scripts/build-dataverse-schema-plan.py
uvicorn optimus_admin_gateway.main:app --host 127.0.0.1 --port 8766
```

For local tests only:

```bash
export OPTIMUS_DEV_MODE=true
```

## Dataverse schema planning

The public contract and deterministic non-applying plan are:

```text
dataverse/schema/optimus-admin-gateway.dataverse.json
dataverse/schema/optimus-admin-gateway.dataverse.schema.json
dataverse/plans/optimus-admin-gateway.schema-plan.json
```

`python scripts/build-dataverse-schema-plan.py` verifies the committed plan.
`--write` is used only when a reviewed contract change intentionally rebuilds
the plan.

`dataverse/pac/Test-OptimusDataverseSchemaPlan.ps1` performs a private,
read-only environment preflight. It has no Apply switch, creates no tables or
rows, and stores tenant binding evidence outside the public repository.

See `docs/DATAVERSE_SCHEMA.md`.

## Module map

The API, catalog, OpenAPI and PowerShell runbook paths below are present.
Power Platform, Copilot, Dataverse and deployment assets remain in dependent PRs.

- `src/optimus_admin_gateway/` — API, validation and safety controls.
- `config/operations.catalog.json` — allowlisted operation registry.
- `openapi/` — canonical OpenAPI 3 contract.
- `power-platform/custom-connector/` — Swagger 2.0 custom connector template.
- `runbooks/` — PowerShell 7 allowlisted dispatcher and operation scripts.
- `copilot-studio/agents/` — agent instruction templates.
- `dataverse/` — tenant-neutral schema contract, deterministic dry-run plan, sanitized unpacked solution baseline and PAC preflight.
- `power-platform/flows/` — approval-flow blueprint using numeric Dataverse choice values.
- `deployment/` — deployment and tenant-overlay templates.

## Windows PowerShell quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
$env:OPTIMUS_DEV_MODE = "true"
$env:OPTIMUS_EXECUTOR_MODE = "disabled"
.\.venv\Scripts\python.exe -m uvicorn optimus_admin_gateway.main:app --host 127.0.0.1 --port 8766
```

Open http://127.0.0.1:8766/healthz to verify the local service. Development calls
use the explicit local principal and role headers described in the security
model. Keep development mode confined to local tests; the reference executor
still rejects live requests.

## Exchange runbook boundary

The allowlisted PowerShell 7.4+ runbook returns mutation previews without
importing Exchange modules, reading certificates or opening a connection.
Malformed delegate/approval inputs fail before connection. Read-only diagnostic
operations do query Exchange when used outside tests; DryRun prevents mutations
and does not mean that every diagnostic is offline.

The repository tests replace every Exchange command with synthetic responses.
A live runbook invocation is a separate tenant-controlled operation: direct
Automation invocation must not bypass API roles and approval verification.
The API reference executor remains disabled and does not invoke this runbook.


## Dataverse metadata applicator

The repository now includes a source-only, check-first metadata applicator. Its
default mode is offline review and it cannot write metadata unless an operator
supplies all of the following at runtime: an explicit `-Apply` switch, a
mode-specific private authorization valid for no more than four hours, the
exact target environment identity, an access-token file and a durable evidence
directory. Secret, authorization, journal, export and evidence paths are
rejected when they resolve inside the repository.

The applicator preserves the historical review base `4aab546e...` and pins contract
`ad0275c6...` and plan `dd1a4c4d...`. It also requires the private authorization
to name the exact published applicator commit being executed. Every metadata
create request is solution-scoped to `OptimusAdminGateway`; a full read-only
check-first pass must succeed before the first write, missing components are
created in propagation-safe phases, exact matches are reused and conflicting
metadata stops the run. Apply and rollback use distinct authorizations; a
rollback authorization is bound to the SHA-256 of one exact apply journal.

Publishing this source does not apply it. CI performs only offline hash checks,
static safety checks and fake-transport idempotency tests. See
`dataverse/apply/README.md`.


## Protected integration and execution binding - 2026-09-14

The old branch-only base is retained as contract-review provenance. Runtime
binding now requires the protected main anchor fc5e45d35376184609341ec1b1232ca381c89993,
the exact pinned contract and plan, and critical checkout/index content matching
HEAD (canonical LF text on Windows). Git replace refs and ambient Git redirection
cannot change this check. This works from a fresh clone after a protected squash;
it does not permit reuse of an authorization naming another applicator commit.

Bearer requests reject HTTP redirects, including redirects that would rewrite a
POST as a GET. A metadata action still requires its own private, expiring,
environment-specific authorization and exact current commit. Web publication or
merging this package does not authorize an Azure, Exchange or Dataverse operation.
