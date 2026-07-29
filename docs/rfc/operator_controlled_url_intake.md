# RFC: Operator Controlled URL Intake

## Status

Lifecycle: **Partially Implemented**.

The decision remains Draft and unratified. A local/private single-URL endpoint
and a browser fallback exist in the repository (implementation PRs #1717 and
#1720), with contract tests in
`tests/test_hub_api_controlled_url_intake.py`. This is not evidence of a public
deployment, complete RFC implementation, source verification, crawling, or
truth adjudication.

Issue #1753 reconciles this record with the implementation. The versioned
application payload contract is
[`ops/ec2/controlled_url_intake.v1.schema.json`](../../ops/ec2/controlled_url_intake.v1.schema.json).
When prose and that schema disagree about request fields, response fields,
error codes, or limits, the schema and executable tests are the narrower source
of truth. Network and security behavior remains implemented by
`ops/ec2/hub-api.sh`.

## Decision boundary

HUB_Optimus Operator may request URL-only intake only through a controlled
backend step.

A submitted URL is a source reference until the backend retrieves, bounds,
extracts, and records source text. Intake does not verify truth, bypass access
controls, or convert a URL into a conclusion.

This RFC authorizes no additional public API exposure, crawler behavior,
browser-side third-party fetching, authentication changes, storage changes, or
analysis contract changes. Existing code must be evaluated against its reviewed
issues, tests, and deployment evidence.

## Parent boundary

This RFC extends `docs/rfc/ingestion_evidence_intake_boundary.md`.

That parent boundary permits preservation of the submitted URL, retrieval date,
visible title, source domain, source type, and whether content was fetched or
merely referenced. It does not turn retrieved material into verified evidence.

## Implemented narrow flow

```text
Operator URL
-> POST /intake/url with {"url": "..."}
-> validate URI, host, port and resolved addresses
-> controlled single-resource fetch
-> content-type and byte bounds
-> bounded HTML/plain-text extraction
-> flat provenance response
-> Operator browser-local draft
```

The endpoint fetches one supplied resource and validated redirect hops. It does
not crawl links, execute page JavaScript, retrieve embedded resources, run the
Semantic Engine, or make a truth decision.

## Canonical application payload contract

The canonical v1 schema contains three document shapes:

- `request`;
- `success_response`;
- `error_response`.

It also records the reviewed runtime limits and stable application error-code
mapping. HTTP framing, invalid UTF-8, malformed JSON, non-object JSON, and
oversized request-body errors occur before the URL-intake application handler;
those generic API error bodies are intentionally outside this application
schema.

### Endpoint and request

```text
POST /intake/url
Content-Type: application/json
```

```json
{
  "url": "https://example.com/article"
}
```

Only `url` has application meaning. The current v1 handler ignores additional
object properties. In particular, it does not implement `source_hint` or
`operator_context`, and ignored fields do not become context, evidence,
analysis input, or provenance.

### Flat success response

```json
{
  "status": "ok",
  "intake_type": "controlled_url",
  "url": "https://example.com/article",
  "final_url": "https://example.com/article",
  "source_domain": "example.com",
  "retrieved_at_utc": "2026-07-20T00:00:00+00:00",
  "title": "Public source article title.",
  "text": "Plain extracted article text.",
  "content_type": "text/html; charset=utf-8",
  "bytes_read": 4096,
  "truncated": false,
  "redirects": [],
  "verification_status": "unreviewed",
  "learning_status": "candidate-source-not-verified",
  "extraction_notes": [
    "Fetched by local backend controlled URL intake.",
    "No cookies, authentication, browser automation, or paywall bypass were used.",
    "Text extraction is source-bound and does not verify truth."
  ]
}
```

The response is flat. There is no nested `intake` object. The accepted final
resource is `final_url`, not `resolved_url`. `bytes_read` replaces the earlier
proposal's `text_length`; it records retained response bytes, not character
count.

### Flat application error response

```json
{
  "status": "error",
  "error": "url_fetch_failed",
  "message": "URL fetch failed with HTTP 403.",
  "url": "https://example.com/article",
  "verification_status": "unreviewed"
}
```

The stable code field is `error`, not `error_code`. The current handler echoes
the submitted `url` value for provenance, including a non-string value on the
`invalid_url` path. A controlled fetch failure says nothing about whether the
source is true, false, valid, or invalid.

## URL validation boundary

The implementation rejects:

- non-HTTP/HTTPS schemes;
- empty or malformed URLs;
- raw spaces, control characters, and Unicode IRIs;
- URLs containing credentials;
- missing, malformed, local, or non-public hosts;
- non-default HTTP/HTTPS ports;
- private, loopback, link-local, multicast, unspecified, and other non-global
  resolved addresses;
- known IPv6 transition forms that embed a non-global IPv4 destination;
- redirects to a rejected destination;
- redirects without `Location`;
- unsupported content types;
- empty extracted text.

International hostnames must use an IDNA A-label. Non-ASCII path and query text
must be percent-encoded before submission.

## SSRF and network boundary

For each supplied URL and permitted redirect hop, the current launcher:

- parses the URL before fetching;
- resolves the hostname and rejects the whole hop when any returned address is
  not permitted;
- disables environment proxies;
- opens a numeric socket to one of the validated addresses;
- verifies that the connected peer remains in the validated set;
- preserves the hostname for the HTTP `Host` header and HTTPS SNI/certificate
  verification;
- validates every redirect before the next request;
- sends no cookies, authorization header, local credentials, or browser state.

The synchronous Linux server uses one monotonic eight-second application budget
across address candidates, redirects, TLS, headers, and body reading.
Interruption of a blocking system DNS resolver is best-effort rather than a
portable cancellation guarantee. Infrastructure egress controls, NAT, firewall,
resolver configuration, and host deployment remain outside the repository's
application-level proof boundary.

## Runtime limits

These are implemented values, not recommendations:

| Boundary | Implemented value |
| --- | --- |
| JSON request body | 4,096 bytes |
| Submitted URL | 2,048 characters |
| Total fetch budget | 8 seconds |
| Redirects | At most 3 |
| Retained raw response body | 1,000,000 bytes |
| Extracted source text | At most 24,000 characters before an optional ellipsis |
| Maximum returned `text` | 24,001 characters including an optional ellipsis |
| Remote request method | `GET` |
| Accepted schemes | `http`, `https` |
| User-Agent | `HUB_Optimus-Operator-URL-Intake/0.1 (+https://huboptimus.dev/operator/)` |

The reader requests one byte beyond the raw-body limit to detect overflow,
retains at most 1,000,000 bytes, and sets `truncated=true`; it does not claim to
have read or extracted the remainder.

## Extraction behavior

The current extractor:

- accepts HTML, XHTML, and plain-text responses;
- decodes the declared charset when known and falls back to UTF-8 with
  replacement for undecodable bytes;
- ignores `canvas`, `iframe`, `noscript`, `script`, `style`, `svg`, and
  `template` element content;
- preserves a cleaned document title when available;
- normalizes whitespace, removes duplicate cleaned lines, and drops short
  non-sentence fragments;
- returns non-empty bounded text or a controlled `empty_extraction` error.

It is a bounded text extractor, not a complete article parser. It may retain
navigation or other visible boilerplate and may omit meaningful dynamic,
embedded, caption, or short-form content. It does not:

- execute JavaScript;
- interact with cookie banners;
- log in;
- bypass paywalls;
- fetch document links or embedded resources;
- infer unavailable text.

## Operator behavior

The repository Operator posts only `{"url": sourceUrl}` to the controlled
endpoint when a URL exists and source text is empty.

On success, it:

- uses `text` as the browser-local draft input;
- preserves submitted and final URL, source domain, title, retrieval time,
  redirect chain, content type, byte count, truncation, and unreviewed status;
- continues through the existing local conservative-triage UI.

On failure, it:

- shows the controlled error message;
- asks the operator to paste source text;
- does not fetch the third-party URL directly from the browser;
- does not classify the failed source as false or invalid.

If the operator supplies text and a URL, the browser treats the URL as
operator-provided, unfetched attribution. The primary action analyzes actual
text only: pasted text or text returned by controlled intake.

The hard-coded endpoint URL in the static Operator is repository configuration,
not proof that the service is publicly deployed, reachable, secure, or
available.

## Storage and privacy

The endpoint returns fetched text within the request/response lifecycle and
does not add a server-side fetched-text store. No persistence, retention,
encryption, or deletion guarantee is established by this RFC.

No implementation may log full article text, personal data, cookies,
authorization headers, or sensitive operator content by default without a
separately reviewed policy and change.

## Stable application failure codes

The schema and launcher currently define:

- `invalid_url`;
- `invalid_url_host`;
- `invalid_url_port`;
- `unsupported_url_iri`;
- `unsupported_url_scheme`;
- `unsupported_url_credentials`;
- `unsupported_url_port`;
- `blocked_url_host`;
- `unresolvable_url_host`;
- `unsupported_content_type`;
- `empty_extraction`;
- `redirect_without_location`;
- `too_many_redirects`;
- `url_fetch_failed`;
- `url_fetch_timeout`;
- `url_fetch_unavailable`;
- `url_too_long`.

The schema's `x-hub-optimus-error-http-status` map records the current HTTP
status for each code. Generic request-body errors remain outside this list
because URL intake has not started when they occur.

## Security review checklist

The repository tests cover:

- URI, port, address, and redirect rejection;
- DNS rebinding/connection pinning boundaries;
- IPv6 transition-address cases;
- response size and extracted-text bounds;
- one total timeout budget;
- disabled environment proxies;
- absent cookies and authorization headers;
- malformed HTTP and read failures;
- single-resource fetching;
- unreviewed success and failure provenance.

Passing tests prove only those reviewed code paths. They do not attest the
configuration or behavior of a deployed host.

## Acceptance criteria for issue #1753

- One versioned schema defines current request, success, and application error
  payloads.
- The RFC, backend constants, Operator request, schema examples, limits,
  User-Agent, and error-code set are coupled by executable tests.
- No nested response, `resolved_url`, `error_code`, 40,000-character limit, or
  obsolete User-Agent is presented as the active contract.
- No network, deployment, storage, verification, or analysis capability is
  added by the reconciliation.
- GitHub remains the source of truth.

## Validation

```bash
python -m pytest -q \
  tests/test_hub_api_controlled_url_intake.py \
  tests/test_operator_pwa_product_actions.py
python -m json.tool \
  ops/ec2/controlled_url_intake.v1.schema.json >/dev/null
python tools/check_mojibake.py \
  docs/rfc/operator_controlled_url_intake.md
```
