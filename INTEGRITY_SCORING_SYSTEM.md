# Sistema de Puntuación de Integridad

Este documento describe un esquema de evaluación cuantitativa para medir la **integridad** de propuestas y procesos en los escenarios simulados por HUB_Optimus.  Su objetivo es proporcionar una métrica transparente que refleje cómo de alineada está una acción o acuerdo con los principios del proyecto.

## Motivación

La integridad es un concepto amplio que engloba honestidad, coherencia ética y sostenibilidad.  Para que el núcleo de simulación pueda tomar decisiones basadas en datos y no en percepciones subjetivas, se propone un **sistema de puntuación** que descompone la integridad en varios componentes evaluables.

## Dimensiones de la integridad

El sistema se basa en cinco dimensiones principales.  Cada una se puntúa en un rango de 0 a 1, donde 0 representa la ausencia de la cualidad y 1 su máximo cumplimiento.

1. **Equidad (EQ)** – Evalúa si la propuesta distribuye beneficios y costes de manera justa entre los actores.  Se valoran elementos como la reciprocidad y la ausencia de ventajas desproporcionadas.
2. **Transparencia (TR)** – Mide el grado en que las acciones, incentivos y condiciones de una propuesta son visibles y comprensibles para todas las partes.
3. **Sostenibilidad (SO)** – Captura la capacidad de un acuerdo para mantenerse estable a medio y largo plazo sin incentivos ocultos que lo erosionen.
4. **Alineación de Incentivos (AI)** – Comprueba si los incentivos de los actores están alineados con la estabilidad global y no fomentan desviaciones oportunistas.
5. **Verificabilidad (VE)** – Indica la facilidad con la que se puede comprobar el cumplimiento de las condiciones pactadas y la existencia de mecanismos de rendición de cuentas.

Cada dimensión puede descomponerse en sub‑criterios específicos según el tipo de escenario (p. ej., en negociaciones diplomáticas, la verificabilidad puede incluir observadores neutrales y mecanismos de sanción).

## Fórmula de cálculo

Se define el **Índice de Integridad (II)** como una media ponderada de las cinco dimensiones:

\[
II = w_{EQ} \cdot EQ + w_{TR} \cdot TR + w_{SO} \cdot SO + w_{AI} \cdot AI + w_{VE} \cdot VE
\]

donde \(w_{EQ}, w_{TR}, w_{SO}, w_{AI}, w_{VE}\) son los pesos asignados a cada dimensión.  Por defecto, se sugiere un peso uniforme (0,2 cada uno), aunque puede adaptarse según las prioridades de un escenario concreto.

Los pesos deben cumplir:

\[
\sum_{i=1}^{5} w_i = 1\quad\text{y}\quad w_i \ge 0
\]

## Clasificación de resultados

Para facilitar la interpretación, se proponen tres categorías cualitativas basadas en el Índice de Integridad:

| Intervalo de II | Categoría           | Descripción                                                  |
|-----------------|---------------------|--------------------------------------------------------------|
| 0 – 0,49        | **Baja Integridad** | La propuesta carece de equidad, transparencia o verificabilidad.  Se considera inaceptable en el contexto de HUB_Optimus. |
| 0,50 – 0,79     | **Integridad Media**| Cumple varios criterios, pero presenta deficiencias que podrían comprometer la estabilidad a largo plazo.  Requiere revisión y ajustes. |
| 0,80 – 1,00     | **Alta Integridad** | La propuesta está sólidamente alineada con los principios de HUB_Optimus.  Es equitativa, transparente, sostenible y verificable. |

## Procedimiento de evaluación

1. **Definir sub‑criterios**: para cada dimensión, el equipo define sub‑criterios adaptados al escenario específico (por ejemplo, en un alto el fuego, la sostenibilidad puede incluir mecanismos de supervisión internacional y calendarios realistas de retiro de tropas).
2. **Asignar puntuaciones**: cada sub‑criterio se evalúa en una escala de 0 a 1.  Estas puntuaciones se agregan para obtener la puntuación de cada dimensión.
3. **Determinar pesos**: se acuerdan los pesos \(w_i\) de las dimensiones.  En ausencia de preferencias específicas, se utiliza la distribución uniforme.
4. **Calcular II**: se aplica la fórmula anterior para obtener el Índice de Integridad.
5. **Interpretar resultados**: se clasifica la propuesta según el intervalo correspondiente y se formulan recomendaciones (por ejemplo, reforzar la verificabilidad o ajustar los incentivos).

## Ejemplo de aplicación

En un escenario de alto el fuego parcial entre dos facciones:

- **Equidad (EQ)**: 0,8 (las concesiones son proporcionales y equitativas).
- **Transparencia (TR)**: 0,9 (todas las condiciones se documentan y comparten con un mediador neutral).
- **Sostenibilidad (SO)**: 0,7 (el acuerdo es viable durante seis meses, pero requiere un plan de desescalada más claro a largo plazo).
- **Alineación de Incentivos (AI)**: 0,6 (existen incentivos para mantener el alto el fuego, pero ciertos actores podrían beneficiarse de interrupciones menores).
- **Verificabilidad (VE)**: 0,8 (observadores independientes pueden confirmar el cumplimiento de las condiciones).

Con pesos uniformes (0,2 para cada dimensión), el índice queda:

\[
II = 0,2\times 0,8 + 0,2\times 0,9 + 0,2\times 0,7 + 0,2\times 0,6 + 0,2\times 0,8 = 0,76
\]

Según la tabla, el escenario se clasificaría como **Integridad Media**.  Se recomendaría reforzar la alineación de incentivos y mejorar la sostenibilidad a largo plazo para alcanzar una integridad alta.

## Integración con el núcleo de simulación

El núcleo debe calcular el Índice de Integridad en cada ronda o al finalizar la negociación.  Este índice se incluirá en los informes generados por el simulador y servirá para:

* Alertar a los usuarios de acuerdos que aparentan éxito pero presentan baja integridad (falsos éxitos).
* Comparar distintas políticas o estrategias bajo un marco común.
* Guiar la mejora de propuestas mediante la identificación de dimensiones débiles.

La evaluación cuantitativa de la integridad no sustituye el juicio humano, pero ofrece un punto de partida objetivo para la toma de decisiones.