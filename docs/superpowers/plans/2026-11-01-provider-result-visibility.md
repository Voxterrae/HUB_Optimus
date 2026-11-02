# Provider result visibility implementation plan

> **For agentic workers:** Execute inline with superpowers:executing-plans. Steps use checkbox gates; source acceptance is recorded against the exact GitHub SHA.

**Goal:** Successful provider results remain visible when matching bookmarks fill the twenty-result limit.

**Architecture:** Keep the selected provider, response validation and destination policy. Add validated provider results first; append safe matching bookmarks only when constructing the final response. Fragment-insensitive deduplication prefers the actual provider result.

**Tech stack:** Existing .NET10 Core client and executable Search tests; existing isolated Windows smoke.

**Spec:** Governance issue [#2061](https://github.com/Voxterrae/HUB_Optimus/issues/2061), continuing the owner's repair/testing instruction. Provider-first ordering is the implementation decision for this correction; there is no new quota or setting.

## Global constraints

- Maximum20 total results; title240, snippet1200, destination2048 and response1MiB limits remain unchanged.
- Preserve cancellation, authenticated local TLS, token handling, private bookmark omission, visible provider errors and no automatic fallback.
- Cover typed Web/Index, direct SearXNG and legacy Wikipedia consistently.
- No paid resources, persistent deployment, secrets, authority or protection changes.

## Review focus

Saturated bookmarks; provider/bookmark duplicate fragments and provenance; empty/failed/invalid provider bodies; twenty valid provider results; canceled or invalid input; bookmark edits during an in-flight request.

## Task1: correct result composition

**Files:** SearchService.cs; Search tests Program.cs; new ProviderPriorityTests.cs.

**Interface:** Existing SearchAsync overloads and SearchResponse remain unchanged.

- [x] Add regressions for typed scopes, direct SearXNG, Wikipedia, duplicate provenance, twenty provider results, empty/failed provider bookmark recovery, and submission-time bookmark snapshots.
- [x] Run Search tests and observe the provider-visibility cases fail before changing production code.
- [x] Defer matching bookmarks to final response composition; maintain all existing validation and errors.
- [x] Update the previous explicit bookmark-first assertion to the documented provider-first behavior.
- [x] Run Search/Core/Privacy/backend suites and packager tests, serially; record observed counts.
- [x] Append the operational checkpoint to AI_HANDOFF, attributing earlier174-check acceptance to4c9 only.
- [ ] Independent final review; publish owner-Verified commits and a protected PR for2061.
- [ ] Fresh exact-source native service/GUI acceptance and all seven mandatory PR checks before normal protected merge.

## Acceptance record

Observed priority RED60/66 then GREEN66/66; submission snapshot RED66/67 then final GREEN67/67 Search; Core39/39, Privacy28/28, backend48/48, packager23 tests pass. Native exact-source/required CI/final review remain pending. Historical source inventories remain immutable snapshots; this plan does not certify binaries or live Internet search.
