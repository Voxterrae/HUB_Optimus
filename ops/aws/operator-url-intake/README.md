# Operator URL intake infrastructure candidate

Fail-closed AWS CDK TypeScript implementation prepared under
[`#1917`](https://github.com/Voxterrae/HUB_Optimus/issues/1917).

Status: **candidate, disabled and not deployed**.

## Boundary

- authenticated `POST /intake/url` only;
- Cognito Hosted UI and short-lived JWT authorization-code flow intended for
  S256 PKCE;
- three attempts per authenticated subject per UTC day;
- strict SSRF, redirect, size, content-type, timeout and log-redaction limits;
- exact CORS origin `https://huboptimus.dev`;
- Lambda reserved concurrency `0` and public signup disabled by default;
- no OpenAI call, EC2, VPC, NAT Gateway, load balancer, SQS, custom domain or
  DNS change;
- mandatory cost-alert address, tagged USD 10 pilot budget and anomaly alert.

Exact CDK context `publicPilotEnabled=true` is required to raise concurrency to
one and permit verified-email public signup. Supplying that context, deploying,
changing DNS/TLS or activating the Pages feature flag requires a separate
owner-reviewed authorization.

See `OPERATOR_URL_INTAKE_DESIGN.md` and `CANDIDATE_STATUS.md`.

## Local validation

```bash
npm ci
npm run build
npm test -- --runInBand
npm exec --offline -- cdk synth -c publicPilotEnabled=false
```

Verified candidate result: TypeScript PASS, Jest 48/48 PASS and CDK synth PASS.

## Traceability starter attribution

The initial CDK scaffold derives from Lars Andersson's Traceability starter and
retains its Beer-Ware license in `LICENSE`. HUB_Optimus-specific operational
ownership remains governed by the canonical repository documents.

[Where the hell is the git project that owns this?](https://lars-andersson.medium.com/where-the-hell-is-the-git-project-that-owns-this-550bd96dd230)
