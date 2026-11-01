#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Publication,
    [string]$EvidenceDirectory,
    [ValidatePattern('^[0-9a-fA-F]{40}$')][string]$SourceCommit,
    [switch]$Gui
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'Windows required. No Windows acceptance checks ran.'
}
$publicationPath = [IO.Path]::GetFullPath($Publication)
if (-not $EvidenceDirectory) { $EvidenceDirectory = Join-Path ([IO.Path]::GetTempPath()) ('OptimusEvidence-' + [Guid]::NewGuid().ToString('N')) }
$evidence = [IO.Path]::GetFullPath($EvidenceDirectory)
# Never mix reports with profiles or the service's private temporary directory.
$profile = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Optimus'
if ($evidence.TrimEnd('\').Equals($profile, [StringComparison]::OrdinalIgnoreCase) -or $evidence.StartsWith($profile + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Evidence must be outside default profiles.' }
if (Test-Path -LiteralPath $evidence) { throw 'Evidence directory must be new; existing evidence is not overwritten.' }
New-Item -ItemType Directory -Path $evidence | Out-Null
$reportPath = Join-Path $evidence 'result.json'
$sourceState = 'not-requested'
try {
    $required = @('Optimus.exe', 'Optimus.dll', 'Optimus.Core.dll', 'Optimus.runtimeconfig.json', 'Search\Optimus.SearchHost.exe', 'Search\Optimus.SearchHost.dll', 'Search\Optimus.SearchHost.runtimeconfig.json', 'Search\index.json', 'Diagnostics\Optimus.Windows.Smoke.exe', 'Diagnostics\Optimus.Windows.Smoke.dll', 'Diagnostics\Optimus.Core.dll', 'Diagnostics\Optimus.Windows.Smoke.runtimeconfig.json')
    foreach ($relative in $required) { if (-not (Test-Path -LiteralPath (Join-Path $publicationPath $relative) -PathType Leaf)) { throw ('Publication incomplete: ' + $relative) } }
    $metadata = [ordered]@{ utc = [DateTime]::UtcNow.ToString('o'); powershell = $PSVersionTable.PSVersion.ToString(); os = [Environment]::OSVersion.VersionString; guiRequested = [bool]$Gui; sourceCommit = $SourceCommit; sourceVerification = $sourceState; files = @() }
    $sourceVerified = [bool]$SourceCommit
    foreach ($relative in @('Optimus.exe', 'Optimus.dll', 'Optimus.Core.dll', 'Search\Optimus.SearchHost.exe', 'Search\Optimus.SearchHost.dll', 'Search\index.json', 'Diagnostics\Optimus.Windows.Smoke.exe', 'Diagnostics\Optimus.Windows.Smoke.dll', 'Diagnostics\Optimus.Core.dll')) {
        $file = Get-Item -LiteralPath (Join-Path $publicationPath $relative)
        $nativeHeadMatch = $null
        if ($SourceCommit -and ($relative.EndsWith('.exe', [StringComparison]::OrdinalIgnoreCase) -or $relative.EndsWith('.dll', [StringComparison]::OrdinalIgnoreCase))) {
            $nativeHeadMatch = $file.VersionInfo.ProductVersion -and $file.VersionInfo.ProductVersion.IndexOf($SourceCommit, [StringComparison]::OrdinalIgnoreCase) -ge 0
            if (-not $nativeHeadMatch) { $sourceVerified = $false }
        }
        $metadata.files += [ordered]@{ sourceHeadMatchesProductVersion = $nativeHeadMatch; name = $relative; bytes = $file.Length; sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant(); version = $file.VersionInfo.FileVersion; informationalVersion = $file.VersionInfo.ProductVersion }
    }
    if ($SourceCommit) { $sourceState = if ($sourceVerified) { 'verified-product-version' } else { 'unverified-product-version' } }
    $metadata.sourceVerification = $sourceState
    $metadata | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $evidence 'metadata.json') -Encoding UTF8
    if ($SourceCommit -and -not $sourceVerified) { throw 'Executable or managed assembly source provenance unverified.' }
    # ProcessStartInfo on .NET Framework has no ArgumentList; quote Windows arguments.
    function Quote-Argument([string]$Value) {
        '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
    }
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = Join-Path $publicationPath 'Diagnostics\Optimus.Windows.Smoke.exe'
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.Arguments = (Quote-Argument $publicationPath) + ' ' + (Quote-Argument $reportPath)
    if ($Gui) { $start.Arguments += ' --gui' }
    $helper = [Diagnostics.Process]::Start($start)
    try {
        if (-not $helper.WaitForExit(180000)) {
            # Only the exact still-live process created here and its descendants are stopped.
            & (Join-Path $env:SystemRoot 'System32\taskkill.exe') /PID $helper.Id /T /F | Out-Null
            $cleanupFailed = $LASTEXITCODE -ne 0 -or -not $helper.WaitForExit(5000)
            @{ Status = 'failed'; Failure = 'Diagnostic helper exceeded 180 seconds.'; Checks = @(); CleanupFailures = @(if ($cleanupFailed) { 'Owned helper tree shutdown failed.' }) } | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding UTF8
            $exitCode = 1
        } else { $exitCode = $helper.ExitCode }
    } finally { $helper.Dispose() }
    if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) { throw 'Diagnostic helper exited without a structured report.' }
    $result = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
    $image = Join-Path $evidence 'owned-window.png'
    if (Test-Path -LiteralPath $image -PathType Leaf) { @{ bytes = (Get-Item -LiteralPath $image).Length; sha256 = (Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant() } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'image.json') -Encoding UTF8 }
    Write-Host ('Windows acceptance: ' + $result.Status + '. Evidence: ' + $evidence)
    if ($exitCode -ne 0 -or $result.Status -ne 'passed') { exit $(if ($exitCode -eq 3) { 3 } else { 1 }) }
    exit 0
} catch {
    # Do not serialize exception details, command lines, profile paths or host output.
    if (-not (Test-Path -LiteralPath $reportPath)) { @{ Status = 'failed'; Failure = 'Publication preflight or diagnostic execution failed.'; SourceVerification = $sourceState; Checks = @(); CleanupFailures = @() } | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding UTF8 }
    Write-Error 'Windows acceptance failed. Review the structured report; no passing Windows evidence was produced.'
    exit 1
}
