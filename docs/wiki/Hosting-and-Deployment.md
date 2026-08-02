# Hosting y despliegue

> **Estado:** GitHub Pages público; backend privado pendiente.
> **Última revisión:** 2026-08-02.
> **Base auditada:** [`c399c94`](https://github.com/Voxterrae/HUB_Optimus/commit/c399c94e098058a723482001811c7d8491ebbd5e).

| Superficie | Alojamiento | Estado |
| --- | --- | --- |
| Web y Operator público | GitHub Pages | Disponible; intake manual/local desplegado en `c399c94`. |
| Preview de revisión | ChatGPT Sites, cuando se utilice | No es fuente de verdad ni producción canónica. |
| `hub-api` | EC2, `127.0.0.1:8080` | Última auditoría conocida, 2026-07-29: host existente y servicio local, pero despliegue obsoleto; estado actual no reatestado. |
| Operator privado | `api.huboptimus.dev` | No operativo; candidato en PR #1844. |

## GitHub Pages

El workflow publica `site/` cuando los cambios correspondientes llegan a
`main`.

- [Workflow Pages](https://github.com/Voxterrae/HUB_Optimus/blob/c399c94e098058a723482001811c7d8491ebbd5e/.github/workflows/pages.yml)
- [Última ejecución auditada](https://github.com/Voxterrae/HUB_Optimus/actions/runs/30765273410)
- [Web pública](https://huboptimus.dev/)

No hace falta modificar el DNS de `huboptimus.dev` para trabajar con GitHub
Pages si ya está correctamente configurado.

## Orden para activar el backend

1. Fusionar y validar la seguridad de despliegue de
   [#1832](https://github.com/Voxterrae/HUB_Optimus/issues/1832).
2. Desplegar y acreditar el SHA exacto mediante
   [#1831](https://github.com/Voxterrae/HUB_Optimus/issues/1831).
3. Preparar Redis, NGINX, TLS, firewall y Microsoft Entra.
4. Validar propietario, equipo y cuenta sin rol.
5. Ejecutar QA real y rollback.
6. Solo entonces fusionar y desplegar la
   [PR #1844](https://github.com/Voxterrae/HUB_Optimus/pull/1844).

No debe enviarse tráfico de producción a `api.huboptimus.dev` hasta disponer de
destino estable, servicios preparados y una vía de emisión TLS definida. Con
ACME DNS-01 puede emitirse el certificado antes de publicar el registro de
servicio; con HTTP-01 debe utilizarse una ventana DNS controlada y validar TLS
antes de admitir tráfico de usuarios.

La auditoría de 2026-07-29 observó un checkout antiguo, NGINX solo en HTTP y sin
DNS resolviendo para la API. Es evidencia histórica, no prueba del estado live
actual. No se publican en la Wiki direcciones, identificadores ni credenciales
del host.

## Seguridad documental

Esta Wiki no debe contener secretos, direcciones internas sensibles, cookies,
tokens, tenant secrets, credenciales ni valores reales de configuración.

- [Guía AWS de desarrollo](https://github.com/Voxterrae/HUB_Optimus/blob/c399c94e098058a723482001811c7d8491ebbd5e/docs/architecture/aws_dev_runtime.md)
- [Operaciones EC2](https://github.com/Voxterrae/HUB_Optimus/blob/c399c94e098058a723482001811c7d8491ebbd5e/ops/ec2/README.md)
