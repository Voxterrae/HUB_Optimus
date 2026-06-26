# RFC: WhatsApp Claim Intake Adapter Boundary

## Status

- Draft / RFC only
- Governance proposal
- Not implemented
- Tracks issue #1650
- No runtime, schema, dataset, fixture, benchmark, CI, dashboard, scoring, bot, webhook, or LLM-as-judge change

## Purpose

This RFC defines a safe boundary for using WhatsApp or similar external messaging channels as manual or semi-manual intake sources for `claim_record` analysis.

The goal is to let low-friction user-submitted material be transformed into structured epistemic decomposition without implying that HUB_Optimus has direct backend access to WhatsApp, TikTok, Meta, Twilio, Make, Zapier, or any other external channel.

Core rule:

```text
External chat content is intake material, not project truth.
```

Spanish reference:

```text
El contenido de chat externo es material de entrada, no verdad del proyecto.
```

## Relationship to Existing Work

This RFC does not replace existing work.

- `docs/rfc/epistemic_analysis_modes.md` defines `claim_record` as the mode for concrete assertions and lists the expected decomposition fields.
- Issue #1547 defines the current `claim_record` dataset/schema lane for narrative-risk claim triage.
- Issue #1650 requests this external messaging intake boundary.

## Intake Boundary

A WhatsApp-originated item may enter HUB_Optimus only as user-submitted material that is explicitly framed before analysis.

Allowed flow:

```text
WhatsApp or mobile share sheet -> manual copy / controlled adapter -> claim_record -> epistemic decomposition -> human-readable result
```

Disallowed flow:

```text
WhatsApp -> hidden HUB_Optimus backend authority -> approve / deny / decide action
```

The adapter, if it exists in the future, is not an authority. It may only preserve, normalize, redact, and package submitted material for analysis.

## Minimal User Flow

A non-technical user should be able to send material with a simple instruction such as:

```text
Check this.
```

or:

```text
Is this narrative or evidence?
```

The receiving operator or adapter may then transform the item into a structured claim intake envelope. The user does not need to know the internal terms `claim_record`, `evidence_tier`, or `narrative_amplification`.

Example low-friction path:

```text
1. User sees a TikTok, screenshot, message, article, or video.
2. User taps share or forward.
3. User sends it to a trusted WhatsApp contact, group, or future controlled intake endpoint.
4. The material is converted into a claim_record candidate.
5. HUB_Optimus returns a decomposition, not a verdict of truth.
```

## Input Requirements

Every WhatsApp-originated claim intake should preserve at least:

- submitted claim text or a concise operator-extracted claim;
- source channel;
- source control status;
- evidence items or declared attachments;
- privacy redaction status;
- requested output type.

Minimal input envelope:

```json
{
  "analysis_mode": "claim_record",
  "source_channel": "whatsapp",
  "source_control": "manual_copy_or_user_submitted",
  "claim_text": "...",
  "evidence_items": [],
  "attachments_declared": [],
  "privacy_redactions_applied": true,
  "requested_output": "epistemic_decomposition"
}
```

`source_control` should be explicit because a forwarded message, screenshot, copied link, downloaded file, and user-written summary have different evidentiary value.

## Output Requirements

The output must keep the existing `claim_record` decomposition boundary.

Minimal output envelope:

```json
{
  "analysis_mode": "claim_record",
  "claim": "...",
  "evidence": [],
  "inference": "...",
  "uncertainty": "...",
  "narrative_amplification": "...",
  "operational_relevance": "...",
  "non_authority_notice": "This output structures the claim; it does not verify, approve, deny, predict, or decide action."
}
```

The result may be rendered in plain language for a chat user, but the canonical structure must preserve the analytical separation.

## Plain-Language Result Pattern

For a non-technical mobile user, the output should be short and operational:

```text
What it claims:
...

What evidence is shown:
...

What is assumed or inferred:
...

What is still uncertain:
...

Narrative risk:
...

Useful next step:
...
```

The result must not say only `true` or `false` when the underlying evidence is incomplete, mixed, or indirect.

## Privacy and Redaction

External messaging content may contain personal data. Before material becomes a repository issue, dataset item, fixture, or public record, the operator must check for:

- phone numbers;
- names of private individuals;
- faces of private individuals;
- addresses;
- account handles where unnecessary;
- message metadata;
- screenshots containing unrelated contacts or notifications;
- minors;
- medical, legal, financial, or identity information.

Redaction must happen before publication or versioned storage.

## Human Confirmation Boundary

A WhatsApp message, TikTok video, screenshot, or forwarded post must not become repository truth automatically.

Before any item is stored in GitHub as an issue, dataset entry, fixture, or documentation example, a human operator must confirm:

1. the claim text is accurately extracted;
2. the evidence items are described without overstating them;
3. personal data has been redacted;
4. uncertainty is explicit;
5. the item belongs to `claim_record`, not `proposal_analysis` or `conflict_analysis`.

## Non-Goals

This RFC does not add, authorize, or require:

- WhatsApp API integration;
- TikTok API integration;
- Twilio integration;
- Meta API integration;
- Make or Zapier scenario implementation;
- webhook code;
- bot behavior;
- background automation;
- scraping;
- feed monitoring;
- runtime changes;
- `run_scenario.py` changes;
- `hub_optimus_simulator.py` changes;
- scenario schema changes;
- dataset changes;
- fixture changes;
- benchmark changes;
- CI changes;
- dashboards;
- scoring;
- LLM-as-judge;
- automated truth adjudication;
- approval, denial, compensation, enforcement, or operational command decisions.

## Acceptance Criteria

This RFC satisfies issue #1650 when:

- it defines WhatsApp and similar external messaging channels as intake sources only;
- it clearly separates external message intake from HUB_Optimus authority;
- it defines minimal input and output envelopes;
- it preserves the `claim_record` output fields;
- it includes a low-friction user flow suitable for non-technical users;
- it includes privacy and redaction requirements;
- it defines a human confirmation boundary before repo or dataset storage;
- it explicitly blocks runtime, schema, dataset, fixture, benchmark, CI, dashboard, scoring, bot, webhook, and LLM-as-judge changes;
- it remains small, reviewable, reversible, and RFC-only.

## Future Work

Possible follow-up work must be opened as separate GitHub issues after this RFC is reviewed.

Possible future sequence:

1. `docs: add operator guidance for external claim intake`
2. `docs: add mobile share-sheet examples for claim_record intake`
3. `rfc: define controlled external adapter requirements`

No follow-up is authorized by this RFC alone.
