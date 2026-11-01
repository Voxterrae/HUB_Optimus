# Mwmbl Web pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Probar consultas Web reales a través de Optimus Search con una fuente externa explícita sin activar facturación.
**Architecture:** Adaptador Mwmbl optin tras la interfaz común del host HTTPS existente. La UI conserva fuentes/resultados y añade error de cuota; el inicio nativo automático mantiene su configuración previa.
**Tech Stack:** .NET10/ASP.NET Core/BCL, WPF existente; sin nuevos paquetes.
**Spec:** ../specs/2026-11-01-mwmbl-pilot-design.md

## Global Constraints
Base 46085be8; no CI/merge/infra/pagos/cuentas/llaves. Endpoint HTTPS fijo.1MiB/32depth/10s/20results/240title/1200content.1.1s minimum inicios por proceso. TLS y autenticación existentes intactos; SearXNG parcial sigue fallando. No defecto/aceptación Windows inferidos desde Linux.

## Review Focus
- La espera por el turno y el cuerpo respetan cancelación/plazo; no envíos tardíos.
- El bearer/perfil no se reenvía y no se siguen redirecciones.
- JSON válido con filas inválidas no fabrica resultados ni procedencia.
- HTTP429 es visible, sin fallback o reintento automático.
- CLI no activa el proveedor sin selección explícita y el índice sigue sin red.

### Task1 — Adaptador y selección CLI
**Files:** New src/Optimus.Search/IWebSearchProvider.cs, MwmblSearchProvider.cs; modify SearxSearchProvider.cs, SearchServer.cs, Program.cs; tests/MwmblPilotTests.cs + registration.
**Interfaces:** SearchServer accepts IWebSearchProvider?; SearchAsync unchanged query/language/token -> results. Existing SearchProviderException gains RateLimited state.
- [x] Prueba conductual CLI con --web-provider mwmbl debe arrancar solo por selección explícita, index vacío sano y cerrar por owner pipe.
- [x] Ejecutar contra baseline; debe fallar por opción no soportada, sin errores de compilación.
- [x] Añadir pruebas parser/procedencia, filtros, errores/esquema/redirect/429, límite/cancelación y espaciado; implementar el adaptador mínimo.
- [x] Ejecutar backend completo y conservar RED/GREEN.

### Task2 — Mensaje nativo y documentación
**Files:** Windows Core/SearchService.cs + Search.Tests; Search README/PROTOCOL/docs/VALIDATION_MWMBL_PILOT.md.
- [x] Añadir prueba de429 desde servicio local; observar mensaje anterior no específico.
- [x] Añadir texto de cuota y verificar Search59+pruebas nuevas y Core/Privacy/builds.
- [x] Documentar CLI optin, procedencia, privacidad, cuota/IP y límites; sin nuevas entregas binarias ni certificados de ejecución.

### Task3 — Prueba externa y revisión
- [x] Con las fuentes finales, usar cliente TLS real de producción y servicio real para3 consultas públicas espaciadas; no bearer en logs.
- [x] Registrar resultados/tiempos diferenciados de pruebas controladas, conservar vacío/error como tal.
- [x] Ejecutar regresiones aplicables, revisión independiente y verificar el diff del candidato.

**Entrega externa posterior al commit:** publicar PR borrador apilada sobre#2034 y registrar SHA/evidencias en#2021, sin merge. El registro externo enlaza la implementación probada y mantiene separados Windows, despliegue e índice mundial; evita un SHA autorreferente en este archivo.
