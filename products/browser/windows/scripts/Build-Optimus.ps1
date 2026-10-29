[CmdletBinding()]
param([string]$Dotnet = 'dotnet')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    & $Dotnet --version
    if ($LASTEXITCODE -ne 0) { throw 'SDK .NET 10 no disponible. Consulta global.json y PILOTO.md.' }
    & $Dotnet run --project tests/Optimus.Core.Tests -c Release
    if ($LASTEXITCODE -ne 0) { throw 'Las pruebas del núcleo fallaron.' }
    foreach ($suite in @('Optimus.Search.Tests', 'Optimus.Privacy.Tests')) {
        & $Dotnet run --project (Join-Path 'tests' $suite) -c Release
        if ($LASTEXITCODE -ne 0) { throw "Pruebas fallidas: $suite" }
    }
    & $Dotnet build src/Optimus.App/Optimus.App.csproj -c Release -p:EnableWindowsTargeting=true
    if ($LASTEXITCODE -ne 0) { throw 'La compilación falló.' }
    $output = Join-Path $repo 'artifacts/win-x64'
    if (Test-Path $output) { Remove-Item -Recurse -Force $output }
    & $Dotnet publish src/Optimus.App/Optimus.App.csproj -c Release -r win-x64 --self-contained false -p:EnableWindowsTargeting=true -o $output
    if ($LASTEXITCODE -ne 0) { throw 'La publicación local falló.' }
    Copy-Item docs/PILOTO.md (Join-Path $output 'PILOTO.md')
    Copy-Item docs/third-party (Join-Path $output 'third-party') -Recurse
    'Optimus Browser 0.2.0 · privado, SIN FIRMA · framework-dependent · win-x64' | Set-Content (Join-Path $output 'BUILD-INFO.txt') -Encoding utf8
    Get-ChildItem $output -Recurse -File | Where-Object Name -ne 'SHA256SUMS.txt' | Sort-Object FullName | ForEach-Object {
        $relative = [IO.Path]::GetRelativePath($output, $_.FullName).Replace('\','/')
        '{0}  {1}' -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $relative
    } | Set-Content (Join-Path $output 'SHA256SUMS.txt') -Encoding ascii
    Write-Host "Compilación privada sin firma preparada en $output. No se ha instalado ni ejecutado."
} finally { Pop-Location }
