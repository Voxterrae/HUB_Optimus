> Fuente canónica v1: [languages/es](./languages/es)
> EN es traducción de paridad/referencia. Si hay conflicto de política lingüística,
> [docs/context/STATUS.md](../docs/context/STATUS.md) prevalece.

# Workflow (ES)

Este directorio contiene el **flujo operativo** para ejecutar simulaciones diplomáticas con estructura: roles, objetivos, rondas, criterios de verificación y una capa de aprendizaje (“meta-learning”) para iterar.

## Cómo empezar (rápido)
1) Entrada en español: [../../../docs/es/00_start_here.md](../docs/es/00_start_here.md)
2) Prueba guiada: [../../../docs/es/03_try_a_scenario.md](../docs/es/03_try_a_scenario.md)
3) Elige un escenario:
   - Escenario 001: [./scenario_001_partial_ceasefire.md](./workflow/scenario_001_partial_ceasefire.md)
   - Escenario 002: [./scenario_002_verified_ceasefire.md](./workflow/scenario_002_verified_ceasefire.md)

## Qué hay aquí
- **Escenarios**
  - [./scenario_001_partial_ceasefire.md](./workflow/scenario_001_partial_ceasefire.md) (alto el fuego parcial)
  - [./scenario_002_verified_ceasefire.md](./workflow/scenario_002_verified_ceasefire.md) (alto el fuego verificado)

- **Plantilla para crear escenarios**
  - [./04_scenario_template.md](./workflow/04_scenario_template.md)

- **Aprendizaje iterativo (meta-learning)**
  - [./05_meta_learning.md](./workflow/05_meta_learning.md)

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
- Declaración base (ES): [../../languages/es/01_base_declaracion.md](./languages/es/01_base_declaracion.md)
- Arquitectura base (ES): [../../languages/es/02_arquitectura_base.md](./languages/es/02_arquitectura_base.md)
- Flujo operativo (ES): [../../languages/es/03_flujo_operativo.md](./languages/es/03_flujo_operativo.md)

## Convención de idioma
- ES es la fuente canónica para `v1_core`.
- EN es traducción de paridad/referencia, no fuente canónica.
- Si hay conflicto entre documentos, prevalece `docs/context/STATUS.md`.
- Los enlaces EN/ES al inicio de documentos son navegación de paridad; no cambian la autoridad canónica.

Siguiente: [./04_scenario_template.md](./workflow/04_scenario_template.md)
