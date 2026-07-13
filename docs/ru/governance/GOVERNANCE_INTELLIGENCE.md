# HUB_Optimus — Governance Intelligence Protocol

Status: Active upon merge of the ratifying Pull Request  
Proposal record: [#1694](https://github.com/Voxterrae/HUB_Optimus/issues/1694)  
Authority: Canonical governance protocol  
Scope: Documentation and analytical process only

## Purpose

Governance Intelligence is the required analytical discipline for separating claims, evidence, inference, uncertainty, narrative amplification, and operational relevance when HUB_Optimus examines complex institutional, civic, technological, or informational material.

This protocol governs how analysis is structured and reviewed. It does not determine what conclusions must be reached, create an autonomous authority, or replace human judgment.

## Source of truth and authority

GitHub issues, Pull Requests, commits, checks, and versioned repository documents are the project record. Chat messages, model outputs, hidden prompts, conversation memory, external AI reviews, screenshots, and uncommitted drafts are advisory inputs unless and until they are represented in that record.

No claim gains authority because it is repeated, popular, urgent, emotionally forceful, produced by a capable model, or attributed to a prestigious source. Authority and confidence must come from inspectable evidence, explicit reasoning, repository governance, and human-accountable review.

When chat state conflicts with GitHub state, GitHub wins.

## Required analytical record

A Governance Intelligence analysis MUST keep the following six layers distinct:

| Layer | Required question | Required output |
| --- | --- | --- |
| Claim | What exactly is being asserted? | A specific, bounded statement |
| Evidence | What inspectable material supports or contradicts it? | Sources, observations, provenance, and limitations |
| Inference | What reasoning moves beyond the evidence? | An explicit reasoning step, not a disguised fact |
| Uncertainty | What remains unknown, contested, incomplete, or unverifiable? | Gaps, conflicts, assumptions, and confidence limits |
| Narrative amplification | What may be overstated, compressed, framed, or emotionally amplified? | The distortion mechanism and its likely effect |
| Operational relevance | Why does this matter to the repository or reviewed case? | A valid signal, a bounded consequence, or an explicit no-action result |

All six layers MUST be present. A layer may state `none identified`, `no evidence provided`, or `no action justified`; it must not be omitted to create artificial certainty.

## Claims

A claim MUST be recorded before it is evaluated. Recording a claim does not mean accepting it.

A claim SHOULD identify, where available:

- the speaker, author, system, or institution making it;
- the time and context in which it was made;
- the population, event, system, or decision it concerns;
- the degree of certainty expressed;
- the conditions under which the claim would be testable or falsifiable.

Compound claims SHOULD be decomposed into independently reviewable statements.

## Evidence and provenance

Evidence MUST remain inspectable and attributable. Where practical, an analysis SHOULD record the source, repository path or external reference, date, access context, and whether the material is primary, secondary, derived, user-provided, or model-generated.

Model-generated text is not evidence merely because a model produced it. It may summarize, compare, or propose an inference, but the supporting material must remain separately visible.

Screenshots, social posts, excerpts, and authority statements are artifacts or claims. They are not conclusive proof without adequate provenance, context, and corroboration.

Conflicting evidence MUST be preserved rather than silently discarded. Missing evidence MUST be stated explicitly.

## Inference and uncertainty

Every step that moves beyond directly supported evidence MUST be marked as inference.

An inference SHOULD state:

- which evidence it uses;
- which assumptions it depends on;
- which alternative explanations remain plausible;
- what new evidence could strengthen, weaken, or reverse it.

Uncertainty MUST NOT be collapsed into a binary verdict merely to make the output appear decisive. Unknown, contested, incomplete, and unverifiable are materially different states and SHOULD be identified separately.

## Narrative amplification

Narrative amplification analysis examines how a claim may gain apparent force beyond its evidence. Relevant mechanisms include repetition, urgency, selective omission, compression of uncertainty, appeal to authority, emotionally loaded framing, false consensus, and movement from possibility to certainty.

Identifying amplification does not prove that the underlying claim is false. It identifies a review risk that must be separated from the claim's evidential status.

## Operational relevance and signal gate

Operational relevance records the bounded consequence of the analysis. It does not automatically authorize implementation or recommend an outcome.

Repository action is justified only when there is a valid signal:

- regression;
- unclear architecture;
- contributor friction;
- documentation drift;
- CI or runtime signal;
- governance risk;
- explicit user request.

When no valid signal exists, the correct result is controlled observation. When a signal exists, any action MUST be represented as a small, traceable, reviewable GitHub issue or Pull Request with explicit scope and validation.

## AI and chat control boundary

Chat is an interaction surface, not the project control plane.

AI systems may observe, analyze, draft, review, compare, and execute a narrowly authorized repository change. They MUST NOT self-authorize that change or become a hidden source of authority.

No model family, model version, provider, prompt, conversation, memory system, ranking, or hidden control path may:

- ratify governance;
- override repository evidence;
- alter roadmap or architecture without the required GitHub record;
- approve its own work;
- merge its own governance change;
- bypass protected-branch, review, or CI requirements;
- conceal provenance, uncertainty, model involvement, or material disagreement.

A more capable model may improve analytical depth, but it does not receive greater governance authority. Changing models or providers does not change this boundary.

Human accountability remains mandatory for ratification, publication, escalation, and sensitive use. AI assistance must remain visible through the issue, branch, commits, Pull Request, review record, and checks that govern the change.

## Prohibited uses

This protocol MUST NOT be used as:

- a true/false oracle;
- a substitute for primary evidence or domain expertise;
- a hidden scoring, ranking, or decision authority;
- a pretext for surveillance or profiling of private persons;
- a mechanism for coercion, deception, propaganda, targeted political persuasion, harassment, or psychological manipulation;
- an automated censorship or enforcement mechanism;
- a basis for consequential decisions about people without separate legal, governance, and human review;
- a method for bypassing lawful oversight or repository governance;
- a way to present uncertain analysis as settled fact.

## Relationship to existing repository documents

This protocol specializes the analytical decomposition and human-AI handoff rules already reflected in the Charter, Kernel, Consensus Process, Evaluation Standard, External AI Review Protocol, AGENTS.md, and AI handoff record.

`docs/concepts/governance-intelligence.md` remains a non-normative conceptual introduction. This file is the canonical governance source for the protocol.

`docs/rfc/constitutional_governance_ai_regulatory_boundary.md` remains a separate Draft RFC. Ratifying this protocol does not accept, supersede, or silently implement that RFC.

Any conflict or proposed expansion MUST be resolved through the repository's existing source-of-truth and consensus rules.

## Change control

Material changes to this protocol require:

1. an explicit GitHub issue or RFC describing the signal, scope, risks, and compatibility;
2. a small Pull Request with a visible diff;
3. synchronized governance mirrors under the repository translation policy;
4. human-accountable review with objections recorded and resolved;
5. passing repository checks before merge.

Merge of the Pull Request linked to issue #1694 constitutes ratification of this version, provided no sustained governance objection remains.

This protocol does not authorize runtime, schema, benchmark, CI, roadmap, provider, ingestion, scoring, dashboard, or deployment changes. Each such change requires its own scoped GitHub signal and review path.

## Validation

A conforming review can answer, from the record:

- What is claimed?
- What evidence supports or contradicts it, and where did that evidence come from?
- What is inferred rather than observed?
- What remains uncertain?
- What narrative amplification is present or absent?
- What operational signal exists, if any?
- Who remains accountable for the decision or next action?
- Which GitHub artifact records the authoritative state?

The protocol is structurally valid when its canonical file and all required language mirrors exist, preserve normative meaning, contain no placeholders, and introduce no unscoped implementation change.
