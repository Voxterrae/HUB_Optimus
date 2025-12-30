> 🇬🇧 English source: ../en/02_arquitectura_base.md

# Arquitectura base (ES)

Este documento describe la arquitectura conceptual de **HUB_Optimus**: cómo se estructura un escenario, cómo se evalúa y cómo se transforma el resultado en mejoras del sistema.

---

## 1) Visión general
HUB_Optimus organiza el análisis y la ejecución de escenarios en **capas**. Cada capa responde a una pregunta distinta y reduce un tipo de error típico en negociaciones (sesgos, incentivos incorrectos, acuerdos no verificables, repetición de patrones fallidos).

---

## 2) Capas (Layers) y función

### Capa 0 — Coherencia del núcleo (Kernel)
**Pregunta:** ¿esto viola el criterio supremo de estabilidad?  
**Salida:** aprobado / rechazado como solución estabilizadora.

### Capa 1 — Calibración humana
**Pregunta:** ¿qué sesgos o dinámicas humanas distorsionan la lectura del acuerdo?  
**Salida:** nivel de prioridad + guía de encuadre (framing).

### Capa 2 — Incentivos
**Pregunta:** ¿qué conductas se recompensan o se castigan realmente?  
**Salida:** mapa de incentivos + señales de riesgo (p. ej., “éxito falso”).

### Capa 3 — Evaluación sistémica
**Pregunta:** ¿qué impacto tendrá en estabilidad a medio/largo plazo?  
**Salida:** clasificación de riesgo + impacto en estabilidad + ventana de corrección.

### Capa 4 — Mediación preventiva
**Pregunta:** ¿qué intervenciones mínimas evitan el modo de fallo?  
**Salida:** opciones de intervención (verificación, secuencia, incentivos, encuadre público).

### Capa 5 — Patrón histórico
**Pregunta:** ¿esto ya ocurrió? ¿cómo falló o tuvo éxito antes?  
**Salida:** nivel de advertencia por recurrencia + condiciones de divergencia.

---

## 3) Entradas y salidas del sistema (I/O)

### Entrada típica (input)
Un escenario bien formado incluye:
- disparador (qué ocurre),
- contexto estructural,
- actores/roles,
- incentivos y restricciones,
- objetivo mínimo,
- propuesta inicial,
- verificación y cumplimiento,
- riesgos y puntos de fricción,
- criterios de evaluación.

### Salida típica (output)
- clasificación (estabilizador / desestabilizador / transitorio / no evaluable),
- mapa de incentivos (qué se premia y qué se castiga),
- guía de encuadre (cómo comunicar sin sesgar),
- lista de intervenciones preventivas,
- aprendizaje: parches y cambios priorizados (meta-learning).

---

## 4) Principales modos de fallo que la arquitectura intenta evitar
- **Acuerdos sin verificación**: “paz declarada” que no se puede comprobar.
- **Incentivos perversos**: se premia el anuncio, no el cumplimiento.
- **Ambigüedad estratégica**: útil para firmar, fatal para implementar.
- **Secuencia imposible**: el orden de pasos hace inviable la ejecución.
- **Repetición histórica**: mismo patrón, mismo fracaso.
- **Euforia/relajación**: sesgos humanos tras “buenas noticias”.

---

## 5) Artefactos del repositorio y dónde viven
- Entrada y guías: `docs/` y `docs/es/`
- Workflow (plantillas + escenarios): `v1_core/workflow/` y `v1_core/workflow/es/`
- Base conceptual: `v1_core/languages/en/` y `v1_core/languages/es/`

---

## 6) Estándar mínimo de un documento “usable”
Un documento se considera listo cuando:
- tiene enlaces internos funcionales,
- define términos clave,
- incluye criterios verificables,
- evita contradicciones,
- permite repetición por terceros (reproducibilidad).

---

## 7) Enlaces internos
- Declaración base (ES): `./01_base_declaracion.md`
- Flujo operativo (ES): `./03_flujo_operativo.md`
- Workflow (ES): `../../workflow/es/README.md`
