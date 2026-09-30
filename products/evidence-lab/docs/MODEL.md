# Dataverse model

## Separation of concerns

`OptimusEvidenceLab` is a domain solution for evidence, provenance and
aggregate observations. It is deliberately separate from
`OptimusAdminGateway`, which governs administrative requests, approvals, jobs
and events.

## Tables

- **Geography** — canonical or source-specific geographic scope.
- **Source** — stable source identity and reproducibility metadata.
- **Release** — one versioned publication or captured source release.
- **Metric** — stable semantic definition, unit and population.
- **Observation** — one aggregate value bound to a Geography, Release and Metric.

## Relationships

```text
Source     1 ─── N Release
Geography  1 ─── N Observation
Release    1 ─── N Observation
Metric     1 ─── N Observation
```

All delete cascades are restrictive.

## Responsible-use boundary

No patient-level data, names, contact data, identifiers, individual risk
scores or nationality-based causal inferences are permitted in this version.
