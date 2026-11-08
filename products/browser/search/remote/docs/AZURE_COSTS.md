# Azure: comparación y costes del piloto — 4 de noviembre de 2026

Recomendación técnica: Container Apps Consumption para demanda intermitente, condicionada a medir arranque en frío y consumo real. No es una selección económica autorizada ni un despliegue. App Service es una alternativa válida si existe un plan pagado con capacidad libre o se exige latencia caliente estable. La Static Web App Free actual no ejecuta esta API.

| Requisito | Container Apps Consumption | App Service |
| --- | --- | --- |
| Proceso ASP.NET Core separado | Contenedor Linux amd64 con .NET, ingress TLS | Runtime .NET compatible en plan/OS elegido, o contenedor |
| Demanda mínima | minReplicas=0 puede llegar a cero; primera consulta puede arrancar réplica | Un plan dedicado mantiene instancias asignadas; Always On depende del nivel |
| Facturación principal | vCPU-segundo, GiB-segundo y solicitudes HTTP externas al entorno | Tarifa del SKU/OS/región por instancia asignada y tiempo |
| Piloto propuesto | 0,25 vCPU, 0,5 GiB, una revisión activa, min0/max1, sujeto a medida | Un plan nuevo dedicado introduce coste fijo; evaluar capacidad existente |
| Cuota gratuita | Franquicias mensuales compartidas por suscripción; no reservadas a Optimus | Free/Shared sirven para ensayos con límites; no tratarlos como plan productivo garantizado |
| Apagado | Cero réplicas elimina cómputo de réplicas; otros recursos pueden seguir cobrando | Detener/quitar la aplicación no elimina el coste del plan dedicado |
| Portabilidad | Mismo contenedor y HTTP/JSON | Mismo contrato; el contenedor puede reutilizarse si el nivel lo admite |

## Modelo de coste para completar antes de autorizar

No se citan importes EUR no verificados. Faltan suscripción/oferta, región, divisa contractual, impuestos, créditos y uso de franquicias por otros servicios. Obtener una estimación oficial fechada para el alcance exacto, con escenario normal y escenario de tráfico abusivo continuo.

Franquicia documentada Consumption por mes natural y suscripción: 180.000 vCPU-s, 360.000 GiB-s y 2.000.000 solicitudes. No sumar estas cantidades por aplicación. Cómputo activo: 0,25 × segundos activos de réplica y 0,5 × segundos activos. Réplicas mínimas activas y determinadas condiciones de inactividad tienen reglas de tarifa diferentes. Lo siguiente es un escenario exclusivamente ACTIVO, sin otras aplicaciones consumiendo franquicia, no una previsión de uso real ni de factura:

| Horas activas/mes | vCPU-s | GiB-s | vCPU-s fuera de franquicia | GiB-s fuera de franquicia |
| --- | ---: | ---: | ---: | ---: |
| 10 | 9.000 | 18.000 | 0 | 0 |
| 100 | 90.000 | 180.000 | 0 | 0 |
| 720 (30 días continuos) | 648.000 | 1.296.000 | 468.000 | 936.000 |

Coste total = cómputo activo/inactivo facturable + solicitudes facturables + registro de imágenes + tráfico saliente/interregional + telemetría/retención/exportación + almacenamiento/operaciones + red/seguridad seleccionada + dominios/certificados de pago + impuestos aplicables. En App Service sustituir cómputo/solicitudes del modelo ACA por las instancias del plan y sus condiciones.

| Componente | Decisión propuesta del piloto | Dato económico pendiente |
| --- | --- | --- |
| Cómputo y solicitudes | Consumption pequeño, escala0..1 | Tarifas de región/oferta; franquicia restante; solicitudes y segundos por arranque |
| Imagen | Imagen por digest en registro autorizado existente | ACR SKU/almacenamiento/transferencias si se elige; no crear ACR por defecto |
| Catálogo | Ocho documentos embebidos e inmutables en imagen | No añadir Blob/AI Search ni disco persistente en este incremento |
| Registro de actividad | Sin destino de logs de app ni HTTP ingress logs | Si luego se habilitan: ingestión, retención, exportación y datos personales |
| Red | Sin VNet propia/NAT/private endpoint/gateway de pago por defecto | Salida de Internet/interregional; cada componente opcional tiene tarifa propia |
| Identidad/secretos | Registro privado de hashes; mecanismo de montaje pendiente | Costear Key Vault u otro mecanismo si se selecciona; no activar por inferencia |
| Protección de abuso global | Límites locales con cuatro solicitudes simultáneas | Gateway/WAF/contador distribuido sería otra decisión y puede tener coste fijo |
| Dominio | Host Azure cuando se autorice exposición | No comprar dominio/certificado; registrar si hay componente de pago |

maxReplicas=1 reduce escalado ordinario, pero Microsoft documenta réplicas adicionales temporales durante mantenimiento. Reinicios y solapamientos reinician/multiplican contadores locales. Las peticiones rechazadas pueden haber consumido red/plataforma antes de llegar a la aplicación. No existe un techo monetario estricto derivado del rate limit.

Los presupuestos de Azure envían avisos: no detienen recursos ni consumo. Los datos de coste llegan con retraso. Un spending limit basado en crédito no está disponible en todas las ofertas; no inferirlo de una cuenta de pago por uso. Definir responsable, avisos, umbral de revisión y procedimiento de cierre; no automatizar borrados sin autorización.

## Fuentes oficiales consultadas

- [Facturación Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/billing): medidores, franquicias, cero réplicas, condiciones adicionales.
- [Escalado](https://learn.microsoft.com/en-us/azure/container-apps/scale-app): min/max y solapamiento temporal en mantenimiento.
- [Arranque en frío](https://learn.microsoft.com/en-us/azure/container-apps/cold-start): contraparte de escala a cero.
- [Costes App Service](https://learn.microsoft.com/en-us/azure/app-service/overview-manage-costs): instancias, plan sin apps y costes asociados.
- [Planes App Service](https://learn.microsoft.com/en-us/azure/app-service/overview-hosting-plans): capacidades por nivel.
- [Precios App Service](https://azure.microsoft.com/en-us/pricing/details/app-service/windows/): límites de Free/Shared y aplicación detenida.
- [Registro de imágenes](https://azure.microsoft.com/en-us/pricing/details/container-registry/) y [ancho de banda](https://azure.microsoft.com/en-us/pricing/details/bandwidth/).
- [Costes Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/cost-usage).
- [Opciones de logs](https://learn.microsoft.com/en-us/azure/container-apps/log-options) y [campos HTTP](https://learn.microsoft.com/en-us/azure/container-apps/log-monitoring). Desactivar destino no prueba ausencia de registros internos del proveedor.
- [Presupuestos](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets) y [spending limit](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit).

Las páginas oficiales son vivas. Actualizar precios y condiciones en la fecha de autorización efectiva.
