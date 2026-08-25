# HUB_Optimus Operator URL intake infrastructure candidate

Fail-closed AWS CDK TypeScript candidate for
[`Voxterrae/HUB_Optimus#1917`](https://github.com/Voxterrae/HUB_Optimus/issues/1917).
It is prepared for review only: it has not deployed resources, changed DNS, or
enabled URL retrieval on the public Operator.

## What it defines

- one Cognito-JWT-protected `POST /intake/url` HTTP API route;
- OAuth authorization-code + S256 PKCE with the exact `operator/intake` scope;
- a public browser client with no secret and no password, SRP, admin-password,
  custom, or implicit authentication flow;
- required software-token MFA and administrator-created users only;
- the Cognito Lite feature plan rather than a higher-priced Plus tier;
- a bounded ARM64 Lambda with DNS/IP pinning and SSRF controls;
- an on-demand DynamoDB quota of three attempts per subject and UTC day;
- exact-origin CORS for `https://huboptimus.dev`;
- seven-day privacy-minimised application and access logs;
- a unique `HUBOptimusCostUnit=ControlledUrlIntake` allocation tag;
- a tagged USD 10 workload budget, a gross USD 25 account budget, and cost
  anomaly notifications;
- a browser PKCE helper that stores only a single-use transaction in
  `sessionStorage` and keeps tokens in memory.

There is no EC2, VPC, NAT Gateway, load balancer, SQS queue, provisioned
database, OpenAI call, custom domain, or DNS record.

The target is fixed to AWS account `904851777129` and region `eu-west-1`.
Changing either fails synthesis. The default service state is disabled with
Lambda reserved concurrency `0`. A private smoke can be represented only by
`serviceEnabled=true`; public signup is rejected by this candidate even if a
caller supplies `publicSignupEnabled=true`.

See [`OPERATOR_URL_INTAKE_DESIGN.md`](OPERATOR_URL_INTAKE_DESIGN.md),
[`CANDIDATE_STATUS.md`](CANDIDATE_STATUS.md), and
[`PRIVATE_SMOKE_RUNBOOK.md`](PRIVATE_SMOKE_RUNBOOK.md).

## Local validation

```bash
npm ci
npm run check
npm run cdk -- synth \
  -c serviceEnabled=false \
  -c publicSignupEnabled=false
```

The checked candidate passes TypeScript compilation, 103 Jest tests, and CDK
synthesis in disabled and private-smoke configurations. The compiled Lambda
handler is committed deliberately: before building, `npm run check` compares
the checked-in file byte for byte with a fresh compiler output; synthesis also
fails if it is absent. A clean checkout therefore cannot silently package an
empty or stale function asset.

`npm run predeploy:check -- --phase=foundation` and
`npm run predeploy:check -- --phase=private` are read-only local gates. Both
validate the exact account, region, `HUBOptimusOperatorDeploy` role, approved
40-character commit, and clean worktree. The private phase additionally
requires the user-defined cost tag to be active. Foundation omits only that
check because the new tag cannot be activated before a tagged resource exists;
the protected workflow must force the disabled template in that phase. Neither
command deploys or substitutes for an owner-approved protected workflow.

## Deployment boundary

Do not deploy from this isolated candidate or from an unmerged pull request.
The private smoke remains blocked until the existing AWS mutation hold is
lifted, the identity choice is approved, the exact merged commit and alert
recipient are protected inputs, CDK bootstrap roles are reviewed, credits and
gross spend are checked, and a single non-bypassable workflow forces
`serviceEnabled=true` with signup disabled.

No long-lived AWS credentials belong in this project, GitHub, browser storage,
or chat.

## Traceability starter attribution

The scaffold originated from Lars Andersson's Traceability starter and retains
its Beer-Ware license in [`LICENSE`](LICENSE). HUB_Optimus-specific security,
cost, and product changes do not transfer operational ownership to the starter
author.

[Traceability starter background](https://lars-andersson.medium.com/where-the-hell-is-the-git-project-that-owns-this-550bd96dd230)
