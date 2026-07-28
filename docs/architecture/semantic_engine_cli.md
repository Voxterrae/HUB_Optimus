# Semantic Engine CLI

## Status

Minimal CLI usage document for the HUB_Optimus Semantic Engine.

The CLI is the first execution surface for Semantic Engine contracts. It is intentionally small and does not implement API, HERMES, AWS, S3, vector search, evaluators, normalizers, scoring, or model-based judging.

## Command

```bash
python -m semantic_engine.cli analyze examples/semantic_engine/case_minimal.json
```

By default, the command writes contractual JSON to stdout.

## Output file

Use `--output` to write the same contractual JSON to a local file:

```bash
python -m semantic_engine.cli analyze examples/semantic_engine/case_minimal.json \
  --output outputs/semantic_engine/analysis_result.json
```

When `--output` is used:

- stdout remains empty on success;
- the JSON result is written as UTF-8;
- parent directories are created if needed;
- stderr remains reserved for controlled errors.

## Operating contract

```text
stdout = contractual JSON only when no --output path is provided
stderr = controlled human-readable errors
exit 0 = success
exit 1 = expected input/output error
```

## Current input contract

The source of truth is the versioned JSON Schema:
[`semantic_engine/contracts/case_input.schema.json`](../../semantic_engine/contracts/case_input.schema.json).
The CLI validates every case against `CaseInput v1` before constructing an
`AnalysisResult`.

The minimal case JSON must be an object with non-empty string fields:

```json
{
  "case_id": "case-minimal-001",
  "core_version_ref": "main",
  "input_summary": "Minimal CLI smoke case for Semantic Engine contracts."
}
```

Contract rules:

- unknown fields are rejected at the root and inside claim/evidence records;
- arbitrary JSON is allowed only inside an explicit `metadata` object, which is
  preserved in the output but remains opaque and non-authoritative; metadata
  keys do not become executable fields, evidence, verification, scoring,
  decision traces, audit events, or governance authority;
- `claim_id` and `evidence_id` values must be unique within their collections;
- every `supports_claim_ids` and `contradicts_claim_ids` entry must identify a
  submitted claim;
- input `decision_trace` and `audit_log` fields are forbidden because those are
  output-only engine records;
- errors identify the rejected JSON path, for example
  `$.claims[1].claim_id`.

The Operator handoff posts this CaseInput shape to the local `/analyze`
endpoint. The API delegates analysis to `hub-core analyze`, which invokes this
same CLI validator. Browser-local draft rendering remains a preview, not a
backend analysis or a substitute contract.

## Out of scope

- New public API surface
- HERMES PWA
- AWS runtime
- S3 persistence
- Vector DB
- Evaluators
- Normalizers beyond required field validation
- Scoring
- LLM/SLM judge
- Existing scenario runtime changes

## Next gate

After local output writing is stable, the next persistence step can define archive layout and S3 handoff rules. S3 should not be added until local output behavior is stable and reviewable.
