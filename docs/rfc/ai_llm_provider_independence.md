# RFC: AI / LLM Provider Independence

## Status

Draft / RFC-only / not implemented.

This RFC defines how HUB_Optimus remains operational if ChatGPT, Codex, OpenAI, or any specific AI/LLM provider becomes unavailable, degraded, restricted, replaced, or unsuitable.

This RFC does not authorize runtime changes, provider integrations, API work, agent orchestration, model routing, local model deployment, authentication, billing, cloud infrastructure, HERMES work, CI changes, benchmark changes, or semantic scoring changes.

Parent issue: #1634

## Decision

HUB_Optimus must be provider-independent.

No AI provider, model, chat session, assistant, IDE extension, automation tool, or external review system is the source of truth.

GitHub remains the source of truth through:

- issues;
- pull requests;
- commits;
- reviewed files;
- CI results;
- tests;
- RFCs;
- releases;
- repository documentation.

AI tools may assist with drafting, review, implementation, analysis, or handoff, but they remain advisory operators.

## Why this RFC exists

HUB_Optimus currently uses ChatGPT, Codex, GitHub, local terminals, and human review. This creates operational value, but also a dependency risk if any AI platform changes availability, behavior, model policy, pricing, access, or interface.

The system must remain portable across:

- ChatGPT;
- Codex;
- Copilot;
- Claude;
- Gemini;
- Grok;
- Perplexity;
- local models;
- future providers;
- human-only operation.

The project must not collapse if one provider disappears.

## Definitions

### Provider

Any external or local platform that supplies AI/LLM capabilities, including chat assistants, coding agents, review tools, summarizers, search agents, or model APIs.

### Advisory operator

An AI or human assistant that may propose, summarize, draft, review, or implement work under explicit GitHub-governed boundaries.

An advisory operator does not create project truth unless its output is committed, reviewed, and merged through GitHub.

### Source of truth

The authoritative project state. For HUB_Optimus, this is GitHub: issues, PRs, commits, repo files, CI, releases, and versioned docs.

### Handoff package

The minimum set of artifacts needed for another human or AI operator to continue work safely.

## Core rule

> AI output is advisory until GitHub makes it real.