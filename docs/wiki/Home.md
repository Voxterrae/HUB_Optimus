# HUB_Optimus

> **Estado:** Wiki de navegación; no sustituye la documentación versionada.
> **Última revisión documental:** 2026-10-16.
> **Base documental:** [`23ea5a6`](https://github.com/Voxterrae/HUB_Optimus/commit/23ea5a6677c07dcefab60f70c6b1641a3541f0b0).
> Esta revisión no reatesta despliegues ni servicios externos.

HUB_Optimus organiza información en una cadena revisable:

**Realidad → Evidencia → Inferencia → Narrativa → Señal operativa**

No es un oráculo, no determina automáticamente qué es verdad y no sustituye la
responsabilidad humana.

## Accesos rápidos

- [Web pública](https://huboptimus.dev/)
- [Operator público](https://huboptimus.dev/operator/?lang=es#product_intake)
- [[Guía de Operator|Operator-User-Guide]]
- [[Resolución de problemas|Operator-Troubleshooting]]
- [[Arquitectura|Architecture]]
- [[Hosting y despliegue|Hosting-and-Deployment]]
- [[Roadmap y estado|Roadmap-and-Live-Status]]
- [Empezar en español](https://github.com/Voxterrae/HUB_Optimus/blob/23ea5a6677c07dcefab60f70c6b1641a3541f0b0/docs/es/00_start_here.md)

## Estado resumido

- La web pública se despliega mediante GitHub Pages.
- El Operator público puede preparar borradores a partir del texto completo
  pegado y conservar una URL exacta como atribución local no verificada.
- El Operator público no recupera URLs: una URL sola termina de inmediato y
  remite al futuro Operator privado autenticado.
- La última auditoría conocida encontró el backend EC2 limitado a `localhost`
  pero obsoleto; su estado actual todavía no se ha reatestado.
- La frontera privada con Microsoft Entra/OIDC tiene código integrado mediante
  la [PR #1844](https://github.com/Voxterrae/HUB_Optimus/pull/1844); esta
  integración no acredita su despliegue.

## Fuente de verdad

Para cualquier conflicto, prevalecen `main`, los objetos vivos de GitHub y los
contratos aplicables del repositorio.

- [Jerarquía de fuentes](https://github.com/Voxterrae/HUB_Optimus/blob/23ea5a6677c07dcefab60f70c6b1641a3541f0b0/docs/context/SOURCE_OF_TRUTH.md)
- [README principal](https://github.com/Voxterrae/HUB_Optimus/blob/23ea5a6677c07dcefab60f70c6b1641a3541f0b0/README.md)
- [Estado de capacidades](https://github.com/Voxterrae/HUB_Optimus/blob/23ea5a6677c07dcefab60f70c6b1641a3541f0b0/docs/architecture/capability_status.md)
