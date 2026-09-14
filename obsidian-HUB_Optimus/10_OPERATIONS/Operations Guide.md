---
type: "operations"
status: "partial"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "operations"
  - "runbook"
  - "provenance"
---

# Operations Guide

## Local Development

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Scenario and Semantic commands are documented en [[Scenario CLI]] y [[Semantic Engine CLI]].

## Managed Host Commands

```bash
hub-core status
hub-core test
hub-core benchmark
hub-core semantic-smoke
hub-core scenario-smoke
hub-core analyze /path/to/case.json
```

Release operations require an explicit full commit SHA or tag; no implicit branch/HEAD default.

## Deploy Discipline

1. Verify owner-authorized merged ref.
2. Run preflight read-only checks.
3. Deploy the exact ref.
4. Inspect release state and validation evidence.
5. Restart service explicitly only after review.
6. Verify process-bound `/status`.
7. Preserve rollback/recovery records.

## Rollback Discipline

Rollback validates the target release and launcher provenance, snapshots current state and restores transactionally on failure.

## Pages Operations

A merge touching `site/**` triggers Pages workflow source. Observe check/deployment status and verify `/`, `/operator/` and the new intelligence route.

## Observability Boundary

There is run/release provenance and service status, but no full monitoring/telemetry platform. [[Local Control Prototype]] does not implement OpenTelemetry.

## Related

- [[EC2 Core Runner and Run Registry]]
- [[EC2 Release Operations]]
- [[Deployment Architecture]]
- [[Operational Records]]
