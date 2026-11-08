# Decisiones antes del primer servicio compartido

Estado: código candidato y propuesta inerte, sin autorización económica ni recursos identificados. La revisión de código no autoriza facturación ni exposición pública. #2079 sigue siendo la coordinación; #2062 conserva su aceptación Web separada.

| Decisión | Propuesta concreta | Evidencia que falta para pasar |
| --- | --- | --- |
| Alcance inicial | Piloto por invitación sobre ocho resúmenes españoles, sin Web general | Aceptar cobertura, personas invitadas, responsable de datos y consultas de aceptación |
| Hosting | ACA Consumption 0,25 vCPU/0,5 GiB, revisión única, min0/max1 | Confirmar arranque en frío aceptable o capacidad de App Service ya pagada |
| Cuenta y emplazamiento | No seleccionar automáticamente | tenantId, subscriptionId, grupo de recursos exacto y dedicado/compartido, región y nombre de recursos |
| Permisos | Principal de despliegue limitado al alcance aprobado | Identidad efectiva, roles/denegaciones, permisos reales, políticas/cuotas; revisión separada de registros de proveedor o RBAC si hacen falta |
| Economía | Presupuesto con revisión y cierre manual definido | Oferta, divisa, impuestos, créditos/caducidad, franquicia restante, tarifas regionales, forecast normal y adverso, importe mensual y responsable de alertas/cierre |
| Credenciales | Bearer remoto individual de siete días como máximo para piloto | Aceptación del modelo de invitación, emisión/distribución privada, montaje externo de solo lectura, acceso UID1654, prueba de revocación tras reinicio |
| Identidad futura | Entra/OIDC si se requiere alta de usuarios/SSO o escala pública | Tenant/audience/issuer/scopes, registro y políticas autorizados; no existen en este candidato |
| Imágenes | Digest inmutable de bases SDK/runtime y de aplicación | Procedencia/firma/SBOM/escaneo según política, registro autorizado y acceso pull, build y prueba real en contenedor |
| Exposición | HTTPS con certificado normal en ingress; HTTP8080 solo interno | Aprobar origen, cambiar ingress interno mediante diff separado, probar certificado, redirecciones, acceso directo bloqueado y privacidad de plataforma |
| Privacidad | No conservar consultas ni tokens; sin destino de logs de app | Revisar políticas heredadas, diagnósticos, metadatos de plataforma, accesos y retención; acordar política operativa |
| Coste de abuso | Límites locales y capacidad acotada, sin garantía monetaria | Aceptar exposición residual o costear gateway/WAF/cuotas distribuidas por separado |
| Clientes | Adaptador remoto HTTP/JSON independiente | Pruebas Windows, Linux y Android contra origen HTTPS; consentimiento/selección explícita y almacenamiento seguro de credencial |
| Cambio de versión | Catálogo y código por imagen revisada, sin importación remota | Digest anterior, catálogo correspondiente, registro de credenciales vigente y ensayo de rollback sin recuperar secretos revocados |

Secuencia posterior: completar el manifiesto de promoción; revisar el diff exacto; validar políticas/cuotas/schema y what-if en el alcance autorizado; desplegar solo tras autorización; medir cold start, p95/p99, CPU/RAM, auth, abuso, privacidad y coste; probar clientes nativos; invitar al piloto después de aceptación. No usar resultados locales para afirmar que Azure o los clientes están validados.

Criterios sugeridos que deben ratificarse: consultas representativas del corpus con URL/procedencia correctas, vacío real sin fallback, rechazo de credenciales inválidas/caducadas, límites comprobados en el servicio real, ausencia de datos sintéticos en logs revisables, cierre confirmado y rollback al digest aceptado. La latencia y el presupuesto se fijarán numéricamente antes de activar, tras acordar el compromiso de arranque en frío.
