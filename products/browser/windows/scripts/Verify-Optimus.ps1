[CmdletBinding()]
param([string]$Dotnet = 'dotnet', [string]$Artifact = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (!$Artifact) { $Artifact = Join-Path $repo 'artifacts/win-x64' }
$Artifact = [IO.Path]::GetFullPath($Artifact)
Push-Location $repo
try {
    & $Dotnet run --project tests/Optimus.Core.Tests -c Release
    if ($LASTEXITCODE -ne 0) { throw 'Pruebas del núcleo fallidas.' }
    foreach ($suite in @('Optimus.Search.Tests', 'Optimus.Privacy.Tests')) {
        & $Dotnet run --project (Join-Path 'tests' $suite) -c Release
        if ($LASTEXITCODE -ne 0) { throw "Pruebas fallidas: $suite" }
    }
    & $Dotnet build src/Optimus.App/Optimus.App.csproj -c Release -p:EnableWindowsTargeting=true
    if ($LASTEXITCODE -ne 0) { throw 'Compilación fallida.' }
    $manifest = Join-Path $Artifact 'SHA256SUMS.txt'
    if (!(Test-Path $manifest)) { throw 'Falta SHA256SUMS.txt. Ejecuta Build-Optimus.ps1.' }
    foreach ($line in Get-Content $manifest) {
        if ($line -notmatch '^([a-f0-9]{64})  (.+)$') { throw 'Manifiesto de hashes inválido.' }
        $expected = $Matches[1]; $relative = $Matches[2]
        $path = [IO.Path]::GetFullPath((Join-Path $Artifact $relative))
        if (!$path.StartsWith($Artifact + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Ruta fuera del artefacto.' }
        if ((Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "Hash distinto: $relative" }
    }
    Write-Host 'Núcleo, compilación y hashes correctos. La ejecución y la accesibilidad en Windows requieren la lista manual de PILOTO.md.'
} finally { Pop-Location }
