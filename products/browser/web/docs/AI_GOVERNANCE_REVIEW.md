# Optimus web pilot — AI Governance Review v0.1

Review evidence prepared from the repository's [template](../../../../templates/governance/AI_GOVERNANCE_REVIEW_v0.1.md). It grants no authority, compliance certification, rights exception, deployment permission or merge approval. An unmerged proposal is not current project policy. Contributor credit and third-party rights remain intact.

## 1. Proposal and exact review scope

- Repository: `Voxterrae/HUB_Optimus`; scoped issue and PR are linked in the PR body.
- Date (UTC): 2026-10-30.
- Base: `79c1d95d65e0f8b903039249cd8ce890b1ffe111`, the source-import branch reviewed in draft #2018, not a claim that the import is merged.
- Final reviewed head: the full SHA recorded externally in the final PR body after push; this file does not embed its own commit hash.
- Affected scope: `products/browser/web/` and exact static copy `site/browser/`. Exact final paths/hashes and command results are in the module validation record and final PR diff.
- Implemented candidate: six-language static UI, bounded user-submitted Wikipedia requests, opt-in device preferences/links, local-only speech capability handling. Private acceptance hosting is external deployment evidence, separate from GitHub main, Pages and Azure.
- Proposed: protected integration of the static Pages artifact and a future reviewed Azure Static Web Apps Free deployment. The ARM file has not been executed or provider-validated.
- Excluded: AI model/API activation, generative answers, own web index, autonomous browser actions, remote speech, IoT, paid resources, native Windows changes, credentials, core runtime, CI, project authority and licensing.
- AI assistance: implementation, copy drafting and advisory technical review. No AI self-approval, independent merge authority or private prompt disclosure.

## 2. Six-layer analytical record

### Claim

The proposed increment provides a useful configurable web companion with explicit search and typed fallback. It does not establish that Optimus is better than every browser, universally protective, accessible for every person or ready for production hardware.

### Evidence

The source, tests and design contract are committed with this record. Actual commands, outcomes and browser observations are recorded in `VALIDATION.md` and the PR for the externally named final head. Root `AGENTS.md`, `CONTRIBUTING.md`, the Founder Ownership and Authority Charter, owner identity manifest and controlling handoff were inspected from GitHub main. The Pages workflow uploads `site/` directly after matching pushes to `main`; it does not build this product. Existing native and React sources are preserved by the separate source-import proposal.

### Inference

Large controls, explicit choices, language separation, keyboard alternatives and restrained defaults are expected to reduce interaction friction. This is design reasoning, not measured evidence from older adults, disabled participants or expert users. Such users can require different interaction patterns.

### Uncertainty

Local speech capability and voice packages vary by device/browser. No physical microphone, Windows release, screen-reader acceptance or native-speaker translation review is certified. External Wikipedia availability/content, hosting limits, actual Azure eligibility/costs and final Pages deployment remain outside module-test proof. Required GitHub checks/signatures and human disposition must be refreshed at the final head.

### Narrative amplification

The initial ambition of a permanently superior browser could turn a limited pilot into an unsupported universal claim. Avoid product copy implying comprehensive protection, automatic private-mode switching, verified ethical content or an independently crawled web index. Separate working behavior, test evidence and future proposals.

### Operational relevance

This is a small, reviewable product increment with explicit external data flow and local voice limits. It justifies a draft PR and private acceptance testing; it supplies no protected-main, paid-infrastructure or sensitive-action authorization.

## 3. Human authority and permission boundary

- Final accountable authority remains the human project owner under the repository Charter and identity manifest; the controlling owner-authority handoff is unchanged.
- Human decision: pending in GitHub. No informal identity claim, account name, automatic signature or model output substitutes for the protected process.
- Required current-head checks, signatures and owner decision must be established from GitHub before merge. This record does not change any protection.
- Browser user explicitly starts search, playback or push-to-talk and may stop. No collaborator or AI receives new system privileges, credentials or general delegation.
- No IoT execution, sensitive downstream decision, paid infrastructure or account/contract activation is permitted by this increment. Future integrations require their own scoped issue, review, permission and operational evidence.

## 4. Capability, data, and impact boundary

- Input: query text, selected preferences, saved-link title/URL and transient local speech text. Output: Wikipedia result text/links, local UI and optional local audio.
- Network: only explicit search to six fixed Wikipedia language origins. Queries and ordinary connection metadata reach Wikipedia. External-link navigation is a separate user action handled by the host browser.
- Retention: only opted-in preferences and at most 50 links under the application's own device key. No application persistence of queries, results, audio or transcripts. Clearing affects that application key, not third-party records or host-browser history.
- Speech: only browser-declared local voices; recognition requires local-processing capability and an already available package. No remote fallback, automatic model download, continuous listening, command execution or auto-submit.
- Failure modes: unavailable/slow/malformed search, stale asynchronous callbacks, denial/corruption of storage, missing local speech, unsuitable or inaccurate external content, focus/reflow defects, and access to opted-in data by users of the same device profile. Bounds, cancellation, inert rendering, explicit controls and typed fallback constrain the candidate; they do not eliminate every risk.
- No authority, rights, licensing, contract or sensitive-use change is proposed. The original marks are reused with source provenance; third-party rights remain applicable.

## 5. Validation and reversibility

Commands: `node --test tests/*.test.mjs`, syntax checks of the ES modules, JSON parsing, exact static artifact comparison and actual browser task checks. Final results, covering regressions and verification limits belong in `VALIDATION.md` and the final PR body, tied to the external full head SHA. No older CI pass should be copied as evidence for a new head.

Azure provider validation/what-if, deployed Azure behavior, physical microphone/local package acceptance, screen-reader/user testing, native-speaker review and native Windows execution are not established by this change. Pages publication remains pending protected integration and successful deployment workflow evidence.

Before merge, withdraw by closing the draft. After an authorized merge/publication, revert the scoped increment and verify the Pages workflow. The private acceptance host can return to its prior version or be withdrawn within its own access boundary. No Azure resource has been created by this proposal.

## 6. Human review disposition

- Human review and decision: pending.
- Exact head: externally recorded in the final PR body, refreshed after any push.
- Technical findings and their disposition: recorded in module validation; technical review is advisory, not a human authorization.
- Authorized next action claimed by this record: none. Existing owner authority, protected review, signatures and required checks remain applicable.
