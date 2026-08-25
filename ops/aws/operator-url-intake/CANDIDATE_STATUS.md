# HUB_Optimus Operator infrastructure candidate

Status: **LOCAL / DISABLED / NOT DEPLOYED / PUBLIC NO-GO**  
Prepared: 2026-08-25

The candidate defines a bounded authenticated implementation of
`POST /intake/url`. It has not changed AWS account `904851777129`, DNS,
`api.huboptimus.dev`, GitHub Pages, or the live Operator.

## Closed locally

- Account and region are fixed to `904851777129` and `eu-west-1`.
- Service enablement is separate from account creation.
- Public signup is rejected; private smoke permits one invited MFA user.
- Cognito uses authorization code + S256 PKCE, exact `operator/intake` scope,
  short tokens, no client secret, and no direct password/SRP/custom flow.
- API Gateway and Lambda independently validate access-token client and scope.
- SSRF controls include IPv4/IPv6 special ranges, all-answer DNS validation,
  numeric-address pinning, fresh sockets, peer verification, redirect
  revalidation, HTTPS downgrade blocking, and bounded responses.
- Workload and gross-account budgets cover tagged and untagged spend visibility.
- The deployment role name, account, region, clean tree, exact SHA, and active
  cost tag have phased read-only predeploy checks with no role-name override;
  foundation omits only the not-yet-activatable tag gate.
- CDK feature flags are explicitly pinned to current recommendations.
- The Lambda JavaScript asset is compiled and present; a pre-build byte
  comparison rejects stale output and synthesis fails if it is missing.
- The companion browser integration defaults disabled, uses PKCE S256 and an
  in-memory Bearer token, and never caches runtime enablement or OAuth callback
  query values.

## Local evidence

- TypeScript build: passed.
- Jest: 103/103 tests passed.
- Companion Operator/i18n/PWA/wiki checks: 84/84 selected tests passed with
  Node-backed browser/service-worker harnesses (pytest itself was unavailable
  in this isolated environment).
- Disabled synthesis: passed with `serviceEnabled=false` and signup false.
- Private structural synthesis: passed with `serviceEnabled=true` and signup
  false.
- Public-signup synthesis: rejected as designed.
- No AWS command, deployment, DNS change, merge, or public feature enablement
  was performed.
- The supplied Billing screenshot shows a USD 22.30 monthly forecast. If that
  figure is current, only about USD 2.70 remains below the proposed USD 25 gross
  account alert. Credit balance and expiry were not visible or verified.

## Remaining blockers before a private AWS canary

1. Lift the active AWS mutation hold through the repository's owner-governed
   process; issue #1917 by itself does not authorize deployment.
2. Merge an owner-reviewed commit and provide its protected exact SHA; do not
   deploy a pull-request head.
3. Resolve the Cognito-versus-Entra identity decision.
4. Review the trust and permissions of `HUBOptimusOperatorDeploy`, CDK bootstrap,
   and CloudFormation execution roles; root is forbidden.
5. Verify current gross spend, promotional-credit balance and expiry, alert
   recipient, and remaining headroom below the USD 25 gross cap before creating
   anything.
6. Run a disabled foundation phase, wait for the unique allocation tag to
   appear, activate it, and verify both budgets and alert delivery.
7. Provide a protected non-bypassable deployment path that forces signup false,
   binds the reviewed change set and SHA, and cannot switch profile or role
   after validation.
8. Publish the output-derived static runtime configuration through a separate
   reviewed Pages change, still disabled until the invited-user window.
9. Execute the positive and negative private smoke matrix, privacy review,
   rollback, and post-test cost check.

Until all nine gates pass, the correct decision is **NO-GO for AWS smoke**.
Public signup, production, DNS publication, and general public URL intake remain
**NO-GO** after that private canary as well.
