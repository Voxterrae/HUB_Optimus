# Operación técnica del piloto

Este documento define un alcance técnico propuesto. No asigna titularidad, participación, representación o derechos económicos, ni sustituye acuerdos societarios, laborales o de contribución. El documento privado de organización queda fuera de este repositorio y de los archivos públicos.

## Roles propuestos

| Función | Alcance |
|---|---|
| Dirección del producto | Objetivos, prioridad, aceptación y coordinación de tareas. |
| Operación técnica | Preparación y validación de cambios; propuesta de despliegue dentro del alcance aprobado. |
| Revisión | Comprobación independiente de código, evidencias y límites; no constituye autorización automática. |
| Colaboración | Encargo y acceso mínimos por módulo, con atribución y condiciones documentadas. |
| Administración de cuenta y gasto | Entidad y permisos efectivamente comprobados; contratación y consumo sujetos a las condiciones aplicables. |

No se crean roles en proveedores ni se modifican permisos mediante esta propuesta. Las reglas del repositorio HUB_Optimus y su decisión humana protegida siguen siendo aplicables.

## Separación de entornos

- Proyecto `optimus`, entorno `pilot`, centro de coste `optimus`.
- Recursos Azure propuestos bajo `rg-optimus-pilot` y etiquetas de proyecto, entorno y coste; todavía no creados.
- Mantener datos empresariales, contratos y expedientes fuera de la aplicación pública y de su repositorio.
- Cuentas de colaboradores individuales; no introducir claves, credenciales o datos personales en código, artefactos, URLs ni logs.
- No usar la ausencia de coste inicial, una alerta presupuestaria o un crédito como garantía de gasto cero permanente.

## Cambios que exigen aceptación específica

Revisar antes de activar: un proveedor de voz remoto; almacenamiento/sincronización de usuarios; permisos nuevos; publicación comercial; suscripción o conversión a pago por uso; identidad de la entidad contratante; licencias de aportaciones; emparejamiento o control de dispositivos. Nada de ello se activa por el piloto estático.

## Datos del piloto

No hay backend de usuario. El navegador envía búsquedas a los hosts Wikipedia permitidos solo tras una acción explícita. Preferencias y enlaces se guardan en una única clave de dispositivo solo si se elige recordarlos. No se guardan consultas, resultados, audio o transcripciones. Borrar los datos de la aplicación no elimina registros de proveedores ni historiales del navegador anfitrión.

El estado local no es un sistema de autenticación ni un almacén de secretos. Un dispositivo compartido requiere que la persona decida si recordar sus enlaces; el control permite volver al estado de sesión y solicitar el borrado de la clave propia.
