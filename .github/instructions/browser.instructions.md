---
applyTo: "products/browser/**,site/browser/**,.github/workflows/optimus-windows-smoke.yml,.github/workflows/optimus-public-pilot-smoke.yml,.github/workflows/optimus-real-web-smoke.yml"
---

# Optimus Browser instructions

## Boundaries and sources

- Follow `AGENTS.md`, the repository-wide instructions and `git-workflow.instructions.md`; this file grants no merge, dispatch, deployment or authority exception.
- Read the affected component's README, current source/tests, workflow and linked validation record. Historical import manifests, alpha labels and run reports describe their stated revision, not current acceptance. README claims that CI is inactive or accepts arbitrary source SHAs are superseded by the registered, pinned workflows below; inspect their current behavior.
- Keep the WPF/WebView2 Windows product, shared local Search host, React demo and static Web companion distinct. A demo or static page is not native browsing, general-Web coverage, an authenticated remote service or accessibility acceptance.
- Windows/Search changes must preserve the shared contract with Linux; consult `products/browser/search/docs/PROTOCOL.md` before changing transport. Retain IPv4 loopback, HTTPS/TLS-HMAC authentication before bearer/query bytes, token-file privacy and exact-owned process cleanup. Never expose this host by changing its bind or sharing device tokens.

## Local validation commands

Use the commands for the changed surface and report the actual working directory, toolchain, outcome and skips. Do not substitute remembered suite counts for fresh results.

From `products/browser/windows`, use .NET SDK **10.0.403** (`global.json`; manual QA preflight requires that exact SDK):

```sh
dotnet --version
dotnet run --project tests/Optimus.Core.Tests -c Release
dotnet run --project tests/Optimus.Search.Tests -c Release
dotnet run --project tests/Optimus.Privacy.Tests -c Release
dotnet run --project ../search/tests/Optimus.Search.Tests -c Release
python3 -m unittest discover -s tools/release -v
dotnet build Optimus.slnx -c Release -p:EnableWindowsTargeting=true -m:1
```

From `products/browser/web` (no npm install/build step):

```sh
node --test tests/*.test.mjs
node --check dist/app.mjs
node --check dist/core.mjs
node --check dist/i18n.mjs
node --check dist/voice.mjs
```

From the repository root, after the documented Python development setup:

```sh
python -m pytest -q products/browser/web/tests/test_browser_web_node_suite.py
python -m pytest -q tests/test_optimus_public_pilot.py tests/test_optimus_public_pilot_smoke.py tests/test_optimus_real_web_smoke.py
```

For static Web changes, keep `products/browser/web/dist/` and `site/browser/` byte-identical; from the repository root check `diff -qr products/browser/web/dist site/browser` where available. Pages publishes `site/` directly, not the React demo or an implicit build. Review `.github/workflows/pages.yml` and the current environment hold before publication; source parity does not establish deployed or served bytes.

## Packaging and provenance

- Follow `products/browser/windows/tools/release/README.md` for the three self-contained win-x64 publications, real CLI help import, documentation/notices, metadata and ZIP verification. `scripts/Build-Optimus.ps1` and `scripts/Verify-Optimus.ps1` require PowerShell 7; Build replaces its `artifacts/win-x64` output, so inspect that target first. Neither script executes the Windows product or proves native acceptance.
- Preserve historical `SOURCE_MANIFEST*.json` bytes and scope; do not rewrite old hashes to describe newer sources. An approved new delivery needs a separately attributed inventory of its final source bytes, intentional differences and validation. The packager reads tracked filenames but current working-tree bytes: a supplied commit string does not certify a clean tree.
- Validate a prepared publication from `products/browser/windows` with `python3 tools/release/package_optimus.py --verify-publication <absolute-publication-path>`. Preserve complete source siblings, third-party notices, exact frozen-help pins, runtime-version checks, full hash coverage and path/privacy rejection. Do not broaden pinned DLL exceptions to bypass a new runtime version.
- Never package profiles, tokens, private catalogs, certificates/keys, credentials or raw QA logs. Checksums establish integrity relative to trusted provenance, not publisher authenticity, binary signing or execution. Public-pilot generation/verification follows `products/browser/search/docs/PUBLIC_PILOT.md`; its eight summaries and the separate three-help corpus are finite, not Internet search.

## Manual Windows and real-Web evidence

- Read the three scoped `.github/workflows/optimus-*-smoke.yml` files directly before proposing QA. They are manual, `contents: read`, public `Voxterrae/HUB_Optimus`/repository-ID gated, protected-`main`, owner-ID/login constrained and cache/artifact-upload free. Preserve those gates, immutable action/source pins and bounded execution; never dispatch as a side effect of editing instructions.
- Inputs confirm literal reviewed product pins; they cannot select arbitrary valid SHAs. A new executable candidate requires a protected pin update. Record product SHA, workflow/harness SHA, run ID/attempt and upstream/dependency provenance separately. Do not assume the current branch is the product selected by an existing workflow.
- Native acceptance uses `scripts/Test-OptimusWindows.ps1` through Windows PowerShell **5.1**, with the exact `-SourceCommit` embedded in all required component ProductVersions. Use the packaged diagnostic helper; do not load .NET 10 assemblies into PowerShell 5.1. See `products/browser/windows/ci/README.md` for isolated service/GUI prerequisites and reports; the template outside `.github/workflows` is dormant, not a workflow to register directly.
- GUI needs a disposable clean user/VM, absent default Optimus profile, free required port, interactive desktop and existing WebView2 Evergreen. Do not inspect/delete a real profile or install a runtime to force green. Service and GUI reports are independent; missing, failed, blocked or unrequested evidence is not PASS. Public-pilot QA requires both service and GUI plus its fixed asset hashes.
- Follow `products/browser/search/docs/REAL_WEB_SMOKE_2062.md` and the current workflow for isolated real-Web QA. `startup-only` is query-free diagnosis, never relevance acceptance; `queries` is separately authorized fixed-query evidence. Retain domain-and-topic pairing, provenance, no fallback/resubmission or quota/challenge bypass, sanitized reporting and exact-owned cleanup. Do not turn synthetic fixtures or a blocked upstream into public-Web acceptance.
- Linux cross-builds, portable suites and broad green CI establish only their asserted checks. They do not accept a later product SHA, Windows service/GUI, physical Windows 10/11, keyboard/Narrator/NVDA, accessibility, general-Web relevance, signed distribution or production availability. Report each required manual gate as PASS, FAIL, BLOCKED or UNRUN with exact evidence.

## Cloud and data safety

- The static Web pilot has no product backend/secret store: keep queries explicit, local voice requirements and opt-in device persistence from `products/browser/web/README.md`. No remote voice fallback, silent microphone/model installation, telemetry, IoT or account activation follows from this surface.
- Azure files are preparation, not deployed infrastructure. Read `products/browser/web/ops/azure/README.md` and `products/browser/web/docs/TECHNICAL_OPERATIONS.md` before any proposal. Subscription/tenant identity, accountable operator, permission, cost, exact artifact, approval and rollback/acceptance need separate evidence and authorization. Free SKU, credits and budget alerts do not guarantee zero charges or stop consumption. Do not provision, publish, add secrets, convert plans or expose the local Search protocol as part of an instruction-only change.
