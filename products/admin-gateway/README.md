# Optimus Admin Gateway

A tenant-neutral, governed administration module for **HUB_Optimus**.

This foundation documents a planned product for allowlisted Microsoft 365 administration through Copilot Studio, Power Platform and mobile clients, without an unrestricted PowerShell shell. This checkout contains documentation only; executable capabilities require the reviewed follow-up slices.

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

The commands below apply to a complete Admin Gateway package checkout. The
foundation slice establishes only the product and tenant boundary; executable
API, runbook and deployment assets arrive in the focused follow-up slices.

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

The following layout describes the complete package planned across the focused follow-up slices. These implementation paths are not present in this foundation-only checkout.

- `src/optimus_admin_gateway/` — API, validation and safety controls.
- `config/operations.catalog.json` — allowlisted operation registry.
- `openapi/` — canonical OpenAPI 3 contract.
- `power-platform/custom-connector/` — Swagger 2.0 custom connector template.
- `runbooks/` — PowerShell 7 allowlisted dispatcher and operation scripts.
- `copilot-studio/agents/` — agent instruction templates.
- `dataverse/` — tenant-neutral data model and PAC bootstrap.
- `power-platform/flows/` — approval-flow blueprint.
- `deployment/` — deployment and tenant-overlay templates.
