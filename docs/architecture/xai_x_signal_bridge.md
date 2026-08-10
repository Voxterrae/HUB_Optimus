# xAI / X Signal Bridge foundation

## Status and authority

This document describes the local phase-one prototype introduced under
[issue #1874](https://github.com/Voxterrae/HUB_Optimus/issues/1874). It is an
implementation boundary, not evidence of a live integration, deployment,
partnership, endorsement, approved X application, or configured provider
account.

The official visible X identity for this project is
[`@HubOptimus`](https://x.com/HubOptimus). The handle is not a sufficient
authorization identifier: a later live implementation must obtain the
authenticated account's stable `user_id` through
[`GET /2/users/me`](https://docs.x.com/x-api/users/get-my-user) and compare it
with a separately approved owner record before any write. That ID is not known
or asserted by this repository.

xAI is an optional analytical witness. X is an optional public-signal source
and governed publication destination. Neither becomes an authority over
claims, evidence, governance, publication, or human decisions.

## Implemented package boundary

The prototype is isolated in `hub_optimus/connect/` and is not imported by the
scenario runtime, Semantic Engine, Operator, browser code, EC2 scripts, or a
deployment.

| Module | Implemented phase-one behavior | Explicit non-capability |
| --- | --- | --- |
| `contracts.py` | Immutable provider-neutral request, result, citation, usage, hashing, and controlled-error contracts | No network, authentication, storage, evaluator, or model authority |
| `provider_xai.py` | Deterministic xAI Responses request bodies, `store: false`, non-public-classification rejection, optional ZDR-attestation policy, disabled-by-default adapter, injected transport protocol | No xAI SDK, HTTP client, credential loading, fixed model name, retry logic, or live transport |
| `source_x.py` | Disabled-by-default read adapter and compact X signal record with string IDs, URLs, dates, provenance, edit history, and text hash | No search client, crawler, write method, raw-post corpus, deletion synchronizer, or live transport |
| `publisher_x.py` | Disabled-by-default exact-account policy and deterministic `DryRun` plan bound to a SHA-256 digest | No publish method, OAuth, media upload, reply, mention, DM, like, follow, repost, quote, trend automation, or live write |

All tests are offline and use injected fakes. Enabling an adapter does not make
the repository network-capable; a separately reviewed transport would still
be required.

## xAI analytical-provider contract

The provider plan uses the xAI Responses surface rather than Chat Completions,
keeps `model_ref` as an opaque deployment reference, and produces a literal
request body with `input`, `store: false`, and a concrete object schema under
`text.format`. xAI documents Responses as the recommended interface. A future
transport must send that exact body; the prototype adapter locally revalidates
its returned JSON against Draft 2020-12 but supplies no transport. External
schema references are rejected so validation cannot become a hidden network
path.

`store: false` disables Responses state/history; it does **not** establish
Zero Data Retention. xAI may retain API inputs and outputs for abuse monitoring
under its default policy. When a deployment requires ZDR, configuration can
require the future transport to attest the `x-zero-data-retention: true`
response header. The current repository cannot verify team-level ZDR.

Sources:

- [xAI Responses and Chat comparison](https://docs.x.ai/developers/model-capabilities/text/comparison)
- [xAI Structured Outputs](https://docs.x.ai/developers/model-capabilities/text/structured-outputs)
- [xAI citations](https://docs.x.ai/developers/tools/citations)
- [xAI security and Zero Data Retention](https://docs.x.ai/developers/faq/security)

The dormant result contract can represent future provider citations with two
scopes kept distinct:

- `encountered`: the provider reported the URL among sources it found;
- `inline_cited`: the returned text attached an inline citation annotation.

The current request body enables no xAI search tool, so a normal phase-one
result has no tool-generated citations. Neither scope independently verifies
the cited material. Full provider input, structured output, citation URLs, and
raw response bodies are excluded from sanitized audit records; their hashes
and counts remain inspectable.

## X read-side data boundary

X post and user IDs are stored as decimal strings, not JSON numbers, following
the [X ID guidance](https://docs.x.com/fundamentals/x-ids). A derived post
record keeps:

- `post_id` and stable `author_id`;
- `username_at_observation` as mutable display context;
- an ID-based `https://x.com/i/status/{post_id}` reference form observed in
  xAI citations and the observed
  `https://x.com/{username}/status/{post_id}` permalink;
- creation and last-hydration timestamps;
- retrieval method and a content-addressed provenance-reference digest;
- normalized edit-history IDs and content-addressed evidence-reference digests;
- SHA-256 and character count of normalized text;
- `raw_text_retained: false`.

The package does not copy the observation body into the derived signal record;
the caller and any future transport remain responsible for the lifetime of
their `XPostObservation` object. The persistable record has no text field. This
reduces corpus and deletion-sync exposure; it does not itself satisfy every X
retention, rehydration, display, or deletion obligation. Those obligations
require a separate live-adapter review against the
[X Developer Policy](https://docs.x.com/developer-terms/policy) and
[X Display Requirements](https://docs.x.com/developer-terms/display-requirements).

## X publication policy

The only phase-one output is a deterministic plan. Its future X API payload is
strictly:

```json
{"text":"exact approved text"}
```

Links, review-only media metadata, source revision, evidence references, and
human-supplied gate facts remain outside the API payload but inside the hashed
approval descriptor. Identical descriptors produce identical hashes; any
publication-relevant change invalidates the hash.

Planning is disabled by default. When explicitly enabled, the policy accepts
only a standalone informational post for `@HubOptimus` and
rejects:

- another target account or non-`DryRun` mode;
- replies, quotes, DMs, likes, follows, reposts, or automated mentions;
- drafts, unverified evidence, non-public or client data;
- unresolved security, rights, or vulnerability status;
- affiliation, sponsorship, or endorsement claims;
- unsigned commercial commitments;
- repetitive or trend-driven automation;
- common credential-shaped text, any outbound-link query string, and local,
  non-global, browser-ambiguous, or bare autolinkable domain targets.

These structural checks constrain a plan; classification and gate flags are
caller assertions. They do not independently prove that content is true,
public, rights-cleared, secure, or commercially ratified.
Human review remains mandatory. X's current creation and automation boundaries
are documented in [Create Posts](https://docs.x.com/x-api/posts/create-post)
and the [X Automation Rules](https://help.x.com/en/rules-and-policies/x-automation).

## Future live-write gate

No live-write code exists in phase one. A separate issue and reviewed change
would have to establish all of the following before execution could be
considered:

1. user-context OAuth with the minimum reviewed scopes;
2. `GET /2/users/me` binding to the separately approved stable account ID;
3. display of the exact payload and complete approval descriptor;
4. explicit human approval of the exact `payload_sha256`;
5. a HUB Gateway receipt binding requester, approver, account ID, payload hash,
   policy revision, and expiry;
6. a single allowlisted `POST /2/tweets` attempt, fail-closed handling of an
   ambiguous result, and reconciliation before any retry;
7. immutable result evidence containing the returned post ID and post-check.

Merge of this prototype would not authorize that work or supply any of those
external facts.

## Product, data, and brand separation

- HUB_Optimus remains provider-agnostic; xAI can be replaced without changing
  Core authority.
- Requests labelled non-public are rejected. The caller remains accountable
  for correctly classifying input as public HUB_Optimus material.
- LCDH-OS, CRM, tenant, mailbox, customer, and private client data are outside
  this package.
- The browser must never hold provider or X credentials or call either API
  directly.
- The project must not use xAI, Grok, X, or Elon Musk to imply affiliation,
  sponsorship, endorsement, or shared ownership.
- Brand use must remain accurate and separately reviewed against the
  [xAI Brand Guidelines](https://x.ai/legal/brand-guidelines).

## Validation boundary

The focused tests cover disabled adapters, injected fake transports,
non-public-classification rejection, local JSON Schema result validation,
absence of raw X post text from the derived record, deterministic hashes,
account and interaction policy, rejection gates, strict text-only API payload
shape, sanitized audits, and absence of bundled network/live-publish code.

The repository has no local general-purpose secret scanner or SAST tool. These
tests are scoped regression evidence, not secret-scanning, legal, policy,
security, deployment, or platform-compliance certification. Hosted GitHub
checks and any external account or app settings remain separate live evidence.
