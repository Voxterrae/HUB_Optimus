# Private URL-intake smoke runbook

This runbook is preparation, not authorization. Running a deploy command changes
AWS and is forbidden until the repository owner explicitly lifts the current
mutation hold for the exact merged commit and scope.

## Intended result

For a short window, one administrator-created user with software-token MFA can
sign in at `https://huboptimus.dev/operator/`, submit one or two benign public
HTTPS URLs, and receive source-bound extracted text. Anonymous users, ID tokens,
wrong clients/scopes, SSRF targets, and the fourth authenticated attempt in the
same approved window must fail. The expiry schedule returns Lambda to reserved
concurrency zero even if manual
rollback is delayed. The governed rollback then removes the stage and schedule.

## Hard gates

All items must be true before any mutation:

- issue #1831 or its successor records that AWS mutation is unblocked;
- the deployment source is one exact reviewed and merged 40-character SHA;
- the identity owner has approved Cognito for this canary, or the candidate has
  been replaced with the approved Entra design;
- prepare, execute, and emergency stop use only `HUBOptimusOperatorPrepare`,
  `HUBOptimusOperatorExecute`, and `HUBOptimusOperatorStop`, respectively, in
  account `904851777129`, never root, and region `eu-west-1`;
- CDK bootstrap, versioned asset bucket, file-publishing role, and CloudFormation
  execution-role trust/policies are reviewed;
- current month gross spend, forecast, credits, and credit expiry are recorded;
- the remaining headroom below the USD 25 gross-account cap is known and
  sufficient for the reviewed change set;
- the alert address is owner-controlled and monitored during the window;
- the protected deployment path accepts no arbitrary profile, role, account,
  region, context, or unreviewed template arguments;
- rollback operator and stop condition are named.

If any item is false or unknown, stop.

## Local evidence before a change set

From a clean checkout of the approved merged SHA:

```bash
cd ops/aws/operator-url-intake
npm ci
npm run check
export AWS_REGION=eu-west-1
export HUB_OPTIMUS_DEPLOY_SHA=<approved-merged-40-character-sha>
npm run predeploy:check -- --phase=foundation
```

The predeploy command is read-only. Its success does not authorize deployment
and does not prove role policy, credits, budgets, or change-set safety. The
foundation phase omits only the cost-allocation-tag activation check because
AWS cannot expose a new user-defined key until a tagged resource exists; the
protected workflow must force the reviewed foundation template. `controls` and
`private` both require the tag to be active. `private` also requires
`CANARY_STARTED_AT` and `CANARY_EXPIRES_AT` to describe an immediate UTC window
with at least 30 minutes remaining and no longer than two hours.

Synthesize all three states into separate directories and review every diff:

```bash
CDK_PROVENANCE=(
  -c publicSignupEnabled=false
  -c identityProviderDecision=cognito-temporary-canary
  -c gitCommit="$HUB_OPTIMUS_DEPLOY_SHA"
  -c repoName=Voxterrae/HUB_Optimus
  -c branchName=main
  -c environmentName=private-canary
)

npm run cdk -- synth \
  --output cdk.out.foundation \
  -c deploymentPhase=foundation \
  "${CDK_PROVENANCE[@]}"

npm run cdk -- synth \
  --output cdk.out.controls \
  -c deploymentPhase=controls \
  "${CDK_PROVENANCE[@]}"

npm run cdk -- synth \
  --output cdk.out.private \
  -c deploymentPhase=private \
  "${CDK_PROVENANCE[@]}"
```

Foundation has no route/stage, concurrency `0`, and, among cost controls, only
the gross USD 25 budget. Controls still has no route/stage and concurrency `0`, but adds the
tagged USD 10 budget, anomaly monitor, and Hosted UI domain. Private adds
exactly one JWT route, integration, permission, authorizer, and stage; it sets
concurrency `1`, burst `2`, rate `0.2`, mandatory canary-window parameters, and
adds one fixed Scheduler target plus its single-purpose role/policy to stop
concurrency at expiry. The private phase also adds one encrypted, four-day SQS
dead-letter queue and three visible failure alarms for that auto-stop path.
No phase may add VPC/NAT/EC2, a general-purpose queue, a custom API domain, or DNS.

## Phase 1: foundation

Only the protected owner-approved workflow may create the reviewed foundation
change set. It must force `deploymentPhase=foundation`, signup false, the exact
account/region/role/provenance, and the approved
parameters:

- owner-controlled `CostAlertEmail`;
- exact callback and logout `https://huboptimus.dev/operator/`.

Do not activate the service. Verify the gross USD 25 budget and email path
first. The new `HUBOptimusCostUnit` tag can take time to appear in Billing and
then to activate. Wait until it is `Active` and `UserDefined`; foundation does
not yet create the tagged budget or anomaly monitor.

Record only sanitized resource identifiers and statuses. Do not record tokens,
email addresses, full URLs, page text, or credentials.

## Phase 2: cost controls and identity setup

Run `npm run predeploy:check -- --phase=controls` from the same merged SHA.
Review a change set that adds only the Hosted UI domain, tagged USD 10 budget,
anomaly monitor/subscription, and the operational SNS email topic/subscription;
Lambda must remain at concurrency `0` and no API stage may exist. Confirm the
SNS subscription, use the unique `OperatorAuthDomainPrefix`, verify both budgets
and alert delivery, then create exactly one administrator-invited
Cognito user and finish the required password change and TOTP enrollment
manually. Read its immutable Cognito `sub` once, compute its lowercase SHA-256
locally, and store only that hash as the protected
`CanaryAllowedSubjectSha256` input. Do not put the raw subject, hash, email, or
MFA material in an issue, log, artifact, or command history. Self-signup must
remain impossible.

## Phase 3: private activation

After a second explicit approval of the reviewed private change set:

1. Run `npm run predeploy:check -- --phase=private` from the same clean approved
   commit and stop unless the tag is active and the two-hour UTC window is
   valid.
2. Keep self-signup disabled, verify exactly one invited user exists, and bind
   the private change set to its protected `CanaryAllowedSubjectSha256` value.
3. First publish the Operator `v0-28` code with its checked-in disabled, empty
   runtime config. Wait for Pages propagation, use a clean browser profile,
   and verify `v0-28` is the active controller before attempting login.
4. In a separate reviewed change, publish `runtime-config.v1.js` containing
   only the exact CloudFormation raw API invoke URL, Cognito issuer,
   authorize/token/logout endpoints, client ID, exact callback, and scope. No
   secret exists for this public client.
5. Enable the private runtime flag only for the scheduled test window. Verify
   the config matches the eu-west-1 API Gateway and Cognito outputs; the client
   rejects arbitrary HTTPS domains and stale/offline config.
6. Activate the reviewed template with `deploymentPhase=private`, signup false,
   the protected allowed-subject hash, and the exact
   `CanaryStartedAt`/`CanaryExpiresAt` values used by predeploy.
7. Verify real preflight/POST CORS from `https://huboptimus.dev` before the
   positive URL case.
8. Verify the one-time Scheduler expression equals the reviewed expiry and its
   target is only `lambda:PutFunctionConcurrency` on the intake function.
9. Confirm the controls-phase SNS email subscription before activation. Keep the
   three auto-stop alarms visible and in `OK` throughout expiry; each publishes
   to that topic, while the operator also monitors them manually. Budgets and
   Cost Anomaly Detection are delayed financial signals rather than kill
   switches.

The static page is publicly downloadable, but the API remains invitation-only:
the page must not call intake without an in-memory access token.

## Smoke matrix

Use only pre-agreed benign HTTPS pages without query secrets, personal data,
paywalls, authentication, or redirects for the positive case.

Wait at least six seconds between distinct matrix attempts so the stage's
`0.2` request/second throttle is not confused with the global canary quota. Do
not add a delay between a browser-generated CORS preflight and its POST.

The entire approved window has a hard quota of three authenticated Lambda
attempts, including malformed bodies, and the quota is consumed before body
parsing or URL validation/fetch. Crossing UTC midnight does not renew it. Do not try to run
every unit case live or reset the DynamoDB row. Use this exact division:

| Case | Where | Expected result |
|---|---|---|
| Anonymous POST | Live, before Lambda | `401`; Lambda is not invoked |
| ID token as Bearer | Live, before Lambda | `401` |
| Access token with wrong client | Reviewed authorizer test | `401` |
| Access token without `operator/intake` | Reviewed authorizer test | `403`/`401`; no fetch |
| Missing or incorrect PKCE verifier | Browser/auth test | token exchange fails |
| Attempt 1: invited user and benign HTTPS URL | Live Lambda | `200`, source-bound schema |
| Attempt 2: one loopback/private/metadata target | Live Lambda | safe `400`; no outbound fetch |
| Attempt 3: pre-agreed HTTPS-to-HTTP redirect | Live Lambda | safe `502` |
| Attempt 4: repeat benign URL | Live Lambda | `429`; no fetch |
| Mixed DNS, compressed/unsupported content, peer mismatch, byte/text limits | Automated tests only in this window | bounded safe result |

Additional outbound cases require a separately approved new window. Do not add
users or alter/reset quota data merely to expand this test.

Confirm browser title/text rendering uses `textContent`. Check that application
and access logs contain no JWT, subject, page content, request body, complete
URL, email, or origin-controlled header value.

## Immediate rollback

Stop on any unexpected spend, role/account mismatch, anonymous access, token or
content in logs, SSRF anomaly, unbounded request, or schema mismatch.

For an immediate stop, run the protected stop-only workflow. It sets concurrency
to `0` immediately, reasserts zero while an in-flight stack update continues,
and sets it to `0` again after stability. The stop role must allow the reviewed
10,800-second session used by this containment path.
At `CanaryExpiresAt`, the one-time schedule independently performs the same stop;
the handler's time check is a third fallback. The governed `deactivate` transition
must run only after concurrency is already verified as `0`, then restore
`deploymentPhase=controls` from the exact activation
`SourceCommit`, with signup false. This removes route/stage/schedule and reconciles
Lambda concurrency `0`. Then disable the static runtime flag and verify the
public Operator returns to local/pasted-text behavior. Remove the invited smoke
user after evidence capture; deleting the retained pool remains a separate
reviewed action.

After rollback, record gross spend/forecast, budget state, invocation count,
throttles, errors, and the sanitized test matrix. Public signup, DNS mapping,
production release, and merge of follow-on changes require separate decisions.
