# SCENARIO_SCHEMA (HUB_Optimus)

Este documento define la estructura formal de un escenario en HUB_Optimus.
Objetivo: que todas las simulaciones sean comparables, auditables y repetibles.

## Regla de oro
- Mantén los mismos campos, mismo orden, mismo significado en todos los idiomas.
- Lo que no esté definido aquí se considera GAP y debe marcarse explícitamente.

## Estructura obligatoria (recomendada v1)

### 0) Identificación del escenario
- ID (ej. SCN-003)
- Dominio
- Versión
- Fecha
- Evaluador(es)
- Nivel de confidencialidad

### 1) Desencadenante
Qué evento/decisión activa el análisis.

### 2) Contexto estructural
Condiciones de base: asimetrías, presiones, historial, dependencias, ventanas de corrección.

### 3) Análisis de incentivos (Capa 2)
- Conductas recompensadas / castigadas
- Riesgos de escalada
- Señales ("red flags")

### 4) Calibración humana (Capa 1)
- Sesgos probables
- Sensibilidad política
- Urgencia vs ruido
- Guía de encuadre

### 5) Evaluación sistémica (Capa 3)
Responde de forma explícita:
1. Reducción de riesgo futuro
2. Estabilidad medio/largo plazo
3. Alivio inmediato (si aplica)
4. Corrección de incentivos
5. Lock-in / bloqueo de correcciones

### 6) Patrón histórico (Capa 5)
- Coincidencia (sí/no/parcial)
- Modo de fallo recurrente (si existe)
- Nivel de advertencia

### 7) Coherencia del núcleo (Capa 0)
- ¿Alineado con criterio supremo?
- ¿Hay deriva/captura/coerción?
- Decisión: aprobado / rechazado / aprobado con condiciones

### 8) Opciones de mediación preventiva (Capa 4)
Opciones no coercitivas para mejorar estabilidad y verificabilidad.

### 9) Clasificación final
- Tipo de resultado: estabilizador / desestabilizador (enmascarado) / neutral / no evaluable
- Vector de riesgo primario
- Postura recomendada

### 10) Integración en memoria
Qué patrón se refuerza o qué "excepción positiva" se registra.

### 11) Notas / GAPs
Lista de cosas que faltan para evaluar mejor.
