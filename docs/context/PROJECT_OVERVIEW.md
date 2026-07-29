# HUB_Optimus — project overview

Verified against repository commit
`df0ef345e5ac627f3e2735573c802fe2f60821f4` on 2026-07-29.

## In one paragraph

HUB_Optimus is a versioned methodology, governance corpus, and set of narrow
software prototypes for structuring scenarios, claims, evidence references,
uncertainty, and review. The repository currently contains a deterministic
round-based simulator, minimal Semantic Engine contracts/CLI, a browser
Operator prototype, local intake/operations scripts, experimental laboratory
tools, datasets, tests, and a static public site. It does **not** contain an
autonomous truth engine, general diplomatic evaluator, prediction system,
publicly attested Semantic Engine service, or completed enterprise/HERMES/
post-quantum product.

The detailed evidence ledger is
[`../architecture/capability_status.md`](../architecture/capability_status.md).

## What is built

- Canonical Spanish v1 methodology and an English parity target under
  `v1_core/languages/`.
- Human governance documents under `docs/governance/`.
- A JSON-schema-validated scenario CLI and a simple round-based simulator.
- Frozen scenario benchmarks and deterministic structural tests.
- Minimal Semantic Engine records and a CLI that assembles reviewable output.
- A local/browser Operator that prepares intake and draft records.
- A local/private single-URL intake path with strict stated limits.
- Experimental generator, mutator, telemetry, boundary, and frontier tools.
- Deterministic narrative dataset/schema consistency checks.
- Static site/PWA files and GitHub workflow code.

Each item is narrower than the overall project ambition. The ledger states its
tests, limitations, and known open defects.

## What is not built or not verified

- truth adjudication, motive inference, LLM-as-judge, autonomous decisions, or
  authority over people or institutions;
- real-world prediction, probabilistic forecasting, or evidence that synthetic
  scenario behavior generalizes to diplomacy;
- HERMES, an enterprise product, a post-quantum control plane, provider routing,
  public authentication/billing, or a public Semantic Engine API;
- an approved AWS-to-Azure migration or any provider commitment inferred from
  existing development scripts;
- professional Russian, Hebrew, or Simplified Chinese parity;
- private GitHub settings such as required reviews, Secret Scanning, Push
  Protection, rulesets, or a live deployment unless separately attested;
- current contents or released artifacts from
  [HUB-Optimus-labs](https://github.com/Voxterrae/HUB-Optimus-labs); another
  repository is external to this baseline and remains unresolved here.

## Kernel, consensus, runtime, and RFC are different things

| Term | Current repository meaning |
| --- | --- |
| Normative governance / Kernel | Human-authored rules under `docs/governance/`, including `KERNEL.md`, Charter, Consensus Process, and Trust Layer. These are protected text, not an executable or an AI authority. |
| Canonical v1 methodology | The Spanish source under `v1_core/languages/es/`; English is a parity target. It describes more than the simulator implements. |
| Simulator | Python prototype with simple actors, rounds, policies, and exact offer-threshold success. It is not the Kernel and does not ratify governance. |
| Semantic Engine | Minimal contracts and deterministic CLI record assembly. It does not determine truth, score people, or make decisions. |
| Operator | Browser/local intake and draft-preparation surface. Its drafts are not automatically engine results or verified evidence. |
| RFC | A proposal under `docs/rfc/`. Merge records the proposal; it does not automatically accept it or authorize implementation. |

The current Consensus Process requires human proposal, review, objection
handling, ratification, and a record. It does not yet make every roster,
quorum, threshold, window, emergency, or rollback rule mechanically decidable.
Proposed changes associated with issue #1751 and PR #1773 are absent from this
baseline and are not current governance. The Pull Request's current lifecycle
is mutable GitHub state and remains external to this snapshot.

The versioned RFC registry is
[`../rfc/registry.v1.json`](../rfc/registry.v1.json), with a readable guide in
[`../rfc/README.md`](../rfc/README.md).

## How claims are classified

| Class | Meaning here |
| --- | --- |
| Verified fact | Directly supported by a repository file, executable test, GitHub record, or inspected external state at the stated date. |
| Human/project declaration | A versioned statement of purpose, ownership, rights, governance, or ratification; it remains attributable to the responsible humans and may require legal/professional review. |
| Calculation or synthetic observation | Reproducible result inside the current simulator/tool assumptions; not a real-world fact or forecast. |
| Estimate or inference | Interpretation that must show assumptions and uncertainty. |
| Proposal | RFC or issue text that is not implemented or authoritative without its decision record. |
| Unknown / unverified | Evidence was unavailable, external, stale, or insufficient. No positive claim should be inferred. |

## Languages

Spanish is canonical for v1 methodology. English is the parity target.
Documentation also has German, Catalan, French, Russian, Hebrew, and Chinese
paths at different maturity levels. Directory or filename presence is not
translation quality. Russian remains progressive; Hebrew is right-to-left and
still largely stub/mirror content; current Chinese scope is intended as
Simplified Chinese (`zh-Hans`) but is stored under `docs/zh`. Native or
qualified human review is required before calling any of these professionally
translated or at parity.

## Operating discipline

- The ordered project hierarchy is
  [`SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md); GitHub `main` and each live
  GitHub object's own state come first for their applicable question.
- `docs/context/STATUS.md` resolves language and canonical-source conflicts
  only within that domain.
- Changes should remain one issue, one bounded branch, and one reviewable PR.
- AI can prepare evidence and proposals; it cannot supply human ratification,
  legal advice, professional translation review, or self-approval.
- Passing tests reduce known uncertainty; they do not establish correctness
  outside the tested contract.
