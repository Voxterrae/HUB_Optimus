# Validation record

## Protected integration candidate - 2026-09-14

Windows, Python 3.14, isolated Admin Gateway environment:

- editable package installation with development dependencies succeeded;
- all 33 product tests passed;
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
PowerShell runbooks, Power Platform, Dataverse and deployment assets belong to
later dependent PRs. Tenant deployment remains gated by the security model and
issue #1869; this test record does not certify a production deployment.

The original API proposal recorded 28 local tests and a later 29-test hosted
result. Git history retains those earlier candidate records.
