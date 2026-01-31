# Guía de Uso del Núcleo de Simulación de HUB_Optimus

Este documento explica cómo utilizar el núcleo de simulación prototípico que acompaña a HUB_Optimus.  El propósito de este núcleo es ofrecer una base de código mínima pero funcional para cargar escenarios, asignar políticas básicas a actores, ejecutar rondas de negociación y evaluar condiciones de éxito.  A partir de esta base se podrán incorporar políticas más sofisticadas, cifrado de comunicaciones y métricas de evaluación como el **Índice de Integridad**.

## Archivos principales

| Archivo                      | Descripción                                                                                                      |
|-----------------------------|------------------------------------------------------------------------------------------------------------------|
| `hub_optimus_simulator.py`  | Módulo que define las clases `Scenario`, `Actor` y `Simulator`, así como políticas sencillas de ejemplo.  Permite cargar escenarios desde JSON/YAML y ejecutar rondas de negociación. |
| `run_scenario.py`           | Script de línea de comandos que invoca al simulador sobre un escenario determinado y devuelve un informe JSON.   |
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

Los escenarios se describen mediante un archivo JSON (también se acepta YAML) con los campos siguientes:

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

* `title` y `description` proporcionan contexto humano.
* `roles` define los actores que participarán en la negociación.  Cada elemento puede incluir campos adicionales (por ejemplo, la política a usar).
* `success_criteria` es un mapa de clave/valor.  La simulación se detiene cuando cualquier actor emite una acción que coincida con una clave y valor del criterio (por ejemplo, `{"offer": 5}`).
* `max_rounds` limita el número máximo de rondas para evitar bucles infinitos.

## 3. Ejecución desde la línea de comandos

Para ejecutar un escenario:

```bash
python run_scenario.py --scenario example_scenario.json --seed 42
```

* `--scenario` especifica la ruta al archivo de escenario.  Puede ser una ruta relativa o absoluta.
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

El módulo `hub_optimus_simulator.py` está diseñado para ser extensible.  Puedes definir políticas personalizadas para los actores proporcionando funciones que acepten el estado de la negociación y devuelvan la siguiente acción.  También puedes cargar escenarios desde YAML o definirlos directamente como diccionarios en Python y pasarlos al simulador.

## 4. Ampliaciones futuras

El núcleo es intencionadamente minimalista.  Algunas direcciones de ampliación recomendadas son:

1. **Integración de bibliotecas de negociación** como NegMAS para estrategias más sofisticadas.  Esto debe hacerse a través de módulos de extensión que respeten la Carta del Núcleo.
2. **Incorporación de cifrado** (ver `hub_optimus_kyber_integration_demo.py`) para intercambiar propuestas de forma segura entre actores.
3. **Índice de Integridad**: implementar el cálculo automático del índice definido en `INTEGRITY_SCORING_SYSTEM.md` y añadirlo al informe de salida.
4. **Interfaz gráfica o web**: crear una CLI más amigable o un panel web para seleccionar escenarios, actores y parámetros sin necesidad de modificar archivos a mano.

## 5. Sincronización de traducciones (opcional)

El script `i18n_sync.py` ayuda a mantener sincronizada la documentación multilingüe.  Comprueba que todos los archivos en `docs/` que están en inglés tienen traducciones correspondientes en los subdirectorios de idiomas (`es`, `de`, `fr`, `ca`, `ru`).  Para ejecutarlo, coloca el script en la raíz del proyecto (o especifica la ruta `--docs_dir`) y ejecuta:

```bash
python i18n_sync.py --docs_dir docs
```

El script imprimirá una lista de ficheros que faltan en cada idioma y devolverá un código de salida diferente de cero si encuentra diferencias.  Esto facilita la detección temprana de desalineaciones entre versiones.

---

Con esta guía y los archivos proporcionados, puedes transformar la documentación conceptual de HUB_Optimus en un prototipo operativo.  Si encuentras errores o tienes ideas para mejorar el núcleo, no dudes en proponer cambios siguiendo la gobernanza definida en la Carta del Núcleo.