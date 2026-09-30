# Operator owner/team OIDC deployment runbook

Issue: `#1835`

Status: **repository deployment candidate; not evidence of a live identity or
EC2 deployment**.

## Decision

Authenticated URL intake is restricted to accounts explicitly assigned one of
two Microsoft Entra application roles:

- `HUB.Owner`;
- `HUB.Operator`.

The identity boundary is a single-tenant Entra confidential web application.
The enterprise application must require assignment. The two roles must belong
to the same App Registration used for login so Entra emits them in the ID
token's `roles` claim. oauth2-proxy v7.15.3 maps that claim to its groups input
and accepts only those two exact values. Email addresses, display names, tenant
groups, domains, and caller-supplied headers are not authorization inputs.

The initial deployment deliberately sets `cookie_refresh = "0"`. Reauthentication
happens when the 55-minute session expires; silent refresh must not be enabled
until Entra role preservation during refresh is proven against the pinned
oauth2-proxy release.

## Same-origin topology

The public static site and authenticated intake have different duties:

```text
public Sites Operator
  -> pasted source text only
  -> explicit login link

api.huboptimus.dev:443 (NGINX, only public service)
  -> /operator/       authenticated static Operator
  -> exact /oauth2/start, /oauth2/callback and /oauth2/sign_out routes
                       oauth2-proxy on 127.0.0.1:4180
  -> /api/intake      authenticated gateway on 127.0.0.1:8081
                           -> local hub-api on 127.0.0.1:8080/intake/url
  -> Redis sessions   127.0.0.1:6379 only
```

The browser never stores an ID token, access token, client secret, cookie
secret, or internal capability. It sends `POST /api/intake` only while its
origin is exactly `https://api.huboptimus.dev`, using the opaque secure session
cookie. The public Sites origin does not call the API; a URL plus pasted text is
handled locally as operator-provided text with an unverified URL attribution.

The API never redirects failures. NGINX returns one exact two-field JSON shape
for edge failures; the gateway returns the versioned envelope. Both use the
same `req_<NGINX request id>` value in the body and response header. The private
console is entered explicitly through:

```text
https://api.huboptimus.dev/oauth2/start?rd=https%3A%2F%2Fapi.huboptimus.dev%2Foperator%2F
```

The protected console is deliberately not an offline PWA: on the private
origin it unregisters Operator service workers, removes Operator shell caches,
and NGINX sends `Cache-Control: no-store`. The visible sign-out action clears
the oauth2-proxy session through the fixed same-origin route and returns only
to `/signed-out`; callers cannot supply another destination. Browser-local
draft/learning retention remains a separate, explicitly visible local-storage
boundary rather than an authentication cache.

## Repository artifacts

- `ops/ec2/oauth2-proxy.cfg.example`: pinned Entra, role and Redis-session
  contract;
- `ops/ec2/oauth2-proxy.service`: fail-closed version/config preflight and
  systemd sandbox;
- `ops/ec2/nginx/operator-api.conf`: TLS, `auth_request`, exact Origin, header
  allowlist and same-origin routes;
- `ops/ec2/operator-intake-gateway.py`: bounded authenticated gateway;
- `ops/ec2/operator-intake-gateway.service`: loopback service and sandbox;
- `ops/ec2/operator_public_intake.v1.schema.json`: browser/gateway envelope;
- `site/operator/index.html`: public/manual and private/authenticated browser
  behavior, sign-out and private-cache removal;
- `site/operator/sw.js`: public PWA shell with an explicit private-origin
  unregister/fetch bypass.

NGINX removes client cookies, bearer tokens, Authorization, and all client
identity/capability headers before the gateway hop. It constructs the gateway
request from the identity returned by oauth2-proxy plus a root-managed internal
capability. The gateway independently validates capability, subject, role,
Origin, framing, size, rate/concurrency limits and the local upstream envelope.
It requires the upstream `url` to equal the requested URL exactly, validates a
contiguous redirect chain and final hostname, and rejects stale or cross-source
responses before their content can cross the public boundary.

## Prerequisites and deployment order

Activation is blocked until all of these are true:

1. `#1832` has been reviewed and merged;
2. `#1831` has deployed the reviewed full commit SHA to EC2 and recorded that
   exact release;
3. `api.huboptimus.dev` resolves only to the intended host and has a valid TLS
   certificate;
4. Redis is installed, protected, bound only to loopback, and unavailable from
   the public network;
5. the Entra tenant, App Registration, Enterprise Application, roles,
   assignments, Conditional Access and MFA policy have been reviewed by the
   owner;
6. the host has the pinned oauth2-proxy v7.15.3 binary and NGINX with
   `ngx_http_auth_request_module`;
7. a real authorized owner account, authorized team account and unassigned
   account are available for acceptance tests.

Do not expose oauth2-proxy, Redis, the gateway, or hub-api on a non-loopback
address.

## Entra configuration

1. Create or select one single-tenant App Registration.
2. Add the exact Web redirect URI
   `https://api.huboptimus.dev/oauth2/callback`.
3. Add the `HUB.Owner` and `HUB.Operator` app roles with exact case and permit
   only users/groups as appropriate for this internal application.
4. In the Enterprise Application, set **Assignment required?** to **Yes**.
5. Assign the owner and approved team identities to the intended role. Do not
   grant access through email-domain matching.
6. Apply the tenant's MFA and Conditional Access requirements.
7. Record the tenant ID and client ID in the installed config; never commit the
   client secret.

The issuer must remain
`https://login.microsoftonline.com/<TENANT_ID>/v2.0`. Do not use `common`,
`organizations`, `consumers`, or another tenant.

## Host secret files

Create secrets outside the release tree:

```text
/etc/hub-optimus/secrets/oauth2-proxy-client-secret
/etc/hub-optimus/secrets/oauth2-proxy-cookie-secret
/etc/hub-optimus/secrets/operator-intake-capability.conf
/etc/hub-optimus/operator-intake-gateway.env
```

The client-secret file contains only the Entra secret value with no trailing
newline. The cookie-secret file contains exactly 32 cryptographically random raw
bytes. The NGINX include defines `$hub_internal_capability` once. The gateway
EnvironmentFile defines `HUB_OPERATOR_INTAKE_CAPABILITY` with the same value.
That capability must be an unpadded 43–128-character base64url value generated
from cryptographically random bytes. The EnvironmentFile is a root-managed
systemd input for the gateway's isolated dynamic user, not a shell or shared
host environment. Give each service only the minimum read access it needs; do
not place values in shell history, Git, support output, or this runbook.

## Preflight

Run repository checks from the exact release checkout:

```bash
python -m pytest -q \
  tests/test_ec2_operator_api_proxy_config.py \
  tests/test_ec2_oauth2_proxy_config.py \
  tests/test_ec2_operator_intake_gateway.py \
  tests/test_operator_oidc_boundary.py \
  tests/test_operator_private_session_boundary.py \
  tests/test_operator_pwa_product_actions.py
python -m json.tool \
  ops/ec2/operator_public_intake.v1.schema.json >/dev/null
python -m py_compile ops/ec2/operator-intake-gateway.py
```

On the target host, validate the installed artifacts before any reload:

```bash
/usr/local/bin/oauth2-proxy-v7.15.3 \
  --config=/etc/hub-optimus/oauth2-proxy.cfg --config-test
nginx -t
systemctl daemon-reload
systemctl start redis-server
systemctl start oauth2-proxy operator-intake-gateway hub-api
systemctl reload nginx
```

Do not continue when a version check, config test, dependency, secret read,
certificate, DNS check or service sandbox fails.

## Acceptance matrix

Test against the deployed commit, not a developer checkout:

| Case | Expected result |
| --- | --- |
| Public Sites, URL only | No API request; localized private-intake action |
| Public Sites, URL plus pasted text | Local review flow; URL recorded as not fetched |
| Private console without session | Explicit login flow; no protected asset disclosed |
| Private API without session | 401 JSON; no redirect or upstream call |
| Wrong/missing Origin | 403 JSON; no upstream call |
| Valid identity without either app role | 403 JSON; no upstream call |
| `HUB.Owner` | Console loads; one reviewed URL request can reach intake |
| `HUB.Operator` | Same bounded intake behavior as owner |
| Forged `X-Hub-*`, `X-Auth-*`, Cookie or Authorization headers | Values do not reach gateway/upstream |
| More than 4,096 request bytes | Rejected before hub-api |
| Subject/IP rate or concurrency excess | 429/503 bounded envelope; no queue growth |
| Expired session | 401 JSON; explicit reauthentication required |
| Explicit sign-out | Session cookie cleared; fixed `/signed-out`; protected shell/assets return 401 afterward |
| Private console offline after logout/expiry | No cached protected shell is returned |
| Method/body/deadline/edge-upstream failure | Exact flat JSON for 405/408/413/429/500/502/503/504; never an HTML error page |
| Upstream response for a different URL | 502 versioned rejection; no mismatched source content returned |
| Successful or failed request correlation | Body and `X-Request-ID` contain the same `req_` identifier |
| Safari/iOS with tracking prevention | Same-origin session works without third-party cookie dependence |

For every authenticated gateway response, verify the versioned JSON envelope.
NGINX edge failures occur before or instead of that contract and use the exact
flat shape and error/status map in
`operator_public_intake.v1.schema.json`; the browser validates it separately.
The callback route disables both access and error logging so its code/state
query cannot enter NGINX logs. Other logs may record request ID, status, latency
and bounded operational counters; they must not record the submitted URL/body,
fetched text, cookies, authorization codes, tokens, secrets, internal
capability, or full identity claims.

## Rollback

If authentication, role enforcement, envelope validation, or the intake
gateway misbehaves:

1. remove the public `operator-api.conf` from the active NGINX include set and
   run `nginx -t`;
2. reload NGINX, which removes the public boundary without changing the public
   Sites manual-text flow;
3. stop `operator-intake-gateway` and `oauth2-proxy`;
4. roll the EC2 release back through the reviewed `rollback-current` process;
5. retain request IDs and secret-free diagnostics, rotate credentials only
   when exposure is suspected, and record the incident/decision in GitHub.

Rollback must not silently switch Sites to unmerged files or expose the local
hub-api directly.

## What merge does not prove

Merging these artifacts proves only reviewed repository behavior and tests. It
does not prove that Entra roles are assigned, secrets exist, MFA/Conditional
Access is effective, DNS/TLS is correct, Redis is hardened, EC2 runs the exact
commit, or a real Safari/iOS identity flow passes. Those are deployment and
acceptance gates for `#1835`; the issue must remain open until their evidence is
recorded.
