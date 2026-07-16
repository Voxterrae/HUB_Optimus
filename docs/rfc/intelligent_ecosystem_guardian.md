# RFC: IEG — Intelligent Ecosystem Guardian

**Estado:** Borrador / RFC únicamente / no implementado
**Fecha:** 2026-07-16
**Issue principal:** #1696
**Tipo:** Arquitectura conceptual, ciencia aplicada y apoyo a la decisión
**Ámbito:** Documentación únicamente

> Este documento no autoriza código, despliegues, conectores, sensores, alertas operativas, restricciones de navegación, decisiones públicas ni actuaciones sobre fauna. Define un marco revisable para estudiar un posible sistema de apoyo a la conservación. Toda decisión marítima, veterinaria, científica o administrativa corresponde a las autoridades y profesionales competentes.

## 1. Decisión

HUB_Optimus puede documentar **IEG — Intelligent Ecosystem Guardian** como una propuesta de apoyo a la decisión para conservación, comenzando por el caso de las orcas ibéricas, siempre que:

- GitHub conserve la fuente de verdad del proyecto;
- cada afirmación distinga evidencia, inferencia e incertidumbre;
- los modelos produzcan estimaciones revisables, no órdenes ni diagnósticos;
- el sistema declare las limitaciones de cada fuente de datos;
- las decisiones permanezcan bajo responsabilidad humana competente;
- cualquier implementación futura se divida en issues y PR pequeñas;
- no se presenten objetivos numéricos como resultados o garantías;
- el contenido audiovisual preserve el mismo rigor que la arquitectura.

IEG no se incorpora al runtime actual de HUB_Optimus mediante esta RFC. La arquitectura descrita es una **hipótesis de diseño**, no una capacidad existente.

## 2. Misión y narrativa

### 2.1 Misión

Ayudar a científicos, equipos de conservación y autoridades competentes a integrar observaciones ecológicas y marítimas con procedencia verificable, estimar solapamientos y riesgos con incertidumbre visible, comparar opciones preventivas y registrar la revisión humana de cada recomendación.

### 2.2 Visión contenida

IEG aspira a ser una infraestructura federada de evidencia y apoyo a la decisión, no un “cerebro del océano”, una autoridad autónoma ni un sistema que comprenda por sí solo la intención de los animales.

### 2.3 Lema público propuesto

> **Cuando el ecosistema genera señales, aprendemos a escucharlas.**

El lema es narrativo. En términos técnicos, “escuchar” significa registrar datos autorizados, evaluar su calidad, conservar la incertidumbre y someter las conclusiones a revisión humana.

## 3. Descomposición epistemológica del paquete original

| Capa | Contenido admisible | Límite obligatorio |
| --- | --- | --- |
| Afirmación | La subpoblación ibérica es muy pequeña y está catalogada En Peligro Crítico | La cifra debe llevar año, fuente e intervalo de incertidumbre cuando exista |
| Evidencia | Informes oficiales, publicaciones revisadas por pares, observaciones validadas y datos con procedencia | La repetición mediática o una imagen aislada no elevan el nivel de evidencia |
| Inferencia | El aprendizaje social puede contribuir a la difusión de conductas | No equivale a demostrar intención, trauma, agresión o una causa única |
| Incertidumbre | Motivación exacta de las interacciones, cobertura de observación, relación causal entre presiones y respuesta | Debe permanecer visible en modelos, mapas, alertas y narrativa pública |
| Amplificación narrativa | “Colapso”, “venganza”, “ataque”, “extinción en décadas”, “IA que entiende su cultura” | No se adopta sin evidencia específica y metodología adecuada |
| Relevancia operativa | Mejorar observación, prevención, coordinación y evaluación de opciones | No habilita mando, navegación, diagnóstico ni política automática |

## 4. Base científica fechada

Esta sección fija el mínimo de evidencia que debe acompañar cualquier versión pública o técnica de IEG. Las cifras no son constantes permanentes: deben revisarse cuando se publiquen nuevos censos o evaluaciones.

### 4.1 Estado y abundancia

- La orca ibérica está catalogada **En Peligro Crítico**.
- El taller internacional de 2024 informó una estimación de **37 individuos en 2023**.
- El Comité Científico de la Comisión Ballenera Internacional resumió la población en 2024 como de “unos 40” individuos; otras formulaciones oficiales del mismo proceso indican que probablemente eran menos de 40.
- Por tanto, la redacción operativa recomendada es: **“subpoblación críticamente amenazada, estimada en 37 individuos en 2023; las cifras deben actualizarse con cada evaluación”**.

### 4.2 Demografía

El informe del taller de 2024 resume que:

- la supervivencia de crías mejoró respecto a los primeros años de la década de 2000;
- la supervivencia adulta disminuyó, especialmente en hembras;
- la reproducción es lenta y los intervalos estimados entre nacimientos son largos;
- la estimación reciente de crecimiento poblacional contenía incertidumbre compatible tanto con un ligero descenso como con un ligero crecimiento.

Estas señales justifican vigilancia demográfica. No justifican por sí solas afirmar que la población “se está extinguiendo en décadas” o que se encuentra en un “colapso” cuantificado sin un análisis de viabilidad poblacional actualizado.

### 4.3 Interacciones con embarcaciones

- Las nuevas interacciones se documentan desde **2020**.
- Se concentran con frecuencia en la popa y el **timón** de veleros y otras embarcaciones.
- El taller internacional de expertos de 2024 concluyó que no había evidencia de que la conducta fuese agresiva.
- El patrón observado compartía más rasgos con una conducta de moda, juego o socialización.
- La motivación exacta permanece sin resolver y puede depender de múltiples estímulos y contextos.

El término recomendado es **interacción**. “Ataque”, “agresión”, “venganza” o “trauma detectado” no deben utilizarse como explicación factual.

### 4.4 Alimentación y atún rojo

- Las orcas ibéricas muestran una asociación ecológica importante con el atún rojo atlántico.
- El stock de atún rojo del Atlántico oriental y Mediterráneo se recuperó de forma sustancial tras las medidas adoptadas desde 2006.
- Esto no elimina preguntas locales sobre accesibilidad, distribución espacial, estacionalidad, artes de pesca, competencia y coste energético de captura.

IEG puede estudiar **accesibilidad local de presas** como variable. No debe describir una “crisis del atún rojo” sin evidencia contemporánea y espacialmente pertinente.

### 4.5 Sanidad

No se adopta la afirmación de un aumento progresivo de enfermedades cutáneas en la subpoblación ibérica. La señal respaldada es una **brecha de monitorización sanitaria sistemática**.

Las fuentes oficiales recomiendan fortalecer:

- respuesta a varamientos;
- necropsias rigurosas;
- análisis veterinarios, forenses y genéticos;
- fotoidentificación y seguimiento longitudinal;
- coordinación entre laboratorios y redes de observación.

Una lesión visible es una observación que requiere revisión especializada. No es un diagnóstico automático.

### 4.6 Distribución y coordinación regional

El área de interés incluye el Estrecho de Gibraltar y la costa atlántica ibérica, con movimientos estacionales hacia Portugal y Galicia. El marco de coordinación debe priorizar España y Portugal e incluir, según el caso y la evidencia disponible, a Marruecos, Francia, la Comisión Ballenera Internacional y ACCOBAMS.

## 5. Qué es IEG

IEG es una propuesta para:

- registrar evidencia ecológica y marítima con procedencia;
- integrar observaciones heterogéneas sin ocultar sus limitaciones;
- estimar solapamientos espacio-temporales y riesgo de interacción;
- formular hipótesis de conducta y transmisión social;
- simular escenarios con incertidumbre explícita;
- comparar opciones de conservación;
- apoyar revisión científica, veterinaria, marítima y administrativa;
- conservar un registro auditable de datos, modelos y decisiones humanas.

## 6. Qué no es IEG

IEG no es:

- una capacidad implementada del runtime actual de HUB_Optimus;
- una autoridad marítima o ambiental;
- un sistema de navegación o control del tráfico;
- un diagnóstico veterinario;
- una prueba de intención, emoción, trauma o agresión animal;
- un predictor infalible de conducta;
- un sistema de vigilancia masiva de personas o embarcaciones;
- una justificación para publicar localizaciones sensibles sin control;
- una política pública ya adoptada;
- un sistema autónomo de aprendizaje, alerta, sanción o intervención;
- una garantía de reducción de interacciones o mejora ecológica.

## 7. Principios de diseño

1. **Evidencia antes que narrativa.** Cada salida enlaza con fuentes y transformaciones.
2. **Observación no es inferencia.** Los datos brutos se conservan separados de las estimaciones.
3. **Proxy no es diagnóstico.** Presión ambiental o riesgo de interacción no equivalen a estrés fisiológico medido.
4. **Estimación no es decisión.** Toda acción sensible requiere autoridad humana.
5. **Incertidumbre visible.** Ninguna interfaz debe ocultar cobertura, calidad, calibración o datos ausentes.
6. **Degradación controlada.** Si falla un modelo, deben seguir disponibles los datos validados y sus límites.
7. **Privacidad y sensibilidad ecológica.** Se minimizan identificadores de personas y se protegen localizaciones cuya difusión pueda causar perturbación.
8. **Interoperabilidad.** Formatos abiertos y contratos versionados cuando sea posible.
9. **Reproducibilidad.** Dataset, código, modelo, parámetros y revisión quedan versionados.
10. **Reversibilidad.** Modelos y recomendaciones pueden retirarse o revertirse.
11. **Competencia institucional.** Las autoridades oficiales conservan mando y responsabilidad.
12. **Escalado por evidencia.** Ningún módulo se amplía sin señal, evaluación y issue separada.

## 8. Modelo lógico de cinco módulos

Los cinco módulos son dominios lógicos. No implican cinco microservicios obligatorios ni autorizan implementación.

### 8.1 OPP — Orca Protection Protocol

**Objetivo:** apoyar la prevención de interacciones de riesgo mediante observaciones validadas, estimación de solapamiento y comunicación revisada.

**Entradas candidatas:**

- avistamientos validados;
- fotoidentificación;
- detecciones acústicas autorizadas;
- posiciones y densidad de embarcaciones obtenidas legalmente;
- meteorología y estado del mar;
- avisos oficiales y restricciones vigentes;
- historial de interacciones con calidad documentada.

**Salidas propuestas:**

- eventos de presencia observada o detección acústica;
- mapas de solapamiento con vigencia temporal;
- estimación de riesgo de interacción con intervalo o categoría de confianza;
- borradores de aviso para revisión humana;
- registro estructurado de interacción, incluido el componente afectado de la embarcación.

**Límites:**

- AIS informa sobre tráfico de embarcaciones; no detecta orcas.
- Una detección acústica no ofrece cobertura total y requiere validación del clasificador.
- La ausencia de vocalizaciones no demuestra ausencia de animales.
- IEG no activa zonas de baja velocidad ni emite instrucciones de navegación por sí mismo.
- Las comunicaciones públicas y medidas de tráfico corresponden a autoridades competentes.

### 8.2 BMO — Behavioral Model for Optimus

**Objetivo:** organizar observaciones de conducta y formular hipótesis revisables sobre aprendizaje social y cambio de patrones.

**Funciones propuestas:**

- taxonomía versionada de conductas observables;
- asociación entre individuos mediante fotoidentificación validada;
- mapas de coocurrencia y aprendizaje social hipotético;
- detección de cambios de frecuencia o contexto;
- clasificación de patrones compatibles con juego, exploración u otras categorías definidas por especialistas;
- registro de evidencia a favor y en contra de cada hipótesis.

**Límites:**

- no detecta trauma, intención, emoción, agresión ni motivación interna;
- no atribuye causalidad a hembras adultas o matriarcas sin evidencia longitudinal;
- una correlación social no prueba transmisión cultural;
- las categorías deben ser definidas y revisadas por etólogos y especialistas en orcas.

**Salida mínima:** hipótesis conductual + evidencia + alternativas + incertidumbre + revisor científico.

### 8.3 SRPS — Stressor and Response Proxy System

El nombre se corrige respecto a “Stress-Response Prediction System” para evitar presentar un diagnóstico de estrés biológico que los datos propuestos no pueden demostrar por sí solos.

**Objetivo:** estimar exposición a factores de presión y riesgo de interacción, conservando cada componente y su incertidumbre.

**Entradas candidatas:**

- densidad y velocidad de embarcaciones;
- ruido submarino medido o modelizado;
- accesibilidad local de presas;
- meteorología y oceanografía;
- interacciones recientes;
- observaciones sanitarias revisadas;
- cobertura y calidad de sensores.

**Salidas propuestas:**

- perfil de exposición por variable;
- índice operativo de presión, solo después de calibración;
- estimación de riesgo de interacción;
- ventanas espacio-temporales de revisión;
- factores dominantes, datos ausentes y confianza;
- acciones preventivas candidatas para revisión humana.

**Límites:**

- el resultado no es un biomarcador ni una medida clínica de estrés;
- un valor normalizado de 0 a 100 solo sería admisible tras definir escala, población de referencia, calibración, error e interpretación;
- no se debe combinar evidencia heterogénea en una puntuación opaca;
- las observaciones sanitarias no se incorporan sin revisión veterinaria.

### 8.4 CTS — Cultural Transmission Simulation

**Objetivo:** explorar escenarios sobre cómo una conducta podría difundirse o desaparecer bajo diferentes supuestos sociales y ambientales.

**Funciones propuestas:**

- simulación basada en redes sociales o agentes;
- escenarios de adopción, persistencia y abandono de conductas;
- sensibilidad a estructura social, exposición, edad y contexto;
- comparación de hipótesis alternativas;
- validación retrospectiva cuando existan series temporales suficientes.

**Salidas propuestas:**

- distribución de escenarios;
- supuestos explícitos;
- intervalos de incertidumbre;
- variables con mayor sensibilidad;
- condiciones que invalidarían el modelo.

**Límites:**

- no predice con certeza la conducta futura;
- no convierte una simulación en explicación causal;
- no atribuye cultura a partir de una sola correlación;
- no recomienda intervenciones sin pasar por evaluación científica y de bienestar animal.

### 8.5 CSSI — Conservation Strategy Support for Iberia

El nombre se corrige respecto a “Conservation Strategy Spain & Portugal Implementation”. IEG puede apoyar el análisis de opciones; no implementa política pública.

**Objetivo:** comparar opciones de conservación para el espacio ibérico y facilitar coordinación institucional con evidencia trazable.

**Componentes propuestos:**

- monitorización sanitaria sistemática;
- protocolos de navegación adaptativa evaluados por autoridades;
- protección espacial o temporal basada en evidencia;
- coordinación España–Portugal y cooperación regional;
- análisis de accesibilidad a presas y actividad pesquera;
- formación y comunicación para navegantes;
- evaluación ex ante y ex post de medidas;
- registro de competencia legal, responsable, vigencia y revisión.

**Salida mínima:** opción de política + fundamento + incertidumbre + efectos esperados + riesgos + autoridad competente + estado de revisión.

## 9. Arquitectura técnica propuesta

### 9.1 Vista por planos

```text
Fuentes autorizadas y entradas manuales
  |
  v
Evidence Gateway
  - autenticación y autorización
  - procedencia y licencia
  - clasificación de sensibilidad
  - validación de formato
  |
  v
Normalización y control de calidad
  - tiempo y georreferencia
  - deduplicación
  - indicadores de cobertura
  - revisión de identidad/foto-ID
  - conservación del dato original
  |
  +--------------------+---------------------+
  |                    |                     |
  v                    v                     v
Registro de eventos    Almacén geoespacial   Objetos científicos
observables            y series temporales   audio, imagen, informes
  |                    |                     |
  +--------------------+---------------------+
                       |
                       v
Capa de características y contratos versionados
                       |
          +------------+------------+-------------+-------------+
          |            |            |             |             |
          v            v            v             v             v
        OPP          BMO          SRPS           CTS           CSSI
          |            |            |             |             |
          +------------+------------+-------------+-------------+
                       |
                       v
Capa de evidencia y recomendaciones
  - fuente y linaje
  - incertidumbre
  - versión de modelo
  - caducidad
  - alternativas
                       |
                       v
Revisión humana por competencia
  - científica
  - veterinaria
  - marítima
  - conservación/política
                       |
                       v
Salidas autorizadas
  - informe
  - mapa
  - hipótesis
  - aviso aprobado
  - opción de política
```

### 9.2 Componentes

```text
IEG-Core
|
|-- governance-plane
|   |-- source-policy
|   |-- access-control
|   |-- data-classification
|   |-- human-review-routing
|   `-- decision-audit
|
|-- evidence-plane
|   |-- observation-registry
|   |-- provenance-ledger
|   |-- data-quality-service
|   |-- geospatial-time-series-store
|   |-- scientific-object-store
|   `-- retention-and-redaction
|
|-- analytics-plane
|   |-- OPP-domain
|   |-- BMO-domain
|   |-- SRPS-domain
|   |-- CTS-domain
|   `-- CSSI-domain
|
|-- model-governance
|   |-- dataset-cards
|   |-- model-registry
|   |-- validation-reports
|   |-- calibration-and-drift
|   |-- approval-gates
|   `-- rollback
|
|-- decision-support-plane
|   |-- evidence-briefs
|   |-- geospatial-products
|   |-- recommendation-records
|   |-- authority-review-queue
|   `-- publication-control
|
`-- cross-cutting-controls
    |-- encryption-and-secrets
    |-- audit-logging
    |-- security-monitoring
    |-- incident-response
    |-- observability
    |-- interoperability
    `-- licensing-and-rights
```

### 9.3 Arquitectura de despliegue

La arquitectura de referencia debe admitir procesamiento por lotes y, cuando esté justificado, flujos cercanos al tiempo real.

- **Edge autorizado:** preprocesamiento acústico o de sensores con almacenamiento temporal, reloj sincronizado, registro de salud y actualización firmada.
- **Ingesta segura:** colas o APIs autenticadas, límites de tasa, idempotencia y cuarentena de entradas inválidas.
- **Procesamiento central:** normalización, geoespacial, análisis y simulación en servicios separables, no necesariamente microservicios desde el primer prototipo.
- **Persistencia:** registro de eventos, almacén geoespacial, objetos científicos y ledger de procedencia.
- **Modelos:** registro de versión, dataset, parámetros, métricas, restricciones y aprobación.
- **Interfaz humana:** revisión por rol, explicación de fuentes, incertidumbre y caducidad.
- **Publicación:** salida separada del entorno analítico, con aprobación y redacción de datos sensibles.

No se adopta “cloud-native microservices” como obligación inicial. Un monolito modular u offline reproducible puede ser más seguro para el primer prototipo.

## 10. Capacidades y límites de las fuentes de datos

| Fuente | Puede aportar | No demuestra por sí sola | Controles mínimos |
| --- | --- | --- | --- |
| Avistamientos validados | presencia, hora, posición, contexto | ausencia fuera del campo de observación | protocolo, experiencia del observador, evidencia y revisión |
| Fotoidentificación | individuo probable, asociación y seguimiento | estado clínico completo o intención | calidad de imagen, catálogo versionado, doble revisión |
| AIS | posición, rumbo y velocidad de buques que transmiten | presencia de orcas ni todo el tráfico | licencia, cobertura, latencia, filtrado y minimización |
| Hidrófonos | señales acústicas dentro de cobertura | ausencia de animales cuando no vocalizan | calibración, ruido, tasa de falsos positivos, revisión acústica |
| Satélite ambiental | temperatura, productividad, frentes y contexto oceánico | identificación fiable en tiempo real de una orca individual | resolución, nubosidad, latencia y procedencia |
| Telemetría satelital autorizada | posición aproximada de un animal marcado | cobertura de toda la población | permisos, bienestar animal, error y duración del dispositivo |
| Datos de pesca y atún | capturas, esfuerzo, distribución o índices disponibles | accesibilidad efectiva para cada grupo de orcas | escala espacial, retraso, sesgo y acuerdos de uso |
| Meteorología/oceanografía | condiciones ambientales | causa directa de una conducta | modelo, resolución y validación local |
| Lesiones visibles | señal que requiere revisión | diagnóstico, etiología o tendencia poblacional | protocolo fotográfico y evaluación veterinaria |
| Varamientos/necropsias | evidencia sanitaria y causal de alta calidad | estado de animales vivos no examinados | cadena de custodia, laboratorio y coordinación regional |

## 11. Contratos mínimos de datos

Los ejemplos son conceptuales. No modifican el schema actual de HUB_Optimus.

### 11.1 `observation_event`

```json
{
  "event_id": "obs-uuid",
  "observed_at": "ISO-8601",
  "received_at": "ISO-8601",
  "location": {
    "geometry": "GeoJSON-or-redacted-reference",
    "spatial_error_m": 0
  },
  "source": {
    "type": "sighting|photo_id|acoustic|ais|satellite|fishery|health",
    "reference": "stable-source-reference",
    "operator": "authorised-role-or-organisation",
    "license": "recorded-rights-status"
  },
  "observation_type": "presence|vocalisation|interaction|lesion_visible|environment",
  "subject_id": "optional-reviewed-individual-id",
  "value": {},
  "quality": {
    "confidence": "low|medium|high",
    "flags": [],
    "review_status": "raw|reviewed|rejected"
  },
  "sensitivity": "public|restricted|ecologically_sensitive",
  "derived_from": []
}
```

### 11.2 `model_output`

```json
{
  "output_id": "model-output-uuid",
  "model": {
    "name": "opp-overlap-model",
    "version": "immutable-version",
    "validation_report": "reference"
  },
  "generated_at": "ISO-8601",
  "valid_until": "ISO-8601-or-null",
  "input_event_ids": [],
  "output_type": "interaction_risk|pressure_proxy|behaviour_hypothesis|scenario",
  "value": {},
  "uncertainty": {
    "method": "documented-method",
    "interval_or_category": {},
    "coverage_gaps": []
  },
  "limitations": [],
  "review_status": "unreviewed|scientific_reviewed|rejected",
  "non_authoritative": true
}
```

### 11.3 `recommendation_record`

```json
{
  "recommendation_id": "rec-uuid",
  "created_at": "ISO-8601",
  "jurisdiction": ["ES", "PT"],
  "recommendation_type": "review|communication|monitoring|policy_option",
  "evidence_summary": [],
  "alternatives": [],
  "uncertainty": [],
  "responsible_authority": "competent-authority-or-null",
  "approval": {
    "required": true,
    "status": "draft|approved|rejected|expired",
    "reviewers": []
  },
  "validity": {
    "from": "ISO-8601-or-null",
    "until": "ISO-8601-or-null",
    "stop_conditions": []
  },
  "non_authoritative": true
}
```

## 12. Linaje, calidad y evidencia

Cada transformación debe conservar:

- identificador de fuente;
- fecha de observación y de recepción;
- licencia y derechos de uso;
- clasificación de sensibilidad;
- transformaciones aplicadas;
- versión de código, dataset y modelo;
- datos excluidos y razón;
- cobertura conocida y ausencia de cobertura;
- revisión humana;
- caducidad de la salida;
- correcciones y retiradas posteriores.

No se permite el **lavado de fuente**: una observación débil no se convierte en hecho confirmado por haber pasado por un modelo o un dataset.

## 13. Gobierno del aprendizaje y de los modelos

“Autoadaptativo” no significa aprendizaje autónomo en producción.

El ciclo permitido para una futura implementación sería:

```text
nuevos datos autorizados
  -> control de calidad
  -> dataset versionado
  -> entrenamiento o recalibración offline
  -> evaluación temporal y geográfica
  -> revisión científica y técnica
  -> aprobación humana
  -> despliegue limitado y reversible
  -> monitorización
  -> rollback o retirada si falla
```

Queda fuera de alcance:

- reentrenamiento continuo sin revisión;
- cambio automático de umbrales operativos;
- aprendizaje con datos sin licencia o procedencia;
- promoción de hipótesis a hechos por repetición del modelo;
- uso de un LLM como juez científico final;
- despliegue de un modelo sin informe de validación y condiciones de retirada.

## 14. Flujo de decisión

```text
1. Observar
   dato bruto + procedencia + cobertura

2. Detectar
   evento, cambio o solapamiento candidato

3. Evaluar
   evidencia + alternativas + incertidumbre + riesgo de error

4. Revisar
   especialista según competencia

5. Recomendar
   opción no vinculante, con vigencia y condiciones de parada

6. Decidir
   autoridad humana competente

7. Medir
   resultado, efectos no deseados y calidad de la señal

8. Aprender
   actualización versionada tras revisión
```

### 14.1 Roles mínimos

- **Operador de datos:** ingesta y calidad; no valida conclusiones científicas.
- **Revisor científico:** conducta, ecología, bioacústica o población.
- **Revisor veterinario:** salud y lesiones.
- **Revisor marítimo:** seguridad y comunicación a navegantes.
- **Responsable de conservación/política:** competencia institucional y proporcionalidad.
- **Responsable de datos y seguridad:** acceso, retención, incidentes y auditoría.
- **Mantenedor técnico:** implementación, observabilidad y rollback.

Una misma persona no debe aprobar en solitario una salida de alto impacto cuando exista conflicto de funciones.

## 15. Evaluación científica y técnica

### 15.1 Preguntas de evaluación

- ¿La fuente detecta lo que afirma detectar?
- ¿Cuál es la cobertura temporal y espacial real?
- ¿Qué tasa de falsos positivos y falsos negativos existe?
- ¿El modelo está calibrado fuera de su periodo y zona de entrenamiento?
- ¿La incertidumbre se corresponde con el error observado?
- ¿La recomendación mejora una decisión humana respecto a la línea base?
- ¿Aparecen efectos adversos, desplazamiento de riesgo o perturbación adicional?
- ¿El sistema mantiene utilidad cuando faltan sensores o datos?

### 15.2 Métricas candidatas

- completitud, latencia y frescura de datos;
- precisión, recall y tasa de falsas alarmas donde exista verdad de referencia;
- error de calibración y cobertura de intervalos;
- rendimiento por zona, estación y tipo de embarcación;
- estabilidad temporal y deriva;
- tasa de revisión, rechazo y corrección humana;
- tiempo hasta la comprensión de una alerta;
- disponibilidad del sistema y degradación controlada;
- cumplimiento de licencias, acceso y retención;
- impacto ecológico, solo con diseño causal y plazo adecuados.

### 15.3 Afirmaciones numéricas no adoptadas

| Afirmación del paquete inicial | Estado | Requisito antes de utilizarla |
| --- | --- | --- |
| “70 % menos interacciones de riesgo” | No adoptada como objetivo ni promesa | definición de interacción, línea base, contrafactual, periodo, potencia y evaluación independiente |
| “40 % de mejora en estrés” | No adoptada | biomarcadores o medida validada, relación causal y revisión veterinaria/etológica |
| “25 % más precisión predictiva” | No interpretable sin referencia | tarea, baseline, métrica, dataset temporal externo e intervalo de confianza |
| “100 % de cobertura de rutas” | No adoptada | definición de cobertura, sensores, disponibilidad, resolución y límites geográficos |
| “primer sistema del mundo” | No adoptada | revisión documental independiente y definición comparable |

Las cifras podrían convertirse en **hipótesis preregistradas** de un piloto futuro, nunca en garantía de resultado.

## 16. Puertas de implementación

Ninguna puerta se abre mediante esta RFC.

### Gate 0 — Revisión científica y de gobernanza

- panel interdisciplinar;
- revisión de afirmaciones y taxonomías;
- límites de bienestar animal y seguridad marítima;
- clasificación de riesgo regulatorio y de datos.

### Gate 1 — Inventario y acuerdos de datos

- fuentes disponibles;
- licencias y permisos;
- cobertura, calidad y latencia;
- sensibilidad ecológica y privacidad;
- responsables y retención.

### Gate 2 — Registro de evidencia offline

- ingesta manual o por lotes controlada;
- contratos mínimos;
- procedencia y auditoría;
- sin alertas operativas.

### Gate 3 — Prototipo de un solo módulo en modo sombra

- una pregunta limitada;
- datos históricos o paralelos;
- resultados invisibles para navegación pública;
- comparación contra especialistas y baseline.

### Gate 4 — Piloto limitado y autorizado

- zona, periodo y usuarios definidos;
- plan de parada;
- revisión humana obligatoria;
- comunicación pública aprobada;
- monitorización de efectos adversos.

### Gate 5 — Evaluación independiente

- protocolo preregistrado;
- dataset temporal o geográfico externo;
- análisis de error y sesgo;
- publicación de limitaciones;
- decisión explícita de continuar, corregir o retirar.

### Gate 6 — Escalado

- issue o RFC separada por especie, territorio, fuente y capacidad;
- acuerdos institucionales;
- presupuesto de operación y mantenimiento;
- gobernanza de incidentes, datos y modelos.

## 17. Perfil de instrucciones para GPT / Optimus

Este fragmento es un perfil asesor. No sustituye las instrucciones superiores del sistema, la evidencia versionada, las autoridades competentes ni la revisión profesional.

```text
Perfil asesor: IEG — Intelligent Ecosystem Guardian

FUENTE DE VERDAD
- GitHub versionado define el estado del proyecto.
- Las fuentes científicas y oficiales definen el estado del conocimiento externo.
- El chat y la salida del modelo son asesoría, no autoridad.

MÉTODO OBLIGATORIO
- Separar: afirmación, evidencia, inferencia, incertidumbre,
  amplificación narrativa y relevancia operativa.
- Fechar cifras y evaluar la antigüedad de las fuentes.
- Mostrar procedencia, alternativas y datos ausentes.
- Usar "interacción" y no atribuir agresión, venganza, trauma,
  intención o causalidad sin evidencia específica.
- Tratar aprendizaje social o transmisión cultural como hipótesis
  evaluables, no como certeza automática.

LÍMITES
- No diagnosticar estrés o enfermedad desde proxies ambientales.
- No afirmar que AIS detecta orcas.
- No interpretar ausencia acústica como ausencia de animales.
- No emitir órdenes de navegación, cierres, sanciones o política.
- No ocultar incertidumbre detrás de una puntuación única.
- No prometer porcentajes de impacto no validados.
- No presentar simulaciones como predicciones garantizadas.
- No reemplazar a científicos, veterinarios ni autoridades.

MÓDULOS LÓGICOS
- OPP: observación y prevención de interacciones.
- BMO: clasificación conductual e hipótesis sociales.
- SRPS: proxies de factores de presión y riesgo, no diagnóstico.
- CTS: simulación de escenarios culturales con incertidumbre.
- CSSI: comparación de opciones de conservación para Iberia.

FORMATO DE SALIDA
1. Decisión o pregunta analítica.
2. Evidencia y fecha.
3. Inferencias.
4. Incertidumbre y alternativas.
5. Riesgo de error o amplificación.
6. Relevancia operativa.
7. Revisión humana requerida.
8. Fuentes.
```

## 18. Paquete audiovisual 9:16 — 55 segundos

### 18.1 Guion corregido

| Tiempo | Locución | Texto breve en pantalla |
| --- | --- | --- |
| 0:00–0:05 | “El océano deja señales. Interpretarlas exige ciencia, contexto y prudencia.” | Ciencia. Contexto. Prudencia. |
| 0:05–0:12 | “La subpoblación ibérica de orcas está En Peligro Crítico. En 2023 se estimaron 37 individuos.” | 37 estimadas en 2023 · fuente en créditos |
| 0:12–0:21 | “Desde 2020 se observan interacciones con embarcaciones, a menudo centradas en el timón. Los expertos no las consideran agresión. Su motivación exacta sigue abierta.” | Interacción, no agresión · causa no resuelta |
| 0:21–0:29 | “IEG es una propuesta de apoyo a la conservación, no una autoridad autónoma.” | IEG · apoyo a la decisión |
| 0:29–0:38 | “Integra observaciones, acústica autorizada, tráfico marítimo y condiciones ambientales para estimar solapamientos y riesgos.” | Fuente + cobertura + incertidumbre |
| 0:38–0:47 | “No diagnostica a los animales ni decide por las autoridades. Cada señal conserva su procedencia y cada recomendación requiere revisión humana.” | Evidencia trazable · revisión humana |
| 0:47–0:55 | “IEG. Cuando el ecosistema genera señales, aprendemos a escucharlas.” | Intelligent Ecosystem Guardian |

### 18.2 Plan de montaje

| Escena | Visual recomendado | Tratamiento técnico |
| --- | --- | --- |
| 1 | superficie oceánica y ondas acústicas abstractas | movimiento lento; sin alarmas ni rojo de emergencia |
| 2 | orcas ibéricas o mapa regional con material autorizado | crédito y fecha visibles en créditos finales |
| 3 | timón de velero y aproximación calmada de una orca | no dramatizar colisión; no recrear “ataque” |
| 4 | diagrama de datos entrando en una capa de evidencia | separar observación, modelo y revisión |
| 5 | mapa de solapamiento con zonas difusas e incertidumbre | no mostrar rutas como instrucciones oficiales |
| 6 | científica, veterinario o autoridad revisando evidencia | representar responsabilidad humana real |
| 7 | grupo de orcas alejándose en mar abierto | cierre sobrio; lema y fuentes |

### 18.3 Prompts visuales

Los prompts no garantizan exactitud biológica. Toda imagen generada debe etiquetarse como ilustración y revisarse antes de publicación.

**Prompt 1 — apertura**

```text
Formato vertical 9:16, océano Atlántico al amanecer, superficie y columna de agua,
ondas acústicas abstractas muy sutiles, estética documental científica,
sin texto, sin logotipos, sin dramatismo, sin animales en peligro.
```

**Prompt 2 — contexto ibérico**

```text
Formato vertical 9:16, pequeño grupo de orcas en aguas del Atlántico ibérico,
comportamiento natural y calmado, escala realista, luz submarina documental,
sin persecución, sin contacto forzado, sin texto, sin logotipos.
```

**Prompt 3 — interacción con timón**

```text
Formato vertical 9:16, vista dividida sobre y bajo el agua de un velero detenido,
timón visible en popa y una orca inspeccionándolo a distancia prudente,
conducta no agresiva, mar calmado, estilo documental realista,
sin daños, sin impacto, sin texto, sin logotipos.
```

**Prompt 4 — arquitectura IEG**

```text
Formato vertical 9:16, visualización técnica sobria de observaciones de campo,
hidrófono, tráfico de embarcaciones, datos ambientales y revisión científica
conectados a un registro de evidencia, distinguir claramente datos, modelo y humano,
paleta oceánica, sin texto legible, sin logotipos.
```

**Prompt 5 — revisión humana**

```text
Formato vertical 9:16, equipo multidisciplinar de conservación revisando un mapa
con procedencia, incertidumbre y ventanas temporales, entorno profesional realista,
ninguna pantalla de mando militar, ninguna decisión automática, sin logotipos.
```

**Prompt 6 — cierre**

```text
Formato vertical 9:16, grupo de orcas nadando en mar abierto con luz natural,
cardumen de peces a distancia, tono esperanzador y sobrio, documental,
sin halo mágico, sin interfaz invasiva, sin texto, sin logotipos.
```

### 18.4 Sonido, locución y accesibilidad

- locución serena y no sensacionalista;
- velocidad aproximada de 135–145 palabras por minuto, ajustada tras prueba real;
- música ambiental con licencia documentada;
- no usar vocalizaciones de orca sin conocer procedencia, especie, contexto y derechos;
- subtítulos completos y sincronizados;
- contraste suficiente y zona segura para interfaces móviles;
- no usar destellos rápidos ni sobrecargar la pantalla;
- incluir créditos de fuentes científicas y audiovisuales.

### 18.5 Control de derechos y procedencia

Pexels, Pixabay, Videvo, CapCut u otras bibliotecas son **lugares de búsqueda**, no una declaración automática de “libre de derechos”. Cada recurso requiere comprobación individual.

Registrar como mínimo:

```text
asset_id
source_url
creator_or_owner
asset_title
download_date
license_name_and_version
allowed_uses
attribution_required
modification_allowed
redistribution_allowed
territorial_or_platform_limits
proof_of_license
edits_applied
reviewer
publication_id
```

No publicar un clip si:

- no puede demostrarse la licencia aplicable;
- contiene marcas o personas sin permisos adecuados;
- revela localizaciones ecológicamente sensibles;
- representa una interacción como agresión sin base;
- mezcla imagen generada con documental sin etiquetado;
- utiliza material de una autoridad o institución fuera de sus condiciones de reutilización.

## 19. Protocolo operativo propuesto

Este protocolo solo describe una futura cadena de revisión.

### 19.1 Entrada

1. recibir observación o dataset autorizado;
2. clasificar procedencia, licencia, sensibilidad y competencia;
3. validar tiempo, posición, formato y cobertura;
4. conservar original y transformación;
5. enviar entradas dudosas a cuarentena.

### 19.2 Análisis

1. ejecutar únicamente modelos aprobados para esa fuente y zona;
2. conservar versión y parámetros;
3. producir salida con incertidumbre y caducidad;
4. comparar con baseline y alternativas;
5. bloquear publicación si falta evidencia mínima.

### 19.3 Revisión

1. enrutar por tipo: científica, veterinaria, marítima o política;
2. registrar aceptación, rechazo o corrección;
3. impedir que un LLM apruebe la salida final;
4. exigir segunda revisión para comunicaciones o medidas sensibles;
5. conservar conflicto y desacuerdo, no forzar consenso artificial.

### 19.4 Comunicación

1. indicar qué se observó y qué se infirió;
2. mostrar fuente, fecha, cobertura, incertidumbre y vigencia;
3. identificar la autoridad responsable;
4. retirar o corregir salidas caducadas;
5. evitar localizaciones sensibles en productos públicos.

### 19.5 Seguimiento

1. medir resultado y efectos adversos;
2. registrar falsos positivos, falsos negativos y datos ausentes;
3. revisar calibración y deriva;
4. activar condición de parada cuando se supere el riesgo permitido;
5. actualizar solo mediante dataset y modelo versionados.

## 20. Seguridad, privacidad y sensibilidad ecológica

Una futura implementación debe incluir:

- control de acceso por rol y mínimo privilegio;
- autenticación fuerte para operadores;
- cifrado en tránsito y reposo;
- gestión externa de secretos;
- logs de auditoría inmutables o con protección contra alteración;
- inventario de datos y retención limitada;
- borrado o anonimización cuando proceda;
- respuesta a incidentes y notificación;
- seguridad de edge devices y actualizaciones firmadas;
- revisión de dependencias y cadena de suministro;
- redacción de identificadores de embarcaciones cuando no sean necesarios;
- protección de posiciones de animales sensibles;
- separación entre entorno analítico y publicación pública.

No deben almacenarse en GitHub público datos privados, localizaciones sensibles sin redacción, credenciales, acuerdos restringidos ni datasets cuya licencia impida publicación.

## 21. Riesgos y mitigaciones

| Riesgo | Consecuencia | Mitigación mínima |
| --- | --- | --- |
| Falso positivo de presencia | aviso innecesario o pérdida de confianza | calibración, doble fuente cuando sea posible, revisión y caducidad |
| Falso negativo | ausencia de aviso donde existe presencia | comunicar cobertura, no equiparar silencio con ausencia, degradación segura |
| Proxy interpretado como estrés | afirmación biológica falsa | nombre corregido, componentes visibles, revisión científica |
| Hipótesis cultural convertida en hecho | antropomorfismo y política inadecuada | alternativas, validación longitudinal y lenguaje probabilístico |
| Publicación de posición sensible | perturbación o seguimiento no deseado | acceso restringido, resolución reducida y retardo |
| Uso impropio de AIS | privacidad o vigilancia de personas | minimización, propósito definido y revisión legal |
| Drift de modelo | degradación silenciosa | monitorización, evaluación temporal y rollback |
| Confusión con autoridad oficial | riesgo marítimo o institucional | marca de no autoridad, aprobación competente y canales oficiales |
| Dependencia de proveedor | bloqueo técnico o pérdida de trazabilidad | contratos abiertos, exportación y modelo neutral |
| Material audiovisual sin derechos | retirada o responsabilidad legal | ledger de licencias y prueba de uso |
| Narrativa alarmista | pérdida de rigor y confianza | revisión editorial contra la base científica |
| Scope creep | arquitectura imposible de revisar | una capacidad, una issue y una PR |

## 22. Dependencias para cualquier implementación futura

- revisión por especialistas en orcas, ecología, bioacústica, población y comportamiento;
- revisión veterinaria y de redes de varamientos;
- competencia y autorización de autoridades marítimas y ambientales;
- acuerdos de datos con responsabilidades claras;
- análisis legal de AIS, telemetría, privacidad y reutilización;
- estudio de viabilidad de sensores y mantenimiento;
- baseline y protocolo de evaluación preregistrado;
- presupuesto de operación, ciberseguridad y respuesta a incidentes;
- gobernanza España–Portugal y coordinación regional cuando corresponda;
- revisión de accesibilidad y comunicación pública;
- issue o RFC separada para cada fuente, módulo, interfaz o piloto.

## 23. Fuera de alcance de esta RFC

- modificar el runtime de HUB_Optimus;
- modificar schemas, benchmarks o CI;
- construir datasets sintéticos;
- instalar hidrófonos o telemetría;
- integrar AIS, satélite, pesca o APIs externas;
- entrenar modelos;
- crear dashboards o apps;
- emitir alertas a navegantes;
- definir rutas o maniobras de seguridad;
- activar zonas lentas o restricciones;
- diagnosticar salud o estrés;
- implementar vigilancia o seguimiento de personas;
- desplegar aprendizaje continuo;
- adoptar una estrategia gubernamental;
- prometer impacto numérico;
- ampliar traducciones;
- incorporar vídeos, fotografías o música de terceros al repositorio.

## 24. Criterios de aceptación

La RFC es aceptable cuando:

- se identifica como documentación no implementada;
- las cifras de población están fechadas y no se presentan como constantes;
- conducta, aprendizaje social y motivación conservan incertidumbre;
- no se usa agresión como explicación respaldada;
- no se afirma una tendencia sanitaria no demostrada;
- AIS, acústica, satélite y telemetría tienen límites explícitos;
- SRPS produce proxies, no un diagnóstico de estrés;
- CTS produce escenarios, no predicciones garantizadas;
- CSSI apoya opciones, no implementa política;
- la arquitectura distingue dato, modelo, recomendación y decisión;
- la revisión humana y la autoridad competente son obligatorias;
- no se adoptan 70 %, 40 %, 25 %, 100 % ni “primero del mundo”;
- el guion audiovisual conserva la evidencia y la incertidumbre;
- cada recurso audiovisual requiere licencia y procedencia;
- cualquier implementación futura queda tras issues/RFC separadas;
- no se modifican runtime, CI, benchmarks, schemas ni roadmap.

## 25. Validación de esta PR documental

```bash
python tools/check_mojibake.py docs/rfc/intelligent_ecosystem_guardian.md
git diff --check -- docs/rfc/intelligent_ecosystem_guardian.md
```

La comprobación de enlaces de CI debe validar las referencias externas.

`docs/context/AI_HANDOFF.md` no requiere actualización porque esta RFC no cambia el estado operativo, el runtime, CI, benchmarks, schemas, prioridades ni requisitos de entrega actuales.

## 26. Referencias

### Fuentes oficiales principales

1. International Whaling Commission. *Report of the Scientific Committee 2024*, sección sobre Iberian killer whales.
   https://iwc.int/public/downloads/KxHsW/SC_REP_2024.pdf

2. MITECO / International Workshop on the Interactions between Iberian Killer Whales and Vessels. *Report of the Workshop*, Madrid, febrero de 2024.
   https://www.miteco.gob.es/content/dam/miteco/es/biodiversidad/temas/biodiversidad-marina/orcas/informe-taller-orcas-miteco-en.pdf

3. IUCN Red List. *Orcinus orca, Strait of Gibraltar subpopulation*. Evaluación citada y enlazada en el informe oficial del taller de 2024.

4. IUCN Red List. *Thunnus thynnus*. Evaluación citada y enlazada en el informe oficial del taller de 2024.

### Publicaciones científicas citadas por el proceso de expertos

5. Esteban, R. et al. (2016). Dynamics of killer whale, bluefin tuna and human fisheries in the Strait of Gibraltar. DOI: `10.1016/j.biocon.2015.11.031`.

6. Esteban, R. et al. (2016). Using a multi-disciplinary approach to identify a critically endangered killer whale management unit. DOI: `10.1016/j.ecolind.2016.01.043`.

7. Esteban, R. et al. (2022). Killer whales of the Strait of Gibraltar, an endangered subpopulation showing a disruptive behavior. DOI: `10.1111/mms.12947`.

## 27. Siguiente decisión permitida

La siguiente acción no es construir el “full stack”. Es revisar esta RFC contra:

- evidencia científica actualizada;
- límites de HUB_Optimus;
- competencia institucional;
- seguridad marítima;
- viabilidad de datos;
- protección de información sensible.

Solo después de aceptación explícita puede abrirse una issue limitada para **un registro offline de evidencia**, sin alertas ni modelos de producción.
