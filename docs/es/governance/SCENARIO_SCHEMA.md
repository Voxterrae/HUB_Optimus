# Contratos de escenario de HUB_Optimus

> **Estado de traducción: `review-needed`.** Este texto es una traducción
> candidata sin evidencia de revisión lingüística humana cualificada. La fuente
> canónica para esta superficie de gobernanza es
> [la versión inglesa](../../governance/SCENARIO_SCHEMA.md).

## Propósito

HUB_Optimus mantiene de forma intencionada dos contratos de escenario
distintos:

1. la plantilla rica de trabajo humano, utilizada para estructurar el análisis
   y la revisión; y
2. la entrada JSON ejecutable y estricta que acepta el simulador prototípico.

Son superficies de autoría relacionadas, no representaciones equivalentes.
Convertir un flujo humano en JSON ejecutable es una decisión de modelado manual
y con pérdidas. El repositorio no incluye un conversor automático, y la
aceptación ejecutable no verifica la narrativa humana ni ninguna afirmación
sobre el mundo real.

## Límites de las fuentes

- Referencia del flujo humano:
  [`../../../v1_core/workflow/04_scenario_template.md`](../../../v1_core/workflow/04_scenario_template.md)
- Plantilla ligera de autoría del repositorio:
  [`../../scenarios/scenario_template.md`](../../scenarios/scenario_template.md)
- Estructura ejecutable:
  [`../../../scenario.schema.json`](../../../scenario.schema.json)
- Cargador JSON autoritativo y validación entre registros:
  [`../../../run_scenario.py`](../../../run_scenario.py)
- Comportamiento del runtime:
  [`../../architecture/runtime_contract.md`](../../architecture/runtime_contract.md)
- Guía operativa:
  [`../../../SIMULATION_README.md`](../../../SIMULATION_README.md)
- Precedencia de las fuentes de verdad del proyecto:
  [`../../context/SOURCE_OF_TRUTH.md`](../../context/SOURCE_OF_TRUTH.md)
- Política de idiomas canónicos y espejos:
  [`../../context/STATUS.md`](../../context/STATUS.md)

El schema define la estructura del documento. El cargador rechaza además
constantes JSON no estándar y nombres de actor duplicados. El schema aplicable,
el cargador/código, las pruebas y el contrato de runtime son autoritativos para
el comportamiento ejecutable. `STATUS.md` gobierna las cuestiones de idioma
canónico. Este documento de gobernanza relaciona esos límites; no sustituye ni
amplía las fuentes ejecutables.

## Contrato JSON ejecutable

El objeto raíz tiene exactamente cinco campos obligatorios. Se rechazan los
campos desconocidos en la raíz y dentro de `roles[]`.

| Campo JSON | Forma aceptada | Uso actual por el cargador/runtime | Lo que no implica |
|---|---|---|---|
| `title` | Cadena no vacía ni compuesta solo por espacios | Se guarda en el `Scenario` del runtime. Actualmente no afecta a las acciones ni al éxito. | Un ID del flujo, una versión, un registro de evidencia o un título real verificado. |
| `description` | Cadena no vacía ni compuesta solo por espacios | Se guarda en el `Scenario`. Las políticas incluidas actualmente no la leen. | Contexto estructurado, una cronología, verificación de la verdad o una narrativa evaluada. |
| `roles` | Array no vacío; cada elemento contiene únicamente las cadenas no vacías `name` y `role` | El cargador exige valores `name` únicos. `name` identifica al actor y su entrada en el historial. `role` se entrega a la política seleccionada; la política actual `biased` trata de forma especial los valores exactos `hardliner` y `mediator`, mientras que la política predeterminada y los demás roles usan ofertas uniformes. | Objetivos, restricciones, autoridad, deberes de verificación, biografía o una política declarada por actor. |
| `success_criteria` | Objeto no vacío cuyos valores son cadenas, números, enteros, booleanos o `null` de JSON | Después de cada ronda hay éxito cuando cualquier acción de cualquier actor coincide con uno cualquiera de los pares clave/valor. Por tanto, los criterios tienen semántica OR, no AND. Las políticas incluidas solo emiten `offer`. El kernel compara `actor_action.get(key)` con el valor esperado; por ello, un criterio `null` también coincide con una acción que omite esa clave. | La definición humana de éxito mínimo o ampliado, verificación, durabilidad, estabilidad o calidad de la política. |
| `max_rounds` | Entero mayor o igual que `1` | Fija el máximo de rondas. Se devuelve fallo si ningún criterio mecánico coincide antes del límite. | Una agenda de rondas, secuencia, fecha límite, plan de negociación o garantía de que se ejecuten todas las rondas previstas. |

Los archivos ejecutables deben ser JSON estándar. No se aceptan YAML ni las
constantes no estándar `NaN`, `Infinity` y `-Infinity`. La validación de schema
e identidad acredita únicamente la integridad de entrada; no acredita exactitud
factual.

## Relación campo por campo con el flujo humano rico

| Sección del flujo humano | Posible proyección manual a JSON | Contenido solo narrativo o ausente del runtime |
|---|---|---|
| **0. Metadatos** — ID, versión, idioma, fecha de actualización, autoría, estado | Una persona puede elegir un valor breve de presentación para `title`. No existe derivación automática. | Versión, idioma, fechas, autoría, estado del flujo e historial de cambios no tienen campo ejecutable. |
| **1. Resumen ejecutivo** — situación, objetivo mínimo, origen de la dificultad | Puede redactarse manualmente un resumen breve como `description`. | El runtime almacena, pero no evalúa, el resumen, el objetivo, la dificultad ni su base factual. |
| **2. Actores y roles** — partes, terceros, objetivos, límites, presión | Los identificadores y etiquetas breves de rol pueden proyectarse en `roles[].name` y `roles[].role`. Los nombres deben ser únicos. | Objetivos, límites, presión interna, autoridad y relaciones no tienen representación ejecutable. Se rechazan claves adicionales dentro de un rol. |
| **3. Contexto y cronología** — contexto previo, hechos recientes, horizonte | Parte del contexto puede condensarse manualmente en `description`. | No se modelan eventos, fechas, relaciones temporales, hitos ni horizontes de tiempo. |
| **4. Intereses, posiciones y restricciones** — intereses, demandas, restricciones internas, líneas rojas, flexibilidad | Sin proyección directa. | Todos los campos de esta sección son solo narrativos. No pueden añadirse a `roles[]` sin cambiar el schema. |
| **5. Objetivo mínimo y criterios de éxito** — éxito mínimo, éxito ampliado, fracaso claro | Solo un criterio expresable como clave de acción y valor JSON escalar puede codificarse manualmente en `success_criteria`. | No se evalúan la calidad humana del resultado, el éxito ampliado, el fracaso claro, la durabilidad ni la verificación. Varias entradas JSON son alternativas, no una conjunción. |
| **6. Propuesta inicial** — acción, calendario, geografía, excepciones, verificación, medidas ante incumplimiento | Sin proyección directa. | El JSON actual no puede precargar propuestas, calendario, geografía, excepciones ni medidas de cumplimiento. Las políticas incluidas generan acciones `offer` simples durante la ejecución. |
| **7. Verificación y cumplimiento** — verificador, objeto, método, frecuencia, acceso, disputas | Sin proyección directa. | El simulador no integra evidencia, sensores, control de acceso, cumplimiento, resolución de disputas ni Trust Layer. |
| **8. Riesgos y puntos de fricción** — malentendidos, incentivos para engañar, ambigüedad, saboteadores, incidentes | Sin proyección directa. | El runtime actual no consume riesgos ni dinámicas causales o adversariales. |
| **9. Rondas recomendadas** — fases, borrador de acuerdo, puntos abiertos, próximos pasos | Una persona puede elegir `max_rounds` como límite mecánico. | El contenido de las fases, la secuencia, los entregables, los puntos abiertos, la responsabilidad y los plazos no son ejecutables. |
| **10. Evaluación posterior** — claridad, verificabilidad, viabilidad, coste político, riesgo de escalada | Sin proyección de entrada. | Los campos de resultado `status`, `rounds`, `history` y `detail` son datos mecánicos de ejecución; no calculan esas puntuaciones. |
| **11. Meta-learning** — lecciones, fallos, definiciones ausentes, cambios futuros, preguntas nuevas | Sin proyección directa. | El runtime no actualiza escenarios, aprende de las ejecuciones ni crea conclusiones de gobernanza. |

## Relación con la plantilla ligera de autoría

[`../../scenarios/scenario_template.md`](../../scenarios/scenario_template.md)
es una ayuda para proponer y revisar contenido en el repositorio, no un archivo
de entrada del simulador. Su título, contexto breve, etiquetas de actores y una
condición de éxito expresable mecánicamente pueden informar `title`,
`description`, `roles` y `success_criteria` mediante autoría manual. No tiene un
campo específico para `max_rounds`; el límite ejecutable debe elegirse por
separado. Familia, tensión, modo de fallo, invariantes, plan de benchmark y
notas no tienen un campo directo en el runtime. Una propuesta de benchmark no
se convierte en benchmark congelado por el mero hecho de que exista un JSON
ejecutable.

## Los controles del runtime no son campos del escenario

La CLI soportada expone controles externos al documento JSON:

- la ruta posicional del escenario o `--scenario` selecciona el archivo JSON;
- `--seed` elige un flujo aleatorio reproducible;
- `--policy` elige una política soportada para todos los actores (`uniform` o
  `biased`); y
- `--output` elige la ruta del resultado.

Las estrategias humanas por actor, la evidencia, las reglas de verificación y
las fases de negociación no pueden codificarse añadiendo estos nombres al JSON.
Los campos desconocidos se rechazan.

## Ejemplo de proyección mínima

Un flujo humano puede describir varias partes, intereses, riesgos, salvaguardas
y un acuerdo verificado. Esta proyección ejecutable conserva únicamente dos
etiquetas de actor, una condición mecánica de oferta y un límite de cinco
rondas:

```json
{
  "title": "Alto el fuego parcial",
  "description": "Dos facciones negocian un alto el fuego parcial.",
  "roles": [
    {"name": "FaccionA", "role": "negotiator"},
    {"name": "FaccionB", "role": "negotiator"}
  ],
  "success_criteria": {"offer": 5},
  "max_rounds": 5
}
```

Una ejecución exitosa significa únicamente que al menos una acción generada
contenía `"offer": 5` antes del límite. No significa que se haya negociado,
verificado o sostenido un alto el fuego, ni que este sea legítimo o aconsejable.

## Disciplina de cambios

- No introduzcas campos exclusivos del flujo humano en el JSON ejecutable; la
  validación los rechazará.
- No describas la plantilla humana como ejecutable ni el JSON como un escenario
  analítico completo.
- Todo cambio de campo ejecutable requiere un cambio acotado que actualice
  conjuntamente `scenario.schema.json`, el cargador/runtime según corresponda,
  los ejemplos, las pruebas y la documentación del runtime.
- Toda traducción más rica del flujo humano al runtime requiere un issue de
  schema/runtime aprobado explícitamente. Este mapa no concede esa capacidad.

## Madurez de traducción

Este espejo español permanece en estado `review-needed`. Los espejos alemán,
catalán, francés y ruso también permanecen en `review-needed`; hebreo y chino
simplificado permanecen en `stub`. Estos estados se declaran en
[`../../i18n/maturity.v1.json`](../../i18n/maturity.v1.json). Las comprobaciones
estructurales o automatizadas no certifican calidad lingüística, revisión
profesional ni paridad.
