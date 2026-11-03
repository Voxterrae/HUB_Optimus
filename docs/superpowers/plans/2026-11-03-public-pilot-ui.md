# Windows public pilot UI implementation plan

> **For agentic workers:** Use inline execution with RED/GREEN and one fresh whole-branch review; audit helpers are read-only.

**Goal:** Explicit reversible session-only public pilot use from Windows and observed native cloud acceptance.
**Architecture:** Fixed bundled public assets, known hashes, real CLI import to an owned temporary directory, authenticated owned-host selection with rollback, native controls and existing UIAutomation acceptance. Historical source pins remain; separate literal pilot workflow executes reviewed product/helper bytes.
**Tech Stack:** .NET10.0.403 Core/WPF/WebView2; existing C# console suites; Python pytest/workflow checks; standard Windows2022 runner.
**Spec:** docs/superpowers/specs/2026-11-03-public-pilot-ui-design.md; issue2083; owner's explicit hazlo.

## Global Constraints

- Only eight reviewed public summaries; canonical catalog SHA2568294911789f69f2c1262c80153ca0dddd6189e9a198b586f5fbb3beeb0d665ec, provenance5312f482daea11727c9c90a683bcf95dce587021aa6c63609b9038756eb05aae. Normalize CRLF only, no BOM/content changes.
- Do not alter frozen help, backend schema/ranking/TLS/loopback, Web providers/defaults, user-profile persistence, old0790 pins or owner authority.
- No arbitrary inputs, new dependencies/resources/secrets/accounts/endpoints/cost, provider query, fallback or automated user-profile import.
- Preserve prior selection on failure, healthy independent hosts and all pre-existing files. Cancellation and shutdown cannot publish stale state.

## Review Focus

- A second tab or query during switching cannot display results from the old catalog as new.
- Failed activation after normal old-host shutdown must restore the prior selection and not report pilot success.
- Independent healthy host, cancellation and disposal races cannot stop/replace another service or publish late selection.
- Missing/malformed/reparse assets or successful CLI without usable output fail visibly without replacing prior state.
- Packaged/publication data and manual cloud checkout use the exact reviewed bytes; GUI and public-Web claims remain separate.

## Task1: Core transaction and behavioral acceptance

Files: Core/PublicPilotCatalog.cs; Core/SearchHostLauncher.cs; Windows Search.Tests/PublicPilotTests.cs plus registration; existing test helpers as necessary.
Interfaces: public PilotCatalogChange(bool Active,string? Error); PublicPilotCatalog(SearchHostLauncher,string applicationDirectory); bool IsActive; Task<PilotCatalogChange> SetActiveAsync(bool,CancellationToken); IDisposable. Internal OS process runner seam only for tests. Launcher internal SelectIndexAsync(string?,CancellationToken) serializes with ConnectAsync, and CreateStartInfo adds validated optional --index-file.
- [x] Write real-behavior tests for state/asset rejection/actual CLI import and rollback; watch intended failures.
- [x] Implement fixed bounded asset reads, exact hashes, bounded real importer, owned temp lifecycle, serialized launcher startup/rollback and independent-host refusal. No sensitive diagnostics.
- [x] Run complete portable search/backend suites, not only new tests.

## Task2: Native surface and publication

Files: App/OptimusSearchView.cs, BrowserTab.cs, MainWindow.xaml.cs, App.csproj; packaging tests/validator only if fixed asset acceptance needs it; guide.
Interfaces: shared PublicPilotCatalog session manager; MainWindow switch callback cancels all searches and blocks search eligibility during switch; BrowserTab refreshes its search view; controls show exact labels from spec.
- [x] Add UI/source/publication acceptance failures before implementation; build/test meaningful states via Core and native smoke rather than implementation-only assertions.
- [x] Bundle two fixed public assets, wire explicit load/reload/restore, show finite session scope, generic failure and disable busy actions. Restore default without settings persistence.
- [x] Build actual WPF publication/helper and verify packaged asset hashes; preserve three-help index and unrelated features.

## Task3: Native smoke and literal pilot workflow

Files: WindowsSmoke/GuiSmoke.cs; separate .github/workflows/optimus-public-pilot-smoke.yml; root workflow regression tests; guide and append-only AI_HANDOFF.
- [ ] Extend owned UIAutomation with pilot queries, unavailable public asset reload preservation without modifying caller files and restore. Add ordinary loopback bookmark result click/render separately; retain baseline/cleanup and180-second outer budget.
- [ ] Owner Verified product/helper commit, record full source SHA; thereafter add new manual workflow pinned to that literal SHA in every source execution field. Existing0790 workflows unchanged. Tests reject arbitrary source/ref/owner/private/nonmain behavior and absent evidence.
- [ ] Fresh whole-branch review; fix Critical/Important with observed RED/GREEN, record minors.
- [ ] Verify exact blobs/signatures/current main handoff; seven publisher-bound checks plus complete CodeQL success, zero threads, normal protected merge.
- [ ] Dispatch native cloud once with GUI requested, read actual reports/test counts/source identity/normal cleanup. Any real failure gets diagnosis and governed correction; no false acceptance or provider rerun.

Final review:0Critical/4Important/2Minor. FiveCore RED regressions76/81 become81/81 after one verified fix wave. Fixed post-bind child readiness/foreign responder refusal, atomic confirmed cleanup, and exact semantic output binding; GUI unavailable-asset reload lease replaces caller-file mutation, malformed data remains portable evidence. Deferred: extreme OS final cleanup deadline and extra Connect/disposal fixture coverage. Corrected immutable product source91ce4863d756f429d8fcae19787e56d166d69b82 supersedes initialceab; historical0790unchanged. Local fullpytest incomplete after dependency repair/stalled progress; no false green. Protected exact-head CI and actual native run still pending.
