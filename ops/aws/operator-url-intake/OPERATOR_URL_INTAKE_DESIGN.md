# HUB_Optimus controlled URL intake design

Status: local review candidate. No AWS, DNS, GitHub Pages, or public feature
state has been changed.

## Authentication and activation boundary

- Route: authenticated `POST /intake/url` only.
- Body: exactly one JSON member, `{ "url": "https://…" }`.
- API Gateway validates the Cognito issuer and web-client audience, then
  requires the exact custom scope `operator/intake`.
- Lambda independently requires `token_use=access`, the exact Cognito
  `client_id`, the exact whitespace-delimited scope, and a non-empty `sub`.
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
  candidate; one administrator-created user is the maximum private-smoke
  population.
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

Service execution and account creation are deliberately separate. The default
`serviceEnabled=false` sets Lambda reserved concurrency to zero. A private
smoke uses `serviceEnabled=true` and `publicSignupEnabled=false`. Any attempt to
set public signup true fails synthesis. Public access requires a future,
separately reviewed change.

## Capacity, privacy, and cost controls

- API Gateway throttles globally at `0.2` requests/second with burst `2`, so a
  browser's CORS preflight and immediately following POST can complete as one
  user action without increasing sustained throughput.
- Lambda is ARM64, 128 MiB, ten-second execution timeout, eight-second fetch
  budget, and reserved concurrency `0` or `1`.
- DynamoDB atomically permits three attempts per subject and UTC day. Keys use
  a SHA-256 subject hash plus date; raw Cognito subjects are not stored.
- Requests retain at most 1,000,000 response bytes and 24,000 extracted
  characters. Environment values above the compiled maxima fall back to safe
  defaults.
- Logs retain seven days. They contain request IDs, status/latency, truncated
  URL fingerprints, byte counts, redirect counts, and safe error codes—not
  request bodies, page text, complete URLs, JWTs, claims, subjects, or
  origin-controlled content-type strings.
- The unique allocation tag is
  `HUBOptimusCostUnit=ControlledUrlIntake`.
- The tagged workload budget is USD 10/month. The independent gross account
  budget is USD 25/month. Both alert at 50%, 80%, and 100% actual spend and
  100% forecast; credits and refunds are excluded from their cost view.
- Cost Anomaly Detection is scoped to the unique workload tag and alerts at an
  absolute USD 2 impact.

Budgets notify; they do not stop spend. The account budget exists because a tag
filter cannot detect untagged or mis-tagged consumption. AWS can take time to
surface and activate a new user-defined allocation tag, so the runbook uses a
disabled foundation phase before any private service activation.

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
- The Lambda package currently relies on the AWS SDK v3 included in the managed
  Node.js 22 runtime for one DynamoDB update. A production revision should
  bundle and pin that client.
- Unit tests cover policy, extraction, schema, claims, PKCE, pinning options,
  peer matching, quotas, and synthesis. A real network-path canary is still
  required to prove DNS, TLS/SNI, timeout, redirects, and response truncation in
  the selected AWS environment.
- Cognito is a provisional identity choice. Existing governance discussion also
  records an Entra single-tenant direction; the owner must resolve that choice
  before a durable or public deployment.
- A local predeploy script can be bypassed. Deployment remains NO-GO until a
  protected, single-path workflow binds approved SHA, account, region, role,
  cost recipient, disabled signup, change-set review, and deployment in one
  controlled execution.
- Public signup, DNS/TLS publication, production release, merge, and AWS
  mutation are outside this candidate's authorization.
