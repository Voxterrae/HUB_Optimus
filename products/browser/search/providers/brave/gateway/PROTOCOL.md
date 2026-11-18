# Local Web gateway candidate protocol v1

Status: inactive, loopback-only acceptance candidate. Not a public service.
This is separate from the finite-catalog contract in PR #2098.

## Transport and request

The explicit library API starts a server at an ephemeral `http://127.0.0.1:PORT`.
There is no executable host, default configuration, deployment or listener
until a caller invokes StartAsync. Tests supply synthetic credentials/provider.
No production client may send real credentials over this candidate HTTP path;
public hosting requires a separate reviewed HTTPS ingress and secret setup.

Only `POST /v1/web/search` is accepted, with exact loopback Host, no Origin or
query string, `Content-Type: application/json` (optional UTF-8 charset) and one
`Authorization: Bearer TOKEN` header. TOKEN is64 lowercase hexadecimal
characters, distinct from the local SearchHost token and Brave subscription key.

```json
{"query":"Python programming","language":"en"}
```

Exactly those two fields; no duplicates, comments, trailing commas or extra
options. Body maximum4096 bytes and2-second read deadline. Query maximum500
UTF-16 characters and75 whitespace-separated words, no controls or malformed
Unicode. Primary language ES/CA/EN/DE/FR/RU; an optional two-letter region suffix
is accepted, as in es-ES. The existing Brave adapter determines provider mapping.

## Response

```json
{"version":1,"source":"Brave","results":[{"title":"Synthetic help","url":"https://example.org/help","content":"Synthetic text","source":"Brave"}]}
```

An empty results array is a successful empty search. Queries, tokens, provider
raw bodies and credential identities are not echoed. All application responses
set Cache-Control:no-store, X-Content-Type-Options:nosniff and
Referrer-Policy:no-referrer. No CORS or cookies are enabled.

| Status | Code | Meaning |
| --- | --- | --- |
| 400 | invalid-request | Invalid shape, fields or input |
| 401 | unauthorized | Missing, invalid, expired, revoked or unavailable registry |
| 403 | request-forbidden | Origin or unexpected Host |
| 404 | not-found | Unknown route |
| 405 | method-not-allowed | Only POST is supported |
| 413 | request-too-large | Body bound exceeded |
| 415 | unsupported-media-type | Unsupported content type or charset |
| 429 | gateway-busy | Another admitted operation is still active |
| 429 | quota-exhausted | All100 pilot reservations spent |
| 502 | upstream-failed | Generic provider/response failure |
| 503 | quota-unavailable | Durable state cannot be verified or forwarding stopped |
| 504 | request-timeout | Body/provider deadline expired |
| 504 | upstream-timeout | Adapter reported its own timeout |

Errors contain only an error code. A disconnected caller receives no guaranteed
response. Malformed requests rejected by Kestrel itself may have framework-level
responses; the table and privacy headers cover the application handler.

## Private operator state

Credential registry: bounded8192-byte strict JSON,1..8 unique hashes, UTC expiry.
Example uses a synthetic hash; never publish operational credentials.

```json
{"version":1,"credentials":[{"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","expiresUtc":"2026-11-08T00:00:00Z"}]}
```

The hash is SHA256 of the ASCII bearer token, not the token itself. Match uses
fixed-time comparison. Registry is reloaded for each request; remove/replace a
hash to revoke it. Missing, invalid, duplicate, oversized, symlinked or expired
state denies authentication. A backwards clock observation denies subsequent
auth until wall-clock time catches up. Requests already admitted are not
retroactively cancelled by registry edits; stop the server to stop active work.

Pilot quota is a separate operator-owned file, exclusively leased for the
entire server lifetime. `PilotQuota.Initialize(path)` creates only a fresh file;
startup never initializes, repairs or resets it.100 is lifetime total for this
pilot, not a per-client, monthly or per-process allowance.

After authenticated request validation, persist the increment plus pending
marker and Flush(true) BEFORE invoking the provider once. A completed or
cooperatively failed operation clears pending without decrementing count.
Process death while pending blocks future startup. A provider that has not
completed within250ms of cancellation leaves pending and stops all further
forwarding, including after restart. No retries, fallback, refunds or HTTP
reset route. Recovery requires operator investigation and a separately reviewed
pilot/key/budget decision; do not delete/reinitialize state to get past a block.

State must live on a trusted persistent local filesystem whose exclusive lease
and flush semantics are supported. Missing, malformed, exhausted or changed
records fail closed. OS/storage snapshots and a privileged operator can roll
back/replace files; this is not anti-administrator rollback protection or a
provider-enforced monetary cap. Production volume identity, permissions,
key/pilot binding and hard provider billing controls remain activation gates.

## Provider boundary

StartAsync receives a trusted server-side search delegate matching
BraveSearchProvider.SearchAsync. It must return its Task promptly and must use
the reviewed bounded adapter; untrusted extensions are not supported. The
gateway adds admission,10-second async deadline and cancellation handling.
It does not create or store the Brave key or persist queries/results. Caller
code and host instrumentation must also prevent logging, caching or retention.
