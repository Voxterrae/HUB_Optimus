# Remote API isolated verification — 2026-11-04

Executed locally against real loopback HTTP using .NET SDK 10.0.403; no external HTTP, Azure operation, NuGet package, or service activation. The console test runner uses the ASP.NET shared framework and generated, temporary 32-byte random remote bearer credentials. Registry fixtures contain SHA256 of canonical ASCII bearer text; no generated secret is printed or retained here.

## Commands

From the repository root, with `/workspace/scratch/1f94d9822c3f/toolchain/dotnet` prepended to PATH:

```sh
dotnet run --project products/browser/search/remote/tests/Optimus.Search.Remote.Tests --no-launch-profile
dotnet build products/browser/search/remote/src/Optimus.Search.Remote/Optimus.Search.Remote.csproj -c Release --no-restore
dotnet publish products/browser/search/remote/src/Optimus.Search.Remote/Optimus.Search.Remote.csproj -c Release --no-restore -o /tmp/optimus-remote-publish
sha256sum /tmp/optimus-remote-publish/catalog/public-pilot-v0.1.json /tmp/optimus-remote-publish/catalog/public-pilot-v0.1.provenance.json
```

## Observed red, then green

The first build-clean behavioral run, before API implementation, reported **0/15 passed**: expected `NotImplementedException: Remote API not implemented.` and CLI exit 1 instead of required 2. The earlier compiler setup error was corrected before recording that behavioral RED.

Independent wire review found two fixture/implementation disagreements with the portable protocol. First, tests were corrected to provision the approved SHA256(ASCII bearer) credential convention; the pre-fix implementation then reported **5/17 passed**, including `Expected OK; got Unauthorized` in the explicit digest-contract regression. This run also reproduced body-bearing GET returning 200 rather than 400. After those fixes, exact `updatedUtc` field comparison reported **16/17 passed**, with `Expected 2026-11-03T19:29:39Z; got 2026-11-03T19:29:39+00:00`. The API now preserves the original pinned timestamp text.

The final run reported **17/17 passed**. Release build reported **0 warnings, 0 errors**; publish completed successfully with exact pinned catalog and sidecar bytes.

| Verified behavior | Evidence |
| --- | --- |
| Independent process and loopback defaults | Actual API on ephemeral loopback ports; valid CLI on fixed loopback 8080; SIGTERM graceful exit 0 on Linux |
| Portable source results | All eight topic mappings, full original summaries/source/date/provenance, unrelated query yields empty results, no query field |
| Catalog integrity | Authenticated Base64 exact source bytes; both raw pins; every returned summary UTF8 SHA256; catalog and sidecar one-byte tampering reject startup |
| Authentication | Missing/local-format/incorrect/malformed/padded/duplicate/revoked credentials reject; canonical ASCII digest regression; UTC expiry at equality rejects |
| Strict parser | Required fields, duplicate/unknown names, wrong types, excessive depth, malformed UTF8, lone surrogates, trailing JSON, comments and trailing commas reject |
| Request bounds | 2048-byte declared and chunked body limits, 500 UTF16 query limit, 1..8 results, bounded responses |
| HTTP boundary | Every query string including bare `?` rejected; Origin/Cookie rejected; method/content-type/content-encoding checks; spoofed forwarded headers grant nothing; GET bodies rejected |
| Admission and cancellation | Deterministic injected monotonic 30-client/120-global quota and reset; health/unauthenticated traffic consume global quota; fifth active request immediately rejects; disconnect releases permits; slow chunked body reaches two-second deadline |
| Registry | Missing/malformed registry, schema duplicates/unknown fields, empty/>64 rows, duplicate IDs/hashes, invalid IDs/hashes, expired/>7-day expiry reject startup |
| Privacy and startup | Actual CLI stdout/stderr stay empty across synthetic private query, bearer and malformed request target; missing credentials produce only generic startup message; injected ASPNETCORE_URLS/Kestrel endpoints do not bind |

Published raw-byte hashes:

- Catalog: `8294911789f69f2c1262c80153ca0dddd6189e9a198b586f5fbb3beeb0d665ec`.
- Provenance: `5312f482daea11727c9c90a683bcf95dce587021aa6c63609b9038756eb05aae`.

## Limits of this evidence

No Azure deployment, edge TLS/network/ingress acceptance, native-client acceptance, or distributed quota claim. Windows CLI teardown uses test cleanup rather than the Linux SIGTERM assertion. Application-generated errors have bounded uniform JSON; Kestrel parser failures before middleware can have empty HTTP errors. Runtime requires an explicit absolute registry path outside the application directory; ensuring the registry is absent from source/image and supplied through a reviewed external mount remains a deployment responsibility, including symlink controls. Per-process counters reset on restart and are not spending caps. The original backend, catalog and device protocol were not modified by this API implementation.
