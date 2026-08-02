# Arquitectura

> **Estado:** mapa orientativo; no acredita un despliegue.
> **Última revisión:** 2026-08-02.
> **Base auditada:** [`4400b0d`](https://github.com/Voxterrae/HUB_Optimus/commit/4400b0d778dc64779f9db9bd4cdb398a7d46a69b).

## Superficies principales

- **Core:** metodología v1; la versión canónica está en español.
- **Simulator:** prototipo determinista basado en escenarios.
- **Semantic Engine CLI:** valida contratos y prepara registros; no es un juez
  autónomo.
- **Operator:** interfaz de navegador para intake y borradores revisables.
- **GitHub Pages:** alojamiento de la web pública.
- **EC2:** entorno operativo privado/local, sin exposición pública acreditada.
- **Governance:** reglas humanas de revisión, cambios y responsabilidad.

## Flujo público actual

`GitHub main → Pages workflow → huboptimus.dev → Operator manual/local`

El navegador puede preparar borradores con texto pegado. No existe una API
pública de análisis certificada.

## Topología privada propuesta

`NGINX :443 → oauth2-proxy/Entra → gateway limitado → hub-api localhost`

Redis, oauth2-proxy, gateway y `hub-api` deben permanecer en loopback. Esta
topología pertenece a la [PR #1844](https://github.com/Voxterrae/HUB_Optimus/pull/1844)
y todavía no está acreditada como live.

## Límites

- Un documento no demuestra que un servicio esté desplegado.
- Una prueba acredita únicamente el comportamiento que verifica.
- Un borrador de Operator no es evidencia verificada.
- Un RFC no se aprueba a sí mismo.
- La Wiki nunca prevalece sobre `main` o los registros vivos de GitHub.

## Fuentes

- [Mapa completo de arquitectura](https://github.com/Voxterrae/HUB_Optimus/blob/4400b0d778dc64779f9db9bd4cdb398a7d46a69b/docs/architecture/system_architecture_map.md)
- [Contrato de runtime](https://github.com/Voxterrae/HUB_Optimus/blob/4400b0d778dc64779f9db9bd4cdb398a7d46a69b/docs/architecture/runtime_contract.md)
- [Jerarquía de fuentes](https://github.com/Voxterrae/HUB_Optimus/blob/4400b0d778dc64779f9db9bd4cdb398a7d46a69b/docs/context/SOURCE_OF_TRUTH.md)
