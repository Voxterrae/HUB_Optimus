# Guía de Uso del Núcleo de Simulación de HUB_Optimus

Este documento explica cómo utilizar el núcleo de simulación prototípico que acompaña a HUB_Optimus.  El propósito de este núcleo es ofrecer una base de código mínima pero funcional para cargar escenarios, asignar políticas básicas a actores, ejecutar rondas de negociación y evaluar condiciones de éxito.

> **Alcance actual:** El prototipo implementa carga de escenarios, políticas de oferta simples y un informe JSON con `status`, `rounds`, `history` y `detail`.  Funcionalidades como el **Índice de Integridad**, el cifrado de comunicaciones y políticas de negociación avanzadas son **ampliaciones planificadas** (ver sección 4), no características del núcleo actual.
Este documento explica cómo utilizar el núcleo de simulación prototípico que acompaña a HUB_Optimus.  El propósito de este núcleo es ofrecer una base de código mínima pero funcional para cargar escenarios JSON, asignar políticas básicas a actores, ejecutar rondas de negociación y evaluar condiciones de éxito.

> **Alcance actual:** El prototipo implementa carga de escenarios JSON estrictos, políticas de oferta simples y un informe JSON con `status`, `rounds`, `history` y `detail`.  Funcionalidades como el **Índice de Integridad**, el cifrado de comunicaciones y políticas de negociación avanzadas son **ampliaciones planificadas** (ver sección 4), no características del núcleo actual.

## Archivos principales

| Archivo                      | Descripción                                                                                                      |
|-----------------------------|------------------------------------------------------------------------------------------------------------------|
| `hub_optimus_simulator.py`  | Módulo que define las clases `Scenario`, `Actor` y `Simulator`, así como políticas sencillas de ejemplo.  Ejecuta rondas de negociación sobre escenarios ya validados. |
| `run_scenario.py`           | Script de línea de comandos que valida un escenario JSON estricto e invoca el simulador para devolver un informe JSON.   |
| `scenario.schema.json`      | Contrato JSON Schema canónico para los archivos de escenario ejecutables.                                         |
| `example_scenario.json`     | Escenario de ejemplo donde dos facciones negocian un alto el fuego parcial.                                        |
| `i18n_sync.py`              | Utilidad para comprobar la coherencia de traducciones en la documentación (ver sección 5).                        |

## 1. Preparación

1. Asegúrate de disponer de Python 3.7 o superior.
2. Copia los archivos anteriores en un directorio de trabajo.  Si vas a trabajar en un repositorio clonado, colócalos en la raíz del proyecto o en una carpeta `tools/` según tus preferencias.
3. Opcionalmente, crea un entorno virtual para aislar dependencias:

```bash
python3 -m venv venv
source venv/bin/activate
```

## 2. Estructura de un escenario

Los escenarios ejecutables se describen mediante un archivo JSON que debe validar contra `scenario.schema.json`. El contrato actual es estricto: no se aceptan campos extra en la raíz del documento ni dentro de `roles[]`.

```json
{
  "title": "Nombre del escenario",
  "description": "Contexto y antecedentes",
  "roles": [
    {"name": "NombreActor1", "role": "tipo"},
    {"name": "NombreActor2", "role": "tipo"}
  ],
  "success_criteria": {"clave": "valor"},
  "max_rounds": 5
}
```

* `title` y `description` proporcionan contexto humano mínimo para el runtime.
* `roles` define los actores que participarán en la negociación.  Cada elemento debe contener solo `name` y `role`.
* `success_criteria` es un mapa de clave/valor.  La simulación se detiene cuando cualquier actor emite una acción que coincida con una clave y valor del criterio (por ejemplo, `{"offer": 5}`).
* `max_rounds` limita el número máximo de rondas para evitar bucles infinitos.

La plantilla de trabajo más rica (`v1_core/workflow/04_scenario_template.md`) sirve para diseñar escenarios humanos con contexto, verificación, riesgos, evaluación y meta-learning. Esas secciones no forman parte del JSON ejecutable actual salvo que el schema, los ejemplos, los tests y la documentación se actualicen en un PR específico.

## 3. Ejecución desde la línea de comandos

Para ejecutar un escenario:

```bash
python run_scenario.py --scenario example_scenario.json --seed 42
```

* `--scenario` especifica la ruta al archivo de escenario JSON.  Puede ser una ruta relativa o absoluta.
* `--seed` es opcional; fija la semilla del generador aleatorio para obtener resultados reproducibles.

El script imprimirá un informe JSON como el siguiente:

```json
{
  "status": "success",
  "rounds": 2,
  "history": [
    {
      "FacciónA": {"offer": 1},
      "FacciónB": {"offer": 2}
    },
    {
      "FacciónA": {"offer": 4},
      "FacciónB": {"offer": 5}
    }
  ],
  "detail": "Success criteria met at round 2"
}
```

El campo `status` indica si se alcanzó el criterio de éxito (`"success"`) o se agotaron las rondas (`"failure"`).  `history` es una lista de rondas, y cada ronda es un diccionario de acciones por actor.  `detail` aporta información adicional, como la ronda en la que se cumplió el criterio.

### Opciones adicionales

El módulo `hub_optimus_simulator.py` está diseñado para ser extensible.  Puedes definir políticas personalizadas para los actores proporcionando funciones que acepten el estado de la negociación y devuelvan la siguiente acción.  Esas políticas se asignan desde Python o mediante las opciones soportadas por el runner; no se declaran como campos extra dentro del JSON de escenario actual.

## 4. Ampliaciones futuras

El núcleo es intencionadamente minimalista.  Algunas direcciones de ampliación recomendadas son:

1. **Integración de bibliotecas de negociación** como NegMAS para estrategias más sofisticadas.  Esto debe hacerse a través de módulos de extensión que respeten la Carta del Núcleo.
2. **Incorporación de cifrado post-cuántico** (p. ej., MLKEM/Kyber) para intercambiar propuestas de forma segura entre actores.  Esta integración es un objetivo planificado; no existe aún ningún módulo de cifrado en el repositorio.
3. **Índice de Integridad**: implementar el cálculo automático del índice definido en `INTEGRITY_SCORING_SYSTEM.md` y añadirlo al informe de salida.
4. **Interfaz gráfica o web**: crear una CLI más amigable o un panel web para seleccionar escenarios, actores y parámetros sin necesidad de modificar archivos a mano.

## 4b. Instrumentos del laboratorio experimental

Además del núcleo base, el repositorio incluye un conjunto de herramientas de análisis
que permiten mapear el espacio de estabilidad del simulador. Todos los resultados son
efímeros (gitignored) y se regeneran localmente.

| Herramienta | Comando | Propósito |
|---|---|---|
| Generador | `python tools/scenario_generator/generate_scenarios.py` | Genera escenarios sintéticos por familia |
| Telemetría | `python tools/scenario_telemetry.py` | Métricas agregadas de convergencia |
| Mutador | `python tools/scenario_mutator.py` | Barrido de estabilidad variando un eje |
| Búsqueda de frontera | `python tools/scenario_boundary_search.py` | Frontera de estabilidad por eje (búsqueda binaria) |
| Frontera 2D | `python tools/scenario_frontier.py` | Mapas de estabilidad en planos de dos ejes |

La memoria científica del laboratorio se mantiene en `docs/lab_state.md`.

## 5. Sincronización de traducciones (opcional)

El script `i18n_sync.py` ayuda a mantener sincronizada la documentación multilingüe.  Comprueba que todos los archivos en `docs/` que están en inglés tienen traducciones correspondientes en los subdirectorios de idiomas (`es`, `de`, `fr`, `ca`, `ru`).  Para ejecutarlo, coloca el script en la raíz del proyecto (o especifica la ruta `--docs_dir`) y ejecuta:

```bash
python i18n_sync.py --docs_dir docs
```

El script imprimirá una lista de ficheros que faltan en cada idioma y devolverá un código de salida diferente de cero si encuentra diferencias.  Esto facilita la detección temprana de desalineaciones entre versiones.

---

Con esta guía y los archivos proporcionados, puedes transformar la documentación conceptual de HUB_Optimus en un prototipo operativo.  Si encuentras errores o tienes ideas para mejorar el núcleo, no dudes en proponer cambios siguiendo la gobernanza definida en la Carta del Núcleo.
