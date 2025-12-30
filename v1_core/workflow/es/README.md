> 🇬🇧 English source: ../README.md

# Workflow (ES)

Este directorio contiene el **flujo operativo** para ejecutar simulaciones diplomáticas con estructura: roles, objetivos, rondas, criterios de verificación y una capa de aprendizaje (“meta-learning”) para iterar.

## Cómo empezar (rápido)
1) Entrada en español: `../../../docs/es/00_start_here.md`
2) Prueba guiada: `../../../docs/es/03_try_a_scenario.md`
3) Elige un escenario:
   - Escenario 001: `./scenario_001_partial_ceasefire.md`
   - Escenario 002: `./scenario_002_verified_ceasefire.md`

## Qué hay aquí
- **Escenarios**
  - `./scenario_001_partial_ceasefire.md` (alto el fuego parcial)
  - `./scenario_002_verified_ceasefire.md` (alto el fuego verificado)

- **Plantilla para crear escenarios**
  - `./04_scenario_template.md`

- **Aprendizaje iterativo (meta-learning)**
  - `./05_meta_learning.md`

## Cómo ejecutar una simulación (formato recomendado)
**Preparación (2–5 min)**
- Define roles (Parte A, Parte B, mediador/observador).
- Define “éxito mínimo” (qué condiciones hacen que la ronda sea útil).
- Define límites (líneas rojas y zona negociable).

**Ejecución (3 rondas)**
- Ronda 1: propuesta inicial ↔ respuesta
- Ronda 2: ajustes (concesiones, verificación, secuencia)
- Ronda 3: cierre (borrador de acuerdo + puntos abiertos)

**Cierre (5 min)**
- Evalúa: claridad, verificabilidad, viabilidad.
- Registra: concesiones, riesgos, condiciones de seguimiento.
- Decide: ¿qué se prueba distinto en la próxima iteración?

## Base conceptual (si quieres profundizar)
- Declaración base (ES): `../../languages/es/01_base_declaracion.md`
- Arquitectura base (ES): `../../languages/es/02_arquitectura_base.md`
- Flujo operativo (ES): `../../languages/es/03_flujo_operativo.md`

## Convención de idioma
- EN es la referencia original.
- ES se mantiene en paralelo para uso y lectura.
- Cada documento incluye un enlace a su fuente EN/ES al inicio.

Siguiente: `./04_scenario_template.md`
