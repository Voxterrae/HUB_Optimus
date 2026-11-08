#requires -Version 7.0
[CmdletBinding()]
param([string]$Dotnet = 'dotnet', [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$search = [IO.Path]::GetFullPath((Join-Path $repo '../search'))
Push-Location $repo
try {
    & $Dotnet --version
    if ($LASTEXITCODE -ne 0) { throw 'SDK .NET 10 no disponible. Consulta global.json.' }
    foreach ($suite in @('Optimus.Core.Tests', 'Optimus.Search.Tests', 'Optimus.Privacy.Tests')) {
        & $Dotnet run --project (Join-Path 'tests' $suite) -c Release
        if ($LASTEXITCODE -ne 0) { throw "Pruebas fallidas: $suite" }
    }
    & $Dotnet run --project (Join-Path $search 'tests/Optimus.Search.Tests') -c Release
    if ($LASTEXITCODE -ne 0) { throw 'Pruebas del servicio fallidas.' }
    & $Python -m unittest discover -s tools/release -v
    if ($LASTEXITCODE -ne 0) { throw 'Pruebas del empaquetador fallidas.' }
    $output = Join-Path $repo 'artifacts/win-x64'
    if (Test-Path $output) { Remove-Item -Recurse -Force $output }
    & $Dotnet publish src/Optimus.App/Optimus.App.csproj -c Release -r win-x64 --self-contained true -p:EnableWindowsTargeting=true -m:1 -o $output
    if ($LASTEXITCODE -ne 0) { throw 'Publicación nativa fallida.' }
    & $Dotnet publish (Join-Path $search 'src/Optimus.Search/Optimus.Search.csproj') -c Release -r win-x64 --self-contained true -p:Version=0.3.3-alpha -m:1 -o (Join-Path $output 'Search')
    if ($LASTEXITCODE -ne 0) { throw 'Publicación del servicio fallida.' }
    & $Dotnet publish scripts/WindowsSmoke/Optimus.Windows.Smoke.csproj -c Release -r win-x64 --self-contained true -p:EnableWindowsTargeting=true -m:1 -o (Join-Path $output 'Diagnostics')
    if ($LASTEXITCODE -ne 0) { throw 'Publicación del diagnóstico fallida.' }
    Copy-Item scripts/Test-OptimusWindows.ps1 (Join-Path $output 'Test-OptimusWindows.ps1')
    & $Dotnet run --project (Join-Path $search 'src/Optimus.Search/Optimus.Search.csproj') -c Release -- index --input (Join-Path $search 'catalog/optimus-help.json') --output (Join-Path $output 'Search/index.json')
    if ($LASTEXITCODE -ne 0) { throw 'Importación del catálogo público de ayuda fallida.' }
    Copy-Item docs/PILOTO.md (Join-Path $output 'PILOTO.md')
    Copy-Item docs/GUIA_0_3.md (Join-Path $output 'GUIA_0_3.md')
    Copy-Item docs/GUIA_0_3_1.md (Join-Path $output 'GUIA_0_3_1.md')
    Copy-Item docs/GUIA_0_3_2.md (Join-Path $output 'GUIA_0_3_2.md')
    Copy-Item docs/GUIA_0_3_3.md (Join-Path $output 'GUIA_0_3_3.md')
    Copy-Item docs/VALIDATION_0_3_3.md (Join-Path $output 'VALIDATION_0_3_3.md')
    Copy-Item docs/third-party (Join-Path $output 'third-party') -Recurse
    Copy-Item (Join-Path $search 'README.md') (Join-Path $output 'Search/README.md')
    New-Item -ItemType Directory -Force (Join-Path $output 'Search/docs') | Out-Null
    foreach ($doc in @('PROTOCOL.md', 'VALIDATION.md', 'AI_GOVERNANCE_REVIEW.md')) {
        Copy-Item (Join-Path $search "docs/$doc") (Join-Path $output "Search/docs/$doc")
    }
    # The committed ASP.NET notices are exact official v10.0.14 bytes; fail on drift.
    $runtime = Get-Content (Join-Path $output 'Search/Optimus.SearchHost.runtimeconfig.json') -Raw | ConvertFrom-Json
    $aspVersion = ($runtime.runtimeOptions.includedFrameworks | Where-Object name -eq 'Microsoft.AspNetCore.App').version
    if ($aspVersion -ne '10.0.14') { throw 'Actualiza avisos y procedencia ASP.NET Core antes de publicar otra versión del runtime.' }
    'Optimus Browser 0.3.3-alpha · privado, SIN FIRMA · autocontenido · win-x64 · Search/ local' | Set-Content (Join-Path $output 'BUILD-INFO.txt') -Encoding utf8
    & $Python tools/release/package_optimus.py --verify-publication $output
    if ($LASTEXITCODE -ne 0) { throw 'Publicación incompleta o insegura.' }
    Get-ChildItem $output -Recurse -File | Where-Object Name -ne 'BUILD-SHA256SUMS.txt' | Sort-Object FullName | ForEach-Object {
        $relative = [IO.Path]::GetRelativePath($output, $_.FullName).Replace('\','/')
        '{0}  {1}' -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $relative
    } | Set-Content (Join-Path $output 'BUILD-SHA256SUMS.txt') -Encoding ascii
    Write-Host "Publicación privada sin firma preparada en $output. No se ha instalado ni ejecutado. Empaqueta con tools/release/package_optimus.py y metadatos reales."
} finally { Pop-Location }
