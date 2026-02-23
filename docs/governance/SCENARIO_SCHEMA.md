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
- Empty role arrays are rejected.
- Missing required fields are rejected.

## Typical invalid inputs (must fail)
- Missing `success_criteria`.
- `roles` is an empty array.
- `max_rounds` is `0` or a non-integer value.

## Extension guidance
- Keep backward compatibility when possible; add optional fields first.
- If a new required field is needed, bump schema version and update examples/tests in the same PR.
- Update this document and `scenario.schema.json` together; never update one without the other.
