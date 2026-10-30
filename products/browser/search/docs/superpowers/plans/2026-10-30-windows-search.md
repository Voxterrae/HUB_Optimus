# Optimus Search Windows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Tasks use isolated worktrees, nonoverlapping files and the HTTPS contract (final TLS ruling supersedes original HTTP transport). Root owns integration, real-network smoke and publication.

**Goal:** Deliver real general-web search plumbing and a bounded own index through a shared local service consumed by Windows, with Wikipedia explicit.
**Architecture:** Existing WPF/.NET10 client + new loopback ASP.NET Core host. HTTPS v1 separates implementation/platforms; SearXNG is an operator-configured upstream, own index explicitly imported.
**Tech Stack:** .NET10.0.403, BCL/ASP.NET Core, no new third-party NuGet packages; console behavioral tests and existing Python packaging tests.
**Spec:** products/browser/search/docs/superpowers/specs/2026-10-30-windows-search-design.md

## Global Constraints

- Issue2021; preserve Linux work, source provenance, protected main, runtime/Kernel/governance/CI files and private data.
- Service loopback only127.0.0.1, default17831; authenticated search, no Origin/CORS/write API/query logging.
- Token32randombytes/64hex, profile file only; never settings/Git/package/logs/args or upstream disclosure.
- Default Web through local service; Index offline; Wikipedia explicit only. No silent source fallback.
- Query500UTF16,20results, URLs2048/title240/snippet1200, upstream1MiB/10s including body, cancellation and no redirects/cookies/ambient credentials.
- Catalog schemaVersion1,1000docs,64KiB content/document,16MiB file, atomic all-or-nothing import; deterministic actual own index, no query history/crawl.
- No new paidresources/Azure/Dataverse/AI/provideraccounts. No Windows execution/signature/accessibility claim from Linux checks.

## Review Focus

1. Cancel/change scope while launcher/token/read or stream pending: no request or result from revoked generation (Task2).
2. Port collision and independently started service: never kill someone else's process or leak local token upstream (Task2).
3. Invalid/overlarge imported catalog and failed output write: existing index preserved, no partial publishing (Task1).
4. HTTP request with malicious Origin/Host or oversized unauthorized query: reject before provider/index work, no secret/error logging (Task1).
5. Bundle/package missing host/notice/source or containing token/profile: fail packaging, preserve original build sources (Task3).

### Task 1: Shared local search service and own index

**Files:** Create products/browser/search/src/Optimus.Search/{Optimus.Search.csproj,SearchModels.cs,CatalogStore.cs,LocalSearchIndex.cs,SearxSearchProvider.cs,SearchServer.cs,Program.cs,TokenStore.cs}; products/browser/search/tests/Optimus.Search.Tests/{Optimus.Search.Tests.csproj,Program.cs}; products/browser/search/global.json. Worker may split one concern into another small file under these directories.
**Interfaces:** Frozen HTTP and CLI spec above, no shared binary dependency with Windows. Runtime host DLL/EXE `Optimus.SearchHost` via AssemblyName. Class/method implementation choices are worker-owned. Endpoint/parser contracts exact from spec.
- [ ] Write meaningful failing console tests for import/match/ranking/ties/invalid inputs; real streamed HTTP provider bounds/cancellation; real loopback API auth/origin/host/method/errors, index-no-network and web-unconfigured-no-fallback.
- [ ] Observe RED behavior/setup missing entry points, implement smallest engine/host with no additional packages, then GREEN; record actual commands/output.
- [ ] Test specific review-focus3/4 and malformed provider response, unknown length and late/cancelled read.
- [ ] Run `dotnet run --project products/browser/search/tests/Optimus.Search.Tests -c Release`, build host, syntax/diff and commit.

### Task 2: Native Windows service target, launcher and source choices

**Files:** Modify products/browser/windows/src/Optimus.Core/{SearchModels.cs,SearchService.cs,SearchSubmissionGate.cs,BrowserSettings.cs,SettingsStore.cs} only as needed; products/browser/windows/src/Optimus.App/{OptimusSearchView.cs,BrowserTab.cs,MainWindow.xaml.cs,PrivacySettingsDialog.cs}; create scoped SearchHostLauncher/connection helper(s); tests/Optimus.Search.Tests/Program.cs and relevant existing suite if needed. Do not change backend, project version/build scripts/docs.
**Interfaces:** Add typed target and enum exactly as spec. Existing legacy signatures retained. Service protocol/token path/port exactly as spec. Native host path `Search/Optimus.SearchHost.exe`. Configuration upstream from existing SearxEndpoint; UI explains restart/independently managed host limit. Do not persist token.
- [ ] Add RED tests through actual SearchService/SearchSubmissionGate for default typedWeb URL+auth, explicitIndex/Wiki, invalid/absent token/configuration, protocol marker and provider errors, cancellation/disable/closed lifecycle.
- [ ] Implement typed client and gate preserving legacy tests. Wire all native search entry points to explicit scope; invalidate query edits/scope changes before any network.
- [ ] Implement bounded launcher retaining only its owned process, loopback token use, safe arguments and no startup after cancellation. Add meaningful helper boundary tests for review-focus1/2 as feasible without fake WPF.
- [ ] Run all three native console suites and cross-target `dotnet build ...Optimus.App.csproj -c Release -p:EnableWindowsTargeting=true`, report actual limits, commit.

### Task 3: Windows build, packaging and verified handoff

**Files:** products/browser/windows/scripts/{Build-Optimus.ps1,Verify-Optimus.ps1}, Directory.Build.props version as necessary, docs/GUIA_0_3.md, README.md, tools/release/{package_optimus.py,test_package_optimus.py,README.md}; products/browser/search/{README.md,docs/PROTOCOL.md,docs/VALIDATION.md,docs/AI_GOVERNANCE_REVIEW.md}; module scoped provenance hashes. No root protected files.
**Interfaces:** Consumes reviewed Task1 host and Task2 native client; self-contained win-x64 outputs native root and Search/ childhost. Reuse exact current notices; add missing ASP.NET Core runtime notice from installed/published official runtime. Package version0.3.0alpha; retained original source package remains unchanged.
- [ ] Make build/publish and package include both executables, docs/source/notices and integrity checks; fail if runtime/profile/token/privatefile enters archive or host missing. Meaningful RED/GREEN packaging regressions.
- [ ] Root assembles reviewed commits, runs full native+service+packaging tests, cross-build/publish, then smoke actual index and real generalweb if controlled upstream succeeds. No fixture result called live evidence.
- [ ] Record actual outcomes/limits in module validation and AI review, exact GitHub diff/manifest, new stacked draft PR Related to #2021. Comment handoff in issue2021; preserve contributor credit and protected gates. Do not edit existing source-import manifest retroactively as if bytes unchanged.

### Task 4: Probar identidad del servicio local antes de enviar credenciales

**Files:** Modify SearchServer.cs/TokenStore.cs o helperpropio delbackend, SearchHostLauncher.cs y pruebas de ambos; actualizar docs/PROTOCOL.md según esquemaaditivo. No otrasáreas.
**Interfaces:** /health mantieneJSONexacto name/version. Cabeceras nonce/prueba y HMACportbound exactamentecomoampliaciónspec. TargetWeb/Index no se obtiene del launcher sinpruebaválida; serviceunknownnunca recibe bearer/consulta.
- [ ] Añadir RED real para impostor{name,version} sinprueba, pruebarandom/otroport/replaynonce; no credenciales/consulta ni acción destructiva al procesoajeno.
- [ ] Implementar HMACyverificaciónconstante antesdeentregarTarget. Servidor soporta healthsin nonce sin datos, rechazanoncemalformado; pruebasvinculanpuertoreal.
- [ ] GREEN ambosconjuntos .NET yWPFcrossbuild; reportaractualcomandos/salidas. Probarintegraciónreal servidor+launcher contokencompartido, no dobles que simplemente afirmen identity.
- [ ] Commit/revisiónscopedpropia; rootsolo integra. Actualizarprotocolo, aún ningunaaceptaciónWindows/liveweb por Linux.

### Final fix wave (single worker, authorized ruling)

- Replace local HTTP with HTTPS-only BCL TLS; in-memory host certificate has token-HMAC over exact SPKI + protocol + actual loopback port. Cert selector observes actual bound port, including zero allocation. No trust-all callback, stored private keys or trust-store changes.
- Native health/search use independent dedicated transports per request with captured token; new/reconnected TLS sessions must validate proof before any bearer/query. Retain health nonce as additive only. Test actual service/native TLS, replacement race, reconnect, copied public certificate/proof, malformed identity and cancellation.
- Align native/backend HTTP upstream policy (literal localhost and loopback IPs only); preserve base prefixes and explicit /search. Report nonempty unresponsive_engines as sanitized 502 even for partial results.
- Repair publication-safe docs links, absolute CLI catalog input, truthful optional plugin metadata, and address-bar documentation (explicit Web).
- Run all scoped C# suites, Python packaging tests and WPF cross-build. Physical Windows/live web remain independently blocked; no merge/publication by this worker.
