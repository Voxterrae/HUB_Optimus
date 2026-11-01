# Selección Web nativa — preparación y validación

Fecha: 01/11/2026. Coordinación #2021, propuesta #2040. Este registro se prepara antes de fijar el SHA del candidato. Los resultados posteriores de Windows, la revisión independiente y la disposición del head exacto se registran externamente en la PR y el comentario de coordinación; no se infiere aceptación de un archivo presente o una compilación.

## Uso de la interfaz

En Inicio, pulsa **Elegir fuente Web**. También se puede abrir desde Ajustes → Configurar privacidad y buscador. Elige Web sin configurar, Mwmbl · piloto privado o SearXNG · servidor del operador. Solo SearXNG muestra el campo de servidor. Guardar cierra las páginas actuales, cancela trabajo y conserva la elección para el siguiente inicio; si falla el guardado, la política y fuente activas anteriores se mantienen.

Mwmbl permanece como piloto privado con [condiciones pendientes](WEB_PROVIDER_CONDITIONS_2026_11_01.md). La fuente recibe consulta y conexión al buscar; elegirla o guardarla no envía una consulta. Los resultados identifican su procedencia. El índice Optimus mantiene su corpus importado y funciona sin red; no equivale a cobertura mundial.

Si otra instancia o servicio ocupa el host local y no se confirma su configuración, Web se bloquea con una explicación. Índice sigue disponible. El navegador no detiene un servicio ajeno ni supone que la preferencia elegida ya esté aplicada allí.

## Cambio y referencias

Se parte del piloto `0b6662c60916b7a5043af4b0134adec04c2f60b2` y se incorporan los cambios del padre `5ed8785c5be011dba943371d87de4c4dd074a2c5`: diagnóstico/readiness del GUI y sus registros. La composición conserva ambas líneas sin reescribir historia. La prueba nativa anterior del padre, run 41331622526, acredita ese padre; no acredita por sí sola este selector nuevo.

Se añaden preferencia validada/migración, argumentos de host explícitos, revisión de configuración ante respuestas tardías, error específico de Web que no bloquea Índice, y guardado transaccional. Tras la revisión se añade un pin de la clave pública TLS recibido del proceso hijo por stdout privado, antes de permitir Web. Se mantienen la prueba HMAC del perfil, bearer/nonce, Origin/Host, cuotas del adaptador, reglas de contenido y cierre confirmado. No cambia CI o contratos raíz.

## Evidencia portable del primer candidato 15c3beb

Entorno Ubuntu 24.04.3, SDK 10.0.403/runtime 10.0.14. C# Core 46/46, cliente Search 66/66, Privacy 24/24 y backend 59/59: **195 comprobaciones**; Python 21/21. Las seis compilaciones requeridas, incluidas WPF y helper, terminan sin errores o advertencias. La variante completa del backend por DLL sin DOTNET_ROOT y con SDK en PATH repite 59/59; no cuenta como cobertura adicional. Las comprobaciones CNG de Windows se omiten expresamente en Linux.

RED→GREEN observados:

- Preferencias JSON y migración:39/44→44/44, con cinco fallos nuevos antes de implementar el campo.
- Apply con disco real:44/46→46/46; una firma provisional que lanzaba NotImplementedException permitió observar los dos fallos de comportamiento; no quedan stubs.
- Launcher:61/66→66/66; argumentos, reinicio None↔Mwmbl, bloqueo Web/Índice y respuesta de identidad obsoleta fallaron antes de implementar el contrato. El cierre fallido ya estaba protegido y se conservó.
- Tras el pase completo se añadió acceso directo desde Inicio y un ajuste acotado del helper. Se recompilaron WPF y helper, conservando idénticos Core/backend/tests. Una compilación de helper falló por el nombre Condition ambiguo entre WPF/UIAutomation; se conserva esa evidencia y se corrigió la referencia cualificada antes del pase final.

El manifiesto de ese primer candidato abarca 78inputs de compilación, SHA256 `000ef9463ed7bc3ec40c72d2542bd986439313b63f25bfc510fcb2bfccad28b0`. Los registros distinguen el pase inicial de 12 comandos, el cambio deliberado en cinco archivos App/helper y las compilaciones finales correspondientes.

Comandos desde `products/browser/windows`, con el SDK en PATH: `dotnet build <proyecto> -c Release -m:1` y `dotnet run --project <proyecto> -c Release --no-build` para `tests/Optimus.Core.Tests`, `tests/Optimus.Search.Tests` y `tests/Optimus.Privacy.Tests`. Backend: mismos comandos desde `products/browser/search` con `tests/Optimus.Search.Tests`. Empaquetado: `python3 -m unittest discover -s tools/release -v`. WPF/helper: `dotnet build` de `src/Optimus.App` y `scripts/WindowsSmoke/Optimus.Windows.Smoke.csproj`, añadiendo `-p:EnableWindowsTargeting=true`. Los logs no convierten los PE de fixtures en ejecutables probados.

## Aceptación nativa y opt-in de Internet

Se usa el workflow protegido existente `optimus-windows-smoke.yml` en main, con `source_commit` completo explícito. Primero servicio empaquetado; después GUI. La prueba GUI normal elige fuente explícita, comprueba el campo SearXNG y guardado sin listener, luego ejecuta Índice, guía, navegación loopback, pestaña privada, ajustes y cierre normal. La UIAutomation solo opera ventanas verificadas del proceso propio y su modal, sin teclado/mouse global o inspección del escritorio.

Una consulta Web real se solicita aparte: `Test-OptimusWindows.ps1 -Gui -LiveWeb` o helper `--gui --live-web`. Hace exactamente una consulta pública `web accessibility`, comprueba procedencia Mwmbl en una fila real y un botón de resultado, no abre destinos ni reintenta. Cuota, timeout o vacío se registran como falta de aceptación, sin sustitución de fuente. Antes de capturar, vuelve a Inicio y limpia el campo público usado.

El workflow no cambia ni activa Internet por su booleano GUI habitual. Un candidato de QA separado puede habilitar únicamente ese switch del script para ejecutar la prueba opt-in en la VM; se registran ambos SHAs y se comparan los bytes de producción. Una captura estática no acredita esta ruta.

## Límites y reversión

Los recibos externos deben identificar cada SHA y los resultados del servicio/GUI; hasta entonces no se afirma ejecución nativa de este incremento. No se acredita Windows físico del usuario, accesibilidad certificada, firma o licencia comercial resuelta. No se crea una cuenta, tarjeta o recurso pagado. La consulta al proveedor está redactada y sin enviar.

Para retirar el piloto elige Web sin configurar, conservando Índice. Un servicio externo conserva su propio control. Las reversiones del código y cualquier integración en main siguen el proceso humano vigente; el trabajo de esta propuesta no lo reemplaza.

## Revisión y único pase de correcciones

La revisión independiente del diff completo contra 5ed8785 pidió dos correcciones: vincular el servicio real a su proceso hijo, y resolver la aceptación GUI fallida del candidato 15c3beb. Run 41334405363/job124931037943 pasó 195 comprobaciones Windows y servicio empaquetado, pero GUI falló al buscar un aviso transitorio después de Guardar. El cierre normal y la limpieza sí pasaron; no se hizo consulta Web. No se atribuye ese fallo al guardado sin evidencia.

El pase de correcciones comprueba la fuente efectiva reabriendo el modal propio, después de que el controlador vuelva a estar preparado. Conserva diagnósticos de fase y clasifica fallos sin volcar consultas, texto de página o rutas. El acceso desde Inicio enfoca y desplaza al selector; el catálogo y las guías enviadas coinciden con las opciones actuales.

La identidad nueva informa puerto real y SHA256 del SPKI público solo después del bind, mediante un switch opcional que requiere stdin/stdout redirigidos. Cada conexión TLS de la consulta comprueba ese pin además de HMAC, antes de enviar bearer o consulta. No se exporta clave privada, no se guarda el pin en preferencias y no se usa una cabecera HTTP que un servicio antiguo pudiera ignorar. Índice mantiene compatibilidad con servicio independiente.

RED observado: cuatro casos nuevos de cliente fallan antes del arreglo (66/70), incluido un servidor TLS real que cambia de clave pero conserva el perfil; productor CLI 60/61 antes de informar identidad. Los recibos de la regresión y ejecución Windows posteriores identifican el nuevo SHA externamente. Se conserva un intento intermedio 67/70 por expectativas antiguas de argumentos/observador stdout en fixtures de ciclo de vida; se alinearon los fixtures sin relajar los nuevos controles de seguridad. No se solicita otra ronda de revisión independiente; las correcciones se verifican mediante pruebas y se enumeran en el handoff.

La regresión del único pase de correcciones ejecuta Core46/46, cliente70/70, Privacy24/24 y backend61/61: **201 comprobaciones C# únicas**, además de Python21/21. Backend, WPF y helper compilan sin advertencias/errores. La variante sin DOTNET_ROOT repite el backend como comprobación de descubrimiento del runtime; su resultado exacto se conserva con el manifiesto del pase y se registra en la PR. Windows, GUI y consulta opt-in se acreditan por sus recibos posteriores, no por estas compilaciones Linux.
