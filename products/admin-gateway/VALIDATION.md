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
Power Platform, Dataverse and deployment assets belong to later dependent PRs. Tenant deployment remains gated by the security model and
issue #1869; this test record does not certify a production deployment.

The original API proposal recorded 28 local tests and a later 29-test hosted
result. Git history retains those earlier candidate records.

## PowerShell runbook integration - 2026-09-14

Native Windows PowerShell 7.6.6 parsed the runbook/tests and passed synthetic
behavior probes for both offline mutation previews, missing delegate, missing
approval, and mailbox/store diagnostic failures with structured warnings.
All Exchange functions were simulated; no connection or certificate was used.
The Python product suite passed 34 tests in the isolated environment.

The hosted powershell-contract must execute all eight Pester 5 checks before
merge. Local Pester 3.4 is not represented as Pester 5 validation.
