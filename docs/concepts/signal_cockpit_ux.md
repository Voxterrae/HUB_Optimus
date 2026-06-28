# HUB_Optimus Signal Cockpit UX Concept

## Purpose

Help users understand project state, claims, evidence, uncertainty, and safe next action.

The Signal Cockpit is a conceptual UX layer for comprehension, not an implementation commitment. Its role is to reduce ambiguity around project state and operational signal while preserving GitHub as the only source of truth.

## Status

This document is a concept note only.

It does not authorize implementation, dashboard work, roadmap changes, runtime changes, benchmark changes, schema changes, automation, scoring, or autonomous issue creation.

## Non-goals

- No dashboard implementation.
- No roadmap change.
- No LLM-as-judge.
- No autonomous issue creation.
- No replacement for GitHub truth.
- No visual layer that creates authority outside versioned repository evidence.

## Core panels

### Project State

Shows the interpreted state of the project:

- stable
- warning
- regression
- unknown

The state must be derived from GitHub-visible evidence such as issues, pull requests, commits, CI, repository docs, or an explicit user request.

### Signal Input

Accepts bounded inputs such as:

- GitHub issue
- pull request
- CI/runtime signal
- documentation drift
- contributor friction
- architecture ambiguity
- claim or external material requiring decomposition

### Claim / Evidence / Inference / Uncertainty

Decomposes input into:

- **Claim:** what is being asserted.
- **Evidence:** what supports the assertion.
- **Inference:** what is being assumed.
- **Uncertainty:** what remains unresolved.
- **Operational relevance:** whether the input matters for HUB_Optimus now.

### GitHub Truth Links

Links operational statements back to GitHub evidence where available:

- issue
- pull request
- commit
- CI run
- versioned document
- project board item

If no GitHub evidence exists, the cockpit must mark the item as advisory or unverified.

### Recommended Safe Action

Outputs one of the following:

- observe
- ask for clarification
- open RFC
- create issue
- review pull request
- update documentation
- block action due to insufficient signal

## Activation rule

Only proceed to issue, pull request, RFC, or implementation if there is:

- regression
- unclear architecture
- contributor friction
- documentation drift
- CI/runtime signal
- governance risk
- explicit user request

If none of these signals exists, remain in controlled observation mode.

## Governance constraint

The Signal Cockpit may assist understanding, but it cannot become a source of truth.

GitHub remains authoritative.

Chat, AI output, screenshots, mockups, visual summaries, and external claims remain advisory unless validated against versioned repository evidence.

## Out of scope for this concept note

- UI implementation.
- Frontend framework selection.
- Wireframes.
- Data model changes.
- Runtime integration.
- CI integration.
- Benchmark integration.
- Automated ingestion.
- Scoring or semantic judging.
- Product roadmap commitment.

## Review checklist

A reviewer should verify that this document:

- remains documentation-only;
- does not imply implementation approval;
- preserves GitHub as source of truth;
- keeps AI output advisory unless grounded in repository evidence;
- does not introduce dashboards, scoring, automation, or LLM-as-judge;
- keeps future action gated by concrete signal or explicit request.
