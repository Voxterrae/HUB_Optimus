# Controlled Web implementation plan

> For agentic workers: implement isolated tasks with test-first verification;
> use subagent-driven-development or executing-plans as applicable.

**Goal:** deliver a reversible, inactive hardening of the existing SearXNG route.
**Architecture:** preserve SearchHost v1 and client source selection; POST only
to the operator-configured upstream. Keep activation and costs as human gates.
**Tech Stack:** SDK 10.0.403, ASP.NET shared framework, existing console tests.
**Spec:** `CONTROLLED_WEB_DESIGN.md` in this directory.

## Global constraints

- No external provider queries, installations, deployments, default changes or costs.
- No new NuGet dependencies, workflows, schemas, source-label or TLS/HMAC changes.
- Existing 10 s / 1 MiB / depth32 / 20-result limits and no retries remain.
- Exact base is main `0a1dde5c47be9076973478cfb568a2a8219c3fdb`.

## Review focus

- POST body must be drained in fixtures before testing disconnect/cancellation.
- Unicode/reserved queries must remain form data, absent from request target.
- Duplicate response properties and non-JSON/encoded bodies must fail closed.
- Invalid language must fail before network contact.
- A healthy empty response stays different from engine failure/partial failure.

## Task 1: Provider hardening and regression proof

Files: `src/Optimus.Search/SearxSearchProvider.cs`,
`tests/Optimus.Search.Tests/Program.cs`,
`tests/Optimus.Search.Tests/ProxyIsolationTests.cs`, scoped test helper if needed.
Consumes existing `SearchAsync(string,string,CancellationToken)`; same output.

- [x] Add real-loopback assertions for fixed POST path/body, strict safe-search,
  no query in target, preserved prefixes, invalid language, media/encoding and
  duplicate-key rejection; update body-aware fixtures and proxy assertion.
- [x] Compile/run against original provider; retain expected RED evidence.
- [x] Implement smallest provider change; preserve all existing safeguards.
- [x] Restore from an empty local NuGet source; run complete backend console
  suite with SDK10.0.403. Expected: full completion marker, zero failures.

## Task 2: Reviewable configuration and acceptance

Files: scoped design/plan/validation documents, README and PROTOCOL description.
Consumes verified source and test output; produces no executable provisioning.

- [x] Document local/private configuration, upstream/dependency blockers,
  cost/action worksheet, single-engine provenance and acceptance/rollback gates.
- [x] Update upstream method documentation while retaining local GET contract.
- [x] Run unchanged Windows portable Core/Search/Privacy and synthetic Python
  Search/pilot/harness regressions; distinguish platform skips and blockers.
- [x] Independent read-only review, fix substantive defects, then export a patch
  applicable to the exact main base with evidence and hashes.

## Execution decisions

The user explicitly requested offline development; no activation is part of the
plan. Work occurs in an isolated main snapshot reconstructed through authenticated
read-only retrieval and checked by blob IDs. Local Git history is packaging
scaffolding, not the upstream commit graph or owner signature. No remote push.

## Completion evidence

See `CONTROLLED_WEB_VALIDATION.md` for exact commands, scoped results and limits.
The general repository suite is not claimed green; deployment and live relevance
remain blocked. The final backend suite includes the post-review 21st-record
regression and passes 79/79. All feature assertions were tested against the
original provider before implementation; the extra review regression was added
after implementation without a production-code change.
