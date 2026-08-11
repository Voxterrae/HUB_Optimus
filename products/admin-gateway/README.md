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
- Alternate-key identifiers reject characters that are unsafe in Dataverse alternate-key URLs.
- Tenant secrets and certificates are external to the package.
- The reference executor intentionally fails closed until a deployment adapter is configured.

## Quick start

The commands below apply to a complete Admin Gateway package checkout. The
foundation slice establishes only the product and tenant boundary; executable
API, runbook and deployment assets arrive in the focused follow-up slices.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
python scripts/build-dataverse-schema-plan.py
uvicorn optimus_admin_gateway.main:app --reload
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

- `src/optimus_admin_gateway/` — API, validation and safety controls.
- `config/operations.catalog.json` — allowlisted operation registry.
- `openapi/` — canonical OpenAPI 3 contract.
- `power-platform/custom-connector/` — Swagger 2.0 custom connector template.
- `runbooks/` — PowerShell 7 allowlisted dispatcher and operation scripts.
- `copilot-studio/agents/` — agent instruction templates.
- `dataverse/` — tenant-neutral schema contract, deterministic dry-run plan, sanitized unpacked solution baseline and PAC preflight.
- `power-platform/flows/` — approval-flow blueprint using numeric Dataverse choice values.
- `deployment/` — deployment and tenant-overlay templates.
