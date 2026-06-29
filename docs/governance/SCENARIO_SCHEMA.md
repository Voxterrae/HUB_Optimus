# HUB_Optimus Scenario Schema

## Purpose
Define the minimum structure required to execute `run_scenario.py` safely.
A scenario is a structured input contract, not an argumentative narrative.

## Canonical machine-readable contract
- JSON Schema file: [../../scenario.schema.json](../../scenario.schema.json)
- Contract versioning source: Git history for `scenario.schema.json`

## Required fields
- `title`: non-empty string
- `description`: non-empty string
- `roles`: non-empty array of `{ "name": string, "role": string }`
- `success_criteria`: non-empty object
- `max_rounds`: integer >= 1

## Validation behavior
- Unknown top-level fields are rejected (`additionalProperties: false`).
- Unknown role-level fields are rejected (`additionalProperties: false`).
- Empty role arrays are rejected.
- Missing required fields are rejected.

## Typical invalid inputs (must fail)
- Missing `success_criteria`.
- `roles` is an empty array.
- `roles[]` contains extra fields beyond `name` and `role`.
- `max_rounds` is `0` or a non-integer value.

## Relationship to the workflow scenario template

The workflow scenario template is the human authoring contract.
The JSON schema is the current machine runtime contract.
They are intentionally not equivalent.

The template helps authors describe context, actors, incentives, verification,
risks, rounds, evaluation, and meta-learning. The runtime schema only accepts the
minimal fields needed by the current prototype simulator.

Do not add template-only sections directly to runtime JSON files unless
`scenario.schema.json`, examples, tests, and documentation are updated in the same
scoped PR.

| Workflow template section | Current JSON runtime field | Status | Future semantic destination |
| --- | --- | --- | --- |
| `0) Metadatos` | Not represented | Template-only | Provenance, audit metadata, `core_version_ref` |
| `1) Resumen ejecutivo` | `description` | Partial | `input_summary`, case context |
| `2) Actores y roles` | `roles[].name`, `roles[].role` | Partial | Stakeholders, affected actors, role context |
| `3) Contexto y línea de tiempo` | `description` | Partial | Evidence context, uncertainty context |
| `4) Intereses, posiciones y restricciones` | Not represented | Template-only | Incentive analysis, conflict analysis |
| `5) Objetivo mínimo y criterios de éxito` | `success_criteria` | Partial | Outcome boundary, proposal success criteria |
| `6) Propuesta inicial` | Not represented | Template-only | `proposal_analysis`, submitted proposal boundary |
| `7) Verificación y cumplimiento` | Not represented | Template-only | Verification requirements, audit checks |
| `8) Riesgos y puntos de fricción` | Not represented | Template-only | Failure modes, abuse vectors, uncertainty |
| `9) Rondas recomendadas` | `max_rounds` | Partial | Sequencing requirements, negotiation plan |
| `10) Evaluación (post-mortem)` | Not represented | Template-only | Lab notes, evaluation trace, audit record |
| `11) Meta-learning` | Not represented | Template-only | Meta-learning record, decision trace |

## Runtime boundary

Current runtime success is intentionally narrow: `run_scenario.py` validates a JSON
scenario, executes round-based actor offers, checks whether any actor action
matches any `success_criteria` key/value pair, and writes a deterministic JSON
result.

This schema does not currently evaluate:

- incentive alignment;
- sequencing quality;
- verification strength;
- long-term stability;
- false-success risk;
- corrective options;
- meta-learning outcomes.

Those capabilities belong to the broader governance and Semantic Engine direction
and require separate issues or RFC follow-ups before implementation.

## Extension guidance
- Keep backward compatibility when possible; add optional fields first.
- If a new required field is needed, bump schema version and update examples/tests in the same PR.
- Update this document and `scenario.schema.json` together; never update one without the other.
- Preserve the distinction between template authoring fields and runtime executable fields.
