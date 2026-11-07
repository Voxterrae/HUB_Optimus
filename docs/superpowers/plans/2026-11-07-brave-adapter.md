# Brave adapter implementation plan

> **For agentic workers:** Use superpowers:executing-plans task by task. Steps use checkbox syntax.

**Goal:** Build only the inactive, independently testable Brave Web adapter approved in the hybrid design.

**Architecture:** Separate net10.0 library and console test project under products/browser/search/providers/brave. Production construction owns a hardened HTTP handler; an internal transport constructor permits synthetic offline tests. No reference from any application, gateway, existing backend or workflow.

**Tech Stack:** C#, .NET SDK 10.0.403, framework HTTP/JSON libraries; no packages.

**Spec:** docs/superpowers/specs/2026-11-07-search-hybrid-brave-design.md (first delivery only).

## Global constraints

- Maximum 500 query characters and 75 words; reject controls and unsupported language before sending.
- ES, CA, EN, DE, FR and RU map explicitly to Brave search language; no guessed fallback.
- HTTPS fixed provider destination; token only in x-subscription-token header.
- Maximum 20 results, 10-second deadline, 1 MiB response, JSON depth 32.
- Strict safe search, Web only, no decorations, retries, redirects, cookies or system proxy.
- Plain text, truthful Brave source, no response retention or logs.
- No activation, external query, real key, billing, Azure or application changes.

## Review focus

- Whitespace or control query bypass: reject before the transport runs, including 76 words.
- Cancellation during body streaming: caller cancellation remains distinguishable and body is disposed.
- Unknown-length and dishonest length bodies: enforce actual byte count, not only headers.
- Redirect/error bodies may carry secrets: never read them into diagnostic exceptions or follow them.
- Malformed text/URLs and duplicate fields: reject ambiguous JSON and do not return executable markup or credential-bearing URLs.

### Task 1: inactive adapter and complete offline acceptance

**Files:**
- Create providers/brave/src/Optimus.Search.Brave/Optimus.Search.Brave.csproj (paths relative to products/browser/search).
- Create same directory BraveSearchProvider.cs and SearchModels.cs.
- Create providers/brave/tests/Optimus.Search.Brave.Tests/Optimus.Search.Brave.Tests.csproj and Program.cs.
- Create providers/brave/README.md for commands, boundaries and evidence.

**Interfaces:**
- Public BraveSearchProvider(string subscriptionToken), IDisposable.
- Task<IReadOnlyList<BraveSearchResult>> SearchAsync(string query, string language, CancellationToken cancellationToken = default).
- BraveSearchResult(string Title, string Url, string Content, string Source).
- BraveSearchException with BraveSearchFailure {Authentication, RateLimited, Timeout, Transport, InvalidResponse, Upstream} and generic messages, no upstream exception retained.
- Internal constructor(string token, HttpMessageHandler handler), friend assembly only; deadline stays 10 seconds in tests.

- [ ] Write synthetic transport tests and compiling contract stub. Assert fixed emitted request, all languages, normalized result source, empty results, URL filtering, deduplication, text bounds, input/key validation, errors, no retries and no raw diagnostic leakage. Run and observe behavioral RED from NotImplementedException.
- [ ] Implement bounded adapter; run the console test suite and observe GREEN.
- [ ] Extend tests before any missing hardening: actual streamed over-limit/deadline/cancellation, duplicate/deep JSON, response disposal, caller pre-cancellation and real handler redirect/proxy policy via owned local proxy trap (without upstream requests).
- [ ] Run all new tests plus existing backend console suite; confirm actual SDK and zero build warnings. Review the whole branch independently, address material findings with RED/GREEN regressions.
- [ ] Publish only new adapter/plan/README files on an isolated draft branch. Verify GitHub blobs equal tested bytes and no runtime or CI paths changed. Preserve required signatures/checks and no merge.

Run from products/browser/search: dotnet run --project providers/brave/tests/Optimus.Search.Brave.Tests -c Release.
Expected: all tests PASS, exit 0, no provider network access.

Deferred design deliveries: gateway, durable global quota, client selector and protected credential store, live relevance and billing review. They are not implemented or claimed by Task 1.
