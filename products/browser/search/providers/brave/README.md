# Brave Web adapter (inactive candidate)

Standalone server-side net10.0 library, first increment of the
[hybrid design](../../../../../docs/superpowers/specs/2026-11-07-search-hybrid-brave-design.md).
No application, SearchHost, remote API or workflow references this project.
No account, subscription, key, gateway or Azure resource is configured.

## Run offline acceptance

From `products/browser/search`, using SDK 10.0.403:

```sh
dotnet run --project providers/brave/tests/Optimus.Search.Brave.Tests -c Release
```

No NuGet packages beyond framework references. Fixtures and credentials are
synthetic. One real handler check uses owned loopback TCP listeners; no Brave
request or external destination is used. Test output contains only case names
and exception type names, not fixture bodies or supplied credentials.

## Contract

`BraveSearchProvider(string subscriptionToken)` owns its HTTP client/handler;
dispose the provider after use. Construction performs no request.
`SearchAsync(query, language, cancellationToken)` returns at most 20
`BraveSearchResult` records with Title, Url, Content and Source = Brave.
The library is intended only for a future server gateway. Do not embed a
subscription token in a browser distribution.

The request goes only to `https://api.search.brave.com/res/v1/web/search`, with
the subscription token in a header. It requests strict adult filtering, Web
results only and undecorated text. There is one adapter SendAsync call per
valid operation, no application retry or fallback. The runtime's underlying
transport is not a billing meter; the future gateway must reserve each attempt
before calling this library and retain a durable fail-closed global counter.
Pooled connections are not reused. Redirects, cookies, automatic decompression,
ambient proxy and ambient credentials are disabled; standard TLS validation
remains enabled.

Queries: nonempty, no controls, valid Unicode, at most 500 UTF-16 characters
and 75 whitespace-separated words. ES, CA, EN, DE, FR, RU and corresponding
two-letter region suffixes are mapped explicitly to the primary search language.
Other languages fail locally. Responses are limited to 1 MiB and JSON depth 32;
duplicate JSON fields fail. Maximum duration is 10 seconds with cooperative
transport/body cancellation. Caller cancellation propagates separately.

Malformed individual results are omitted; unsafe URLs and normalized duplicates
are omitted. Text is entity-decoded, stripped of tag-shaped markup and bounded
to 240/1200 characters without cutting surrogate pairs. Results are plain text;
future renderers must never interpret them as HTML. A recognized search response
without a Web section, or with an empty Web section, can yield no results.
Errors use typed BraveSearchFailure codes and generic exceptions without raw
HTTP error bodies, request URLs, credentials or inner transport exceptions.

## Evidence and limits

Local SDK 10.0.403: initial compiling contract stub failed 46/46 behavioral
tests; implementation then passed 46/46. Extended acceptance passed 59/59,
including actual streamed size enforcement, actual 10-second body deadline,
caller cancellation/disposal, duplicate/deep JSON, status classification and
real handler redirect/cookie/proxy isolation. Existing backend console tests
passed 51/51 on the available e69d3f9 source snapshot; this does not certify a
newer full repository or a new Windows GUI.

No live Brave relevance, provider TLS connectivity, billing, quota persistence,
gateway authentication, Windows credential protection, UI or family-safety
acceptance is claimed. This increment does not change the frozen #2062 test.
No production test runner or GitHub Actions workflow is added in this scope.

The library writes no files and has no logging or response cache. Returned
results remain in caller memory; the caller must enforce view lifetime and
prevent persistence. The future gateway/platform must suppress HTTP tracing
that captures queries, headers or bodies. No forensic erasure is promised.

Brave's [API documentation](https://api-dashboard.search.brave.com/api-reference/web/search/get)
was inspected on 2026-11-07. Its
[retention and billing guidance](https://api-dashboard.search.brave.com/documentation/resources/help-feedback)
requires an applicable agreement before retaining API data. Confirm plan/use
rights before activation; do not ingest results into the own index or claim
memory. Strict filtering alone does not establish complete family protection.

## Next increment

Separate reviewed gateway/protocol: server-only mounted secret, authenticated
revocable remote clients, durable 100-attempt pilot accounting and stop path.
Then a separate Windows integration with explicit source choice and external
query notice. Live relevance and any spending require their exact activation
conditions; no service is enabled by building this library.
