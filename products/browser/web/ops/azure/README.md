# Destino Azure preparado, no desplegado

La aplicación es estática y portable. La plantilla ARM `azuredeploy.json` propone solo `Microsoft.Web/staticSites` con SKU `Free` y sin API, almacenamiento, identidad, repositorio conectado, secretos, dominio, CDN empresarial o servicio de voz.

No se ha ejecutado una validación del proveedor ni una implementación Azure en este entorno; no hay Azure CLI o identidad conectada disponible. La comprobación local es sintáctica JSON y revisión de alcance, no una certificación de disponibilidad del nombre, región, elegibilidad o coste de una suscripción concreta.

Antes de usarla:

1. Comprobar entidad contratante, suscripción, permisos y condiciones económicas reales.
2. Elegir grupo de recursos y revisar `what-if`/validación con una identidad autorizada.
3. Mantener SKU Free y comprobar sus cuotas; no habilitar planes o servicios adicionales por comodidad.
4. Publicar `dist/` con el mecanismo de despliegue elegido y conservar cualquier credencial de publicación fuera del código.
5. Revisar origen, TLS, cabeceras, rutas, accesibilidad y consultas/voz desde dispositivos reales.

El recurso Free tiene límites y carece de SLA de producción. Un presupuesto Azure informa del consumo; por sí solo no detiene recursos ni cargos. Los programas de créditos pueden caducar o convertirse a pago por uso. Esta preparación no acepta esas condiciones ni suscribe el proyecto.

Referencias oficiales consultadas el 30 de octubre de 2026:

- https://learn.microsoft.com/en-us/azure/templates/microsoft.web/staticsites
- https://learn.microsoft.com/en-us/azure/static-web-apps/plans
- https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets

`dist/staticwebapp.config.json` configura cabeceras estáticas para Azure. No autentica usuarios ni cambia el acceso privado de la vista de aceptación en otra plataforma.
