# Validation record

Validation target: Optimus Admin Gateway v0.1.0 product package.

Executed locally:

```text
PYTHONPATH=src pytest -q
10 passed
```

Additional checks:

- JSON syntax: operation catalog, Dataverse schema, tenant-overlay schema and connector definition.
- YAML syntax: OpenAPI and approval-flow blueprint.
- Static PowerShell safety checks: allowlisted `ValidateSet`, DryRun default, no `Invoke-Expression`.
- Public package scan: no pilot mailbox addresses, tenant IDs or client environment URL.

PowerShell runtime behavior is not certified locally because PowerShell 7 is not installed in this execution environment. The GitHub workflow performs a PowerShell parser check on a runner with `pwsh`.
