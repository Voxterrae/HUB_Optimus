# Validación de la integración Windows/Search — 01/11/2026

Estado: preparación local de la propuesta de integración. La nueva ejecución
Windows, los checks obligatorios y la revisión final del SHA exacto de la
candidata siguen pendientes; este registro no acredita un merge ni una entrega.
Seguimiento: [#2045](https://github.com/Voxterrae/HUB_Optimus/issues/2045) y
[#2047](https://github.com/Voxterrae/HUB_Optimus/pull/2047).

## Procedencia y correcciones

La importación inicial conservó exactamente las fuentes de ambos módulos en
`5ed8785c5be011dba943371d87de4c4dd074a2c5`. El árbol actual añade las tres
correcciones de integración revisadas en #2049, #2050 y #2051:

- `SearxSearchProvider` usa `UseProxy=false` para comunicarse directamente con
  el endpoint SearXNG configurado por el operador, sin proxies ambientales.
  Conserva la validación TLS normal y los límites de endpoint, redirección y
  cookies. Una prueba con proceso hijo sintético observa una solicitud al
  operador configurado y cero contactos con el proxy ambiental. Esto no es
  aceptación de un proveedor SearXNG público real.
- `SettingsStore.Load` desactiva únicamente un endpoint heredado que cumple el
  resto de la política pero supera el límite de longitud original o escapada.
  Conserva los demás ajustes válidos, incluidas las reglas de privacidad, y
  avisa sin escribir durante Load. El próximo guardado ordinario, incluido el
  cierre de aplicación o pestaña, puede persistir el endpoint como null.
  Endpoints inseguros u otros ajustes inválidos siguen la vía de archivo dañado;
  Save y la validación de red conservan sus límites estrictos.
- El empaquetador acepta únicamente los dos flujos de bytes fijados del índice
  público de tres ayudas, no un catálogo semánticamente equivalente ni un índice
  arbitrario. La fixture pública se conserva en
  `../tools/release/fixtures/public_help_0_3_3.index.json`. Las importaciones de
  usuario mediante el servicio no reciben esta restricción de entrega.

| Índice público admitido | Bytes | SHA256 |
|---|---:|---|
| UTF-8/LF | 2050 | `3f084892eae765fbd1d872beab3514def3967068e4103ebf9831a0d68b26b958` |
| UTF-8/CRLF | 2075 | `18976d5bc476b8a8c2b7f653556f682e63ff00dc9f004453ce51a25f632a26b2` |

## Evidencia local

| Suite en Linux | Resultado observado |
|---|---:|
| Core | 39/39 |
| Windows Search | 59/59 |
| Privacy | 28/28 |
| Backend Search | 48/48 |
| Empaquetador Python | 23 pruebas, sin fallos |

La regresión del proxy pasó de 47/48 a 48/48 en el backend: antes contactaba
al proxy una vez y al operador cero veces; después contacta solo al operador
una vez. La salida Linux marca los casos CNG específicos de Windows como SKIP;
48/48 no acredita esos casos nativos.

La regresión de migración pasó de 26/28 a 28/28: preserva el bloqueo del usuario
y recupera también el caso cuyo URI escapado supera el límite. La regresión del
empaquetador primero demostró la admisión indebida de registros/campos alterados
y después verificó su rechazo en los modos de empaquetado y verificación, junto
con la aceptación de los bytes LF y CRLF fijados. La revisión focal de las tres
correcciones no dejó hallazgos Critical/Important pendientes. Esto no sustituye
la revisión final ni la atribución de resultados al nuevo SHA exacto.

## Evidencia Windows anterior y siguiente aceptación

Las ejecuciones frías [41331622526](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41331622526)
y [41332021001](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41332021001)
validaron su fuente exacta `5ed8785c5be011dba943371d87de4c4dd074a2c5`
con 169 comprobaciones, tres publicaciones autocontenidas, servicio y GUI.
Su workflow fue `078988ba228151ba27f814f6d4ff5d3a7515879b`.
Esas ejecuciones son evidencia histórica de esa fuente, no de esta candidata
corregida. El siguiente piloto debe registrar el SHA completo nuevo, comprobar
ProductVersion en los ocho EXE/DLL y atribuir por separado suites, publicación,
servicio, GUI y limpieza. Un cierre forzado no rescata la aceptación.

## Inventario y límites

`../SOURCE_MANIFEST_WINDOWS_INTEGRATION_2026_11_01.json` enumera los bytes
actuales de Windows y Search, incluida la nueva fixture, las pruebas y este
documento. Excluye salidas de compilación, cachés y su propio archivo. Los
manifiestos anteriores se conservan byte a byte como snapshots históricos:
sus hashes internos describen sus fuentes de entonces y no se recalculan para
simular que describen las correcciones posteriores. El inventario actual no
acredita binarios, ejecución nativa, firma, distribución ni merge.

La búsqueda pública real con SearXNG, las pruebas físicas en Windows10/11,
teclado y Narrator/NVDA, temas/Modo fácil y el aislamiento completo de cookies
mantienen sus propias aceptaciones. Las claves CNG de usuario son no exportables
y se eliminan explícitamente durante el cierre normal del host propio; un crash,
corte de energía, cierre forzado o fallo de eliminación puede dejar una clave
huérfana. No se acredita firma de código ni distribución pública. Permanecen
vigentes las reglas de propietario y `OWNER_AUTHORITY_HANDOFF.md`.
