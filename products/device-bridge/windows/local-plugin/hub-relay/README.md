# HUB_Relay — piloto local 0.2.0

Una operación MCP local: `hub_relay_windows_diagnostics`. Devuelve la versión
numérica de Windows y los bytes totales/libres de C:. Necesita un permiso temporal
de un solo uso; instalar el plugin no lo concede.

## Contrato local y permiso

El contrato local 0.2 admite sólo `{}` (lectura denegada) o
`{"permission":"<credencial temporal>"}`. No acepta rutas, comandos, dispositivos,
identidades ni indicadores de aprobación. Se retira la bandera de activación
permanente de 0.1. El resultado conserva el esquema
`hub-relay.local-windows-diagnostics.v0.1`, `biometricEnforced: false` y
`nativeProtocol: false`.

Un operador local, tras una autorización humana explícita y acotada, emite una
credencial aleatoria de 256 bits con vigencia máxima de 120 segundos. El emisor
es una utilidad local, no una herramienta MCP. Sólo se almacena su SHA-256,
operación fija, vigencia y consumo. Todas las instancias comparten una base fuera
de la caché de versiones. La transacción confirma el consumo **antes** del colector.
Un fallo posterior también gasta el permiso; no se devuelve ni se renueva
automáticamente. La concurrencia y los reinicios no habilitan otro uso.

La credencial es transferible: quien la posea puede consumir esa operación.
**No acredita identidad del chat, consentimiento criptográfico ni biometría.**
Se entrega sólo a la llamada autorizada; no se guarda en documentos, recibos,
argumentos de procesos, registros o GitHub. El cliente puede conservar los
argumentos y el resultado en su historial. No se emite otra credencial para
repetir automáticamente un resultado incierto.

El requisito del producto de autorizar desde el Xiaomi sigue vigente. La
excepción local supervisada está registrada en
[PR #2037](https://github.com/Voxterrae/HUB_Optimus/pull/2037#issuecomment-6561070445)
y su continuación en
[la aprobación recibida](https://github.com/Voxterrae/HUB_Optimus/pull/2037#issuecomment-6561326538).
No modifica el contrato nativo, T5/T6/T7, la inscripción ni la raíz del servicio.

## Persistencia y confianza

`PLUGIN_DATA/one-use` debe ser una carpeta local de Windows sin redirecciones,
con propietario y ACL restringidos a la cuenta operadora, SYSTEM y Administradores.
El despliegue prepara esa carpeta; el servidor no relaja permisos ni la crea.
El consumidor abre únicamente una base existente, sin crearla ni repararla.
La ausencia de estado, corrupción, bloqueo o fallo de permisos deniega la lectura.

`permissions.py issue` usa el mismo `PLUGIN_DATA/one-use` y entrega la credencial
sólo por stdout, para mantenerla en memoria. `--data-dir` es exclusivo del operador
local, nunca un argumento MCP. No se emiten permisos para comprobar la instalación.
El registro consumido se conserva; no se restaura una copia antigua de esa base.

El control de la misma cuenta de Windows, del administrador, del código o del
reloj queda fuera del modelo de este piloto. Las ACL no convierten este registro
en almacenamiento nativo protegido. El vencimiento depende del reloj local.
Se garantiza como máximo un intento del colector por permiso, no una respuesta
después de una caída.

## Instalación y validación

Python 3.10 o posterior ya instalado; sólo biblioteca estándar. Se actualiza por
el cliente oficial, sin editar su caché. `PLUGIN_DATA` debe resolver al mismo
directorio estable para emisor y servidor. Los procesos 0.1 anteriores siguen
denegando por defecto y no reciben una bandera de activación.

Desde la raíz del repositorio, sin instalar dependencias:

```powershell
python -I -B -m unittest discover -s products/device-bridge/windows/local-plugin/tests -v
python -I -B tools/check_mojibake.py products/device-bridge/windows/local-plugin
```

Las pruebas usan valores sintéticos y bases temporales. Los procesos de prueba
no obtienen diagnósticos reales. El ensayo autorizado debe acreditar por separado:
versión instalada, descubrimiento nativo, una lectura, reutilización denegada y
llamada vacía denegada. Ejecutar un script stdio no prueba integración en el chat.
Los recibos privados no contienen la credencial.

Transporte MCP `2025-06-18`:
[stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports),
[ciclo de conexión](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
y [herramientas](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).

## Límites y retirada

No permite archivos personales, terminal, ratón, teclado, ADB, firmware ni
administración remota. No usa RDC/Tailscale para leer, no abre puertos ni instala
servicios. Los valores son puntuales; el espacio puede cambiar después.
El único estado añadido es el registro de permisos. Un proceso abierto sin permiso
válido no puede leer Windows. Para detener el piloto basta no emitir permisos y
desactivar su registro en el cliente, sin eliminar otras aplicaciones o archivos.

Android continúa pendiente. ChatGPT web/móvil y otros clientes necesitan su propia
integración; esta entrega no acredita el canal remoto Windows–Xiaomi.
Entrega sobre PR #2037, relacionada con
[HUB_Optimus #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933).
No cambia titularidad, licencias o gobernanza ni incorpora código de RDC/Tailscale.