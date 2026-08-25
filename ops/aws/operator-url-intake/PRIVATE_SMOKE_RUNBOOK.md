# Private URL-intake smoke runbook

This runbook is preparation, not authorization. Running a deploy command changes
AWS and is forbidden until the repository owner explicitly lifts the current
mutation hold for the exact merged commit and scope.

## Intended result

For a short window, one administrator-created user with software-token MFA can
sign in at `https://huboptimus.dev/operator/`, submit one or two benign public
HTTPS URLs, and receive source-bound extracted text. Anonymous users, ID tokens,
wrong clients/scopes, SSRF targets, and the fourth daily request must fail. The
service returns to reserved concurrency zero immediately after evidence is
captured.

## Hard gates

All items must be true before any mutation:

- issue #1831 or its successor records that AWS mutation is unblocked;
- the deployment source is one exact reviewed and merged 40-character SHA;
- the identity owner has approved Cognito for this canary, or the candidate has
  been replaced with the approved Entra design;
- caller identity is the exact `HUBOptimusOperatorDeploy` role in account
  `904851777129`, never root, and region is `eu-west-1`;
- CDK bootstrap and CloudFormation execution-role trust/policies are reviewed;
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
protected workflow must force the reviewed disabled template. Before Phase 2,
repeat the command with `--phase=private`; that phase requires the tag to be
active.

Synthesize both states into separate directories and review the complete diff:

```bash
npm run cdk -- synth \
  --output cdk.out.disabled \
  -c serviceEnabled=false \
  -c publicSignupEnabled=false

npm run cdk -- synth \
  --output cdk.out.private \
  -c serviceEnabled=true \
  -c publicSignupEnabled=false
```

The private template must show exactly one route, JWT authorization and scope,
MFA required, administrator-only account creation, Lambda concurrency `1`,
stage burst `2`/rate `0.2` (one CORS preflight plus its POST), two budgets,
short logs, no VPC/NAT/EC2/SQS, and no
custom domain or DNS.

## Phase 1: disabled foundation

Only the protected owner-approved workflow may create the reviewed disabled
change set. It must force `serviceEnabled=false` and
`publicSignupEnabled=false`, the exact account/region/role, and the approved
parameters:

- owner-controlled `CostAlertEmail`;
- unique `OperatorAuthDomainPrefix`;
- exact callback and logout `https://huboptimus.dev/operator/`.

Do not activate the service. Verify the gross USD 25 budget and email path
first. The new `HUBOptimusCostUnit` tag can take time to appear in Billing and
then to activate. Wait until it is `Active` and `UserDefined`; confirm the tagged
USD 10 budget, gross account budget, and anomaly subscription are visible.

Record only sanitized resource identifiers and statuses. Do not record tokens,
email addresses, full URLs, page text, or credentials.

## Phase 2: private activation

After a second explicit approval of the reviewed private change set:

1. Run `npm run predeploy:check -- --phase=private` from the same clean approved
   commit and stop unless the unique cost tag is active.
2. Create exactly one administrator-invited Cognito user.
3. Complete required password change and TOTP enrollment manually.
4. Keep self-signup disabled and verify it is impossible from the Hosted UI.
5. First publish the Operator `v0-28` code with its checked-in disabled, empty
   runtime config. Wait for Pages propagation, use a clean browser profile,
   and verify `v0-28` is the active controller before attempting login.
6. In a separate reviewed change, publish `runtime-config.v1.js` containing
   only the exact CloudFormation raw API invoke URL, Cognito issuer,
   authorize/token/logout endpoints, client ID, exact callback, and scope. No
   secret exists for this public client.
7. Enable the private runtime flag only for the scheduled test window. Verify
   the config matches the eu-west-1 API Gateway and Cognito outputs; the client
   rejects arbitrary HTTPS domains and stale/offline config.
8. Activate the reviewed template with `serviceEnabled=true` and signup false.
9. Verify real preflight/POST CORS from `https://huboptimus.dev` before the
   positive URL case.

The static page is publicly downloadable, but the API remains invitation-only:
the page must not call intake without an in-memory access token.

## Smoke matrix

Use only pre-agreed benign HTTPS pages without query secrets, personal data,
paywalls, authentication, or redirects for the positive case.

Wait at least six seconds between distinct matrix attempts so the stage's
`0.2` request/second throttle is not confused with the per-subject quota. Do
not add a delay between a browser-generated CORS preflight and its POST.

The single user has a hard quota of three authenticated Lambda attempts per UTC
day, and the quota is consumed before URL validation/fetch. Do not try to run
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

Additional outbound cases require a later UTC day and a separately approved
window. Do not add users or alter/reset quota data merely to expand this test.

Confirm browser title/text rendering uses `textContent`. Check that application
and access logs contain no JWT, subject, page content, request body, complete
URL, email, or origin-controlled header value.

## Immediate rollback

Stop on any unexpected spend, role/account mismatch, anonymous access, token or
content in logs, SSRF anomaly, unbounded request, or schema mismatch.

The protected rollback change set must restore
`serviceEnabled=false` and `publicSignupEnabled=false`, producing Lambda
reserved concurrency `0`. Then disable the static runtime flag and verify the
public Operator returns to local/pasted-text behavior. Do not destroy retained
identity resources during the smoke; deletion is a separate reviewed action.

After rollback, record gross spend/forecast, budget state, invocation count,
throttles, errors, and the sanitized test matrix. Public signup, DNS mapping,
production release, and merge of follow-on changes require separate decisions.
