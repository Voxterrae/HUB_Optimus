# Optimus Admin Gateway

A tenant-neutral, governed administration module for **HUB_Optimus**.

The product provides allowlisted Microsoft 365 administration operations to Copilot Studio, Power Platform and mobile clients without exposing an unrestricted PowerShell shell.

## Product/client boundary

- **HUB_Optimus** owns the generic gateway, contracts, operation catalog, tests and deployable templates.
- **Client tenants** own identities, mailbox addresses, tenant IDs, connection references, approvals, logs and evidence.
- The first pilot tenant is represented only by a private client overlay outside the public product repository.

See `docs/CLIENT_BOUNDARY.md`.

## Safety defaults

- Read-only planning is the default.
- Mutation operations require `dry_run=false`, a matching approved plan receipt and a configured executor.
- Arbitrary command text and arbitrary script paths are rejected.
- Tenant secrets and certificates are external to the package.
- The reference executor intentionally fails closed until a deployment adapter is configured.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
uvicorn optimus_admin_gateway.main:app --reload
```

For local tests only:

```bash
export OPTIMUS_DEV_MODE=true
```

## Module map

- `src/optimus_admin_gateway/` — API, validation and safety controls.
- `config/operations.catalog.json` — allowlisted operation registry.
- `openapi/` — canonical OpenAPI 3 contract.
- `power-platform/custom-connector/` — Swagger 2.0 custom connector template.
- `runbooks/` — PowerShell 7 allowlisted dispatcher and operation scripts.
- `copilot-studio/agents/` — agent instruction templates.
- `dataverse/` — tenant-neutral data model and PAC bootstrap.
- `power-platform/flows/` — approval-flow blueprint.
- `deployment/` — deployment and tenant-overlay templates.
