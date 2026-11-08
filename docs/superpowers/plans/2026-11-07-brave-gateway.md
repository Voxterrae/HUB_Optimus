# Inactive Brave gateway implementation plan

> **For agentic workers:** Use superpowers:executing-plans. Implement inline, then independent whole-branch review.

**Goal:** Prepare real local HTTP gateway acceptance with authentication and durable100-attempt admission; keep production inactive.

**Architecture:** New ASP.NET Core library and console tests under products/browser/search/providers/brave/gateway. The library exposes explicit startup on an ephemeral127.0.0.1 port only, receives an explicitly supplied search delegate, and has no executable host/default key or production registration. Production host, TLS ingress, mounted secrets, Azure persistent volume and UI are separate activation increments.

**Tech Stack:** C# net10.0, SDK10.0.403, framework-only HTTP/JSON/cryptography/files.

**Spec:** docs/superpowers/specs/2026-11-07-search-hybrid-brave-design.md, gateway increment; issue #2113.

## Global constraints

- No live Brave requests, real keys, subscription, billing, Azure or existing runtime/CI changes.
- POST /v1/web/search, strict UTF-8 JSON with exactly query/language;4096-byte bound and2-second request-read deadline.
- Query at most500 UTF-16 characters/75 words/no controls; ES/CA/EN/DE/FR/RU only.
- Authentication by a distinct64-lowercase-hex remote bearer credential, SHA256-only registry with explicit UTC expiry. Reload registry for every request; unavailable/expired/revoked means401.
- Lifetime exclusive file lease;100 total reserved attempts; flush durable state before calling provider, never refund failed/uncertain attempts. Missing/corrupt/changed state fails closed.
- Concurrency1 with immediate busy rejection; no retry/fallback. Separate provider/library10-second deadline and request cancellation.
- No logs, raw request/provider details, persistence of results or query echo; no-store responses. Quota metadata is not a monetary cap or rollback-proof database.

## Review focus

- Authenticated malformed/oversized bodies must not consume a reservation or invoke provider.
- Process restart and second-process open must preserve quota/exclusion.
- Corrupt/missing state and write failure must stop forwarding, including after earlier success.
- Slow/cancelled work must not admit overlapping upstream operations or refund reservations.
- Revoked/expired tokens, duplicate fields and hostile Origin/Host/method must be rejected with generic silent responses.

### Task 1: authenticated gateway and durable reservation

**Files:** gateway/src/Optimus.Search.Brave.Gateway project with CredentialRegistry.cs, PilotQuota.cs, GatewayServer.cs, StrictInput.cs; gateway/tests/Optimus.Search.Brave.Gateway.Tests project/Program.cs; gateway/README.md and PROTOCOL.md.

**Interfaces:** PilotQuota.Initialize(path) explicitly creates fresh state only; PilotQuota.Open(path), TryReserve(), IDisposable hold exclusive lease; GatewayServer.StartAsync(credentialPath,quotaPath,searchDelegate,cancellationToken) binds loopback0 only, Address, IAsyncDisposable. Registry format version1 with1..8 credentials {sha256,expiresUtc}. Search delegate matches BraveSearchProvider.SearchAsync and returns IReadOnlyList<BraveSearchResult>.

- [ ] Write compiling contract stubs and offline HTTP/file tests; run to observe behavioral RED.
- [ ] Implement strict registry/request parsing, durable exclusive quota and local server; run GREEN.
- [ ] Verify real401/400/403/405/413/415/429/503, successful response, no-store, revocation, expiry, no provider on invalid/busy/exhausted requests, restart/failure reservation and cross-process lease.
- [ ] Build warning-free; run gateway and existing adapter suites, independently review, fix material findings with RED/GREEN tests.
- [ ] Publish only scoped additions in draft stacked on adapter75e3438; verify source readbacks, retain signature/check/activation gates. Update #2111 metadata with actual comment/CI inspection only.

Command from products/browser/search: dotnet run --project providers/brave/gateway/tests/Optimus.Search.Brave.Gateway.Tests -c Release. Expected: complete passing suite, exit0, only synthetic provider and owned loopback sockets.

## Decisions and limits

Local filesystem is the trusted operator boundary. Missing state never auto-initializes during service startup. Initialization is a separate API requiring a new path, never an HTTP route. After restart, valid prior state is accepted; filesystem snapshots/operator replacement can roll back it, so this is not anti-administrator rollback protection. Public hosting must add reviewed persistent-volume identity, permissions, TLS, provider/key binding and stop/revocation configuration before any paid activation. No claim that this local server is remotely deployable as-is.
