# Guía de Uso del Núcleo de Simulación de HUB_Optimus

Este documento explica cómo utilizar el núcleo de simulación prototípico que acompaña a HUB_Optimus.  El propósito de este núcleo es ofrecer una base de código mínima pero funcional para cargar escenarios JSON, asignar políticas básicas a actores, ejecutar rondas de negociación y evaluar condiciones de éxito.

> **Alcance actual:** El prototipo implementa carga de escenarios JSON estrictos, políticas de oferta simples y un informe JSON con `status`, `rounds`, `history` y `detail`.  Funcionalidades como el **Índice de Integridad**, el cifrado de comunicaciones y políticas de negociación avanzadas son **ampliaciones planificadas** (ver sección 4), no características del núcleo actual.

## Archivos principales

| Archivo                      | Descripción                                                                                                      |
|-----------------------------|------------------------------------------------------------------------------------------------------------------|
| `hub_optimus_simulator.py`  | Módulo que define las clases `Scenario`, `Actor` y `Simulator`, así como políticas sencillas de ejemplo. Ejecuta rondas de negociación sobre escenarios ya validados. |
| `run_scenario.py`           | Cargador canónico y script de línea de comandos que validan un escenario JSON estricto antes de invocar el simulador. |
| `scenario.schema.json`      | Contrato estructural JSON Schema para los archivos de escenario ejecutables. |
| `example_scenario.json`     | Escenario de ejemplo donde dos facciones negocian un alto el fuego parcial.                                        |
| `i18n_sync.py`              | Auditor de cobertura y madurez declarada para onboarding y gobernanza (ver sección 5).                            |

## 1. Preparación

1. Asegúrate de disponer de Python 3.11 o superior. El repositorio y el
   bootstrap usan sintaxis de Python 3.11; versiones anteriores no forman parte
   del contrato soportado.
2. Copia o clona el repositorio completo en un directorio de trabajo.
3. Crea un entorno virtual para aislar dependencias:

```bash
python3 -m venv venv
source venv/bin/activate
```

4. Instala las dependencias del runtime:

```bash
python -m pip install -r requirements.txt
```

`requirements.txt` contiene únicamente dependencias necesarias para ejecutar
los comandos soportados. Para desarrollar y ejecutar la suite instala
`requirements-dev.txt`; este incluye el fichero de runtime y añade `pytest` y
`PyYAML`:

```bash
python -m pip install -r requirements-dev.txt
```

Como alternativa reproducible, el bootstrap distingue ambos modos:

```bash
python scripts/bootstrap.py --runtime-only
python scripts/bootstrap.py
python scripts/bootstrap.py --runtime-only --check
```

El modo `--check` verifica cada dependencia directa declarada para el nivel
seleccionado, incluido el paquete `PyYAML` mediante su módulo importable
`yaml`; no instala paquetes ni ejecuta la suite.

## 2. Estructura de un escenario

Los escenarios ejecutables se describen mediante un archivo JSON que debe
validar contra `scenario.schema.json`. El contrato actual es estricto: no se
aceptan campos extra en la raíz del documento ni dentro de `roles[]`, y el
decodificador rechaza las constantes no estándar `NaN`, `Infinity` y
`-Infinity`. Solo se admite JSON; el runtime no implementa carga YAML.

El JSON Schema valida la estructura de cada registro. El cargador canónico
`run_scenario.load_validated_scenario()` aplica además la invariancia entre
registros que exige nombres de actor únicos. `Scenario.from_json()` delega en
ese mismo cargador y no introduce valores predeterminados permisivos.

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
* `roles` define los actores que participarán en la negociación. Cada elemento debe contener solo `name` y `role`, y cada `name` debe ser único dentro del escenario.
* `success_criteria` es un mapa de clave/valor.  La simulación se detiene cuando cualquier actor emite una acción que coincida con una clave y valor del criterio (por ejemplo, `{"offer": 5}`).
* `max_rounds` limita el número máximo de rondas para evitar bucles infinitos.

La plantilla de trabajo más rica (`v1_core/workflow/04_scenario_template.md`) sirve para diseñar escenarios humanos con contexto, verificación, riesgos, evaluación y meta-learning. Esas secciones no forman parte del JSON ejecutable actual salvo que el schema, los ejemplos, los tests y la documentación se actualicen en un PR específico.
La relación campo por campo, incluidas las pérdidas deliberadas de esa
proyección manual, se documenta en
[`docs/governance/SCENARIO_SCHEMA.md`](docs/governance/SCENARIO_SCHEMA.md).

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
| Búsqueda de frontera | `python tools/scenario_boundary_search.py` | Frontera por eje: búsqueda binaria para rondas y enumeración exhaustiva para actores y umbral |
| Frontera 2D | `python tools/scenario_frontier.py` | Mapas de estabilidad en planos de dos ejes |

Cada ejecución del generador escribe `generation_manifest.json`. Ese manifiesto
identifica el conjunto actual mediante un `run_id` reproducible y hashes SHA-256;
la telemetría lo detecta y verifica automáticamente, por lo que no mezcla archivos
sobrantes de ejecuciones anteriores. Los bytes verificados se conservan en memoria
y se ejecutan desde una copia temporal aislada; la telemetría no vuelve a abrir la
ruta mutable después de verificar su hash.

El conjunto completo y el manifiesto se preparan antes de publicar. Si falla una
escritura, backup o publicación, el generador restaura el conjunto y manifiesto
anteriores. `--count` debe ser mayor que cero. El espacio que el generador
considera propio se limita a rutas inmediatas con la forma
`<familia>/<familia>_<número>.json`. Para eliminar archivos obsoletos solo dentro
de ese espacio explícito:

```bash
python tools/scenario_generator/generate_scenarios.py --count 20 --clean
```

Sin `--clean`, los archivos obsoletos se conservan y se notifican, pero quedan
fuera del manifiesto actual. Otros JSON, subdirectorios y notas dentro del
directorio de salida nunca se eliminan.

La memoria científica del laboratorio se mantiene en `docs/lab_state.md`.

## 5. Sincronización de traducciones (opcional)

El script `i18n_sync.py` contrasta las superficies de onboarding y gobernanza
versionadas en `docs/i18n/maturity.v1.json`. Aplica el tier declarado para cada
locale BCP-47 (`en`, `es`, `de`, `ca`, `fr`, `ru`, `he`, `zh-Hans`) y distingue
archivos ausentes, stubs, borradores, revisión pendiente, revisión acreditada,
fuente canónica y paridad. Para ejecutarlo desde la raíz:

```bash
python i18n_sync.py --docs-dir docs
```

El script devuelve cero cuando las declaraciones coinciden con los archivos y
existen todas las superficies exigidas por cada tier. Un resultado verde no
certifica calidad lingüística ni traducción completa; esas afirmaciones requieren
el estado y la evidencia de revisión definidos en el manifiesto.

---

Con esta guía y los archivos proporcionados, puedes transformar la documentación conceptual de HUB_Optimus en un prototipo operativo.  Si encuentras errores o tienes ideas para mejorar el núcleo, no dudes en proponer cambios siguiendo la gobernanza definida en la Carta del Núcleo.
