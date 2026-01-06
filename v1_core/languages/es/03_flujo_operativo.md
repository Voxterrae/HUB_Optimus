> 🇬🇧 English source: [../03_flujo_operativo.md](../03_flujo_operativo.md)

# Flujo operativo (ES)

Este documento describe el flujo recomendado para usar HUB_Optimus: desde elegir o crear un escenario hasta ejecutar rondas, evaluar, y aplicar meta-learning para mejorar el sistema.

---

## 1) Objetivo del flujo
- Convertir una situación compleja en un **proceso estructurado**.
- Evitar “acuerdos bonitos” sin implementación.
- Capturar aprendizaje reutilizable para futuras mediaciones/simulaciones.

---

## 2) Preparación (2–10 minutos)

### 2.1 Elegir un escenario
- Si vas a practicar: usa un escenario existente en `v1_core/workflow/es/`.
- Si vas a crear uno nuevo: usa la plantilla [v1_core/workflow/es/04_scenario_template.md](../../workflow/es/04_scenario_template.md).

### 2.2 Definir roles y límites
- Parte A / Parte B / mediación (opcional).
- Define líneas rojas y zona negociable.
- Define qué información es pública y qué es interna.

### 2.3 Definir “éxito mínimo”
Un criterio operativo corto, verificable:
- “Éxito mínimo” = 1–3 frases, medibles.

---

## 3) Ejecución (3 rondas recomendadas)

### Ronda 1 — Propuesta inicial
- Propuesta breve (objetivo, alcance, calendario).
- Respuesta: aceptación parcial + condiciones / rechazo + alternativa.

### Ronda 2 — Ajuste estructural
Enfocar en:
- verificación (quién/cómo/acceso),
- secuencia (orden de pasos),
- incentivos (qué se premia/castiga),
- consecuencias (qué pasa si se viola).

### Ronda 3 — Cierre
- Borrador de acuerdo (8–15 líneas).
- Lista de “puntos abiertos”.
- Próximos pasos (quién hace qué y cuándo).

---

## 4) Evaluación (post-ronda)
Evalúa con criterios simples (0–5) y evidencia textual:
- Claridad
- Verificabilidad
- Viabilidad
- Coste político
- Riesgo de escalada

Salida: una clasificación breve (estabilizador / desestabilizador / transitorio / no evaluable).

---

## 5) Aplicación de capas (cómo usar la arquitectura en la práctica)
Para no perder tiempo, usa las capas como “checkpoints”:

- **Capa 2 (Incentivos):** ¿qué se recompensa de verdad?
- **Capa 1 (Humana):** ¿qué sesgos están dominando el marco?
- **Capa 3 (Sistémica):** ¿estabilidad a medio/largo plazo mejora o empeora?
- **Capa 5 (Histórica):** ¿es un patrón que falla recurrentemente?
- **Capa 4 (Preventiva):** ¿qué intervención mínima evita el modo de fallo?
- **Capa 0 (Núcleo):** ¿pasa el criterio supremo?

---

## 6) Meta-learning (iteración)
Después de cada simulación:
- Identifica el “parche mínimo viable”.
- Aplica cambios priorizados al escenario/plantilla.
- Repite el escenario o crea una variante.

Documento guía:
- [v1_core/workflow/es/05_meta_learning.md](../../workflow/es/05_meta_learning.md)

---

## 7) Artefactos de salida (qué guardar)
- borrador final de acuerdo,
- puntos abiertos,
- métricas (0–5) con evidencia,
- cambios recomendados (priorizados),
- versión del escenario (incrementa vX.Y).

---

## 8) Enlaces internos
- Declaración base (ES): [./01_base_declaracion.md](./01_base_declaracion.md)
- Arquitectura base (ES): [./02_arquitectura_base.md](./02_arquitectura_base.md)
- Workflow (ES): [../../workflow/es/README.md](../../workflow/es/README.md)
- Plantilla de escenario (ES): [../../workflow/es/04_scenario_template.md](../../workflow/es/04_scenario_template.md)
- Meta-learning (ES): [../../workflow/es/05_meta_learning.md](../../workflow/es/05_meta_learning.md)
