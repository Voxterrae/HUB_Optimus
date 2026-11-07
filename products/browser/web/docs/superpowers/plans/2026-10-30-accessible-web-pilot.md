# Optimus accessible web pilot implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Tasks use independent worktrees with no overlapping owned files; integration and publication remain sequential.

**Goal:** Deliver a private, useful, six-language mobile web pilot with accessible controls, real Wikipedia search and honest local voice capability handling.

**Architecture:** Static HTML/CSS/ES modules with no dependencies. Search and voice lifecycles are bounded modules; translations are separate data. Preserve existing native and React sources, and mirror new reviewed sources to a separate GitHub proposal.

**Tech Stack:** HTML5, CSS, ES modules, Node24 built-in test runner, static Sites preview; Pages/Azure static deployment targets without paid activation.

**Spec:** docs/superpowers/specs/2026-10-30-accessible-web-pilot-design.md

## Global Constraints

- No paid resources, Azure signup, contract acceptance, ownership/permission changes or live device control.
- Preserve original marks and graphite/copper/mint appearance; comfortable18px default and principal44px touch targets.
- Six languages es/ca/en/de/fr/ru; language selection never implies identity or ability inference.
- Search only on submit to six fixed Wikipedia hosts, query500,10results,1MiB,10s; stale and cancelled work cannot update UI.
- Optional device persistence: schema1, app key optimus.browser.pilot.v1, no queries/results/audio/transcripts, maximum50saved links.
- Voice is explicit, local-only, capability-gated,30s dictation cap and no remote fallback/model installation.
- No service worker, backend, analytics, cookies, third-party scripts/fonts or false native/privacy/security claims.
- Private preview audience stays owner-only. GitHub main and existing Pages deployment remain unchanged pending protected review.

## Review Focus

- Delayed availability, HTTP body or voice events after cancellation/language change must stay inert.
- Long translated labels and320px/200% layout must remain readable with keyboard access.
- Corrupt/denied storage and hostile stored URLs must fail to memory without executing content.
- Voice unsupported, missing local language, denied permission and unavailable browser controls must leave typing/search useful.
- Private preview authentication and source publication must never include private operating-note data or credentials.

### Task1: Languages

**Files:** dist/i18n.mjs; tests/i18n.test.mjs.
**Interfaces:** exports exactly as Spec. Produce a stable complete key set for Task3; copy key manifest to report.
- [ ] Write failing behavioral tests for unsupported-language fallback, plain-text parameter interpolation, missing-key safety and missing/extra-key validation; run and observe failures.
- [ ] Implement six complete dictionaries for the four routes, search, voice, privacy and errors, using clear native-language phrasing.
- [ ] Run node --test tests/i18n.test.mjs and self-review; commit owned files and report.

### Task2: Local voice lifecycle

**Files:** dist/voice.mjs; tests/voice.test.mjs.
**Interfaces:** VoiceController from Spec; no DOM rendering or dictionary dependency.
- [ ] Write failing tests at browser-boundary injection for absent APIs, local-language filtering, stop/cancelled availability/late result, permission denial,30s timeout and disposal; verify RED.
- [ ] Implement local-only synthesis/dictation with generation-bound events, timers and cleanup.
- [ ] Run node --test tests/voice.test.mjs; self-review, commit and report actual limits.

### Task3: Accessible app and real search

**Files:** dist/index.html, app.mjs, core.mjs, styles.css, manifest.webmanifest; tests/core.test.mjs; local assets.
**Interfaces:** consumes i18n/voice exports; produces complete browser UI and bounded search/storage behavior.
- [ ] Write failing tests for submit URL/body limits, stale cancellation, malformed result handling, safe destinations and opt-in sanitized persistence. Use real bounded streams; inject only external transport/storage boundaries.
- [ ] Implement core and UI with semantic controls, all visible copy through dictionary, six-language switching, routes, visual settings, saved links, privacy explanation and local voice controls.
- [ ] Run node --test tests/core.test.mjs; self-review, commit and report.

### Task4: Integrate, verify and publish private pilot

**Files:** README.md; docs/VALIDATION.md; docs/TECHNICAL_OPERATIONS.md; staticwebapp.config.json; source/hosting manifests; private operating note outside repo.
**Interfaces:** combines reviewed tasks; source helper owns remote source publication; GitHub changes stay in isolated proposal.
- [ ] Integrate reviewed commits and run node --test tests/*.test.mjs, syntax checks and static-file packaging checks.
- [ ] Browser QA through supported Sites preview; fix observed functional/UI failures with regression tests where meaningful.
- [ ] Fresh broad final review; address important findings in one combined pass with regression evidence.
- [ ] Publish owner-private preview through Sites helper and verify terminal deployment; create scoped GitHub issue/PR with exact source and evidence. Prepare Pages/Azure deployment documentation without activating accounts or main merge.
- [ ] Save owner-private operating note; report actual URL, validations and material limits.
