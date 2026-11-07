# Contraste de ayudas emergentes Windows

Seguimiento: [#2021, observación manual](https://github.com/Voxterrae/HUB_Optimus/issues/2021#issuecomment-6690790082).
Base revisada: `main@0a1dde5c47be9076973478cfb568a2a8219c3fdb`.

## Causa y cambio localizado

La paleta de texto de Optimus convivía con el fondo predeterminado del popup
WPF. La regresión nativa reproduce un fondo claro `#FFF1F2F7` en Oscuro antes
del parche. El nuevo estilo implícito de `ToolTip` define conjuntamente fondo,
texto y borde mediante `DynamicResource`, manteniendo la plantilla nativa.

Se usa `OptimusPanelBrush` para conservar también la pareja
`SystemColors.WindowBrush`/`SystemColors.WindowTextBrush` en Alto contraste
del sistema. La política y el mecanismo existente de cambio de tema no cambian.

| Paleta | Fondo | Texto | Contraste de texto |
| --- | --- | --- | --- |
| Claro | `#F0F2F3` | `#18212B` | 14,48:1 |
| Oscuro | `#171C24` | `#F5F2EC` | 15,30:1 |
| Alto contraste de Optimus | Negro | Blanco | 21:1 |
| Alto contraste de Windows | Window | WindowText | Elección del sistema/usuario; sin imponer colores fijos |

Se revisaron las ayudas de navegación, dirección, botón «Ir o buscar», tema,
menú, apertura privada, búsqueda de inicio y resultados, y campo de sitio en
ajustes de privacidad. Todas usan `ToolTip` de WPF sin estilo local que anule
el nuevo estilo implícito.

## Regresión nativa reproducible

Desde `products/browser/windows`, con SDK .NET 10.0.403 y escritorio Windows
interactivo:

```sh
dotnet run --project tests/Optimus.Theme.Tests -c Release
```

La suite enlaza `NativeTheme.cs` y `OptimusTheme.xaml` de producción y referencia
`Optimus.Core`. Prueba botones quiet/primary y campos de búsqueda, menú y un
diálogo con propietario. Inspecciona el `TextBlock` y el fondo de la plantilla
nativa, no solo el valor declarado de `Foreground`. Cambia
Oscuro → Claro → Alto contraste → Alto contraste del sistema → Oscuro con la
misma ayuda abierta, y después cierra, cambia a Claro y reabre.

La ejecución automatizada en Windows 10 x64, .NET WindowsDesktop 10.0.14,
reprodujo el fallo sobre el XAML original y pasó **210 comprobaciones** sobre
el parche. Se compiló desde Linux con SDK 10.0.403 y se ejecutó el ensamblado
en Windows con `dotnet Optimus.Theme.Tests.dll`; no se instaló SDK en el equipo.
La compilación de la aplicación WPF y de la suite terminó sin errores ni avisos.

Procedencia de la ejecución nativa (hashes coincidentes en compilación y Windows):

| Archivo | Identificador |
| --- | --- |
| `OptimusTheme.xaml` (blob Git) | `5c6584082b77beaf5661f18d811cc6b364ba6d76` |
| `Program.cs` de la suite (blob Git) | `f5c675ae5e4629af5264b88805d3c356f4de2dcd` |
| `Optimus.Theme.Tests.dll` (SHA-256) | `119435d8fa493e87bc7af2d21089ee21744695d9b9a80493abd5d74601ead1b8` |
| `Optimus.Core.dll` (SHA-256) | `bf690177e334f48c7a50e8564964753061d96ab4ad0016d5cf44db37f3504f19` |

La suite abre ayudas explícitas con `PlacementTarget`; no automatiza el hover
que hace que `ToolTipService` convierta las cadenas usadas por la aplicación.
Aplica la rama de Alto contraste del sistema usando los colores Windows
actuales, sin activar/desactivar el ajuste del sistema ni probar sus eventos.
No inicia WebView2, SearchHost, red ni perfiles de usuario.

Esta suite tiene un comando explícito. Los workflows, sus commits fijados,
protecciones y scripts existentes se conservan; sus checks verdes no acreditan
la ejecución de esta suite nativa.

## Aceptación visual real pendiente

- [ ] Compilar el commit exacto de la propuesta y registrar Windows, versión y SHA.
- [ ] En Claro, Oscuro y Alto contraste de Optimus, abrir con el ratón las ayudas
  de Atrás/Adelante/Recargar/Inicio, dirección y «Ir o buscar · Intro».
- [ ] Repetir para tema, menú, búsqueda de inicio/resultados y ajustes de privacidad.
- [ ] Cambiar de tema, comprobar la siguiente ayuda y el texto legible sin reiniciar.
- [ ] Activar/desactivar Alto contraste desde Windows y comprobar la actualización
  de la ventana principal y un diálogo de ajustes ya abierto.
- [ ] Comprobar teclado, lector de pantalla, escala de texto y recortes.

Registrar resultado y evidencia por paleta. Las comprobaciones automatizadas
anteriores no sustituyen esta aceptación. La revisión y aprobación humana,
con los controles obligatorios del commit vigente, siguen pendientes antes de
integrar. La reversión consiste en retirar el estilo implícito de `ToolTip`.
