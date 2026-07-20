# RFC: Operator Controlled URL Intake

## Status

Draft / RFC-only / not implemented.

## Decision

HUB_Optimus Operator should support URL-only analysis only through a controlled backend intake step.

A submitted URL is a source reference until the backend explicitly retrieves, bounds, extracts, and records source text. Intake does not verify truth, does not bypass access controls, and does not convert a URL into a conclusion.

This RFC authorizes design discussion only. It does not authorize implementation, public API exposure, scraping infrastructure, crawler behavior, browser-side fetching, authentication changes, storage changes, or analysis contract changes.

## Parent boundary

This RFC extends `docs/rfc/ingestion_evidence_intake_boundary.md`.

That parent boundary already states that URL intake may preserve URL, retrieval date, visible title, source domain, source type, and whether content was actually fetched or merely referenced. It also requires separate issues/RFCs before implementation beyond manual/raw intake.

## Problem

Operator currently accepts a URL as reference but cannot read or analyze a URL by itself.

This creates product friction:

- users expect a news/article URL to produce a draft analysis;
- the current browser-only flow requires pasted article text;
- browser-side fetching would be fragile and unsafe;
- the product needs clear error behavior when a site blocks access, requires cookies, uses paywalls, or returns non-article content.

## Goals

- Allow a user to paste a public HTTP/HTTPS URL and request controlled intake.
- Fetch only the supplied URL, not a crawl of linked pages.
- Extract bounded plain text suitable for the existing Operator normalizer.
- Preserve source metadata and uncertainty.
- Fail clearly when content cannot be fetched or safely extracted.
- Keep the backend private/local by default unless a separate public deployment RFC approves exposure.
- Prevent SSRF, crawler drift, credential use, hidden tracking, and source laundering.

## Non-goals

This RFC does not add:

- implementation code;
- public API exposure;
- browser-side `fetch()` to third-party news sites;
- crawler infrastructure;
- recursive link traversal;
- paywall bypass;
- authentication or cookie replay;
- JavaScript browser automation;
- OCR;
- PDF/document extraction;
- vector storage;
- server-side memory persistence;
- dynamic OG per analyzed result;
- LLM-as-judge;
- truth verdicts;
- legal or geopolitical conclusions.

## Proposed controlled flow

```text
operator URL
-> validate URL
-> block unsafe destinations
-> controlled backend fetch
-> content-type and size checks
-> bounded HTML/text extraction
-> source metadata record
-> normalizer input draft
-> existing claim/evidence/inference/uncertainty rendering
```

## Endpoint shape for a later implementation

A later implementation may add a local-only endpoint:

```text
POST /intake/url
```

Example request:

```json
{
  "url": "https://example.com/article",
  "source_hint": "news-article",
  "operator_context": "operator-pwa"
}
```

Example success response:

```json
{
  "status": "ok",
  "intake": {
    "url": "https://example.com/article",
    "resolved_url": "https://example.com/article",
    "source_domain": "example.com",
    "retrieved_at_utc": "2026-07-20T00:00:00Z",
    "content_type": "text/html; charset=utf-8",
    "title": "Article title if available",
    "text": "Plain extracted article text...",
    "text_length": 12345,
    "truncated": false,
    "fetch_status": "fetched",
    "verification_status": "unreviewed",
    "limitations": [
      "Fetched content is not verification.",
      "Extraction may omit navigation, embeds, captions, or dynamic content."
    ]
  }
}
```

Example failure response:

```json
{
  "status": "error",
  "error_code": "fetch_blocked_or_unavailable",
  "message": "The URL could not be fetched or safely extracted.",
  "limitations": [
    "No claim was analyzed from URL-only input.",
    "Paste article text manually or try another public source."
  ]
}
```

## URL validation requirements

A later implementation must reject:

- non-HTTP/HTTPS schemes;
- empty or malformed URLs;
- URLs containing credentials;
- local hostnames;
- private, loopback, link-local, multicast, or unspecified IPs;
- redirects to blocked destinations;
- responses above configured size limits;
- unsupported content types;
- suspicious binary payloads;
- requests requiring cookies, login, or session replay.

## SSRF boundary

URL intake must defend against server-side request forgery.

Minimum requirements:

- parse and normalize the URL before fetch;
- resolve DNS and block private/internal addresses before request;
- re-check the final resolved URL after redirects;
- cap redirect count;
- cap timeout;
- cap response size;
- never send local credentials, cookies, authorization headers, or cloud metadata headers;
- block cloud metadata endpoints and localhost ranges explicitly.

## Fetch limits

Initial recommended limits:

- timeout: 8 seconds;
- redirects: max 3;
- response size: max 1 MB raw body;
- extracted text size: max 40,000 characters;
- request method: GET only;
- accepted schemes: `http`, `https`;
- default User-Agent: `HUB_Optimus-Operator-Intake/0.1 (+https://huboptimus.dev/operator/)`.

These values may change during implementation review, but limits must exist before merge.

## Extraction rules

The extractor should:

- prefer visible text from article-like HTML;
- remove scripts, styles, forms, navigation, cookie banners where reasonably detectable, and hidden elements;
- preserve title when available;
- preserve source URL and resolved URL;
- preserve retrieval timestamp;
- mark extraction as lossy and unverified;
- avoid inventing missing article text;
- fail clearly when content is too short, blocked, unsupported, or unusable.

The extractor must not:

- execute JavaScript;
- interact with cookie banners;
- log in;
- bypass paywalls;
- scrape related links;
- follow article recommendations;
- infer unavailable content.

## Output contract

URL intake output may populate the existing source normalizer fields:

- `source_url` from the final accepted URL;
- `source_text` from extracted plain text;
- `signal_source_type` from explicit source hint or conservative inference;
- metadata fields for retrieval time, source domain, title, fetch status, and extraction limitations.

URL intake must remain upstream of analysis. It prepares material; it does not decide truth.

## Operator UI behavior

When a URL is present and text is empty, a later UI implementation may show:

```text
Read URL
```

If intake succeeds:

```text
URL read. Review extracted text, then analyze.
```

If intake fails:

```text
URL could not be read safely. Paste article text manually.
```

The primary `Analyze` action should only analyze actual text, whether pasted manually or extracted by controlled intake.

## Storage and privacy

Initial implementation should not store fetched text server-side beyond transient request handling unless a separate storage policy is approved.

If request/response logs are needed, they must be limited to public-safe metadata:

- URL domain;
- status code category;
- error code;
- timestamp;
- byte counts;
- duration.

Do not log full article text, personal data, cookies, headers, or user-provided sensitive content by default.

## Failure codes

A later implementation should use stable error codes such as:

- `invalid_url`;
- `blocked_scheme`;
- `blocked_private_address`;
- `redirect_blocked`;
- `timeout`;
- `response_too_large`;
- `unsupported_content_type`;
- `fetch_blocked_or_unavailable`;
- `extractor_empty_text`;
- `extractor_low_confidence`.

## Security review checklist

Before implementation merge:

- SSRF protections are covered by tests;
- redirects are tested;
- private IPs are blocked;
- response size is capped;
- timeout is capped;
- no credentials/cookies are sent;
- no browser-side third-party fetch is added;
- extraction is bounded and non-executing;
- failure states are clear to the user;
- output marks intake as unverified.

## Acceptance criteria for this RFC

This RFC is acceptable when it:

- states that URL intake is not verification;
- requires backend-controlled intake rather than browser scraping;
- defines URL validation boundaries;
- defines SSRF protections;
- defines fetch and extraction limits;
- defines success/failure response shapes;
- defines Operator UI behavior;
- keeps implementation out of this PR;
- preserves GitHub as source of truth.

## Follow-up implementation plan

If accepted, implementation should proceed in small PRs:

1. `ops/api: add controlled URL intake endpoint`
   - endpoint only;
   - local/private API only;
   - SSRF/timeout/size tests.
2. `site/operator: add URL read action`
   - button and UI state only;
   - no browser third-party fetch;
   - consumes controlled endpoint.
3. `tests: add URL intake smoke fixtures`
   - local fixture server or mocked HTTP responses;
   - blocked private URL tests;
   - extraction failure tests.

## Validation

Documentation-only validation:

```bash
python tools/check_mojibake.py docs/rfc/operator_controlled_url_intake.md
```
