# HUB_Relay — candidato de plugin local 0.1.0

**Estado: candidato de pruebas; lectura desactivada por defecto.**
Cualquier excepción temporal al requisito de autorizar desde el Xiaomi debe
ser explícita y acotada. Este paquete no la concede ni la presupone.

## Lo que implementa

Un servidor MCP local con una sola operación, `hub_relay_windows_diagnostics`,
sin argumentos. Al habilitar el perfil supervisado puede obtener exclusivamente:

- versión numérica de Windows: mayor, menor y compilación;
- bytes totales y libres de la unidad fija C:.

Usa la biblioteca estándar de Python, sin descargar dependencias ni ejecutar
PowerShell, Node, ADB, RDC o Tailscale. No enumera carpetas, abre documentos,
crea servicios, escribe resultados en disco ni abre puertos. Los resultados
son instantáneas; el espacio libre puede cambiar después de la lectura.
El cliente de IA puede conservar el resultado en su historial habitual.

El resultado tiene su propio identificador
`hub-relay.local-windows-diagnostics.v0.1` e indica que no aplica biometría ni
el protocolo nativo. No modifica `windows.runtime_inventory.v0_1`, su firma,
la resolución de claves vinculadas, el bootstrap o las reglas del servicio.

## Autorización y límites

Por defecto, la operación devuelve `LOCAL_PILOT_DISABLED` antes de consultar
Windows. Los argumentos MCP no pueden cambiar ese estado. El parámetro de
arranque `--local-supervised-diagnostics` existe para el perfil local que está
en revisión; **no se añade al manifiesto distribuido**.
No debe habilitarse por decisión del modelo. No es una prueba de autorización,
un factor biométrico ni una defensa frente a otro proceso de la misma cuenta.

El requisito vigente de aprobar las lecturas desde el Xiaomi se conserva para
el producto. La activación de este piloto necesita una excepción concreta y
registrada para esa lectura local supervisada y su sesión/vigencia. No se reutiliza la excepción
histórica de auditoría para autorizar un nuevo producto.

Este candidato no permite archivos, terminal, ratón, teclado, Android,
actualizaciones de firmware ni administración remota. La red privada propia,
el canal seguro Windows–Xiaomi, la inscripción y la autorización biométrica
siguen pendientes. Las instalaciones Android continúan aplazadas.

## Compatibilidad

Python 3.10 o posterior debe estar ya instalado y resolverse como `python` en
el cliente local. El cliente resuelve ese comando; el servidor no busca otras
instalaciones ni herramientas y no incluye un instalador.
El servidor usa MCP stdio, ofrece la versión `2025-06-18` y la negocia antes de
aceptar llamadas. No anuncia compatibilidad con versiones que requieran lotes.
El cliente arranca y cierra el proceso; stdout contiene sólo JSON-RPC.

`plugin.json` y `mcp.json` describen el paquete portable. El servidor no está
registrado en el chat por la sola existencia de estos archivos. Su instalación
y descubrimiento en un cliente real se comprobarán después de decidir la
activación. Otros clientes MCP locales pueden reutilizar el mismo servidor,
pero su compatibilidad no queda certificada por nuestras pruebas.

ChatGPT web o el chat en el móvil no ejecutan este proceso local por sí mismos.
Necesitarán una conexión remota compatible, autenticada y desplegada. No se
incluye un servidor público, túnel de terceros ni URL ficticia.

## Pruebas del candidato

Desde la carpeta superior, sin instalar paquetes:

```powershell
python -I -B -m unittest discover -s tests -v
```

Las pruebas con proveedores sintéticos comprueban la lógica del colector sin
leer el equipo. La prueba de proceso real comprueba el protocolo y el rechazo
por defecto; no acredita una lectura real de Windows. El informe de validación
distingue esas pruebas del ensayo supervisado descrito más abajo. La instalación
y el descubrimiento de herramientas en el cliente deben acreditarse por separado.

Referencias del transporte implementado:
[MCP stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports),
[ciclo de conexión](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
y [herramientas](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).
Se referencia una versión concreta, sin afirmar que sea la última del estándar.

## Trazabilidad y retirada

Se prepara a partir de la petición del 1 de noviembre de 2026 y del trabajo
de [HUB_Optimus #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933).
La fuente revisada es `a181f06204ff15fdbce1f4b3388f6086765e4383`.
Este paquete se propone para revisión; no está integrado ni aprobado como contrato.
No cambia titularidad, licencias o gobernanza del proyecto; el código candidato
es una contribución original de HUB_Optimus, sin incorporar código de RDC ni
Tailscale. Sus respectivos productos conservan sus propios derechos.

El servidor no crea un servicio ni estado persistente. Si se instala el paquete,
su registro se gestiona desde el cliente; no equivale a habilitar la lectura.
No elimines otras aplicaciones o conexiones para probar este candidato.

## Ensayo supervisado del 1 de noviembre de 2026

La excepción puntual para este chat quedó registrada en
[PR #2037](https://github.com/Voxterrae/HUB_Optimus/pull/2037#issuecomment-6561070445).
Se inicializó un proceso MCP local, se descubrió la herramienta, se hizo una
lectura con argumentos vacíos y se cerró el proceso con salida 0. El resultado
real cumple el esquema; el comprobante con las mediciones se conserva privado.
Una revisión independiente comprobó su coherencia y la identidad del código.
Esto no autoriza el uso indefinido ni prueba integración en un cliente de IA,
biometría, funcionamiento remoto o instalación en otros equipos.
