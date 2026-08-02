# Resolución de problemas de Operator

> **Estado:** diagnóstico del Operator público auditado el 2026-08-02.  
> **Base auditada:** [`4400b0d`](https://github.com/Voxterrae/HUB_Optimus/commit/4400b0d778dc64779f9db9bd4cdb398a7d46a69b).

| Síntoma | Causa probable | Acción |
| --- | --- | --- |
| Se queda en `6 %` | Está esperando el intake remoto de URL, que no está operativo públicamente. | Borra completamente la URL y usa texto pegado. |
| “URL no disponible” | El backend público no responde o la fuente rechaza la extracción. | Usa el flujo manual; no reintentes indefinidamente. |
| Sigue pidiendo texto | La URL no produjo una fuente utilizable. | Pega el texto completo con el campo URL vacío. |
| Aparece “1.200 caracteres” | Es el contexto opcional, no el máximo de la fuente. | Introduce la fuente en el campo de texto principal. |
| Hay pasajes seleccionados pero no borrador | Falta la confirmación humana. | Revisa, marca la confirmación y pulsa de nuevo. |
| Aparece `401` o `403` | La futura consola privada exige sesión y rol autorizados. | El propietario o IT debe revisar Entra y los roles `HUB.Owner`/`HUB.Operator`. |
| Aparece `429` | Límite temporal de solicitudes. | Espera antes de reintentar. |
| Aparece `502` o un error `5xx` | Servicio privado no desplegado o no saludable. | Utiliza texto manual y revisa el estado de despliegue. |
| Se muestra una versión antigua | Puede quedar una caché del PWA. | Recarga primero. Antes de borrar datos del sitio, exporta los borradores locales. |

No compartas contraseñas, tokens, cookies, secretos, identificadores internos
ni capturas que los contengan.

## Evidencia relacionada

- [Operaciones EC2](https://github.com/Voxterrae/HUB_Optimus/blob/4400b0d778dc64779f9db9bd4cdb398a7d46a69b/ops/ec2/README.md)
- [Issue #1835: frontera autenticada](https://github.com/Voxterrae/HUB_Optimus/issues/1835)
- [PR #1844: implementación OIDC en borrador](https://github.com/Voxterrae/HUB_Optimus/pull/1844)
