# RFC: IP / Patent / Confidential Disclosure Boundary

## Status

Draft / RFC-only / not implemented.

This RFC defines the public/private boundary for HUB_Optimus intellectual property, patent-sensitive material, confidential disclosures, prior-art notes, invention records, enterprise strategy, and counsel-reviewed material.

This RFC does not provide legal advice, does not file patents, does not confirm patentability, does not create a private repository, does not define licensing terms, and does not authorize implementation, commercial launch, enforcement action, runtime changes, CI changes, schema changes, benchmark changes, HERMES work, API work, or enterprise deployment.

Parent issue: #1634

## Decision

HUB_Optimus must separate public repository material from confidential, patent-sensitive, security-sensitive, client-sensitive, and commercial-sensitive material.

Public GitHub may contain governance, RFCs, high-level boundaries, source-of-truth rules, non-confidential docs, tests, examples, and reviewable implementation artifacts.

Public GitHub must not contain unreviewed invention disclosures, confidential implementation strategy, patent claim drafting, private prior-art analysis, client data, commercial contract terms, secrets, credentials, or security-sensitive deployment details.

## Why this RFC exists

HUB_Optimus is publicly visible but rights-restricted. As the system moves toward Semantic Engine, Enterprise, HERMES, and commercial operation, uncontrolled public disclosure could create legal, patent, commercial, security, or client-confidentiality risk.

The project needs a rule that prevents:

- accidental loss of patent novelty;
- public exposure of confidential invention details;
- leaking private client material;
- exposing commercial strategy prematurely;
- mixing legal claims with technical governance;
- publishing sensitive security/deployment details;
- treating chat as a durable confidential register.

## Definitions

### Public repository material

Material safe to publish in the public GitHub repository after normal review.

Examples:

- governance boundaries;
- RFCs;
- non-confidential docs;
- schemas;
- tests;
- examples;
- public claims;
- public evidence;
- implementation already intended for public review;
- high-level architecture boundaries.

### Patent-sensitive material

Material that may affect patentability, claim scope, novelty, inventive step, trade-secret value, or filing strategy.

Examples:

- invention disclosures;
- novel technical mechanisms not yet filed or reviewed;
- claim language;
- technical differentiation arguments;
- prior-art comparisons;
- unpublished implementation details;
- commercializable methods not yet protected.

### Confidential material

Material that should not be placed in public GitHub.

Examples:

- client data;
- private business plans;
- non-public partner discussions;
- legal advice;
- counsel notes;
- security-sensitive design;
- credentials;
- private deployment details;
- contract terms;
- pricing strategy;
- internal invention logs.

### Counsel-reviewed intake

A private workflow where patent-sensitive or legally sensitive material is reviewed before publication, implementation, licensing, enforcement, or external disclosure.

This RFC defines the need for this boundary but does not create legal process or replace counsel.

## Core rule

> Public GitHub is not the confidential invention register.

A public issue, PR, commit, RFC, README, screenshot, chat paste, or social post must not be used as the primary place to store confidential IP strategy.

## Allowed in public GitHub

The following may be public when written conservatively:

- high-level RFC boundaries;
- source-of-truth rules;
- architectural separation;
- non-confidential implementation;
- non-sensitive tests;
- public scenario examples;
- public datasets with no private data;
- public claim records clearly marked as public/unverified when appropriate;
- docs explaining what the system does not do;
- capability status tables that avoid overclaiming;
- reviewable governance language.

## Not allowed in public GitHub

Do not publish:

- patent claim drafts;
- detailed invention disclosures;
- private prior-art conclusions;
- counsel communications;
- legal advice;
- unfiled novel implementation strategy;
- confidential client workflows;
- private business negotiations;
- non-public customer data;
- credentials, tokens, keys, secrets;
- security-sensitive deployment topology;
- exploit, evasion, or unauthorized access details;
- commercial contract terms;
- pricing strategy;
- private enforcement strategy;
- screenshots containing private personal, client, or legal data.

## Patent-sensitive disclosure handling

Before adding patent-sensitive material to GitHub, ask:

1. Is this already public?
2. Is this needed for current review?
3. Could this affect novelty or claim scope?
4. Has counsel reviewed it?
5. Can this be described as a high-level boundary instead?
6. Can implementation details be deferred to a private intake?
7. Is this necessary for an approved issue/PR?

If uncertain, do not publish.

## Public-safe wording pattern

Use conservative public wording such as:

> This capability is planned / RFC-only / not implemented.

> This document defines boundaries and non-goals; it does not disclose confidential implementation details.

> Patent-sensitive implementation details require private counsel-reviewed intake.

Avoid wording such as:

> Here is the exact invention claim.

> Here is how to reproduce the protected mechanism commercially.

> Here is our private patent strategy.