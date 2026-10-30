# ASP.NET Core 10.0.14 — procedencia de avisos

Los archivos siguientes conservan exactamente los bytes de las fuentes oficiales Microsoft/.NET del tag `v10.0.14`. El integrador descargó las fuentes a través de la configuración proxy/CA de la sesión y verificó sus objetos Git; el trabajador de empaquetado copió esos bytes sin editar. No se cambian licencias del proyecto.

| Archivo local | Fuente oficial | SHA-256 de los bytes |
| --- | --- | --- |
| `ASPNetCore.LICENSE.txt` | https://github.com/dotnet/aspnetcore/blob/v10.0.14/LICENSE.txt | `cfc21f5e8bd655ae997eec916138b707b1d290b83272c02a95c9f821b8c87310` |
| `ASPNetCore.THIRD-PARTY-NOTICES.txt` | https://github.com/dotnet/aspnetcore/blob/v10.0.14/THIRD-PARTY-NOTICES.txt | `52af3d603b6d069e635f8afd08ec44ec01559255b5f3afd161ae9e6fe7e7aa54` |

Build-Optimus.ps1 exige que el host autocontenido incluya Microsoft.AspNetCore.App 10.0.14. Otra versión requiere revisar sus avisos y actualizar este registro antes de distribuir. Los avisos .NET, Windows Desktop y WebView2 heredados se conservan en sus archivos existentes.
