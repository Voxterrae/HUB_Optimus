# HUB_Optimus — Capa de Confianza (Trust Layer)

## Propósito
La Capa de Confianza define cómo HUB_Optimus evalúa **afirmaciones**, **compromisos** y **acuerdos** en términos de fiabilidad operativa.

No evalúa intención, moralidad ni legitimidad política.
Evalúa **verificabilidad**, **trazabilidad** y **confiabilidad estructural**.

## Principio Central
Un compromiso que no puede verificarse no debe considerarse fiable, independientemente de quién lo formule.

La confianza no se presupone.
La confianza se **construye mediante estructura**.

---

## Clases de Evidencia (A/B/C)
### Clase A — Compromisos Verificables (Alta confianza)
Características:
- Acciones o estados observables
- Verificación independiente posible
- Condiciones claras de éxito o fallo
- Hitos temporales definidos

Ejemplos:
- Acuerdos con mecanismos de inspección/supervisión
- Acciones auditables públicamente
- Pasos reversibles con monitorización

### Clase B — Compromisos Parcialmente Verificables (Confianza condicionada)
Características:
- Algunos componentes observables
- Alcance de verificación limitado
- Aplicación o cobertura ambigua

Ejemplos:
- Compromisos con informes pero sin verificación independiente
- Acciones condicionales sin consecuencias o reversión definidas

### Clase C — Afirmaciones No Verificables (Baja confianza)
Características:
- Sin verificación externa
- Dependientes de intención o buena fe
- Sin hitos medibles

Ejemplos:
- Garantías verbales
- Declaraciones de intención futura sin mecanismos

---

## Perfil de Confianza (cómo se estima la fiabilidad)
Para cada compromiso, HUB_Optimus genera un **Perfil de Confianza** con estas dimensiones:

1) **Verificabilidad**
- ¿Puede un actor independiente verificar la afirmación?

2) **Trazabilidad**
- ¿Existe un rastro auditable (quién/qué/cuándo/dónde)?

3) **Independencia**
- ¿La verificación es independiente del emisor?

4) **Cobertura**
- ¿La verificación cubre todo el compromiso o solo fragmentos?

5) **Recencia**
- ¿Qué tan actual es la evidencia frente a la ventana del compromiso?

6) **Reversibilidad**
- ¿Puede revertirse la acción si la verificación falla?

Un compromiso puede ser Clase A y aun así ser débil si la cobertura/independencia es pobre.

---

## Protocolo mínimo de verificación (MVP)
Un compromiso se considera “lo bastante fiable como para planificar” solo si incluye:
- Un **resultado observable claro**
- Un **calendario de hitos**
- Un **método de verificación definido**
- Una **vía de disputa** (qué ocurre si la verificación se cuestiona)

---

## Disputas y degradación (sin coerción)
HUB_Optimus no ejecuta ni impone resultados.
Impone **disciplina epistémica**:

- Si la verificación falla → la confianza cae.
- Si se bloquea la verificación → la confianza cae.
- Si la evidencia es parcial → la confianza queda condicionada.
- Si la evidencia es independiente y consistente → la confianza sube.

Esto crea presión por incentivos sin coerción.

---

## Regla anti-gaming
El “cumplimiento de papel” (reporting performativo sin verificación independiente) se trata como Clase B o C,
aunque se presente como Clase A.

---

## Puntos de integración
- Los escenarios deben referenciar evidencia usando: `governance/SCENARIO_SCHEMA.md`
- Las evaluaciones deben citar clase de evidencia + dimensiones del perfil usando: `governance/EVALUATION_STANDARD.md`
