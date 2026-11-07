# Protected deployment design

This document defines the only acceptable future AWS mutation path for the
private URL-intake canary. The candidate implementation is
`.github/workflows/operator-private-canary.yml`; neither this document nor that
unpublished workflow authorizes a change to AWS.

## Repository and environment controls

- Source repository is exactly `Voxterrae/HUB_Optimus`.
- Deployable source is one owner-reviewed commit already merged into protected
  `main`; pull-request heads and dirty worktrees are rejected.
- GitHub Environments are exactly `operator-private-canary-prepare`,
  `operator-private-canary-execute`, and `operator-private-canary-stop`.
  Prepare and execute require separate owner approvals; stop has an independent
  emergency path that cannot be delayed by economic checks.
- OIDC assumes only `HUBOptimusOperatorPrepare`, `HUBOptimusOperatorExecute`, or
  `HUBOptimusOperatorStop`, each from its exact Environment subject, in account
  `904851777129`.
- Workflow permissions are only `contents: read` and `id-token: write`.
- Account `904851777129`, region `eu-west-1`, role name, stack name, repository,
  branch, environment, and signup state are constants, not workflow inputs.
- AWS actions and all third-party actions are pinned to independently reviewed
  immutable full commit SHAs; the AWS credential action is pinned to verified
  v6.2.3 commit `e6de054238d6b7531b4efff3b6587d9aade6a06c`.
- No long-lived AWS access key, CLI profile, arbitrary CDK context, or
  user-selected role/region is accepted.

## Mandatory phase sequence

| Phase | API route/stage | Lambda concurrency | New cost controls | Approval |
|---|---:|---:|---|---|
| `foundation` | absent | `0` | gross USD 25 budget | owner + reviewed change set |
| `controls` | absent | `0` | tagged USD 10 budget and anomaly monitor | owner after active tag and alert test |
| `private` | present, auto-stop scheduled | `1 → 0` at expiry | unchanged | second owner approval for exact two-hour window |
| `deactivate` to `controls` | absent | `0` | retained | exact activation SHA, after stop or expiry |

The workflow must refuse a phase skip. `controls` may run only after the
allocation tag is `ACTIVE` and `UserDefined`; `private` may run only after both
budgets and alert delivery are verified.

## Change-set binding

Every job must run `npm ci`, `npm run check`, and the corresponding
`predeploy:check` from the exact merged SHA. It then synthesizes one template,
records the SHA-256 of the template and reviewed Lambda asset, and creates a
CloudFormation change set without executing it. The prepare role cannot execute;
the execute role cannot prepare or directly update a stack. The execution job
re-synthesizes the source, verifies the canonical template and exact resource
action set, recomputes the protected parameter fingerprint, and executes only
the prepared change-set ARN.

The bootstrap asset bucket must have versioning enabled. Prepare uploads the
deterministic ZIP with a SHA-256 checksum, captures its immutable S3 `VersionId`,
injects `S3ObjectVersion` into the sole Lambda resource, and only then hashes the
template. Execute independently verifies that exact object version and checksum,
and after CloudFormation completes it requires Lambda `CodeSha256` to match. A
bucket without versioning, a missing checksum, or any mismatch is a hard stop.

The approval record must bind all of the following:

- merged source SHA and template SHA-256;
- Lambda bundle SHA-256;
- phase and change-set ARN;
- account, region, stack, prepare/execute role ARNs, and CloudFormation service
  role ARN;
- sanitized change summary;
- `CanaryStartedAt` and `CanaryExpiresAt` for `private`;
- a non-secret fingerprint binding the protected subject hash and exact private
  window; the subject hash itself never enters the approval record;
- rollback operator and stop conditions.

Execution must use that exact change-set ARN. The job must fail if CloudFormation
reports resource replacement outside the reviewed set, if signup is not false,
or if the private window exceeds two hours.

Before executing any update to an existing stack, and again after every
successful phase, the execute role reads the live Cognito pool and browser
client. The workflow requires admin-only account creation, required software
token MFA, OAuth authorization-code flow only, the exact callback/logout/scope,
no client secret, and only refresh-token API auth. A declarative stack output is
not accepted as proof of the live identity state.

## Secret and personal-data handling

The prepare and execute Environments must define the same reviewed values before
either is enabled. The stop Environment contains no canary, identity, cost, or
content secret:

| Kind | Names |
|---|---|
| Secrets | `COST_ALERT_EMAIL`, `CANARY_ALLOWED_SUBJECT_SHA256`, `DEPLOYMENT_FINGERPRINT_KEY`, `PROMOTIONAL_CREDIT_BALANCE_USD` |
| Variables | `CANARY_DEPLOYMENTS_ENABLED`, `AWS_MUTATION_EXCEPTION`, `CANARY_GOVERNANCE_RECORD`, `CANARY_IDENTITY_DECISION`, `COST_REVIEWED_AT`, `CREDITS_REVIEWED_AT`, `ALERT_PATH_VERIFIED_AT`, `GROSS_ACTUAL_USD`, `GROSS_FORECAST_USD`, `PROMOTIONAL_CREDIT_EXPIRES_AT`, `OPERATOR_AUTH_DOMAIN_PREFIX` |

`DEPLOYMENT_FINGERPRINT_KEY` is 32 random bytes encoded as 64 lowercase hex
characters. It HMAC-binds all deployment parameters so the published fingerprint
cannot be used to guess the alert email or subject hash. The alert email and
subject hash are not credentials, but they are personal or
pseudonymous operational data and must not appear in logs, artifacts, templates,
issue comments, or workflow summaries. OAuth tokens, passwords, MFA seeds,
article text, complete submitted URLs, and Cognito user attributes are never
workflow inputs or artifacts.

## Rollback and evidence

The emergency workflow first sets concurrency to `0`, keeps reasserting zero
while any in-flight stack update remains active for up to the full private
window, and sets it to `0` again after stability. Its stop-only role uses a
reviewed three-hour maximum session. The expiry schedule provides an
independent stop. The governed `deactivate` transition then synthesizes the
reviewed `controls` state from the private activation's exact `SourceCommit`; it
does not run `cdk destroy`. The public runtime config is disabled through its own
reviewed Pages change. The handler independently refuses URL work after
`CanaryExpiresAt` if automation and reconciliation are delayed. Scheduler failure
alarms notify the confirmed controls-phase SNS email subscription and are also
manually monitored. Budgets and Cost Anomaly Detection must never be treated as
immediate kill switches.

After the window, record only sanitized evidence: change-set IDs, invocation
count, errors, throttles, budget state, gross spend delta, test-case status,
and confirmation that logs contain no token, subject, email, body, page text,
or complete URL. Cognito remains retained until a separate deletion decision.

## Prerequisites before implementation

1. The repository governance record lifts the AWS mutation hold only for this
   canary and keeps EC2, DNS, production, and public signup blocked.
2. Cognito is recorded as a temporary canary exception to the durable identity
   direction, or the candidate is changed to the approved provider.
3. The OIDC trust, three workflow roles, CloudFormation execution role, CDK
   bootstrap, asset-bucket versioning, and file-publishing policy are inventoried
   and reviewed read-only.
4. Current gross spend, forecast, promotional-credit balance/expiry, alert
   recipient, and headroom below USD 25 are verified. Both gross actual and
   forecast must leave at least USD 3, and at least USD 5 of promotional credit
   must remain valid for more than 24 hours.
5. The candidate workflows, immutable action pins and least-privilege policies
   receive normal code review; all protected Environments remain disabled
   until every preceding prerequisite is evidenced.
