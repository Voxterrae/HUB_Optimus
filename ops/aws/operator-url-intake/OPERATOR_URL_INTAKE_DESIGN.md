# HUB_Optimus controlled URL intake design

Status: local review candidate. No AWS, DNS, GitHub Pages, or public feature
state has been changed.

## Authentication and activation boundary

- Route: authenticated `POST /intake/url` only.
- Body: exactly one JSON member, `{ "url": "https://…" }`.
- API Gateway validates the Cognito issuer and web-client audience, then
  requires the exact custom scope `operator/intake`.
- Lambda independently requires `token_use=access`, the exact Cognito
  `client_id`, the exact whitespace-delimited scope, and the sole invited
  `sub` whose SHA-256 matches the protected canary allowlist.
- The browser client has no secret and supports only OAuth authorization-code
  flow. Implicit, SRP, password, admin-password, and custom auth are disabled.
- The PKCE helper generates 32 random bytes each for verifier, state, and nonce,
  uses S256, consumes a transaction once, and expires it after ten minutes.
- Only the pending verifier/state/nonce transaction enters `sessionStorage`.
  The access token remains in memory. The ID token is decoded for nonce/client
  consistency and then discarded; any returned refresh token is ignored. No
  token may enter local storage, logs, URLs, Cache Storage, or rendered HTML.
- Browser-side JWT decoding is a local consistency gate, not signature
  verification or authorization. API Gateway remains the cryptographic trust
  boundary.
- Access and ID tokens expire after 15 minutes. The unused refresh token expires
  after one hour and is never persisted by the browser helper.
- Cognito requires software-token MFA. Self-signup is always disabled in this
  candidate; a mandatory `NoEcho` hash allowlist restricts execution to one
  administrator-created user even if another account were added accidentally.
- The user pool is pinned to the Cognito Lite plan; paid Plus threat-protection
  features and SMS MFA are not enabled.

The callback and logout values are fixed by CloudFormation validation to
`https://huboptimus.dev/operator/`. The stack outputs the raw API invoke URL,
JWT issuer, web client ID, Hosted UI base URL, callback, and logout value. A
separate static runtime configuration must consume those outputs before a
private browser test can run. That configuration contains identifiers and
endpoints only—never credentials or tokens.

The checked-in static configuration is disabled and empty. The service worker
never precaches or falls back to an older runtime configuration: if the
network-only config request fails, authentication stays disabled. OAuth
callback query values are scrubbed before local external scripts execute; a
callback navigation's request and response are never written to Cache Storage.
Login also requires an exact version response from the active `v0-28` worker,
so the older worker cannot initiate a callback during rollout.

Service execution and account creation are deliberately separate. Synthesis
requires one explicit phase and exact merged-main provenance:

- `foundation`: Lambda concurrency `0`, no API stage, no Hosted UI domain, and
  among cost controls only the gross account budget;
- `controls`: Lambda concurrency `0`, no API stage, the tag-dependent workload
  budget/anomaly monitor, and a confirmed operational SNS email subscription
  after the allocation tag is active;
- `private`: concurrency `1`, one JWT-protected route/stage, mandatory UTC
  start/expiry plus one allowed-subject hash and non-secret subject/window
  binding, and a one-time Scheduler kill switch, with a maximum two-hour window;
- `deactivate`: only from `private`, using that stack's exact `SourceCommit`,
  and restoring the reviewed `controls` template.

At expiry, EventBridge Scheduler calls only `PutFunctionConcurrency` for this
Lambda and sets it to `0`; its trust is restricted to the dedicated schedule
group ARN and account. Failed deliveries retry three times, then enter an
encrypted four-day DLQ; dedicated CloudWatch alarms make target, drop, and DLQ
failure visible and notify the confirmed controls-phase SNS subscription. The
operator also monitors them and runs the independent stop-only workflow at
expiry. The handler independently rejects every request outside the window and
also rejects any mismatch between the protected subject hash, UTC window, and
their reviewed binding. `deactivate` removes the route, stage, schedule, group,
DLQ, alarms, and stop role. Any attempt to enable public signup fails synthesis.

## Capacity, privacy, and cost controls

- API Gateway throttles globally at `0.2` requests/second with burst `2`, so a
  browser's CORS preflight and immediately following POST can complete as one
  user action without increasing sustained throughput.
- Lambda is ARM64, 128 MiB, ten-second execution timeout, eight-second fetch
  budget, and reserved concurrency `0` or `1`.
- DynamoDB atomically permits exactly three authenticated attempts for the
  entire approved window, before body parsing or URL validation. It stores only
  a SHA-256 key derived from the reviewed start/expiry pair, count, and TTL—no
  subject or subject-derived identifier. Crossing UTC midnight does not renew
  the quota.
- Requests retain at most 1,000,000 response bytes and 24,000 extracted
  characters. Environment values above the compiled maxima fall back to safe
  defaults.
- Logs retain seven days. They contain request IDs, status/latency, truncated
  URL fingerprints, byte counts, redirect counts, and safe error codes—not
  request bodies, page text, complete URLs, JWTs, claims, subjects, or
  origin-controlled content-type strings.
- Resource classification is not globally public: Cognito is `restricted`,
  the quota table is `internal-operational`, and the remaining workload is
  `internal`. The alert email is a `NoEcho` CloudFormation parameter and must
  be supplied from a protected environment secret.
- The unique allocation tag is
  `HUBOptimusCostUnit=ControlledUrlIntake`.
- The tagged workload budget is USD 10/month. The independent gross account
  budget is USD 25/month. Both alert at 50%, 80%, and 100% actual spend and
  100% forecast; credits and refunds are excluded from their cost view.
- Cost Anomaly Detection is scoped to the unique workload tag and alerts at an
  absolute USD 2 impact.

Budgets notify; they do not stop spend. The account budget exists because a tag
filter cannot detect untagged or mis-tagged consumption. AWS can take time to
surface and activate a new user-defined allocation tag, so `foundation`
creates tagged resources and, among cost controls, only the gross budget. The
tag-filtered workload budget and anomaly monitor are deferred to `controls`;
`private` is unavailable until that phase succeeds.

AWS budget data is not real-time, and Cost Anomaly Detection is not a two-hour
kill switch. Real containment comes from concurrency `1`, rate `0.2`, three
total attempts, the handler expiry, Scheduler auto-stop, and the independent
stop-only role. Credit balance, expiry, actual cost, and forecast remain fresh
human attestations in both protected deployment Environments.

These are monitoring-only budgets, not paid budget actions, and AWS documents
budget monitoring plus Cost Anomaly Detection as available without additional
feature charges. Normal service usage, email delivery, logs, and data transfer
can still incur charges; free-tier or credit eligibility must be verified on
this specific account rather than assumed.

## Controlled fetch boundary

Every submitted URL and redirect is restricted to ASCII HTTP/HTTPS with a
default port. Credentials, local/internal hostnames, private, loopback,
link-local, multicast, documentation, benchmarking, reserved, and known
transition IP ranges are rejected. The IPv6 policy follows the IANA
special-purpose registry and fails closed outside ordinary global unicast.

All DNS answers must be public and at most sixteen distinct answers are
accepted. A connection uses one validated numeric address, preserves the
original Host and TLS SNI, disables socket reuse, and verifies the connected
peer. Every redirect repeats validation; HTTPS-to-HTTP downgrade is rejected
and the redirect limit is three. Rejected responses and redirect bodies are
destroyed rather than drained.

The fetch sends no cookies, authorization headers, browser state, proxy
settings, or subresource requests. Only identity-encoded `text/plain`,
`text/html`, and `application/xhtml+xml` with unambiguous framing are accepted.
Returned text is unreviewed candidate material, never verified evidence. A
frontend must render title and text with `textContent`, never `innerHTML`.

## Known limitations and non-goals

- This stack creates no `api.huboptimus.dev` custom domain or DNS record.
- The Lambda package is generated by a pinned esbuild version and includes the
  exact pinned DynamoDB SDK client. Verification rebuilds it in memory and
  rejects a stale or externally dependent asset.
- Unit tests cover policy, extraction, schema, claims, PKCE, pinning options,
  peer matching, quotas, and synthesis. A real network-path canary is still
  required to prove DNS, TLS/SNI, timeout, redirects, and response truncation in
  the selected AWS environment.
- Cognito remains a temporary private-canary exception only. Existing
  governance records Entra single-tenant as the durable owner/team direction;
  that exception must be recorded explicitly before even `foundation` is run.
- The candidate workflow binds approved SHA, account, region, separate prepare
  and execute roles, an HMAC parameter fingerprint, cost recipient and disabled
  signup. Its file-publishing session is restricted to one content-addressed
  object; the change set pins that object's immutable S3 version and Execute
  verifies Lambda `CodeSha256` after deployment.
  It creates a change set from the already hashed template (without a second
  CDK deploy synthesis), verifies CloudFormation's original template and exact
  resource-action allowlist, and summarizes it in
  `operator-private-canary-prepare`, then executes only that exact ARN after a
  second approval in `operator-private-canary-execute`, using OIDC credentials.
  A third OIDC role is limited to `PutFunctionConcurrency(0)` on the fixed
  canary Lambda. Exact trust and permission examples live under `iam/`.
  Deployment remains NO-GO until that workflow, its environments and role trust
  are published and independently reviewed.
- Public signup, DNS/TLS publication, production release, merge, and AWS
  mutation are outside this candidate's authorization.
