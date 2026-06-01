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

The minimal case JSON must be an object with non-empty string fields:

```json
{
  "case_id": "case-minimal-001",
  "core_version_ref": "main",
  "input_summary": "Minimal CLI smoke case for Semantic Engine contracts."
}
```

## Out of scope

- API
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
