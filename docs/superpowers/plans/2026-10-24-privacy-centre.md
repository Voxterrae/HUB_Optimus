# Privacy Centre Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare a native, reviewable privacy centre for the existing public site and Operator.

**Architecture:** A local configuration and a small dependency-free renderer drive an accessible static page. Existing Operator storage controls remain the only controls that mutate its data. Publication readiness is an explicit completeness check, not a legal certification.

**Tech Stack:** Static HTML/CSS, plain JavaScript, existing Python/Node tests; browser QA with the available Playwright runtime.

**Spec:** `docs/superpowers/specs/2026-10-24-privacy-centre-design.md` and issue #1984.

## Global Constraints

- Baseline: `fe789f78baddb3723547741211dd8f34b86fe292`.
- No new service, subscription, external JavaScript, network transport or telemetry.
- No new data deletion or consent mechanism; direct users to existing controls.
- Never present unverified controller/contact/provider/retention details as final.
- ES, EN and DE; unsupported locales fall back to EN; language switching writes no storage.
- No Kernel, CI, infrastructure, constitutional, licence or permissions changes.
- Native execution in the isolated feature clone; one independent review of the finished change.

## Review Focus

- A contact flag alone must not generate a link for an empty or unsafe address.
- A configuration claiming readiness with missing required details remains draft.
- Unsupported/malformed locale values fall back without executing content.
- Opening or switching the notice must preserve unrelated and Operator data.
- No-JavaScript readers must receive useful boundaries and navigation.

## Task 1: Native notice and publication completeness

**Files:** Create `site/privacy/index.html`, `site/privacy/privacy.css`, `site/privacy/privacy-config.v1.js`, `site/privacy/privacy.v1.js`; test `tests/test_privacy_centre.py`.

**Interfaces:** Configuration global `HUB_OPTIMUS_PRIVACY_CONFIG`; exported pure helpers `HUB_OPTIMUS_PRIVACY.assessPublication(config)` returning `{ready, missing, contactHref}` and `resolveLanguage(value)` returning `es`, `en` or `de`. The page consumes these through local scripts only.

- [ ] Write tests exercising the real helpers via Node against incomplete, complete and unsafe contact fixtures, and locale fallback fixtures.
- [ ] Run `python -m pytest -q tests/test_privacy_centre.py`; observe failure because the feature is absent.
- [ ] Implement the configuration, helpers and translated page, preserving unknown fields and using `textContent` for configurable values.
- [ ] Run the focused tests; expected zero failures.

## Task 2: Existing entry points and operational documentation

**Files:** Modify only privacy links in `site/index.html` and `site/operator/index.html`, and extend public-route coverage in `tests/test_public_site_links_and_contrast.py`. Create `docs/privacy/README.md` and the prospective `docs/privacy/ai_governance_readiness.md`.

**Interfaces:** Both footer links target the new route. Privacy controls point to existing `advanced_operator_console` and `learning_workspace` anchors. No i18n catalog, version or cache migration is needed for existing translated privacy text.

- [ ] Confirm the new route is included in the existing public-link validator, then observe missing entry-point coverage before editing the footers.
- [ ] Link the existing localized privacy statements; retain their translations and surrounding structure.
- [ ] Document exact storage scope, publication prerequisites, conditional future controls and rollback by reverting this isolated delta.
- [ ] Run focused privacy, public-route and Operator i18n tests; expected zero failures.
- [ ] Run browser QA at desktop/mobile, ES/EN/DE, no JavaScript, synthetic existing storage, contact gating, and a network request allowlist.
- [ ] Run applicable repository checks and record exact outcomes; do not broaden testing without a new concern.
- [ ] Obtain a fresh independent review; fix material findings and verify their regressions.
- [ ] Publish only an isolated draft PR, retaining owner review and publication gates.
