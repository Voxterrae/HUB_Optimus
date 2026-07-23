# Research Memo: Public Calculation Integrity and Automated/Semi-Automated Risk Scoring

## Status

- Draft / documentary research only
- Civic audit scope, not an incident response
- Non-accusatory and reviewable by external collaborators
- No production-system interaction beyond public-document reading
- No implementation work is authorized by this memo

## Purpose

This memo defines a governed research track for public calculation integrity and automated or semi-automated risk-scoring language in Spanish public systems. The purpose is to improve transparency, explainability, reversibility, and citizen recourse without moving into unauthorized access, endpoint probing, or accusatory public claims.

## Scope and boundaries

The memo covers:

- AEAT and TGSS calculation and data-exchange surfaces that are publicly documented or referenced in official administrative material
- automated or semi-automated decision points that affect calculation, correction, settlement, or routing
- calculation integrity, explanation gaps, correction time, and reversibility
- synthetic test cases that do not use real personal data
- public-source evidence, legal and documentary analysis, and transparency metrics

The memo does not cover:

- unauthorized access
- credential testing
- traffic stress testing
- endpoint probing or abuse
- mass submissions to public portals
- personal data processing outside explicit voluntary and strongly anonymized use
- public accusations without evidence decomposition

## Public surfaces to map

The initial review surface should include:

- AEAT tax calculation and reconciliation surfaces
- TGSS contribution and settlement surfaces
- data-exchange surfaces between obligated parties, authorized agents, and public registries
- administrative workflows where mismatch, correction, or settlement logic may be partially automated
- public explanation and appeal channels for administrative decisions

These surfaces should be separated from legal decision-making. A calculation error is not the same as a data-quality problem, and a risk-scoring label is not the same as a legal determination.

## Claim decomposition

| Layer | Example | Evidence class | Operational relevance |
|---|---|---|---|
| Claim | Public systems can make automated or semi-automated decisions that affect citizens. | Public documentation and legal material | Establishes the research scope. |
| Evidence | Official sources describe correction, settlement, mismatch, or routing steps. | Documentary evidence | Supports source-based analysis. |
| Inference | Repeated correction delays may indicate weak reversibility or explanation standards. | Inference from documented process patterns | Useful for risk framing, not proof of misconduct. |
| Uncertainty | The exact decision logic or model weighting may be unavailable in public material. | Uncertainty | Prevents overclaiming. |
| Narrative amplification | A single case should not be generalized into a systemic allegation. | Narrative risk | Keeps the research non-accusatory. |
| Operational relevance | Metrics on reversals, appeal success, and correction time can inform transparency and governance. | Operational signal | Supports reviewable follow-up work. |

## Synthetic test cases

The Phase 1 matrix is intentionally reduced to six high-signal cases:

1. self-employed worker with a change in contribution base
2. company with medical leave or temporary incapacity status
3. worker with multiple jobs
4. fiscal address out of sync
5. debt already paid but not synchronized
6. benefit with variable income

Each case should be evaluated for:

- expected calculation or action
- possible mismatch
- citizen harm
- recourse path
- reversibility metric

## Proposed transparency metrics

| Metric | Why it matters |
|---|---|
| Calculation discrepancy rate | Measures how often the system produces a mismatch or correction need. |
| Appeal success rate | Indicates whether review mechanisms are effective. |
| Reversal rate | Measures how often incorrect outcomes are corrected. |
| Rectification time | Captures delay and administrative burden. |
| Unresolved data mismatch backlog | Shows structural friction and persistence. |
| Explanation gap rate | Measures how often citizens cannot obtain a clear reason for a decision. |
| Human review coverage | Indicates where automated or semi-automated output is still checked by a person. |

## Evidence sources to review

The documentary review should prioritize:

- BOE and other legal sources
- AEAT guidance and published administrative material
- Seguridad Social and TGSS material
- ENS obligations and audit references
- AEPD guidance and case patterns
- Defensor del Pueblo reports or recommendations
- public tender documents
- transparency requests and published responses
- anonymized citizen case studies

## Prohibited methods

This research track must not use:

- unauthorized access
- endpoint probing or abuse
- credential testing
- system stress by traffic
- mass submissions to public portals
- personal-data collection outside explicit voluntary and strongly anonymized use
- any method that would convert research into operational intrusion or public accusation

## Research posture

This memo is a bounded, documentary, synthetic, and non-operational research instrument. It is intended to support fair review of public calculation integrity, explanation quality, and citizen recourse while preserving legal, privacy, and safety boundaries.
