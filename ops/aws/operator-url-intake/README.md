# HUB_Optimus Operator URL intake infrastructure candidate

Fail-closed AWS CDK TypeScript candidate for
[`Voxterrae/HUB_Optimus#1917`](https://github.com/Voxterrae/HUB_Optimus/issues/1917).
It is prepared for review only: it has not deployed resources, changed DNS, or
enabled URL retrieval on the public Operator.

## What it defines

- one Cognito-JWT-protected `POST /intake/url` HTTP API route created only in
  the time-bounded private phase;
- OAuth authorization-code + S256 PKCE with the exact `operator/intake` scope;
- a public browser client with no secret and no password, SRP, admin-password,
  custom, or implicit authentication flow;
- required software-token MFA and administrator-created users only;
- a mandatory SHA-256 allowlist for the single invited Cognito subject;
- the Cognito Lite feature plan rather than a higher-priced Plus tier;
- a bounded ARM64 Lambda with DNS/IP pinning and SSRF controls;
- an on-demand DynamoDB quota of exactly three authenticated attempts for the
  entire approved window, including malformed requests; no subject or
  subject-derived identifier is stored;
- exact-origin CORS for `https://huboptimus.dev`;
- seven-day privacy-minimised application and access logs;
- a unique `HUBOptimusCostUnit=ControlledUrlIntake` allocation tag;
- a tagged USD 10 workload budget, a gross USD 25 account budget, and cost
  anomaly notifications, plus a controls-phase SNS email alert path for
  auto-stop failures;
- an esbuild-produced Lambda asset with the DynamoDB SDK pinned and bundled;
- a one-time EventBridge Scheduler kill switch that sets Lambda concurrency to
  `0` at the reviewed expiry, with a dedicated schedule group, four-day
  encrypted SQS DLQ, three failure-state alarms, and the handler window as an
  independent stop layer;
- a browser PKCE helper that stores only a single-use transaction in
  `sessionStorage` and keeps tokens in memory.

There is no EC2, VPC, NAT Gateway, load balancer, provisioned database, OpenAI
call, custom domain, or DNS record. The only SQS queue is the private phase's
short-lived Scheduler DLQ; it never stores submitted URLs or article content.

The target is fixed to AWS account `904851777129` and region `eu-west-1`.
Changing either fails synthesis. There is no implicit default phase. Exactly
one of `foundation`, `controls`, `private`, or governed `deactivate` must be supplied together with the
full merged `main` SHA, exact repository, exact environment, and the temporary
Cognito decision. `foundation` creates no stage and, among cost controls, only
the gross budget;
`controls` adds the Hosted UI, tag-dependent cost controls, and confirmed
operational alert topic while Lambda remains at concurrency `0`; `private`
creates the authenticated route, sets
concurrency to `1`, and schedules automatic concurrency shutdown. `deactivate`
is fixed to the exact `SourceCommit` that created `private` and restores the
`controls` template. Public signup is rejected in every phase.

See [`OPERATOR_URL_INTAKE_DESIGN.md`](OPERATOR_URL_INTAKE_DESIGN.md),
[`CANDIDATE_STATUS.md`](CANDIDATE_STATUS.md), and
[`PRIVATE_SMOKE_RUNBOOK.md`](PRIVATE_SMOKE_RUNBOOK.md).

## Local validation

```bash
cd ops/aws/operator-url-intake
npm ci
npm run check
npm run cdk -- synth \
  -c deploymentPhase=foundation \
  -c publicSignupEnabled=false \
  -c identityProviderDecision=cognito-temporary-canary \
  -c gitCommit=<merged-main-40-character-sha> \
  -c repoName=Voxterrae/HUB_Optimus \
  -c branchName=main \
  -c environmentName=private-canary
```

The checked candidate passes TypeScript compilation, 133 Jest tests, and CDK
synthesis in all three phases. The generated Lambda bundle is committed
deliberately: `npm run check` rebuilds it in memory, verifies that the pinned
DynamoDB client is included, and compares it byte for byte with the reviewed
asset. Synthesis fails if that asset is absent.

The read-only predeploy gate accepts exactly `foundation`, `controls`,
`private`, or `deactivate`. It validates account, region, the phase-specific
`HUBOptimusOperatorPrepare`/`HUBOptimusOperatorExecute` role, exact source, and
a clean tree. `controls` and `private` also require the allocation tag to be active.
`private` additionally requires an immediate UTC window with at least 30
minutes remaining and no more than two hours total. The candidate protected
workflow creates a change set directly from the hashed template, verifies the
CloudFormation copy and exact action allowlist, fingerprints its parameters,
pauses for a second Environment approval, and executes only that ARN with a
different short-lived OIDC role. A third stop-only role can only set the fixed
Lambda's concurrency to zero. None is active until published, reviewed, merged,
and configured in GitHub and AWS.

## Deployment boundary

Do not deploy from this isolated candidate or from an unmerged pull request.
The private smoke remains blocked until the existing AWS mutation hold is
lifted, the identity choice is approved, the exact merged commit and alert
recipient are protected inputs, CDK bootstrap roles are reviewed, credits and
gross spend are checked, and the three protected GitHub Environments plus OIDC
trust are reviewed. Automatic expiry sets Lambda concurrency `0`; governed
`deactivate` restores `controls` and removes the route, schedule, DLQ and alarms.
The independent stop workflow is idempotent and never waits for economic
attestations. Neither path is `cdk destroy`.

No long-lived AWS credentials belong in this project, GitHub, browser storage,
or chat.

## Traceability starter attribution

The scaffold originated from Lars Andersson's Traceability starter and retains
its Beer-Ware license in [`LICENSE`](LICENSE). HUB_Optimus-specific security,
cost, and product changes do not transfer operational ownership to the starter
author.

[Traceability starter repository](https://github.com/zipon/Traceability)
