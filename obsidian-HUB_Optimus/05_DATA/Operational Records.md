---
type: "data-model"
status: "partial"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
source:
  - "ops/ec2/hub-core.sh"
  - "ops/ec2/deploy-current.sh"
  - "ops/ec2/rollback-current.sh"
tags:
  - "data"
  - "operations"
  - "provenance"
---

# Operational Records

## RUN_STATE

Cada run de `hub-core` registra:

```text
run_id
command
release
commit
path
input
ran_at_utc
```

Los directorios usan timestamp UTC y sufijo exclusivo aleatorio.

## Run Outputs

Según el comando:

- `pytest.log`
- benchmark logs/summaries
- `input_case.json`
- `analysis_result.json`
- scenario input/result
- narrative benchmark output

## RELEASE_STATE

Registra la identidad del ref solicitado/resuelto, release, commit, validación y launcher. El proceso HTTP captura además su running release/commit/launcher hash al arrancar.

## ROLLBACK_STATE

Separa una transición de rollback de un deploy y permite inspección/recovery.

## Persistence and Permissions

- Run root: host filesystem gestionado.
- `umask 077`.
- Temp CaseInput de API: mode `0600`, eliminado tras hub-core.
- Los scripts preservan candidate/recovery evidence ante fallo.

## Boundary

Estos records prueban una operación solo cuando se inspeccionan en el host correspondiente. La existencia del formato en el repo no prueba que un run o deployment se haya ejecutado.

## Related

- [[EC2 Core Runner and Run Registry]]
- [[EC2 Release Operations]]
- [[GET status]]
- [[POST analyze]]
