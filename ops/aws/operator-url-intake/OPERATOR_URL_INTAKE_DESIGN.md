# HUB_Optimus Operator URL intake candidate

Status: local, offline CDK candidate. It has not been deployed and does not
change AWS, GitHub, DNS, `api.huboptimus.dev`, or the public Pages feature flag.

## Contract and access boundary

- Route: `POST /intake/url`.
- Body: exactly one JSON member, `{ "url": "https://…" }`.
- Success and application-error payloads follow
  `ops/ec2/controlled_url_intake.v1.schema.json`.
- API Gateway requires a Cognito JWT. There is no anonymous intake route.
- The Cognito client is public (no client secret) and enables only OAuth
  authorization-code flow. The browser must use S256 PKCE; implicit flow is
  disabled. Public verified-email signup is enabled only when CDK context
  `publicPilotEnabled=true` is supplied explicitly; otherwise users are
  administrator-invited only.
- Access and ID tokens expire after 15 minutes. Refresh tokens expire after one
  day.
- CORS permits only `https://huboptimus.dev`. CORS is a browser control, not an
  authentication mechanism.

CloudFormation requires a unique `OperatorAuthDomainPrefix`. Callback and
logout parameters default to `https://huboptimus.dev/operator/` and are
constrained to the `huboptimus.dev` origin.

The stack outputs the raw API invoke URL, JWT issuer, web client ID, Hosted UI
base URL, callback URL, and logout URL. These values are the frontend runtime
configuration required before controlled intake can be enabled.

## Capacity and cost controls

- DynamoDB atomically permits three attempts per authenticated `sub` per UTC
  day. Keys contain a subject hash plus UTC date, not the raw Cognito subject;
  TTL removes stale windows asynchronously.
- API Gateway applies a global rate of 0.5 requests/second with burst 2.
- Lambda uses ARM64, 128 MiB, ten-second execution timeout and an eight-second
  end-to-end remote-fetch budget. Reserved concurrency defaults to 0. Explicit
  `publicPilotEnabled=true` raises it to 1 and simultaneously enables public
  email signup.
- DynamoDB is on-demand. There is no VPC, NAT gateway, SQS queue, EC2 instance,
  or always-on database.
- Application and API access logs retain seven days. They contain request IDs,
  route/status metrics, URL fingerprints, sizes, and error codes only—not page
  content, complete URLs, JWT subjects, or request bodies.
- Deployment requires `CostAlertEmail`; there is no default. A separate tagged
  $10/month pilot budget sends actual-spend alerts at 50%, 80% and 100% plus a
  100% forecast alert. A tagged Cost Anomaly Detection subscription is also
  always wired to that address. Budget accounting excludes credits and refunds
  so promotional balances cannot hide gross pilot consumption. The
  `costTag-project` cost-allocation tag must be activated in Billing for
  tag-scoped reports.

This architecture should have little or no idle infrastructure consumption;
API Gateway, Lambda, DynamoDB, Cognito and CloudWatch usage remain region- and
traffic-dependent. AWS Budgets and anomaly alerts notify—they do not hard-stop
spend. The stage throttle, per-subject quota and reserved concurrency are the
enforced capacity bounds. The $10 pilot budget is separate from any wider
account-level budget.

## Fetch boundary

Every submitted URL and redirect hop is restricted to ASCII HTTP/HTTPS with a
default port. Credentials, local/internal hostnames, private, loopback,
link-local, multicast, reserved and known transition addresses are rejected.
All DNS answers must be public. Connections use a validated numeric address,
preserve Host/SNI, verify the connected peer, and do not use environment proxy
settings. Redirect targets are revalidated and capped at three.

The shared fetch deadline is eight seconds. The handler retains at most
1,000,000 response bytes and 24,000 extracted characters (plus a possible
ellipsis), rejects transformed/compressed bodies, and accepts only
`text/plain`, `text/html`, or `application/xhtml+xml`. It sends no cookies,
authorization headers, browser state, or page subresource requests.

## Activation blockers and limitations

- Pages currently expects `https://api.huboptimus.dev` and keeps controlled URL
  intake disabled. This candidate creates neither that custom domain nor DNS.
- The synthesized default is deliberately non-serving: Lambda reserved
  concurrency is zero and public signup is disabled. Enablement requires the
  exact `publicPilotEnabled=true` context as a separate owner decision.
- API Gateway 401 responses and the handler's 429 quota responses are transport
  errors outside the v1 application schema. The frontend must map them to clear
  sign-in and daily-limit states before its feature flag is enabled.
- Public email signup can be abused by creating multiple accounts. Global API
  throttling and Lambda concurrency bound backend capacity, but production may
  still need CAPTCHA/risk controls or invitation policy.
- Application SSRF checks reduce risk but do not replace an independently
  governed egress firewall. DNS, public routing, certificate authorities and
  the content served by a public host remain external trust dependencies.
- Retrieved text is explicitly unreviewed and is not verified evidence.
- This candidate relies on the AWS SDK v3 supplied by the managed Node.js 22
  Lambda runtime for its single DynamoDB update; a canonical integration may
  choose to bundle and pin that client.
