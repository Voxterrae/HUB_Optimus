# Remote pilot API design — 2026-11-04

Reviewable implementation under #2079. Baseline: HUB_Optimus 9fa3f8a0dbe5ea6919e49240a0df6bac7dbba803. No deployment authorization is inferred.

## Decision and alternatives
Use a separate ASP.NET Core net10.0 process and compile-link only the unchanged LocalSearchIndex.cs/SearchModels.cs ranking types. SearchHost, its loopback TLS/HMAC/profile, packaged help and native client defaults stay untouched. A dedicated hosted API is the only viable remote boundary; exposing the device host would violate PROTOCOL.md. Container Apps Consumption is proposed for intermittent load; App Service is an alternative for already-paid spare capacity or warm latency. The implementation uses explicit short-lived opaque per-client remote bearer credentials for an invitation-only pilot; Entra/OIDC is a later independently validated provider, not a dependency silently activated now.

## Contract and security
POST /v1/search accepts strict bounded JSON {query,limit}; query never appears in a URL or response. GET /v1/catalog returns pinned source bytes and provenance so clients can verify results; GET /healthz is a minimal unauthenticated liveness check. Only authenticated clients see catalog/search. No cookies, browser CORS, profiles, device tokens, external providers, LLM, crawler, writes or query logging. Public transport requires trusted HTTPS at an Azure ingress; only loopback test mode and explicitly configured container-private HTTP are supported by the process.

At most 64 clients, 32 random-byte base64url bearer secrets, SHA256 credential records with unique client IDs and expiry of at most seven days from startup. Constant-time comparison, reject missing/expired/malformed credentials, restart for revocation. The registry must remain outside source/image. Do not claim client-accountability or unstealable bearer tokens. Entra can later retain the Bearer wire contract while validating issuer/audience/signature/expiry and delegated scope.

## Limits and integrity
Body 2048 bytes; query 500 UTF16 units; limit 1..8; JSON depth 4 with duplicate/unknown fields rejected; response <=64 KiB; 4 concurrent requests, zero queue, 2 second application deadline, process-global admission 120/min and per-client 30/min. Limits and expiry use TimeProvider for isolated deterministic tests. Per-process counters reset on restart and may multiply on Azure maintenance overlap; they are not distributed quotas or spending caps. Health is admission-limited too.

Read only the pinned eight-document public catalog plus sidecar. Check exact byte SHA256 against reviewed release constants, then per-summary UTF8 digests. Responses contain full authored summary, source, updatedUtc and provenance; content hashes cover our summaries, not article bytes or truth. Clients compare against a trusted pinned release, not only a checksum returned by the same server. Finite Spanish corpus, no general Web/multilingual coverage. Immutable image/catalog update; rollback redeploys previous reviewed digest; no live indexing endpoint.

## Acceptance
Real loopback HTTP integration with synthetic remote secrets, no external network: all eight topic mappings, unrelated empty result, auth/expiry/revocation, strict JSON/body/query/result limits, rate/concurrency/cancellation, logs free of synthetic secrets/query/IP, tampered source rejection and hash verification. Existing real backend and pilot builder tests must still pass. Prepare inert Azure template, cost worksheet, promotion/rollback runbook and missing decisions. No Azure resource, registration, public endpoint, service activation or release default. Native clients and Azure end-to-end acceptance remain future work.
