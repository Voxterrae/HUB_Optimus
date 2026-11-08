# Public pilot catalog implementation plan

> **For agentic workers:** Use superpowers:executing-plans with RED/GREEN and one fresh whole-branch review.

**Goal:** Deliver an explicit useful eight-reference public catalog and reproducible data artifact for future Azure publication, accepted by the existing real index CLI.

**Architecture:** New reviewed Spanish summaries and a content-bound provenance sidecar stay separate from the frozen three-document help catalog. A standard-library Python builder reads only those fixed files, validates exact public references and hashes, and creates an exclusive-output fixed-member deterministic ZIP. Existing .NET tests import the real catalog and verify finite offline retrieval; no runtime/protocol change.

**Tech Stack:** Existing .NET10.0.403 CLI/BM25; Python3 stdlib; pytest.

**Spec:** Issue2079 and its explicit preparation boundaries. This is a finite public corpus, not Web acceptance or an activated Azure service. The owner's repeated continuation selects execution within the existing no-new-cost scope.

## Constraints and choices

- Eight references: two immutable public HUB docs and six official Microsoft accessibility/identity/Azure docs; short Optimus-authored summaries, no copied articles or private LCDH/profile data.
- Coverage is Spanish guidance about Optimus, Windows accessibility and Microsoft infrastructure. No general-Web or six-language corpus claim.
- Frozen optimus-help.json, release packager/pins, rankings, local TLS/HMAC, Web providers and client settings remain unchanged.
- Builder has only --output; no input/profile path, crawling, source download, directory discovery or environment/credential scan.
- Public policy is stricter than the runtime importer: exact reviewed HTTPS URLs only, no query/fragment/userinfo/private/live-GitHub-branch URL, exact fields and content hashes.
- Hashes bind our committed summaries and catalog, not bytes of the remote articles. Public classification is a reviewed assertion, not automatic DLP or Microsoft endorsement.
- ZIP_STORED, fixed member order,1980 timestamp and file attributes; canonical UTF-8/LF JSON; no current time, machine path or imported platform-dependent index bytes.
- Exclusive output refuses existing files/symlinks; no automatic replace/delete/extract/upload. Validate before creating output. An interrupted write may leave an incomplete archive, so integrity verification is mandatory before import.
- No provider query retry/fallback, resources/accounts/secrets/DNS/endpoint/cost, or automatic updates to user profiles.

## Task1: Corpus and real index acceptance

Files: catalog/public-pilot-v0.1.json; catalog/public-pilot-v0.1.provenance.json; tests/Optimus.Search.Tests/Program.cs and csproj.

- [x] Add real-CLI tests requiring eight records, expected top URLs for eight hand-selected topic queries, an unrelated empty result and deterministic repeated import. Observe RED before the real corpus exists.
- [x] Add authored summaries and sidecar using references actually checked on2026-11-03. Import through the real CLI and load with CatalogStore/LocalSearchIndex; no network or provider fallback.
- [x] Verify malformed/duplicate mutation preserves the previous imported output with exit2 and generic diagnostics. Run the complete backend suite.

## Task2: Public-only artifact builder

Files: tools/build_public_pilot.py; root tests/test_optimus_public_pilot.py; docs/PUBLIC_PILOT.md; docs/context/AI_HANDOFF.md.

- [x] Write CLI behavior tests first: missing feature fails; successful build has exact four members and reproducible bytes; source CWD/profile fixtures are absent.
- [x] Write strict validation/rejection tests for mismatched hashes, unknown fields, duplicate keys/URLs, non-UTC data, unsafe references, symlinks and output overwrite; watch failures before adding each guard.
- [x] Implement fixed-source loading, canonicalization and exact provenance pairing, then deterministic archive output and generic diagnostics.
- [x] Verify LF/CRLF input formatting yields identical canonical archive, and validate/import the extracted catalog with the real CLI locally.
- [x] Document generation/verification/manual import and future Azure Blob/service handoff; no deployment/hosting acceptance. Preserve complete current main handoff before append.

## Review and integration

- [x] Fresh whole-branch review; verified fixes use RED/GREEN. No false classification or coverage claim.
- [ ] Owner Verified scoped commits, exact current source blobs, seven mandatory publisher-bound checks, complete CodeQL success and no unresolved threads before normal protected squash.
- [ ] Keep2079/2062 open for remaining service/coverage gates; attach observed finite corpus evidence and no-resource boundary.

Review evidence:0Critical/2Important/1Minor. One verified fix pass: Unicode-year timestamp accepted by Python but rejected by .NET, and optimized Python removing documentation assertions. Four regressions RED, final50pilot/115combined GREEN; explicit exceptions and trusted external digest precede ZIP opening. Minor guide-revision pointer deferred to release publication metadata, not a runtime acceptance issue. Backend51/51 passes; archive hash unchanged.
