# RFC: Operator Controlled URL Intake

## Status

Lifecycle: **Partially Implemented**.

The decision remains Draft and unratified. A local/private single-URL endpoint
and a browser fallback exist in the repository (implementation PRs #1717 and
#1720), with contract tests in
`tests/test_hub_api_controlled_url_intake.py`. This is not evidence of a public
deployment, complete RFC implementation, source verification, crawling, or
truth adjudication.

Issue #1835 adds a repository deployment candidate for an authenticated
owner/team public boundary around this local endpoint. Its OIDC, gateway and
same-origin artifacts do not prove that Entra, EC2, DNS, TLS or the public API
is deployed. The operational gates are recorded in
[`docs/maintenance/operator_oidc_owner_team.md`](../maintenance/operator_oidc_owner_team.md).
The narrower public contract, including NGINX edge errors and the versioned
gateway envelope, is
[`ops/ec2/operator_public_intake.v1.schema.json`](../../ops/ec2/operator_public_intake.v1.schema.json).

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

This RFC does not by itself authorize public exposure, crawler behavior,
browser-side third-party fetching, authentication, storage, or analysis
contract changes. The narrower owner/team authentication candidate is reviewed
separately under #1835 and remains subject to its deployment evidence. Existing
code must be evaluated against its reviewed issues, tests, and deployment
record.

## Parent boundary

This RFC extends `docs/rfc/ingestion_evidence_intake_boundary.md`.

That parent boundary permits preservation of the submitted URL, retrieval date,
visible title, source domain, source type, and whether content was fetched or
merely referenced. It does not turn retrieved material into verified evidence.

## Implemented narrow flow

```text
authenticated private Operator URL
-> POST /api/intake with {"url": "..."}
-> OIDC session, exact Origin, role, capability and rate/concurrency checks
-> exact flat JSON if NGINX rejects before/instead of the gateway
-> versioned public envelope gateway
-> internal POST /intake/url with {"url": "..."}
-> validate URI, host, port and resolved addresses
-> controlled single-resource fetch
-> content-type and byte bounds
-> bounded HTML/plain-text extraction
-> flat provenance response
-> Operator browser-local draft
```

NGINX and the gateway share one `req_<32 hex>` public request identifier. A
successful gateway response is accepted only when its original URL equals the
submitted URL exactly, its redirect records form one contiguous chain to
`final_url`, and `source_domain` matches that final URL. A structurally valid
response for a different request is rejected before its text is returned.

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
- redirects without exactly one non-empty `Location` header;
- non-200 or partial (`Content-Range`) success responses;
- compressed or otherwise transformed response bodies;
- ambiguous `Content-Length`/`Transfer-Encoding` framing and bodies that end
  before their declared length;
- duplicate, empty, unknown, or transformation charsets and bytes that are
  invalid for the declared text encoding; decoding never substitutes
  replacement characters;
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
- sends no cookies, authorization header, local credentials, or browser state;
- requests `Accept-Encoding: identity` and rejects any encoded or partial body
  instead of presenting undecoded or incomplete bytes as source text;
- validates every representation/framing header occurrence, permits either one
  decimal `Content-Length` or one supported `chunked` transfer framing, and
  rejects an early end-of-body against a declared length.

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
| Browser request deadline | 15 seconds before a local `url_fetch_timeout` fallback |
| Redirects | At most 3 |
| Retained raw response body | 1,000,000 bytes |
| Extracted source text | At most 24,000 characters before an optional ellipsis |
| Maximum returned `text` | 24,001 characters including an optional ellipsis |
| HTML element depth | At most 256 open elements; exceeding it stops parsing fail-closed |
| Candidate `main`/`article` regions | At most 64 |
| Remote request method | `GET` |
| Accepted schemes | `http`, `https` |
| Accepted content encoding | absent or `identity` |
| User-Agent | `HUB_Optimus-Operator-URL-Intake/0.1 (+https://huboptimus.dev/operator/)` |

The reader requests one byte beyond the raw-body limit to detect overflow and
retains at most 1,000,000 bytes. It sets `truncated=true` when the raw body,
cleaned source text, title, or HTML structural depth exceeds its bound; it does
not claim to have read or extracted the remainder. After the HTML depth limit
is reached the parser ignores the remainder rather than trying to recover from
untrusted mismatched closing tags.

The browser deadline is deliberately longer than the backend application
budget so normal backend timeouts can retain their versioned response. It also
bounds a stalled proxy, connection, or response body. Changing the input or
starting another request aborts the earlier browser request; a caller abort is
kept distinct from `url_fetch_timeout`.

## Extraction behavior

The current extractor:

- accepts HTML, XHTML, and plain-text responses;
- parses an exact supported media type, accepts zero or one unambiguous safe
  text `charset` parameter, rejects unknown or transformation codecs such as
  escape decoders, and rejects undecodable bytes without replacement;
- ignores non-content containers such as `aside`, `canvas`, `dialog`, `footer`,
  `form`, `header`, `iframe`, `nav`, `noscript`, `script`, `style`, `svg`, and
  `template`, plus containers explicitly labelled as cookie, consent,
  navigation, advertising, sharing, sidebar, related-content, or promotional
  UI;
- preserves spacing across inline HTML elements instead of splitting one
  sentence into unrelated fragments;
- scores individual `main`/`article` regions against the cleaned document,
  avoiding replacement of a longer document by an unrelated article card;
- preserves a cleaned document title when available;
- normalizes whitespace, removes duplicate cleaned lines, and preserves short
  structured facts such as headings, identifiers, and list items;
- returns non-empty bounded text or a controlled `empty_extraction` error.

It is a bounded heuristic text extractor, not a complete article parser. It may
still retain unlabelled boilerplate or omit meaningful dynamic, embedded,
caption, or short-form content. It does not:

- execute JavaScript;
- interact with cookie banners;
- log in;
- bypass paywalls;
- fetch document links or embedded resources;
- infer unavailable text.

## Operator behavior

The repository Operator posts only `{"url": sourceUrl}` when it is served from
the exact authenticated private origin `https://api.huboptimus.dev`. Optional
pasted text is never included in that request: it remains separately attributed
operator context. The public Sites Operator never calls the intake API. With a
URL and pasted text it prepares the local text-review flow and records that the
URL was supplied but not fetched; with a URL alone it offers the explicit
owner/team login route and asks for pasted source text as the public fallback.

On success, it:

- shows `text` in a review preview and requires explicit human confirmation
  before preparing a draft;
- preserves submitted and final URL, source domain, title, retrieval time,
  redirect chain, content type, byte count, truncation, and unreviewed status;
- canonicalizes source text to NFC with LF line endings, proposes up to five
  mechanical source lines, then requires the operator to confirm one to five
  exact passages whose Unicode-code-point locators and SHA-256 fingerprint use
  that same canonical representation;
- rejects a selected passage when the exact same text occurs more than once in
  the source, asking the operator to expand it until the locator is unique,
  rather than silently binding it to the first occurrence;
- creates one attributed claim and one source-excerpt record per selection;
- links those records explicitly as attribution support, not independent
  corroboration;
- keeps claims, excerpts, inference boundaries, uncertainty, provenance, and
  next review action separate in a draft `CaseInput v1` payload.

On failure, it:

- shows the controlled error message;
- asks the operator to reauthenticate, obtain an assigned role, retry later, or
  use the locally attributed pasted-text flow, according to the bounded error;
- does not fetch the third-party URL directly from the browser;
- does not classify the failed source as false or invalid.

On the authenticated private origin, supplying text and a URL still retrieves
the URL. The retrieved page supplies the source-bound excerpts; the pasted text
is recorded separately as `operator-provided-context-not-attributed-to-source`.
On the public origin the URL is not sent and the pasted text itself becomes the
review source with unverified URL attribution.

Operator context longer than the local 1,200-character metadata field is
stored with explicit original/canonical/stored character counts, a truncation
flag, and the SHA-256 fingerprint of the complete canonical context. It is not
silently presented as complete: the input hint states the limit and both the
primary result and Advanced readout show retained/original Unicode counts and
the separately attributed retained text.

The browser keeps the exact submitted URL only long enough to perform the
controlled request and compare the in-flight request with the current intake.
The exact URL, including path, query, and fragment, is visible to the controlled
intake service even though the fragment is not sent onward in an HTTP request.
Operator therefore warns users not to submit private or signed links, tokens,
one-time codes, or personal data in a URL. The request body still contains only
that URL and never the separately supplied operator context.
Draft, memory, provenance, redirect, and sharing records retain only each URL's
public origin; credentials, path, query, and fragment are withheld because any
of them can contain an opaque secret under an unknown name. Editing the URL
advances the intake generation and discards an earlier response. Editing
operator context or source type invalidates the draft but does not cancel a
valid URL retrieval already in flight; both preparation controls remain
disabled until that retrieval settles.

The Advanced normalizer delegates to the same retrieval and confirmation gate
as the primary action. Removing confirmation, editing a case field, or adding
or removing a claim/evidence record invalidates saving and sharing until a new
draft is prepared. Structural relationships and evidence claim references are
reconciled after record changes so no removed record remains referenced.

The Advanced result viewer is also fail-closed. It accepts either the exact
successful backend response identity or the explicit browser-local normalized
draft identity, requires the complete `AnalysisResult` shape and record types,
checks claim/evidence references, and binds the response to the current case
and core version. When a non-empty input summary is present it must also match.
Malformed, oversized, unrelated, cross-case, or stale responses clear the
visible result instead of being rendered with plausible-looking fallbacks. The
generated local handoff command performs the same envelope and case-identity
checks before printing a response for the viewer.

The primary action prepares a browser-local source review draft. It does not
claim to analyze truth, corroborate the underlying statements, infer intent,
score risk, or execute the Semantic Engine. Changing the URL, context, or
source type invalidates the previous shareable draft. Human-readable share
text enumerates all records within its explicit message bound and states the
number omitted when that bound is exceeded.

The static Operator contains only the same-origin path `/api/intake`; a runtime
origin check prevents the public Sites build from calling it. The explicit
login link and private-origin constant are repository configuration, not proof
that the service is deployed, reachable, secure, or available.

## Storage and privacy

The endpoint returns fetched text within the request/response lifecycle and
does not add a server-side fetched-text store. No persistence, retention,
encryption, or deletion guarantee is established by this RFC.

No implementation may log full article text, personal data, cookies,
authorization headers, or sensitive operator content by default without a
separately reviewed policy and change.

The browser's Advanced console can explicitly save one complete current case
in its local browser profile. The saved envelope is versioned, validated as a
`CaseInput v1` before any UI mutation, and remains until it is replaced or
explicitly deleted. Clearing visible fields does not delete that saved case and
the UI says so. Loading a saved case aborts and clears any live Primary URL
intake/selection binding, keeping saved-case provenance separate from a later
source retrieval. Meta-learning candidates use a separate IndexedDB lifecycle
with inspect, export, import, per-record/per-case deletion, and human-only state
transitions; neither local store is canonical project knowledge.

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
- `unsupported_content_encoding`;
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
- duplicate representation headers, ambiguous framing, partial responses,
  encoded bodies, early EOF, non-scalar Unicode, and excessive JSON nesting;
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
