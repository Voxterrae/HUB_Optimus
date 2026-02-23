> 🇬🇧 English source: [../02_how_to_read_this_repo.md](../02_how_to_read_this_repo.md)

# Cómo leer este repositorio

Este repositorio está organizado para que puedas entender **qué es**, **dónde está cada cosa**, y **cómo usarlo** sin perderte en detalles. La idea es que cualquier persona pueda entrar, elegir idioma y seguir un camino claro.

## Lecturas recomendadas (según tu objetivo)

### Quiero entender rápido "en qué estáis trabajando"
Sigue este orden:
1) [docs/es/00_start_here.md](00_start_here.md)
2) [docs/es/03_try_a_scenario.md](03_try_a_scenario.md)
3) [../../v1_core/workflow/es/README.md](../../v1_core/workflow/es/README.md)

### Quiero practicar escenarios (modo simulación)
Ve directamente a:
- Workflow (ES): [../../v1_core/workflow/es/README.md](../../v1_core/workflow/es/README.md)
- Escenario 001 (ES): [../../v1_core/workflow/es/scenario_001_partial_ceasefire.md](../../v1_core/workflow/es/scenario_001_partial_ceasefire.md)
- Escenario 002 (ES): [../../v1_core/workflow/es/scenario_002_verified_ceasefire.md](../../v1_core/workflow/es/scenario_002_verified_ceasefire.md)
- Plantilla (ES): [../../v1_core/workflow/es/04_scenario_template.md](../../v1_core/workflow/es/04_scenario_template.md)

### Quiero entender el marco conceptual y el método
Empieza por:
- [../../v1_core/languages/es/01_base_declaracion.md](../../v1_core/languages/es/01_base_declaracion.md)
- [../../v1_core/languages/es/02_arquitectura_base.md](../../v1_core/languages/es/02_arquitectura_base.md)
- [../../v1_core/languages/es/03_flujo_operativo.md](../../v1_core/languages/es/03_flujo_operativo.md)
y luego vuelve al workflow.

## Mapa del repo (qué hay en cada carpeta)
- `docs/`  
  Entrada, guía de lectura y una prueba guiada. Si vienes "de fuera", empieza aquí.
- `v1_core/`  
  Núcleo del sistema: workflow, escenarios, plantillas, criterios y aprendizaje iterativo.
- `legacy/`  
  Material anterior o experimental. Útil como referencia, no siempre está "al día".

## Language policy (STATUS)
- Source-of-truth: `docs/context/STATUS.md`
- canonical: `../../v1_core/languages/es/`
- parity reference: `../../v1_core/languages/en/`

## Cómo navegar sin perder contexto
1) Usa los "Start here" y "Try a scenario" para ver el sistema funcionando.
2) Cuando un documento cite algo del núcleo (`v1_core`), sigue el enlace y vuelve.
3) Si un apartado está en EN, usa el enlace a la fuente EN para no bloquearte.

## Dónde está lo importante (atajos)
- Entrada (ES): [docs/es/00_start_here.md](00_start_here.md)
- Probar un escenario (ES): [docs/es/03_try_a_scenario.md](03_try_a_scenario.md)
- Workflow del núcleo (ES): [../../v1_core/workflow/es/README.md](../../v1_core/workflow/es/README.md)
- Plantilla de escenario (ES): [../../v1_core/workflow/es/04_scenario_template.md](../../v1_core/workflow/es/04_scenario_template.md)
- Meta-learning (ES): [../../v1_core/workflow/es/05_meta_learning.md](../../v1_core/workflow/es/05_meta_learning.md)

## Si quieres contribuir (sin romper enlaces)
- Prefiere enlaces relativos (para que funcionen en GitHub y local).
- Mantén los pares EN↔ES con la misma estructura de carpetas.
- Si cambias rutas, corre el link-check (Lychee) antes de hacer push.

Siguiente: [docs/es/03_try_a_scenario.md](03_try_a_scenario.md)
