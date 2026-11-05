---
applyTo: "ops/aws/operator-url-intake/**,.github/workflows/operator-url-intake-validation.yml,.github/workflows/operator-private-canary.yml,.github/workflows/operator-private-canary-stop.yml"
---

# AWS Operator URL-intake candidate

Read `ops/aws/operator-url-intake/README.md`,
`ops/aws/operator-url-intake/CANDIDATE_STATUS.md`,
`ops/aws/operator-url-intake/PRIVATE_SMOKE_RUNBOOK.md` and the applicable
source/workflow. This is a disabled,
invitation-only infrastructure candidate, not a deployed service or general
public URL-intake capability. Historical run counts are not current validation.

## Local candidate validation

Use Node.js 22, matching `.github/workflows/operator-url-intake-validation.yml`.
From `ops/aws/operator-url-intake/`:

```bash
set -euo pipefail
npm ci
npm run check
for phase in foundation controls private; do
  npm run cdk -- synth hub-optimus-operator-infra \
    --output "cdk.out.${phase}" \
    -c "deploymentPhase=${phase}" \
    -c publicSignupEnabled=false \
    -c identityProviderDecision=cognito-temporary-canary \
    -c gitCommit=0000000000000000000000000000000000000000 \
    -c repoName=Voxterrae/HUB_Optimus \
    -c branchName=main \
    -c environmentName=private-canary
done
npm run verify:cdk-assets -- cdk.out.foundation cdk.out.controls cdk.out.private
```

The all-zero SHA is the workflow's synthetic structure-validation marker only;
it is never deployment provenance. These checks compile TypeScript, run the
package test runner, verify the committed Lambda bundle in memory and inspect
three locally synthesized assemblies. They do not deploy, activate identity or
prove a live AWS/browser result. `npm run check` must not be replaced by only
`npm test`: it also verifies the reviewed bundle and compiles the source. Rebuild
the committed bundle with `npm run build:lambda` only for an intentional reviewed
source/dependency update; never silently accept a stale bundle.

## Deployment is a separate owner-authorized operation

Do not dispatch deployment/stop workflows, run `cdk deploy`/`cdk bootstrap`, create
change sets, change IAM/Environments or publish runtime configuration as part of
ordinary validation. `npm run predeploy:check -- --phase=<phase>` is read-only
but contacts AWS and requires the exact approved merged main SHA, clean source,
phase and role; its success alone does not authorize mutation. Synthetic local
provenance is not accepted as approval or live readiness.

Before any forward AWS mutation, re-read the authoritative issue/PR/settings
and verify the current hold is explicitly lifted for the exact merged commit,
the temporary Cognito identity exception is approved, and #1831/#1835 and the
frontend integration gates are satisfied. Preserve fresh cost/forecast/credit
and alert reviews within 24 hours, at least USD 3 headroom for actual/forecast
under the USD 25 gross cap, and at least USD 5 verified credits valid for more
than 24 hours. Require a monitored confirmed alert path, reviewed
bootstrap/asset/execution policies and a named stop operator.
Budget/anomaly signals are delayed, not immediate spend kill switches.

Keep the fixed account `904851777129`, region `eu-west-1`, repository/main,
signup-disabled state and separate short-lived OIDC roles/Environments:

- prepare: `HUBOptimusOperatorPrepare` / `operator-private-canary-prepare`;
- execute: `HUBOptimusOperatorExecute` / `operator-private-canary-execute`;
- stop: `HUBOptimusOperatorStop` / `operator-private-canary-stop`.

Preserve separate owner approvals and prepare/execute separation. Execute only
the reviewed change-set ARN, revalidated template/action set, immutable asset
version/checksum, parameter fingerprint and exact source/window. No arbitrary
account, region, profile, role, context or unreviewed template overrides; no
long-lived AWS keys. The normal phase order is foundation → controls → private;
foundation/controls keep concurrency zero and no intake stage. Private requires
an immediate UTC window of at most two hours, with at least 30 minutes remaining
at predeploy. `deactivate` restores controls from the exact private activation's
`SourceCommit`, after verified concurrency zero; it is not `cdk destroy`.

For an authorized active incident, follow `PRIVATE_SMOKE_RUNBOOK.md`: stop on
identity/account mismatch, unexpected spend, anonymous access, token/content
leak, SSRF or unbounded/schema-anomalous requests. The independent stop-only path
sets concurrency zero, reasserts it during stack updates and verifies it after
stability; it must not wait for economic attestations. Preserve automatic expiry
and handler-window checks, then separately govern deactivate and disabled public
configuration. Do not delete a retained Cognito pool as incidental cleanup.

Keep PKCE/MFA, subject allowlist, attempt quota, SSRF/DNS/IP pinning and log
minimization intact. Never put tokens, MFA material, subject/hash, email,
complete submitted URLs or page content into public logs/issues/artifacts.
Canonical Operator remains Entra owner/team and local/pasted-text first; dormant
auth/config assets are not loaded by its index or precached by its worker.
Changing `enabled` alone cannot activate the canary. Callback/cache/version and
response-adapter work needs separate reviewed evidence; preserve the existing
private-session boundary and human-confirmed atomic claims.
