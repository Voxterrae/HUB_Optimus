# HUB_Optimus — Especificación técnica para respuesta inmediata ante incendios forestales en Catalunya

**Estado:** borrador técnico para generación asistida por GitHub Copilot  
**Fecha:** 2026-07-04  
**Ámbito:** arquitectura, integración de datos, GIS, IA, alertas, auditoría y apoyo a coordinación operativa.

> Este documento define una especificación técnica para construir módulos de apoyo a la decisión dentro de HUB_Optimus. No sustituye al mando oficial, a los protocolos públicos de emergencia ni a la cadena de decisión de Bombers, ADF, Protección Civil, Mossos, SEM u otros organismos competentes. Las alertas del sistema deben entenderse como señal operativa y evidencia técnica, no como órdenes automáticas.

---

## 1. Objetivo del documento

Definir los componentes técnicos, operativos y de integración necesarios para implementar en HUB_Optimus un sistema de apoyo a la actuación inmediata contra incendios forestales en Catalunya.

Este documento sirve como fuente para GitHub Copilot y herramientas de generación asistida para producir:

- Código backend en Node.js, Python, Go, Rust u otros lenguajes compatibles.
- Infraestructura como código mediante Terraform, Pulumi, Bicep, ARM o CloudFormation.
- Pipelines CI/CD.
- APIs REST, Webhooks y conectores MQTT.
- Dashboards GIS y paneles tácticos.
- Módulos IA para detección térmica, hotspots, predicción y mapas de calor.
- Automatización de alertas escalonadas.
- Documentación técnica y manuales de operador.
- Scripts de despliegue y validación.
- Reglas de seguridad, auditoría y trazabilidad.

---

## 2. Principios de diseño

1. **Apoyo a decisión, no sustitución del mando.**  
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

## 3. Arquitectura general

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
  - Umbral 2: alerta operativa.
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
  "notify_url": "https://huboptimus.example/api/satellite/callback",
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

## 5. Procesamiento IA

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

Salida esperada:

```json
{
  "incident_id": "CAT-FIRE-2026-0001",
  "model": "hotspot_detector_v1",
  "generated_at": "2026-07-04T09:20:00Z",
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
  ]
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
      "raster": "s3://huboptimus/fire/CAT-FIRE-2026-0001/prediction_30m.tif",
      "probability_threshold": 0.3
    },
    {
      "minutes": 60,
      "raster": "s3://huboptimus/fire/CAT-FIRE-2026-0001/prediction_60m.tif",
      "probability_threshold": 0.3
    },
    {
      "minutes": 120,
      "raster": "s3://huboptimus/fire/CAT-FIRE-2026-0001/prediction_120m.tif",
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

## 6. Alertas automáticas

Las alertas deben ser eventos auditables. El sistema puede notificar, priorizar y recomendar revisión, pero no debe ejecutar evacuaciones, cierres, despliegues ni órdenes tácticas sin validación humana.

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
  "requires_human_validation": true
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
  "requires_authorized_role": "incident_commander"
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

## 8. API REST propuesta

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

## 9. Dashboard táctico

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

## 10. Procedimiento operativo asistido

El sistema debe representar roles y tareas como objetos de coordinación, no como órdenes autónomas.

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

## 11. Modelo de datos mínimo

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
  "commander_role": "incident_commander"
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
  "uri": "s3://huboptimus/fire/CAT-FIRE-2026-0001/thermal_001.tif",
  "hash_sha256": "<sha256>",
  "created_at": "2026-07-04T09:15:00Z",
  "ingested_at": "2026-07-04T09:16:00Z"
}
```

---

## 12. Seguridad y auditoría

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

## 13. Monitorización

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

## 14. Checklist técnico de despliegue

```text
[ ] RTSP drones configurado sin credenciales en repositorio
[ ] RTSP cámaras térmicas configurado sin credenciales en repositorio
[ ] API satélite conectada mediante secretos seguros
[ ] MQTT sensores IoT recibiendo datos
[ ] Webhooks externos firmados y verificados
[ ] Carga manual GIS habilitada
[ ] IA genera mapas de calor
[ ] IA genera predicción de avance
[ ] Alertas Umbral 1/2/3 activas
[ ] Validación humana activa para umbrales 2 y 3
[ ] Dashboard operativo visible
[ ] Registro y auditoría activos
[ ] Exportación post-incidente disponible
[ ] Pruebas de fallo y degradación completadas
```

---

## 15. Pipeline CI/CD recomendado

```yaml
name: fire-response-ci

on:
  pull_request:
    paths:
      - "services/fire-response/**"
      - "docs/es/operational/fire-response-catalunya.md"
  push:
    branches:
      - main

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate JSON schemas
        run: npm run validate:schemas
      - name: Run unit tests
        run: npm test
      - name: Run security scan
        run: npm run security:scan
      - name: Validate OpenAPI
        run: npm run validate:openapi
```

---

## 16. Backlog inicial para Copilot

### 16.1 Backend

- Crear módulo `services/fire-response`.
- Crear modelos `Incident`, `Alert`, `Evidence`, `GISLayer`, `AIJob`.
- Crear endpoints REST definidos en este documento.
- Implementar validación de payloads con JSON Schema.
- Implementar auditoría por evento.
- Implementar conectores MQTT y webhook.

### 16.2 IA

- Crear interfaz común `AIModelRunner`.
- Implementar job runner para hotspots.
- Implementar job runner para segmentación térmica.
- Implementar job runner para predicción de avance.
- Guardar outputs con hash y metadata.

### 16.3 GIS

- Crear servicio de capas raster/vector.
- Exponer `map-state` por incidente.
- Implementar subida y validación de GeoJSON/GeoTIFF.
- Generar tiles para dashboard.

### 16.4 Dashboard

- Crear vista táctica por incidente.
- Añadir widgets de feed RTSP, mapa térmico, alertas y timeline.
- Añadir estado de fuentes y validación humana.

### 16.5 Seguridad

- Añadir RBAC.
- Añadir verificación de firma en webhooks.
- Añadir política de secretos.
- Añadir logs auditables.

---

## 17. Criterios de aceptación

El módulo se considerará listo para prueba controlada cuando:

1. Todas las fuentes simuladas puedan ingerirse sin credenciales reales.
2. El sistema genere un incidente y lo muestre en GIS.
3. El detector de hotspots produzca GeoJSON válido.
4. El predictor genere raster o placeholder verificable para 30, 60 y 120 minutos.
5. Las alertas se creen según reglas configuradas.
6. Las alertas operativas y críticas requieran validación humana.
7. El dashboard muestre mapa, fuentes, alertas y timeline.
8. Todos los eventos queden auditados.
9. Los tests automáticos cubran payloads, reglas, endpoints y permisos.
10. La documentación indique claramente que el sistema no sustituye al mando oficial.

---

## 18. Nota final para implementación

HUB_Optimus debe funcionar como una torre de control digital: recopila evidencia, estructura señales, muestra escenarios y ayuda a coordinar. La autoridad, la responsabilidad y la decisión final siguen siendo humanas y oficiales.

La misión técnica es reducir ruido, acelerar lectura de situación y evitar que información crítica quede enterrada entre mapas, chats, llamadas, hojas sueltas y esa maravillosa costumbre humana de improvisar sistemas durante una emergencia.