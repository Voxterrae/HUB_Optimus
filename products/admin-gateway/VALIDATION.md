# Validation record

Validation target: reconciled Optimus Admin Gateway v0.1.0 product package.

The product workflow is the authoritative repeatable gate:

```text
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/build-package-manifest.py
Invoke-Pester -Path products/admin-gateway/runbooks/tests -CI
```

The contracts cover:

- JSON syntax and structure for the operation catalog, Dataverse schema, tenant overlay and connector templates.
- YAML syntax for OpenAPI, Copilot Studio templates and the approval-flow blueprint.
- Strict EasyAuth principal parsing, synthetic tenant binding and legacy-header rejection.
- Version-aware enforcement of Starlette's TestClient deprecation warning.
- Independent `Optimus.Reader` and `Optimus.Mutator` gates before the approval gate.
- Tenant-specific connector endpoints; `/common` is forbidden for the production template.
- EasyAuth parameters that require authentication, return `401` and bind allowed audiences.
- Static PowerShell safety: reviewed `ValidateSet`, DryRun default and no dynamic execution.
- Pester runbook contracts on PowerShell 7 in GitHub Actions.
- Public-boundary scans for tenant identifiers, client addresses, secrets and environment URLs.
- Deterministic package coverage, byte sizes and SHA-256 hashes for every tracked asset.

No live Microsoft tenant, Dataverse environment, mailbox, Azure resource or approval was changed or certified by these repository tests. Deployment remains gated on tenant-side EasyAuth, audience, role, network-boundary and executor verification.
