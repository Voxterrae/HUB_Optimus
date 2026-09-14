# Validation record

## Protected integration candidate - 2026-09-14

Windows, Python 3.14, isolated Admin Gateway environment:

- editable package installation with development dependencies succeeded;
- all 34 product tests passed;
- API identity, tenant and role rejection checks passed;
- the semantic plan hash stays stable from DryRun to intended execution;
- a synthetic valid receipt reaches only the disabled reference executor;
- changed parameters, risk or catalog version change the plan hash;
- invalid mailbox, delegate and reason inputs return JSON-safe HTTP 422.

The tests use synthetic identities and example.invalid addresses. No tenant
adapter, live mailbox, approval service or external administration was called.
The hosted product Python contract and required repository controls must also
pass on the final signed candidate before merge.

The API, operation catalog and OAuth/OpenAPI template exist in this slice.
The allowlisted Exchange PowerShell runbook and its tests are now present.
Power Platform templates, Dataverse schema and a gated source applicator are included in this dependent slice. Tenant deployment remains gated by the security model and
issue #1869; this test record does not certify a production deployment.

The original API proposal recorded 28 local tests and a later 29-test hosted
result. Git history retains those earlier candidate records.

## PowerShell runbook integration - 2026-09-14

Native Windows PowerShell 7.6.6 parsed the runbook/tests and passed synthetic
behavior probes for both offline mutation previews, missing delegate, missing
approval, and mailbox/store diagnostic failures with structured warnings.
All Exchange functions were simulated; no connection or certificate was used.
The Python product suite passed 34 tests in the isolated environment.

The predecessor hosted powershell-contract passed all eight Pester 5 checks before
its protected merge. Local Pester 3.4 is not represented as Pester 5 validation.


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

## Idempotent metadata-applicator contract

The committed applicator is validated without a live write token or private
environment binding. The tests prove that:

- offline review verifies the exact contract and plan hashes; live writes additionally bind protected history and the current checkout;
- inspect mode reports `WOULD_CREATE` and performs no non-GET request;
- apply mode completes a full read-only check-first pass before the first write
  and then uses check-first semantics for every choice, table, column, key and
  relationship;
- every metadata create request carries `MSCRM.SolutionUniqueName` with
  `OptimusAdminGateway`;
- a second authorized run reuses exact metadata and emits no metadata writes;
- drift fails before creating additional components;
- table, column and alternate-key phases include explicit metadata propagation
  barriers, while alternate-key indexes are polled to numeric `Active` status 2;
- customizations publish once only when metadata was actually created;
- apply and rollback authorizations are separate, expiring and commit-bound;
- rollback is additionally bound to one exact journal SHA-256, requires the
  exact solution and applicator commit, refuses any non-allowlisted path, and
  refuses to delete anything when any target table contains a row;
- live private paths are rejected inside the repository;
- journals and templates contain no token or private tenant binding.

GitHub Actions parses every PowerShell asset under `products/admin-gateway`,
rejects dynamic execution, verifies that the wrapper defaults to `Offline`, and
runs the Python applicator tests. CI never supplies `-Apply`, a completed
authorization file, a Dataverse token or a customer environment identity.


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

New regression gates: fresh single-branch clone after squash; hidden working-tree and staged edits; wrong history anchor; ambient Git redirection; stale commit authorization; encoded path traversal; GET and POST redirects. All tests are synthetic and use no tenant account.

## Candidate validation result - 2026-09-14

Windows Python 3.14: all 112 product tests passed, exit code 0. The first run
completed test execution but failed in pytest's cleanup of its temporary
"current" symlinks (WinError 448). The successful repeat used a dedicated test
directory and disabled only pytest's best-effort current-alias helper in the
ephemeral harness. Product tests and Git/HTTP guards were unchanged. Hosted CI
must run its normal unmodified pytest and all eight Pester checks before merge.
The deterministic schema plan, offline applicator and package manifest pass.
One upstream AnyIO alias deprecation warning is recorded; no test was skipped.
