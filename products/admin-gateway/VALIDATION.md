# Validation record

Validation target: reconciled Optimus Admin Gateway v0.1.0 product package.

The product workflow is the authoritative repeatable gate:

```text
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/build-dataverse-schema-plan.py
python scripts/build-package-manifest.py
Invoke-Pester -Path products/admin-gateway/runbooks/tests -CI
```

The contracts cover:

- JSON syntax and structure for the operation catalog, Dataverse schema, Dataverse meta-schema, deterministic schema plan, tenant overlay and connector templates.
- YAML syntax for OpenAPI, Copilot Studio templates and the approval-flow blueprint.
- Strict EasyAuth principal parsing, synthetic tenant binding and legacy-header rejection.
- Version-aware enforcement of Starlette's TestClient deprecation warning.
- Independent `Optimus.Reader` and `Optimus.Mutator` gates before the approval gate.
- Tenant-specific connector endpoints; `/common` is forbidden for the production template.
- EasyAuth parameters that require authentication, return `401` and bind allowed audiences.
- Alternate-key-safe identifiers across the API, OpenAPI contract and custom connector.
- Static PowerShell safety: reviewed `ValidateSet`, DryRun default and no dynamic execution.
- Read-only Dataverse schema preflight with no Apply surface and only `pac env who` / `pac env fetch`.
- Pester runbook contracts on PowerShell 7 in GitHub Actions.
- Public-boundary scans for tenant identifiers, client addresses, secrets and environment URLs.
- Sanitized unpacked Dataverse baseline checks bind `OptimusAdminGateway` v0.1.0.0 to publisher `HUB_Optimus`, prefix `opt` and choice prefix `88483`.
- Baseline checks prove zero root components, zero missing dependencies and no committed binary export.
- Schema checks bind four global choices, four tables, 41 scalar columns, four alternate keys and four restrictive relationships to explicit values and limits.
- All custom timestamps explicitly use `UserLocal` / `DateAndTime`; all relationship deletes are `Restrict` and other cascade actions are `NoCascade`.
- Large JSON columns are bounded, marked sensitive and excluded from duplicate platform audit history.
- The deterministic schema plan is non-applying, hash-bound and contains no executable mutation commands or private environment binding.
- Approval-flow filters and decisions use explicit numeric Dataverse choice values rather than labels.
- Deterministic package coverage, byte sizes and SHA-256 hashes for every tracked asset.

Repository tests do not perform or certify live tenant changes. A private non-production client-zero sandbox was used by the owner to create and export the empty solution baseline and may be used for a read-only schema preflight; tenant IDs, environment URLs, identities, private dry-run output and the binary export remain outside the public repository.

No table, column, choice, alternate key, relationship or row is created by the committed dry-run plan. Metadata application remains gated on a separate explicit authorization tied to the exact Git commit, contract hash, plan hash, target environment and expected current component count.
