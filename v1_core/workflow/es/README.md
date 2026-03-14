> English source: [../README.md](../README.md)

# Workflow (ES)

Este directorio contiene el **flujo operativo** para ejecutar simulaciones
diplomaticas con estructura: roles, objetivos, rondas, criterios de
verificacion y una capa de aprendizaje ("meta-learning") para iterar.

## Como empezar (rapido)
1) Entrada en espanol: [../../../docs/es/00_start_here.md](../../../docs/es/00_start_here.md)
2) Prueba guiada: [../../../docs/es/03_try_a_scenario.md](../../../docs/es/03_try_a_scenario.md)
3) Elige un escenario:
   - Escenario 001: [./scenario_001_partial_ceasefire.md](./scenario_001_partial_ceasefire.md)
   - Escenario 002: [./scenario_002_verified_ceasefire.md](./scenario_002_verified_ceasefire.md)
   - Escenario 003: [./scenario_003_coalition_fracture.md](./scenario_003_coalition_fracture.md)

## Que hay aqui
- **Escenarios**
  - [./scenario_001_partial_ceasefire.md](./scenario_001_partial_ceasefire.md) (alto el fuego parcial)
  - [./scenario_002_verified_ceasefire.md](./scenario_002_verified_ceasefire.md) (alto el fuego verificado)
  - [./scenario_003_coalition_fracture.md](./scenario_003_coalition_fracture.md) (fractura de coalicion)

- **Plantilla para crear escenarios**
  - [./04_scenario_template.md](./04_scenario_template.md)

- **Aprendizaje iterativo (meta-learning)**
  - [./05_meta_learning.md](./05_meta_learning.md)

## Como ejecutar una simulacion (formato recomendado)
**Preparacion (2-5 min)**
- Define roles (Parte A, Parte B, mediador/observador).
- Define "exito minimo" (que condiciones hacen que la ronda sea util).
- Define limites (lineas rojas y zona negociable).

**Ejecucion (3 rondas)**
- Ronda 1: propuesta inicial <-> respuesta
- Ronda 2: ajustes (concesiones, verificacion, secuencia)
- Ronda 3: cierre (borrador de acuerdo + puntos abiertos)

**Cierre (5 min)**
- Evalua: claridad, verificabilidad, viabilidad.
- Registra: concesiones, riesgos, condiciones de seguimiento.
- Decide: que se prueba distinto en la proxima iteracion?

## Base conceptual (si quieres profundizar)
- Declaracion base (ES): [../../languages/es/01_base_declaracion.md](../../languages/es/01_base_declaracion.md)
- Arquitectura base (ES): [../../languages/es/02_arquitectura_base.md](../../languages/es/02_arquitectura_base.md)
- Flujo operativo (ES): [../../languages/es/03_flujo_operativo.md](../../languages/es/03_flujo_operativo.md)

## Convencion de idioma
- EN es la referencia original.
- ES se mantiene en paralelo para uso y lectura.
- Cada documento incluye un enlace a su fuente EN/ES al inicio.

Siguiente: [./04_scenario_template.md](./04_scenario_template.md)
