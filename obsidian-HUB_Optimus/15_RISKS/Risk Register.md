---
type: "risk-register"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "risks"
  - "governance"
  - "security"
---

# Risk Register

## Summary

| Risk | Severity | Status | Evidence |
| --- | --- | --- | --- |
| Documentation drift | `high` | `active` | CONFIRMED |
| Ambition–implementation gap | `high` | `active` | CONFIRMED |
| External deployment state | `high` | `unknown` | UNKNOWN |
| Draft mistaken for evidence | `high` | `active` | CONFIRMED |
| API exposure boundary | `high` | `partial` | CONFIRMED |
| Methodology/runtime conflation | `medium` | `active` | CONFIRMED |
| Project intelligence staleness | `medium` | `active` | INFERRED |
| Single owner review dependency | `medium` | `active` | CONFIRMED |

## Documentation drift

- **Severity:** `high`
- **Status:** `active`
- **Evidence:** `CONFIRMED`
- **Observation:** Project overview y capability ledger están fijados a df0ef… del 29-07-2026, mientras main actual es 30e985… del 16-08-2026.
- **Mitigation:** Fijar cada análisis a commit/tree y favorecer código, schemas, tests y workflows actuales.

## Ambition–implementation gap

- **Severity:** `high`
- **Status:** `active`
- **Evidence:** `CONFIRMED`
- **Observation:** La metodología y visión son más amplias que el simulador y Semantic Engine actuales.
- **Mitigation:** Mostrar límites por componente y evitar claims de truth/prediction/autonomy.

## External deployment state

- **Severity:** `high`
- **Status:** `unknown`
- **Evidence:** `UNKNOWN`
- **Observation:** El repositorio contiene workflows y runbooks, no una atestación permanente de Pages, EC2, DNS, TLS o Nginx.
- **Mitigation:** Verificar el objeto externo tras cada despliegue y registrar commit/receipts.

## Draft mistaken for evidence

- **Severity:** `high`
- **Status:** `active`
- **Evidence:** `CONFIRMED`
- **Observation:** Operator y controlled intake generan material local/unreviewed.
- **Mitigation:** Conservar provenance, uncertainty, verification_status y aprobación humana.

## API exposure boundary

- **Severity:** `high`
- **Status:** `partial`
- **Evidence:** `CONFIRMED`
- **Observation:** La API local carece de autenticación; el proxy versionado limita rutas pero su despliegue es externo.
- **Mitigation:** Mantener loopback, allowlist mínima y no exponer /analyze o /status sin un diseño autenticado separado.

## Methodology/runtime conflation

- **Severity:** `medium`
- **Status:** `active`
- **Evidence:** `CONFIRMED`
- **Observation:** La metodología no se carga como policy autónoma.
- **Mitigation:** Representar la relación como guía humana, no como call path.

## Project intelligence staleness

- **Severity:** `medium`
- **Status:** `active`
- **Evidence:** `INFERRED`
- **Observation:** El modelo es un snapshot generado y no se actualiza automáticamente.
- **Mitigation:** Aplicar el protocolo delta, actualizar commit/tree y validar model/notes/site en un PR acotado.

## Single owner review dependency

- **Severity:** `medium`
- **Status:** `active`
- **Evidence:** `CONFIRMED`
- **Observation:** CODEOWNERS asigna todo el repositorio a @Voxterrae y la autoridad final es humana.
- **Mitigation:** Mantener PRs pequeños, evidencia clara y no eludir la puerta de propietario.


## Risk Ownership

Technical risk reduction can be implemented in reviewable PRs. Acceptance of residual risk, authorization, merge and deployment remain human owner actions.

## Related

- [[Security Boundaries]]
- [[Limitations]]
- [[Current State]]
- [[Update Protocol]]
