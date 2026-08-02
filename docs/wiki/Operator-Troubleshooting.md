# Resolución de problemas de Operator

> **Estado:** diagnóstico del Operator público auditado el 2026-08-02.
> **Base auditada:** [`c399c94`](https://github.com/Voxterrae/HUB_Optimus/commit/c399c94e098058a723482001811c7d8491ebbd5e).

| Síntoma | Causa probable | Acción |
| --- | --- | --- |
| Se queda en `6 %` | El navegador todavía ejecuta el worker antiguo `v0-26`. | Recarga dos veces o abre una pestaña privada; confirma después que aparece el flujo manual/local. |
| Una URL sola pide texto | Es el límite intencional del Operator público `v0-27`; no se envió ninguna petición. | Pega el texto completo o espera al Operator privado autenticado. |
| URL + texto no avanza | Falta revisar o confirmar los pasajes propuestos. | Revisa la selección, marca la confirmación y pulsa de nuevo. |
| Aparece “1.200 caracteres” | Es el contexto opcional, no el máximo de la fuente. | Introduce la fuente en el campo de texto principal. |
| Hay pasajes seleccionados pero no borrador | Falta la confirmación humana. | Revisa, marca la confirmación y pulsa de nuevo. |
| Aparece `401` o `403` | La futura consola privada exige sesión y rol autorizados. | El propietario o IT debe revisar Entra y los roles `HUB.Owner`/`HUB.Operator`. |
| Aparece `429` | Límite temporal de solicitudes. | Espera antes de reintentar. |
| Aparece `502` o un error `5xx` | Servicio privado no desplegado o no saludable. | Utiliza texto manual y revisa el estado de despliegue. |
| Se muestra una versión antigua | Puede quedar una caché del PWA. | Recarga dos veces. Antes de borrar datos del sitio, exporta los borradores locales. |

No compartas contraseñas, tokens, cookies, secretos, identificadores internos
ni capturas que los contengan.

## Evidencia relacionada

- [Operaciones EC2](https://github.com/Voxterrae/HUB_Optimus/blob/c399c94e098058a723482001811c7d8491ebbd5e/ops/ec2/README.md)
- [Issue #1835: frontera autenticada](https://github.com/Voxterrae/HUB_Optimus/issues/1835)
- [PR #1844: implementación OIDC en borrador](https://github.com/Voxterrae/HUB_Optimus/pull/1844)
