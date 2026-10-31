#requires -Version 7.0
[CmdletBinding()]
param([string]$Dotnet = 'dotnet', [string]$Python = 'python', [string]$Artifact = '')
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$search = [IO.Path]::GetFullPath((Join-Path $repo '../search'))
if (!$Artifact) { $Artifact = Join-Path $repo 'artifacts/win-x64' }
$Artifact = [IO.Path]::GetFullPath($Artifact).TrimEnd([IO.Path]::DirectorySeparatorChar)
Push-Location $repo
try {
    foreach ($suite in @('Optimus.Core.Tests', 'Optimus.Search.Tests', 'Optimus.Privacy.Tests')) {
        & $Dotnet run --project (Join-Path 'tests' $suite) -c Release
        if ($LASTEXITCODE -ne 0) { throw "Pruebas fallidas: $suite" }
    }
    & $Dotnet run --project (Join-Path $search 'tests/Optimus.Search.Tests') -c Release
    if ($LASTEXITCODE -ne 0) { throw 'Pruebas del servicio fallidas.' }
    & $Python -m unittest discover -s tools/release -v
    if ($LASTEXITCODE -ne 0) { throw 'Pruebas del empaquetador fallidas.' }
    & $Dotnet build src/Optimus.App/Optimus.App.csproj -c Release -p:EnableWindowsTargeting=true -m:1
    if ($LASTEXITCODE -ne 0) { throw 'Compilación nativa fallida.' }
    & $Dotnet build (Join-Path $search 'src/Optimus.Search/Optimus.Search.csproj') -c Release -m:1
    if ($LASTEXITCODE -ne 0) { throw 'Compilación del servicio fallida.' }
    & $Python tools/release/package_optimus.py --verify-publication $Artifact
    if ($LASTEXITCODE -ne 0) { throw 'Publicación incompleta o insegura.' }
    $manifest = Join-Path $Artifact 'BUILD-SHA256SUMS.txt'
    if (!(Test-Path $manifest -PathType Leaf)) { throw 'Falta BUILD-SHA256SUMS.txt. Ejecuta Build-Optimus.ps1.' }
    $covered = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($line in Get-Content $manifest) {
        if ($line -notmatch '^([a-f0-9]{64})  (.+)$') { throw 'Manifiesto de hashes inválido.' }
        $expected = $Matches[1]; $relative = $Matches[2]
        $path = [IO.Path]::GetFullPath((Join-Path $Artifact $relative))
        if (!$path.StartsWith($Artifact + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Ruta fuera del artefacto.' }
        if ($path -eq $manifest -or !$covered.Add($path)) { throw 'Entrada duplicada o autorreferencia en manifiesto.' }
        if ((Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "Hash distinto: $relative" }
    }
    $actual = @(Get-ChildItem $Artifact -Recurse -File | Where-Object FullName -ne $manifest)
    if ($actual.Count -ne $covered.Count) { throw 'Cobertura incompleta del manifiesto.' }
    foreach ($file in $actual) { if (!$covered.Contains($file.FullName)) { throw 'Archivo sin hash en publicación.' } }
    Write-Host 'Pruebas, compilaciones, estructura de publicación y hashes verificados. Ejecución, firma y accesibilidad en Windows pendientes; consulta GUIA_0_3_3.md.'
} finally { Pop-Location }
