# Validación de la propuesta Web controlada

Fecha: 7 de noviembre de 2026, Europe/Madrid. Propuesta local sin publicación.
Base fuente: `0a1dde5c47be9076973478cfb568a2a8219c3fdb`.

## Continuación tras aprobación — 8 de noviembre de 2026

La aprobación del usuario permite preparar la PR del parche revisado. La base
actual observada es `7ca513eb16d12d77ba5f017c63109dab937c12b2`, tres commits por
delante de la base de pruebas original; ninguno cambia los ocho archivos de
esta propuesta. La atribución de las pruebas siguientes sigue siendo la de su
base original, sin trasladarla a un SHA distinto por equivalencia.

La propuesta conserva exactamente el alcance de ocho archivos. La frase de
preparación sin publicación del diseño describe el checkpoint del 7 de noviembre;
la URL y el HEAD de la nueva PR se registran en GitHub al publicarla. No se activa
un proveedor, recurso Azure ni gasto. La aprobación no se presenta como revisión
formal GitHub ni como aceptación de resultados Web reales.

El CI ordinario actual ejecuta Python, no las 79 pruebas backend C#. El workflow
manual Windows está fijado a otro producto y tampoco las acredita en esta PR.
El enlace de CI y sus conclusiones deben leerse en el HEAD exacto; la ejecución
alojada de esta batería C# queda como incremento separado, sin añadir workflows
ni alterar protecciones dentro del parche aprobado.

## Alcance probado

| Batería | Resultado observado | Alcance |
| --- | --- | --- |
| Backend SearchHost | 79/79, exit 0 | HTTP real loopback, formularios, TLS de host, errores/límites, catálogo y procesos sintéticos |
| Windows Core | 39/39, exit 0 | Lógica portable, no WPF ni Windows nativo |
| Windows Search | 81/81, exit 0 | Cliente tipado, launcher, importación/restauración y transporte TLS sintético |
| Windows Privacy | 28/28, exit 0 | Reglas y ciclo de vida portables |
| Python Search/piloto/empaquetado | 142 passed + 107 subtests, exit 0 | Fixtures locales; sin motores ni Azure |
| Compilación final | 0 warnings / 0 errors | SDK .NET exacto 10.0.403, Release |
| Revisión independiente | 0 Critical / 0 Important | Código y documentación; no certificación de producción |

Total de comprobaciones C# focalizadas: 227. Los subtests Python se informan
separadamente y no se suman como nuevas pruebas principales.

## Reproducción

Desde `products/browser/search`, con `dotnet` 10.0.403 en PATH y DOTNET_ROOT:

```sh
dotnet restore tests/Optimus.Search.Tests/Optimus.Search.Tests.csproj --source /absolute/empty-nuget -m:1 -nr:false
dotnet build tests/Optimus.Search.Tests/Optimus.Search.Tests.csproj --no-restore -c Release -m:1 -nr:false /p:UseSharedCompilation=false
dotnet tests/Optimus.Search.Tests/bin/Release/net10.0/Optimus.Search.Tests.dll
```

Desde `products/browser/windows`, repetir restore/build/DLL para
`tests/Optimus.Core.Tests`, `tests/Optimus.Search.Tests` y
`tests/Optimus.Privacy.Tests`. No se añade PackageReference ni se consulta NuGet;
los frameworks usados están disponibles con el SDK existente. La ejecución del
cliente es portable Linux, no aceptación del GUI en Windows.

Desde la raíz, con las dependencias Python existentes declaradas instaladas:

```sh
python -m pytest -q tests/test_optimus_real_web_smoke.py tests/test_optimus_public_pilot.py tests/test_optimus_public_pilot_smoke.py products/browser/windows/tools/release/test_package_optimus.py
```

Entorno utilizado: pytest 9.2.0, jsonschema 4.26.0, PyYAML 6.0.3. No se instalaron
paquetes para este trabajo. Los intentos MSBuild multinodo terminaron sin
diagnóstico completo en este entorno; la ejecución serial `-m:1 -nr:false`
restauró/compiló correctamente sin cambiar los proyectos.

## Evidencia RED/GREEN y revisión

Los tests nuevos compilaron contra el proveedor original: 47/78 pass y 31 fallos
esperados por falta de POST/validación. El primer GREEN dio 72/78; seis fallos
eran una carrera del fixture que se cerraba antes de registrar Accept. Registrar
Accept antes de programar la tarea corrigió el fixture: 78/78.

La revisión independiente señaló un caso de cobertura adicional: propiedades
duplicadas después del resultado 20. Se añadió un registro 21 ambiguo usando
`title` y su escritura JSON escapada; el proveedor ya rechazaba toda la lista.
Sin otro cambio productivo, el run final concluyó **79/79**. Esta prueba adicional
no se presenta como un RED previo de la implementación original.

La primera corrida previa a cambios tenía fallos de lanzamiento del dotnet hijo
por PATH/DOTNET_ROOT incompletos. Se corrigió el entorno y no se atribuyeron esos
fallos al producto. Los fixtures POST consumen su cuerpo acotado antes de probar
cancelación/desconexión, evitando falsos positivos. Los fixtures de timeout y
tamaño declaran JSON para llegar al límite que realmente pretenden probar.

## Suite general del repositorio

Resultado final: **2708 passed, 7 failed, 15 skipped, 1661 subtests passed**,
exit 1, en 233,08 s. No se afirma suite general verde.

| Prueba fallida | Evidencia / límite |
| --- | --- |
| `test_ec2_legacy_adoption.py::test_adopts_9d677_format_and_is_idempotent` | Objeto histórico `9d6771994095e4fc04e8fdbf2caa644ccb002ab1` ausente |
| `test_ec2_validation_boundary.py::test_unmodified_production_supervisor_crosses_real_uid_boundary[passes]` | `/proc/self/task/<pid>/children` no disponible en este aislamiento |
| `test_ec2_validation_boundary.py::test_unmodified_production_supervisor_crosses_real_uid_boundary[fails]` | Sin marcador de validación esperado al fallar la supervisión de descendientes |
| `test_ec2_validation_boundary.py::test_unmodified_production_supervisor_crosses_real_uid_boundary[delayed-descendant]` | Mismo límite /proc, sin marcador esperado |
| `test_public_portfolio.py::test_document_routes_do_not_promote_byte_identical_language_placeholders` | Objeto histórico `8426b08e5f88b650c4d79e41d3ce3afd7d42746b` ausente |
| `test_public_portfolio.py::test_document_route_targets_exist_in_the_pinned_git_tree` | Mismo objeto histórico ausente |
| `test_site_capability_registry_integrity.py::test_every_commit_evidence_path_exists_at_the_declared_object_type` | Mismo objeto histórico ausente |

Todos los paths de pruebas anteriores están bajo `tests/`. Sus nombres exactos
se incluyen también en `evidence/general_failure_nodes.txt` dentro del paquete.


El historial Git local es una instantánea reconstruida, no un clon completo.
Los blob IDs de los cinco archivos modificados coinciden con la base remota;
la identidad del commit de empaquetado local no suplanta el commit upstream.
Un primer intento completo registró 2625 passed, 90 failed, 15 skipped y 1661
subtests: incluía permisos ejecutables no conservados al reconstruir la copia,
objetos históricos ausentes y límites de /proc. No es una señal de CI upstream.
Se corrigieron los modos para la nueva ejecución, sin cambiar scripts del
producto. Un intento intermedio fue interrumpido y no cuenta como suite pasada. Los 90
nombres del primer intento quedan en `evidence/initial_failure_nodes.txt`;
la ejecución corregida final es la referencia de esta propuesta.

No se modifican módulos EC2, portfolio o gobernanza para adaptar sus tests a
este entorno. Toda integración requiere CI de la rama propuesta sobre un clon
con historial y runner apropiado. Los tests focalizados prueban su propio
alcance; no permiten afirmar que todo el repositorio o Windows nativo pasan.

## Límites y artefactos

No se ha enviado ninguna consulta mediante SearXNG, Brave, Bing ni el proveedor
Web del producto. Las lecturas de documentación/GitHub se usaron para diseñar
la propuesta. No hay cuenta, clave, servicio, instalación WSL, imagen publicada,
Azure, gasto, configuración de usuario, fusión ni modificación remota.

Quedan sin probar relevancia real, disponibilidad/licencias de motores, soporte
de idiomas/safe-search, memoria del equipo, despliegue de un lock hermético,
atribución multimotor, exposición remota, Windows físico, WPF/accesibilidad y
tarifas específicas de la cuenta. No se atribuye un bloqueo histórico a 429 o
CAPTCHA sin evidencia. El resultado de #2062 sigue abierto.

El paquete contiene solo el diff, ocho archivos de la propuesta, el informe y
evidencia sintética seleccionada. Excluye bin/obj, .git, perfiles, tokens,
historiales de usuario y logs generales con volcados de entorno. El manifiesto
separa hashes de integridad de una firma de autor: no hay firma oficial de esta
propuesta. Aplicación y reversión del diff se comprueban en otra copia aislada.

La vista HTML es autónoma, sin scripts ni recursos remotos automáticos. Se
verificó estructura/links/tablas mediante parser. La inspección visual headless
no pudo ejecutarse porque Chromium no está instalado; no se descargó un browser.
