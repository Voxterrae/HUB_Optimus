# Carta del Núcleo de HUB_Optimus

Esta carta define las reglas inmutables que gobiernan el núcleo de simulación de **HUB_Optimus**.  Su propósito es transformar los principios filosóficos del proyecto en restricciones técnicas explícitas.  Todo componente que se integre en el núcleo (``Simulator``, ``Scenario`` o ``Actor``) debe respetar estas reglas para preservar la misión del proyecto: promover la estabilidad sistémica y la integridad en contextos diplomáticos.

## Principios fundacionales

El proyecto se rige por cinco principios base que sirven como brújula ética y técnica:

1. **Estabilidad sobre óptica**: la prioridad máxima es la estabilidad sistémica a medio y largo plazo, por encima de aparentes éxitos inmediatos.
2. **Integridad primero**: la influencia y la autoridad se ganan mediante la coherencia ética, no por posición, credenciales o poder coyuntural.
3. **Evaluación sobre narrativa**: los resultados se valoran con criterios estructurales (incentivos, verificación, secuenciación) en lugar de argumentos retóricos.
4. **Prevención sobre reacción**: se privilegia la mediación temprana y discreta frente a la escalada pública y reactiva.
5. **Sin culpabilizar**: los errores y fallos se tratan como síntomas sistémicos, no como fracasos personales.

## Restricciones técnicas del núcleo

Para que estos principios se traduzcan en un comportamiento concreto del software, el núcleo incorpora las siguientes reglas:

### 1. Capacidad ≠ Permiso

El núcleo puede simular dinámicas de negociación y evaluar sus consecuencias, pero **no tiene permitido recomendar acciones que busquen dominar, explotar o manipular a otros actores**.  La potencia computacional debe mejorar la claridad del diagnóstico, no la agresividad de las estrategias.

* **Regla de prohibición de explotación**: cualquier política que optimice el beneficio individual a costa del deterioro de otros actores se marca automáticamente como *resultado de alto riesgo* y se desaconseja.
* **Regla de neutralidad táctica**: el núcleo no genera instrucciones tácticas para actores reales; solo describe consecuencias, riesgos y escenarios alternativos.

### 2. Foco en la estabilidad multi‑actor

Las funciones de utilidad y los criterios de éxito del simulador se definen en términos de **estabilidad conjunta** en lugar de maximización de payoffs individuales.  Las evaluaciones deben tener en cuenta:

* Coherencia a medio y largo plazo de los acuerdos.
* Equilibrio de incentivos entre actores.
* Viabilidad de verificación y cumplimiento.

### 3. Transparencia y auditabilidad

Todas las decisiones internas del núcleo deben ser trazables.  Esto implica:

* **Historial de acciones**: cada ronda de negociación registra las ofertas, concesiones y justificaciones.
* **Criterios explícitos**: los criterios que llevan a declarar el éxito o el fracaso de un escenario se exponen de manera clara en los informes.
* **Sin resultados opacos**: el núcleo no devuelve resultados cifrados o inescrutables; los usuarios pueden revisar por qué se alcanzó un determinado diagnóstico.

### 4. Aislamiento de integración

El núcleo está diseñado para ser extensible mediante *plugins* externos (por ejemplo, bibliotecas de negociación como NegMAS o orquestadores multi‑agente como CrewAI).  Sin embargo, dichas integraciones **nunca pueden modificar las reglas base**.  Deben cumplir los siguientes requisitos:

* **No invasividad**: las extensiones se cargan como módulos secundarios y se comunican con el núcleo a través de interfaces bien definidas.
* **Respeto de la Carta**: cualquier estrategia o algoritmo integrado debe ajustarse a la prohibición de explotación y al enfoque en la estabilidad.

### 5. Seguridad de la información

El núcleo puede incorporar mecanismos de cifrado (por ejemplo, MLKEM/Kyber) para proteger la confidencialidad de propuestas y resultados durante la simulación.  No obstante:

* **El cifrado se aplica al canal**, no al contenido final de los informes.
* **Los resultados siempre serán auditables**; el cifrado no se utiliza para ocultar evaluaciones o recomendaciones.

### 6. Modo didáctico y modo funcional

El núcleo distingue entre dos modos de uso:

* **Modo didáctico**: transparente y orientado a la formación.  Muestra íntegramente el historial de rondas, métricas de integridad y explicaciones.  Recomendado para investigación y enseñanza.
* **Modo funcional** (futuro fork empresarial): mantiene la misma lógica, pero automatiza la ejecución de múltiples escenarios y ofrece informes resumidos.  En ningún caso habilita el control de sistemas externos ni genera estrategias accionables en tiempo real.

## Gobernanza y mantenimiento

El cumplimiento de esta carta debe verificarse mediante pruebas automatizadas y revisiones de código.  Las contribuciones al núcleo deberán:

* Incluir **pruebas unitarias** que demuestren que las nuevas funcionalidades respetan estas reglas.
* Documentar claramente cualquier cambio en las funciones de utilidad o en la definición de estabilidad.
* Ser revisadas por al menos dos colaboradores familiarizados con la misión del proyecto.

## Conclusión

Esta carta transforma los principios éticos de HUB_Optimus en restricciones técnicas vinculantes.  Garantiza que, a medida que el proyecto crezca y se incorporen nuevas herramientas, **la finalidad original—promover la diplomacia integradora y la estabilidad—no se pervertirá**.  Cualquier expansión del núcleo debe comenzar evaluando su conformidad con esta carta.