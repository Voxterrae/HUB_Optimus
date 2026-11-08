---
applyTo: "products/admin-gateway/**,.github/workflows/optimus-admin-gateway.yml"
---

# Admin Gateway

Read `products/admin-gateway/README.md`,
`products/admin-gateway/docs/SECURITY.md` and the affected contract before editing.
The product workflow is `.github/workflows/optimus-admin-gateway.yml`;
root simulator dependencies and green root CI do not establish complete product
API, authentication or PowerShell coverage.

## Offline validation

Use a separate Python 3.11 environment, matching the product workflow. From
`products/admin-gateway/`, with that environment active:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/build-dataverse-schema-plan.py
python scripts/apply-dataverse-schema.py
python scripts/build-package-manifest.py
```

The dev extra supplies the API/authentication dependencies as well as pytest;
without them, collection deliberately omits some API/authentication modules.
Report missing dependencies or omitted coverage, not a complete product PASS.
The three script invocations above verify committed artifacts without applying
metadata. Do not add `--write` merely to silence stale-artifact failures.
For an intentional reviewed artifact update, the plan builder has `--write`;
the manifest builder reads the Git index and requires product/workflow source
changes to be staged first. Inspect that source delta and the resulting artifact
before staging the manifest; do not stage unrelated work.

PowerShell validation is separate. Use PowerShell 7.4+ (`pwsh`, not Windows
PowerShell 5.1) and Pester 5+. From the repository root in `pwsh`:

```powershell
Import-Module Pester -MinimumVersion 5.0 -ErrorAction Stop
Invoke-Pester -Path products/admin-gateway/runbooks/tests -CI
```

Also run the product workflow's PowerShell parse/executable-AST safety checks
when PowerShell assets change. Pester uses synthetic Exchange responses; it
does not establish a tenant connection or prove a live Exchange operation.
If `pwsh`/Pester is unavailable, state that limit instead of counting Python
static checks as PowerShell execution.

## Preserve the trust boundaries

- Keep allowlisted operations and typed parameters; never accept arbitrary
  command/script text, script paths or module names.
- Keep DryRun as the default and the reference live executor disabled. Planning
  and DryRun require `Optimus.Reader`; live mutation additionally requires
  `Optimus.Mutator`, an exact fresh approval receipt and a configured executor.
  The roles are additive; changing `dry_run` alone grants no permission.
- Preserve canonical EasyAuth tenant/object/role claims. Development headers
  work only with explicit local `OPTIMUS_DEV_MODE=true`; do not use them in a
  deployment or weaken the platform authentication boundary.
- Preserve semantic plan hashing and the signed receipt profile. Receipt
  freshness is not durable single-use replay prevention.
- Mutation previews return before Exchange import/certificate/connection work.
  Read diagnostics can still connect to Exchange: DryRun is not synonymous
  with offline operation.

For Dataverse work, read `products/admin-gateway/dataverse/apply/README.md`.
Default applicator mode is offline; `--inspect`/PAC preflight is live read-only,
not a local test. Apply and rollback are separate owner/tenant-authorized
operations, with exact source/contract/plan/environment binding, expiring private
authorization, pre/post exports and durable journals. Rollback needs a distinct
journal-bound authorization and the zero-row gate; do not auto-rollback an
incomplete journal or delete metadata after business rows exist.

Keep tenant overlays, tokens, certificates, identities, approvals, journals,
exports and operational evidence outside the public repository. Repository
integration, API tests or a package manifest authorize no Azure, Exchange,
Power Platform or Dataverse operation.
