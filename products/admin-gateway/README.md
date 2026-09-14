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
uvicorn optimus_admin_gateway.main:app --host 127.0.0.1 --port 8766
```

For local tests only:

```bash
export OPTIMUS_DEV_MODE=true
```

## Module map

The API, catalog and OpenAPI paths below are present. PowerShell, Power Platform,
Copilot, Dataverse and deployment assets remain planned in dependent PRs.

- `src/optimus_admin_gateway/` — API, validation and safety controls.
- `config/operations.catalog.json` — allowlisted operation registry.
- `openapi/` — canonical OpenAPI 3 contract.
- `power-platform/custom-connector/` — Swagger 2.0 custom connector template.
- `runbooks/` — PowerShell 7 allowlisted dispatcher and operation scripts.
- `copilot-studio/agents/` — agent instruction templates.
- `dataverse/` — tenant-neutral data model and PAC bootstrap.
- `power-platform/flows/` — approval-flow blueprint.
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
