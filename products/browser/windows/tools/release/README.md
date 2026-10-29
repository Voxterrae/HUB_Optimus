# Empaquetador Optimus Browser 0.2.0 alpha

Utilidad Python 3.9+ de biblioteca estándar. Requiere `git` en PATH; no necesita ejecutar el producto ni disponer de Windows. Está destinada a una publicación Windows x64 autocontenida ya compilada y a un repositorio Git del navegador nativo. No compila, instala ni publica nada.

```bash
python package_optimus.py \
  --source-root /ruta/al/repositorio-nativo \
  --binary-root /ruta/a/publish-win-x64 \
  --output-dir /ruta/a/entrega \
  --metadata /ruta/a/metadata.json
```

El directorio de salida debe estar fuera de las dos entradas. Una ejecución correcta devuelve 0; los errores devuelven 1 (los argumentos inválidos devuelven 2). La entrega se reemplaza solo después de construir y verificar el ZIP temporal. Una ejecución rechazada conserva cualquier entrega anterior: no debe confundirse con una entrega nueva.

Produce exactamente estos dos archivos de entrega:

- `Optimus_Browser_Windows_0.2.0_alpha.zip`
- `Optimus_Browser_Windows_0.2.0_alpha.zip.sha256`

El ZIP contiene una única carpeta `Optimus_Browser_0.2.0_alpha/`: publicación binaria en su raíz, código nativo seleccionado en `Source/`, `LEEME.txt`, `VALIDACION.md`, `DECISIONES.md` y `SHA256SUMS.txt`. La lista de hashes cubre todos los archivos salvo ella misma, ordenados por ruta relativa. El hash externo cubre el ZIP entero. El LEEME informa que es una alpha privada compilada sin firma, que .NET está incluido y que WebView2 Evergreen debe estar instalado por separado. Indica descomprimir y ejecutar `Optimus.exe`, sin instalación automática ni cambio automático del navegador predeterminado. Describe la guía local mediante reglas, la IA generativa nativa aún sin conectar y la ejecución Windows y aceptaciones de accesibilidad y seguridad pendientes.

## Esquema de metadatos

`--metadata` recibe la ruta de un objeto JSON UTF-8. Todos estos campos son cadenas obligatorias y no vacías. Los campos adicionales se ignoran; no se empaqueta el JSON original.

| Campo | Contenido requerido |
| --- | --- |
| `source_commit` | Identificador completo Git hexadecimal de 40 o 64 caracteres del código nativo. |
| `native_tests` | Comandos y resultados reales de comprobaciones nativas, con sus límites. |
| `companion_tests` | Comandos y resultados reales del componente acompañante, con sus límites. |
| `companion_url` | URL HTTPS del repositorio o referencia externa del componente acompañante. |
| `plugin_id` | Identificador real del plugin correspondiente a esta entrega. |
| `validation` | Texto Markdown de evidencias, plataforma, fecha y comprobaciones pendientes. |
| `decisions` | Texto Markdown de decisiones de esta entrega. |

El operador debe aportar evidencias verdaderas y no introducir secretos, datos personales ni resultados inventados. El empaquetador no comprueba que los comandos declarados se hayan ejecutado ni que la URL o el plugin existan. Nunca atribuye una ejecución real en Windows. No modifica el repositorio.

`git ls-files --cached` determina los nombres seleccionados; sus contenidos se leen del árbol de trabajo actual. Por tanto, `source_commit` identifica la referencia declarada, pero **no certifica que el árbol esté limpio o coincida con ese commit**. Antes de la entrega final hay que registrar el commit real y revisar el estado del árbol; cualquier diferencia intencionada debe quedar explicada en `validation`. Esto permite incluir los cambios aprobados sin inventar un commit o descartar modificaciones silenciosamente.

## Reglas y límites

- Exige `Optimus.exe`, `Optimus.dll`, `Optimus.runtimeconfig.json` y `Microsoft.Web.WebView2.Core.dll` en la raíz de publicación. Todos los archivos seleccionados deben tener contenido.
- Inspecciona la firma PE y la máquina AMD64 del apphost `Optimus.exe`. No impone AMD64 a los ensamblados .NET administrados, que pueden tener cabecera PE AnyCPU. Exige `runtimeOptions.includedFrameworks` con `Microsoft.NETCore.App` y versión, y rechaza `framework`/`frameworks` dependientes del runtime instalado. No certifica la integridad funcional del runtime completo ni ejecuta ensamblados.
- Omite directorios de fuente `.git`, `.superpowers`, `bin`, `obj`, `artifacts`, `tooling` y `__pycache__`. Solo incluye nombres devueltos por Git; los archivos no versionados no entran. Rechaza directorios de código gateway: debe mantenerse en su repositorio externo.
- Rechaza enlaces simbólicos, rutas absolutas, traversal, rutas incompatibles con Windows, colisiones de nombres sin distinción de mayúsculas y archivos binarios que intenten reemplazar documentos generados o `Source/`.
- Rechaza nombres de credenciales, certificados privados y claves (`.pfx`, `.key`, etc.), archivos `.env` y variantes; `.env.example` se permite únicamente si existe entre los archivos seleccionados y supera el escaneo. Rechaza directorios conocidos de perfiles, datos de navegador y logs.
- Escanea contenido de todas las entradas y metadatos con patrones de claves conocidas, claves privadas y asignaciones sospechosas; incluye texto UTF-8 y UTF-16. Nunca imprime la coincidencia de una credencial. Los patrones son una comprobación adicional y no sustituyen una revisión humana de privacidad y secretos.
- Verifica CRC del ZIP, rutas y cobertura/hash íntegros del manifiesto antes de entregar. Fija fechas ZIP, permisos y orden. Mismos bytes de entrada y misma versión de Python/zlib generan el mismo ZIP; no se promete igualdad entre versiones diferentes del compresor.

No contiene ProductCode ni genera un instalador. El código del componente acompañante no se copia.

## Pruebas

```bash
python -m unittest discover -s /ruta/a/release_tools -v
```

Las pruebas usan repositorios Git temporales y cabeceras PE sintéticas no ejecutables. Comprueban integración real de la CLI, reproducibilidad, hashes, selección de fuentes y rechazo de entradas peligrosas. No son una prueba de ejecución del navegador en Windows.
