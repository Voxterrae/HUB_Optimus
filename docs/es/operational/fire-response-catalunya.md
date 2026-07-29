# HUB_Optimus — Borrador conceptual sobre apoyo ante incendios forestales en Catalunya

- **Estado:** exploración técnica documental; no implementada ni autorizada para uso operativo
- **Fecha:** 2026-07-04
- **Ámbito:** propuesta conceptual sobre datos, GIS, IA, alertas, auditoría y apoyo a la decisión

> **Límite vinculante:** este documento no describe una capacidad implementada,
> desplegada, probada ni autorizada de HUB_Optimus. No es un plan de respuesta,
> un manual de operador, una integración con servicios de emergencia ni una
> instrucción para actuar durante una emergencia real. No sustituye al mando
> oficial, a los protocolos públicos ni a ninguna autoridad competente.

---

## 0. Límite de autoridad e implementación

En el repositorio no existe evidencia de un módulo de respuesta a incendios,
una API de emergencias, conectores con organismos públicos, modelos de
predicción de incendios, alertas operativas, un dashboard táctico ni un
despliegue de esta propuesta. Los ejemplos posteriores son formas conceptuales
para revisión; no son contratos de implementación, configuración ejecutable,
endpoints disponibles ni prueba de preparación para producción.

Este documento no autoriza:

- generar o fusionar código, infraestructura como código, workflows de CI/CD
  ni scripts de despliegue;
- construir dashboards, conectores, modelos de IA, alertas, reglas de
  prioridad, despacho o coordinación operativa;
- usar datos, canales, nombres, credenciales, endpoints o procedimientos de
  servicios de emergencia reales;
- presentar una salida de HUB_Optimus como orden, aviso oficial, predicción
  validada o recomendación operativa.

Cualquier trabajo futuro sobre esas superficies requiere un nuevo issue con
alcance propio, un RFC aprobado antes de implementar y revisión y autorización
humanas explícitas de los responsables del repositorio. Esto incluye cualquier
backlog propuesto para GitHub Copilot u otra herramienta de IA. Ninguna revisión
de GitHub sustituye la autorización, validación profesional ni responsabilidad
de las autoridades públicas competentes para un uso real.

Las herramientas de IA, incluido GitHub Copilot, no pueden interpretar este
documento como backlog, orden de implementación ni permiso para abrir o
fusionar cambios. El issue #1685 autoriza únicamente corregir este límite
documental.

En las secciones siguientes, expresiones como «debe», «salida esperada» o
«requisito» describen condiciones hipotéticas que una futura propuesta tendría
que someter a revisión. No afirman comportamiento actual ni crean un compromiso
de implementación.

---

## 1. Objetivo del documento

Conservar, para revisión crítica, una posible descomposición técnica de apoyo a
la decisión ante incendios forestales. La descomposición permite detectar
riesgos, dependencias y límites antes de decidir si corresponde formular un
RFC. No especifica una solución aprobada.

Las superficies mencionadas a continuación son asuntos que una futura decisión
podría estudiar, no entregables ni tareas autorizadas:

- límites de una eventual API, ingesta o integración de datos;
- representación GIS y revisión humana de señales;
- evaluación de modelos hipotéticos y de su incertidumbre;
- controles de seguridad, privacidad, auditoría y trazabilidad;
- condiciones de autoridad necesarias antes de cualquier prueba o despliegue.

---

## 2. Principios de diseño

1. **Apoyo a la decisión, no sustitución del mando.**  
   HUB_Optimus debe generar señales verificables, no órdenes autónomas.

2. **Human-in-the-loop obligatorio.**  
   Toda alerta crítica, evacuación, despliegue o cambio de prioridad requiere validación humana autorizada.

3. **Trazabilidad total.**  
   Cada dato, alerta, modelo, decisión sugerida y modificación de estado debe quedar registrado.

4. **Interoperabilidad.**  
   Los módulos deben usar formatos estándar: GeoJSON, COG, GeoTIFF, MQTT, JSON, OpenAPI y logs estructurados.

5. **Seguridad por defecto.**  
   Nada de credenciales en repositorio. Todo secreto debe ir por vault o gestor seguro de secretos.

6. **Degradación controlada.**  
   Si falla la IA, el sistema debe seguir mostrando datos brutos, capas GIS y comunicaciones esenciales.

---

## 3. Arquitectura conceptual no implementada

### 3.1 Componentes principales

- **Ingesta de datos**
  - Drones por RTSP/RTMP.
  - Cámaras térmicas por RTSP.
  - API satélite para GeoTIFF, COG, NDVI, térmico y true color.
  - Sensores IoT por MQTT/HTTP.
  - Webhooks externos.
  - Carga manual de GeoJSON, GeoTIFF y COG.

- **Procesamiento IA**
  - Detección de hotspots.
  - Segmentación térmica.
  - Clasificación de riesgo por píxel.
  - Predicción de avance del incendio.
  - Generación de mapas de calor.
  - Proyección de frente a 30, 60 y 120 minutos.

- **GIS y visualización**
  - Capas raster: satélite, térmico, IA, predicción.
  - Capas vector: hotspots, frentes, rutas, puntos de agua, zonas de evacuación.
  - Dashboard táctico.
  - Panel de mando unificado.

- **Alertas automáticas**
  - Umbral 1: alerta temprana.
  - Umbral 2: alerta operativa con validación humana obligatoria.
  - Umbral 3: alerta crítica con validación humana obligatoria.

- **Coordinación operativa asistida**
  - Bombers.
  - ADF.
  - Protección Civil.
  - Mossos.
  - SEM.
  - Mando Unificado.

---

## 4. Ingesta de datos

Los payloads de esta sección son sintéticos y no operativos. Los hostnames
reservados o locales y los placeholders no identifican integraciones
disponibles. No deben sustituirse por datos o accesos reales sin un alcance
posterior aprobado y la autoridad competente.

### 4.1 Drones RTSP

No usar credenciales reales en ejemplos, commits, issues ni documentación pública. Los valores deben resolverse mediante variables de entorno o gestor de secretos.

```json
{
  "name": "DronTactico1",
  "type": "rtsp",
  "url": "rtsp://<user>:<password>@<host>:554/live",
  "metadata": {
    "platform": "DJI Matrice",
    "sensor": "FLIR",
    "operator": "Bombers Sector 3",
    "zone": "sector-3"
  }
}
```

Variables recomendadas:

```bash
DRONE_TACTICO_1_RTSP_URL="rtsp://<user>:<password>@<host>:554/live"
DRONE_TACTICO_1_OPERATOR="Bombers Sector 3"
```

### 4.2 Cámaras térmicas RTSP

```json
{
  "name": "TorreTermicaA01",
  "type": "rtsp",
  "url": "rtsp://<user>:<password>@<host>:554/stream1",
  "thermal_threshold_celsius": 55,
  "zone": "zone-a"
}
```

### 4.3 Satélite API

```json
{
  "provider": "satellite_provider",
  "endpoint": "https://api.satelliteprovider.example/v1/tasks",
  "products": ["thermal", "ndvi", "true_color"],
  "notify_url": "https://huboptimus.example/api/ingest/satellite/callback",
  "output_format": ["COG", "GeoTIFF"],
  "priority": "emergency"
}
```

### 4.4 Sensores IoT MQTT

```json
{
  "broker": "mqtt.huboptimus.local",
  "topic": "sensors/zoneA/node12",
  "payload": {
    "device_id": "node12",
    "timestamp": "2026-07-04T09:15:00Z",
    "lat": 41.7000,
    "lon": 2.8500,
    "temperature_celsius": 48.3,
    "humidity_percent": 12,
    "smoke_density": 0.02,
    "battery_percent": 87
  }
}
```

### 4.5 Webhooks externos

```json
{
  "source": "external_provider",
  "type": "hotspot",
  "lat": 41.7023,
  "lon": 2.8521,
  "confidence": 0.87,
  "timestamp": "2026-07-04T09:12:00Z",
  "image_url": "https://provider.example/images/12345.jpg",
  "evidence_id": "provider-12345"
}
```

### 4.6 Carga manual de archivos GIS

Formatos aceptados:

```json
{
  "accepted_formats": ["GeoJSON", "GeoTIFF", "COG", "KML", "CSV"],
  "max_file_size_mb": 2048,
  "required_metadata": ["source", "timestamp", "crs", "uploaded_by", "incident_id"]
}
```

---

## 5. Procesamiento IA hipotético

### 5.1 Detección de hotspots

```json
{
  "model": "hotspot_detector_v1",
  "input": "thermal_geotiff",
  "output": "geojson_points",
  "params": {
    "confidence_threshold": 0.6,
    "min_area_m2": 5,
    "temperature_floor_celsius": 45
  }
}
```

Salida conceptual. El repositorio no genera actualmente este objeto:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [2.8521, 41.7023]
      },
      "properties": {
        "confidence": 0.87,
        "temperature_celsius": 63.2,
        "source": "thermal_geotiff",
        "evidence_id": "thermal-tile-001"
      }
    }
  ],
  "metadata": {
    "incident_id": "CAT-FIRE-2026-0001",
    "model": "hotspot_detector_v1",
    "generated_at": "2026-07-04T09:20:00Z"
  }
}
```

### 5.2 Segmentación térmica

```json
{
  "model": "thermal_segmentation_v1",
  "inputs": ["thermal_raster", "true_color", "ndvi"],
  "output": "burning_area_polygon",
  "params": {
    "min_temperature_celsius": 50,
    "min_polygon_area_m2": 10,
    "smooth_geometry": true
  }
}
```

### 5.3 Predicción de avance

```json
{
  "model": "fire_spread_predictor_v2",
  "inputs": ["thermal", "wind", "topography", "ndvi", "fuel_model", "humidity"],
  "output": "raster_probability",
  "params": {
    "time_horizon_minutes": [30, 60, 120],
    "probability_threshold": 0.3,
    "uncertainty_output": true
  }
}
```

Salida esperada:

```json
{
  "incident_id": "CAT-FIRE-2026-0001",
  "model": "fire_spread_predictor_v2",
  "generated_at": "2026-07-04T09:25:00Z",
  "horizons": [
    {
      "minutes": 30,
      "raster": "s3://<illustrative-bucket>/fire/CAT-FIRE-2026-0001/prediction_30m.tif",
      "probability_threshold": 0.3
    },
    {
      "minutes": 60,
      "raster": "s3://<illustrative-bucket>/fire/CAT-FIRE-2026-0001/prediction_60m.tif",
      "probability_threshold": 0.3
    },
    {
      "minutes": 120,
      "raster": "s3://<illustrative-bucket>/fire/CAT-FIRE-2026-0001/prediction_120m.tif",
      "probability_threshold": 0.3
    }
  ],
  "uncertainty": "medium"
}
```

### 5.4 Clasificación de riesgo por píxel

```json
{
  "model": "pixel_risk_classifier_v1",
  "inputs": ["thermal", "ndvi", "slope", "wind", "distance_to_urban_area", "distance_to_water_point"],
  "output": "risk_class_raster",
  "classes": ["low", "medium", "high", "critical"]
}
```

---

## 6. Esquemas ilustrativos de alertas no ejecutables

Estos bloques son pseudopayloads para revisar límites. No corresponden a un
schema, regla, canal ni integración implementados. Las cadenas de `actions` no
invocan servicios reales. Una futura propuesta solo podría notificar, priorizar
o recomendar revisión bajo la autorización correspondiente; nunca ejecutar
evacuaciones, cierres, despliegues ni órdenes tácticas. Toda alerta operativa,
cambio de prioridad o acción crítica requeriría validación de una persona con
un rol autorizado por la autoridad competente.

### 6.1 Umbral 1 — Alerta temprana

```json
{
  "rule": "hotspot_detected",
  "severity": "early_warning",
  "conditions": {
    "confidence": { "gte": 0.6 },
    "temperature_celsius": { "gte": 45 }
  },
  "actions": [
    "notify_adf_channel",
    "create_incident_evidence_record",
    "add_hotspot_to_gis_layer"
  ],
  "requires_human_validation": false
}
```

### 6.2 Umbral 2 — Alerta operativa

```json
{
  "rule": "spread_prediction",
  "severity": "operational",
  "conditions": {
    "probability": { "gte": 0.3 },
    "towards_critical_zone": true
  },
  "actions": [
    "notify_bombers_channel",
    "request_drone_reconnaissance_review",
    "prioritize_dashboard_sector",
    "create_mando_unificado_task"
  ],
  "requires_human_validation": true,
  "requires_authorized_role": true,
  "role_authority": "competent_public_authority"
}
```

### 6.3 Umbral 3 — Alerta crítica

```json
{
  "rule": "critical_spread",
  "severity": "critical",
  "conditions": {
    "distance_to_urban_area_meters": { "lte": 500 },
    "spread_speed_meters_per_minute": { "gte": 10 },
    "confidence": { "gte": 0.75 }
  },
  "actions": [
    "notify_mando_unificado",
    "notify_proteccion_civil_channel",
    "recommend_evacuation_review",
    "lock_incident_timeline_for_audit"
  ],
  "requires_human_validation": true,
  "requires_authorized_role": true,
  "role_authority": "competent_public_authority"
}
```

---

## 7. Capas GIS

### 7.1 Raster

```json
[
  "satellite_true_color",
  "satellite_thermal",
  "ia_heatmap",
  "ia_probability_raster",
  "risk_class_raster",
  "topography_slope",
  "fuel_model"
]
```

### 7.2 Vector

```json
[
  "hotspots",
  "front_projection",
  "routes",
  "water_points",
  "evacuation_zones",
  "restricted_access_points",
  "resource_positions",
  "critical_infrastructure"
]
```

### 7.3 Esquema GeoJSON para hotspots

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [2.8521, 41.7023]
      },
      "properties": {
        "incident_id": "CAT-FIRE-2026-0001",
        "confidence": 0.87,
        "temperature_celsius": 63.2,
        "source": "drone_thermal",
        "timestamp": "2026-07-04T09:20:00Z",
        "status": "active"
      }
    }
  ]
}
```

---

## 8. API REST conceptual no implementada ni autorizada

### 8.1 Incidentes

```http
POST /api/incidents
GET /api/incidents/{incident_id}
PATCH /api/incidents/{incident_id}
GET /api/incidents/{incident_id}/timeline
```

### 8.2 Ingesta

```http
POST /api/ingest/drone
POST /api/ingest/thermal-camera
POST /api/ingest/satellite/callback
POST /api/ingest/iot
POST /api/ingest/webhook
POST /api/ingest/gis-file
```

### 8.3 IA

```http
POST /api/ai/hotspots/run
POST /api/ai/thermal-segmentation/run
POST /api/ai/spread-prediction/run
GET /api/ai/jobs/{job_id}
GET /api/ai/jobs/{job_id}/outputs
```

### 8.4 Alertas

```http
POST /api/alerts/evaluate
GET /api/alerts
GET /api/alerts/{alert_id}
PATCH /api/alerts/{alert_id}/acknowledge
PATCH /api/alerts/{alert_id}/validate
```

### 8.5 GIS

```http
GET /api/gis/layers
GET /api/gis/layers/{layer_id}
POST /api/gis/layers/{layer_id}/features
GET /api/gis/incidents/{incident_id}/map-state
```

---

## 9. Dashboard conceptual no implementado ni autorizado

```json
{
  "dashboard": "operational_fire_dashboard",
  "widgets": [
    "rtsp_live_feed",
    "thermal_map",
    "hotspot_list",
    "prediction_timeline",
    "wind_indicator",
    "alert_panel",
    "resource_status",
    "evacuation_status",
    "incident_timeline",
    "audit_log"
  ]
}
```

### 9.1 Requisitos del dashboard

- Vista mapa con capas activables.
- Filtro por incidente, sector y nivel de alerta.
- Timeline de evidencias, modelos y decisiones.
- Panel de fuentes activas y fuentes caídas.
- Estado de drones, cámaras, satélite y sensores.
- Estado de validación humana para alertas operativas y críticas.
- Exportación de informe post-incidente.

---

## 10. Campos conceptuales para revisión de autoridad

Los campos siguientes no son un procedimiento operativo ni asignan funciones a
organismos reales. Solo muestran qué información podría someterse a revisión.
Una eventual representación de roles y tareas no podría convertirse en orden
autónoma ni atribuir autoridad a HUB_Optimus.

### 10.1 Bombers

Campos de seguimiento sugeridos:

- Estado del frente principal.
- Sectores activos.
- Recursos asignados.
- Prioridad de reconocimiento.
- Solicitudes de apoyo aéreo registradas por operador autorizado.
- Evolución térmica y predicción del frente.

### 10.2 ADF

Campos de seguimiento sugeridos:

- Vigilancia de flancos.
- Puntos de agua disponibles.
- Rutas de acceso.
- Estado de cortafuegos existentes.
- Incidencias logísticas.
- Vigilancia posterior durante 48 horas cuando proceda.

### 10.3 Protección Civil

Campos de seguimiento sugeridos:

- Infraestructuras sensibles.
- Zonas habitadas cercanas.
- Estado de comunicaciones públicas.
- Recomendaciones pendientes de validación.
- Registro de avisos emitidos por autoridad competente.

### 10.4 Mossos

Campos de seguimiento sugeridos:

- Control de accesos.
- Perímetros de seguridad.
- Cortes de vía registrados.
- Incidencias de seguridad.

### 10.5 SEM

Campos de seguimiento sugeridos:

- Puntos sanitarios.
- Rutas sanitarias.
- Recursos sanitarios disponibles.
- Incidencias médicas registradas.

---

## 11. Modelo de datos ilustrativo no implementado

### 11.1 Incident

```json
{
  "incident_id": "CAT-FIRE-2026-0001",
  "name": "Incendio forestal sector A",
  "status": "active",
  "created_at": "2026-07-04T09:00:00Z",
  "updated_at": "2026-07-04T09:25:00Z",
  "location": {
    "lat": 41.7000,
    "lon": 2.8500,
    "municipality": "example"
  },
  "severity": "operational",
  "commander_role": "<authority-defined-role>"
}
```

### 11.2 Alert

```json
{
  "alert_id": "alert-0001",
  "incident_id": "CAT-FIRE-2026-0001",
  "severity": "operational",
  "rule": "spread_prediction",
  "status": "pending_validation",
  "created_at": "2026-07-04T09:26:00Z",
  "evidence_ids": ["thermal-tile-001", "prediction-job-001"],
  "requires_human_validation": true,
  "validated_by": null,
  "validated_at": null
}
```

### 11.3 Evidence

```json
{
  "evidence_id": "thermal-tile-001",
  "incident_id": "CAT-FIRE-2026-0001",
  "source": "drone_thermal",
  "type": "thermal_geotiff",
  "uri": "s3://<illustrative-bucket>/fire/CAT-FIRE-2026-0001/thermal_001.tif",
  "hash_sha256": "<sha256>",
  "created_at": "2026-07-04T09:15:00Z",
  "ingested_at": "2026-07-04T09:16:00Z"
}
```

---

## 12. Controles hipotéticos para evaluación futura

### 12.1 Requisitos mínimos

- TLS obligatorio para toda comunicación externa.
- MFA obligatorio para operadores humanos.
- Autenticación por roles.
- Separación de permisos entre lectura, validación, administración y auditoría.
- Gestión de secretos mediante vault o servicio equivalente.
- Logs firmados o con hash encadenado.
- Retención mínima configurable, con valor inicial de 30 días.
- Exportación post-incidente.
- Registro de cambios de configuración.

### 12.2 Eventos auditables

```json
[
  "incident_created",
  "data_ingested",
  "ai_job_started",
  "ai_job_completed",
  "alert_created",
  "alert_acknowledged",
  "alert_validated",
  "alert_dismissed",
  "gis_layer_updated",
  "operator_note_added",
  "configuration_changed"
]
```

### 12.3 Política de secretos

```yaml
secrets_policy:
  repository_secrets: forbidden
  env_files_in_repo: forbidden
  local_dev_env_template: allowed
  runtime_secret_manager: required
  rotation_days: 90
```

---

## 13. Métricas conceptuales no implementadas

Métricas mínimas:

```json
[
  "ingestion_latency_ms",
  "ai_job_duration_ms",
  "active_data_sources",
  "failed_data_sources",
  "alerts_created_total",
  "alerts_pending_validation",
  "gis_layer_update_latency_ms",
  "dashboard_active_users",
  "mqtt_messages_per_minute",
  "rtsp_stream_health"
]
```

Alertas técnicas:

```json
[
  "rtsp_stream_down",
  "mqtt_broker_unreachable",
  "satellite_callback_failed",
  "ai_job_failed",
  "gis_tile_generation_failed",
  "audit_log_write_failed",
  "dashboard_unavailable"
]
```

---

## 14. Gate previo a cualquier trabajo futuro

No hay checklist de despliegue, pipeline recomendado ni backlog activo para esta
propuesta. Las superficies siguientes permanecen cerradas hasta que exista una
decisión nueva, trazable y revisada:

| Superficie conceptual | Estado actual | Gate mínimo antes de trabajar |
| --- | --- | --- |
| Código, API, conectores y modelos de IA | No implementados ni autorizados | Issue separado, RFC aprobado, alcance verificable y autorización humana |
| Infraestructura como código, CI/CD y despliegue | No implementados ni autorizados | Issue separado, RFC aprobado, threat model, revisión de secretos y autorización humana |
| Dashboard, GIS y monitorización | No implementados ni autorizados | Issue separado, RFC aprobado, revisión de privacidad y validación de usuarios responsables |
| Backlog para Copilot u otra herramienta de IA | No existe ni está autorizado | Issue separado, RFC aprobado y backlog redactado y autorizado explícitamente por responsables humanos |
| Alertas, prioridades, avisos y coordinación | No implementados ni autorizados | Issue separado, RFC aprobado, autoridad pública competente, protocolo oficial, roles humanos autorizados y validación profesional de seguridad |
| Prueba con datos o canales reales | No autorizada | Issue separado, RFC aprobado, base legal, minimización de datos, procedencia, seguridad y aprobación explícita de la autoridad responsable |

Un futuro issue y su RFC aprobado deberán declarar de nuevo alcance, evidencia,
responsables, no-goals, pruebas y criterio de reversión. Ninguno puede heredar
autorización de este borrador.

---

## 15. Criterios de revisión de este borrador

Este documento solo puede describirse como una exploración controlada cuando:

1. declara que las superficies propuestas no están implementadas ni
   autorizadas;
2. mantiene ejemplos sintéticos, sin credenciales ni endpoints operativos;
3. separa una forma de datos ilustrativa de una capacidad ejecutable;
4. exige validación humana con rol autorizado para prioridades y acciones
   operativas o críticas;
5. no contiene un backlog, pipeline, checklist de despliegue ni permiso
   implícito para que una herramienta de IA produzca implementación;
6. mantiene toda decisión y responsabilidad de uso real en las autoridades
   públicas y profesionales competentes.

Cumplir estos criterios no valida la arquitectura, los modelos, los datos ni la
seguridad de un sistema real. Solo hace revisable el límite documental.
