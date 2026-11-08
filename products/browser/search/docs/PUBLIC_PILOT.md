# Catálogo público piloto v0.1

Este incremento de #2081, bajo #2079, prepara datos para un futuro servicio Microsoft/Azure. Es un catálogo finito de ocho resúmenes propios en español: dos referencias públicas de Optimus y seis de Microsoft. No acredita búsqueda general de Internet ni un servicio Azure desplegado. La aceptación Web de #2062 sigue separada.

| Tema | Consulta de aceptación | Referencia |
| --- | --- | --- |
| Fuentes Web e índice propio | fuentes | README público de Search, revisión inmutable |
| Canal local y perfil | token | PROTOCOL público, revisión inmutable |
| Accesibilidad Windows | contraste | Microsoft Support |
| Navegación por teclado | atajos | Microsoft Support |
| Aplicaciones en contenedores | contenedores | Microsoft Learn, Container Apps |
| Archivos y catálogos | almacenamiento | Microsoft Learn, Blob Storage |
| Identidad y permisos | Entra | Microsoft Learn, identidad |
| Control del gasto | presupuestos | Microsoft Learn, presupuestos |

Los textos son redacción de Optimus, no artículos copiados ni contenido escrito o avalado por Microsoft. Las consultas son ejemplos seleccionados para estos temas, no un benchmark representativo de la Web. Sin coincidencias, el índice devuelve vacío. El corpus no ofrece cobertura multilingüe, rastreo o actualización automática.

## Procedencia y revisión

[Catálogo](../catalog/public-pilot-v0.1.json) y [procedencia](../catalog/public-pilot-v0.1.provenance.json) viajan separados. Cada documento identifica su referencia; los dos documentos HUB fijan la revisión `d77ede8f834fb1e4b078923866a55506e8f64e2d`. Las seis páginas Microsoft son referencias vivas consultadas el 3 de noviembre de 2026 y pueden cambiar. `updatedUtc` y `snapshotUtc` identifican la revisión de nuestros resúmenes; no son la fecha de modificación remota.

La clasificación pública es una afirmación revisada de este corpus concreto, no un detector automático de datos privados, prueba de permisos de terceros o garantía DLP. Los SHA-256 vinculan nuestro catálogo canónico y sus resúmenes con el manifiesto. No verifican los bytes de las páginas remotas ni autentican por sí solos al editor del ZIP. Debe partirse de una revisión de código o entrega cuya procedencia se haya comprobado. Ningún dato de LCDH, historial, marcadores, token o perfil forma parte del corpus.

El importador existente conserva su schema v1; no interpreta la procedencia como credencial ni verifica ese manifiesto. La verificación del paquete se realiza antes de importar. No se cambia el catálogo de tres documentos `optimus-help.json` incluido en la distribución Windows ni se importa este piloto automáticamente en un perfil.

## Generación y comprobación

Desde la raíz del repositorio, con Python 3 y un directorio de salida propio ya existente, ejecutar una sola vez para un nombre absoluto nuevo:

```sh
python products/browser/search/tools/build_public_pilot.py --output /ruta/absoluta/public-pilot-v0.1.zip
```

En PowerShell, la ruta absoluta puede obtenerse con `Join-Path (Get-Location) 'public-pilot-v0.1.zip'`. El único argumento aceptado es `--output`: el generador lee exclusivamente los dos archivos revisados junto al código. No acepta directorios de entrada ni perfiles, no descarga páginas y no consulta proveedores. Valida esquema estricto, referencias HTTPS exactas, fechas UTC, límites de tamaño y hashes. Rechaza claves desconocidas, duplicadas, datos incoherentes, enlaces simbólicos/reparse points existentes y un destino existente. No crea directorios, reemplaza archivos ni sube datos.

El ZIP contiene exactamente `catalog.json`, `provenance.json`, `README.txt` y `SHA256SUMS.txt`, en ese orden. JSON UTF-8 canónico con LF, miembros sin compresión y metadatos fijos producen los mismos bytes para los mismos datos, incluso si los archivos fuente usan CRLF. No se incluye `index.json`: su serialización por el importador puede variar entre plataformas. La salida imprime el SHA-256 del ZIP, sin rutas ni contenido privado.

Usar un directorio local controlado por el operador. Si el proceso falla durante la escritura puede quedar un ZIP incompleto; no se borra ni se reutiliza automáticamente. Verificar tamaño, integridad y checksums antes de importar. En este ejemplo, sustituir primero el SHA-256 por el de una entrega cuya procedencia se haya comprobado. Se valida el hash externo antes de abrir el ZIP, sobre el mismo archivo abierto; después, los miembros exactos y sus hashes sin extraer archivos. Los rechazos siguen activos con `python -O` o `PYTHONOPTIMIZE`:

```python
import hashlib
import zipfile

expected_zip_sha256 = 'SHA256_DE_LA_ENTREGA_REVISADA'
with open('/ruta/absoluta/public-pilot-v0.1.zip', 'rb') as stream:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(65536), b''):
        digest.update(chunk)
    if digest.hexdigest() != expected_zip_sha256:
        raise ValueError('ZIP externo distinto de la entrega revisada')
    stream.seek(0)
    with zipfile.ZipFile(stream) as archive:
        names = ['catalog.json', 'provenance.json', 'README.txt', 'SHA256SUMS.txt']
        if archive.namelist() != names or archive.testzip() is not None:
            raise ValueError('Miembros o integridad del ZIP incorrectos')
        expected = ''.join(hashlib.sha256(archive.read(name)).hexdigest() + '  ' + name + '\n'
                           for name in names[:3]).encode('ascii')
        if archive.read('SHA256SUMS.txt') != expected:
            raise ValueError('Checksums de los miembros incorrectos')
```

Comprobar también el hash externo del ZIP contra la entrega revisada. Tras esa verificación, copiar únicamente `catalog.json` a un directorio de trabajo nuevo y ejecutar el CLI real:

```sh
dotnet run --project products/browser/search/src/Optimus.Search/Optimus.Search.csproj -- index --input /ruta/catalog.json --output /ruta/nuevo-index-public-pilot.json
```

La importación valida el catálogo completo antes de publicar el índice. Para usarlo, indicar explícitamente ese índice al arrancar el servicio local mediante `--index-file`, conforme a [README](../README.md) y [protocolo](PROTOCOL.md). No se comparten tokens de perfil. La selección de fuentes del cliente conserva su comportamiento actual.

## Pruebas y siguiente frontera Azure

Las pruebas de backend ejecutan ese CLI con el corpus real, cargan el índice resultante y comprueban las ocho consultas, vacío real, importación repetida y rechazo de mutaciones sin dañar la salida anterior. Las pruebas Python verifican bytes reproducibles, miembros, checksums, formato, datos rechazados, límites, privacidad sintética y destinos existentes/enlazados. No se ejecuta ninguna consulta externa en estas pruebas.

El paquete es un artefacto de datos preparado para evaluar su futura publicación con versiones en Azure Blob Storage. No activa Blob, Container Apps ni otro recurso. Un servicio compartido necesita todavía contrato remoto, autenticación, protección de abuso, actualización/rollback y aceptación propios, además de identificar suscripción, responsables y coste. El host actual sigue exclusivamente en loopback con TLS/HMAC por dispositivo: cambiar el bind o compartir tokens no constituye ese servicio. Los presupuestos Azure generan avisos; por sí solos no detienen recursos ni consumo.
