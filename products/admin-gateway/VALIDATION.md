# Validation record

Validation target: Optimus Admin Gateway v0.1.0 product package.

Executed locally:

```text
PYTHONPATH=src pytest -q
15 passed
```

Additional checks:

- JSON syntax: operation catalog, Dataverse schema, tenant-overlay schema and connector definition.
- YAML syntax: OpenAPI, agent templates and approval-flow blueprint.
- Static PowerShell safety checks: allowlisted `ValidateSet`, DryRun default, no `Invoke-Expression`.
- PAC bootstrap safety: no dynamic scriptblock construction; fixed `pac` executable and reviewed argument arrays only.
- Dataverse/flow contract: approval blueprint targets `opt_adminrequest` and `opt_state`.
- Public package scan: no pilot mailbox addresses, tenant IDs or client environment URL.
- Repository-wide CI compatibility: static safety tests remain discoverable with the root dependency set, while API/catalog tests run only where product-local FastAPI/Pydantic dependencies are installed by the dedicated module workflow.
- GitHub Actions supply-chain guard: every external action is pinned to the repository-reviewed immutable commit and labeled with the reviewed release.

PowerShell runtime behavior is not certified locally because PowerShell 7 is not installed in this execution environment. The GitHub workflow performs a PowerShell parser check on a runner with `pwsh`.
