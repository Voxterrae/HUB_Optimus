#requires -Version 7.2
[CmdletBinding(DefaultParameterSetName='Offline')]
param(
    [Parameter(ParameterSetName='Apply', Mandatory)] [switch]$Apply,
    [Parameter(ParameterSetName='Rollback', Mandatory)] [switch]$Rollback,
    [Parameter(ParameterSetName='Inspect', Mandatory)] [switch]$Inspect,

    [Parameter(ParameterSetName='Apply', Mandatory)]
    [Parameter(ParameterSetName='Rollback', Mandatory)]
    [Parameter(ParameterSetName='Inspect', Mandatory)]
    [string]$EnvironmentUrl,

    [Parameter(ParameterSetName='Apply', Mandatory)]
    [Parameter(ParameterSetName='Rollback', Mandatory)]
    [Parameter(ParameterSetName='Inspect', Mandatory)]
    [string]$EnvironmentId,

    [Parameter(ParameterSetName='Apply', Mandatory)]
    [Parameter(ParameterSetName='Rollback', Mandatory)]
    [Parameter(ParameterSetName='Inspect', Mandatory)]
    [string]$AccessTokenFile,

    [Parameter(ParameterSetName='Apply', Mandatory)]
    [Parameter(ParameterSetName='Rollback', Mandatory)]
    [Parameter(ParameterSetName='Inspect', Mandatory)]
    [string]$OutputDirectory,

    [Parameter(ParameterSetName='Apply', Mandatory)]
    [Parameter(ParameterSetName='Rollback', Mandatory)]
    [string]$AuthorizationFile,

    [Parameter(ParameterSetName='Rollback', Mandatory)]
    [string]$RollbackJournal,

    [Parameter(ParameterSetName='Apply')]
    [Parameter(ParameterSetName='Rollback')]
    [Parameter(ParameterSetName='Inspect')]
    [int]$ExpectedCurrentComponentCount = 0,

    [string]$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path,
    [string]$PythonExecutable = 'python',
    [string]$PacExecutable = "$HOME/.dotnet/tools/pac"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script = Join-Path $PackageRoot 'scripts/apply-dataverse-schema.py'
if (-not (Test-Path -LiteralPath $Script -PathType Leaf)) {
    throw "Applicator not found: $Script"
}

function Invoke-Native {
    param(
        [Parameter(Mandatory)][string]$Command,
        [Parameter(Mandatory)][string[]]$Arguments
    )
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $Command $($Arguments -join ' ')"
    }
}

if (-not ($Apply -or $Rollback -or $Inspect)) {
    Invoke-Native -Command $PythonExecutable -Arguments @($Script)
    return
}

foreach ($Path in @($AccessTokenFile, $OutputDirectory)) {
    if ($Path -eq $OutputDirectory) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    elseif (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required private file missing: $Path"
    }
}

$Common = @(
    $Script,
    '--environment-url', $EnvironmentUrl,
    '--environment-id', $EnvironmentId,
    '--access-token-file', $AccessTokenFile,
    '--output-directory', $OutputDirectory,
    '--expected-component-count', [string]$ExpectedCurrentComponentCount
)

if ($Inspect) {
    Invoke-Native -Command $PythonExecutable -Arguments @($Common + '--inspect')
    return
}

if (-not (Test-Path -LiteralPath $AuthorizationFile -PathType Leaf)) {
    throw "Authorization file missing: $AuthorizationFile"
}

$PreDirectory = Join-Path $OutputDirectory ('pre-' + ($Rollback ? 'rollback' : 'apply'))
$PostDirectory = Join-Path $OutputDirectory ('post-' + ($Rollback ? 'rollback' : 'apply'))
New-Item -ItemType Directory -Path $PreDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $PostDirectory -Force | Out-Null

$PreZip = Join-Path $PreDirectory 'OptimusEvidenceLab.pre.unmanaged.zip'
$PostZip = Join-Path $PostDirectory 'OptimusEvidenceLab.post.unmanaged.zip'

Invoke-Native -Command $PacExecutable -Arguments @(
    'solution', 'export',
    '--environment', $EnvironmentUrl,
    '--name', 'OptimusEvidenceLab',
    '--path', $PreZip,
    '--overwrite'
)

$Arguments = $Common + @('--authorization-file', $AuthorizationFile)
if ($Apply) {
    $Arguments += '--apply'
}
else {
    if (-not (Test-Path -LiteralPath $RollbackJournal -PathType Leaf)) {
        throw "Rollback journal missing: $RollbackJournal"
    }
    $Arguments += @('--rollback-journal', $RollbackJournal, '--rollback')
}

Invoke-Native -Command $PythonExecutable -Arguments $Arguments

Invoke-Native -Command $PacExecutable -Arguments @(
    'solution', 'export',
    '--environment', $EnvironmentUrl,
    '--name', 'OptimusEvidenceLab',
    '--path', $PostZip,
    '--overwrite'
)

foreach ($Zip in @($PreZip, $PostZip)) {
    $Hash = (Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash.ToLowerInvariant()
    "$Hash  $([IO.Path]::GetFileName($Zip))" |
        Set-Content -LiteralPath "$Zip.sha256.txt" -Encoding utf8NoBOM
}

[ordered]@{
    schemaVersion = '1.0'
    mode = if ($Apply) { 'APPLY_COMPLETE' } else { 'ROLLBACK_COMPLETE' }
    solution = 'OptimusEvidenceLab'
    expectedCurrentComponentCount = $ExpectedCurrentComponentCount
    preExportSha256 = (Get-FileHash $PreZip -Algorithm SHA256).Hash.ToLowerInvariant()
    postExportSha256 = (Get-FileHash $PostZip -Algorithm SHA256).Hash.ToLowerInvariant()
    rowsWritten = 0
    merge = $false
    deployment = $false
} |
    ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath (Join-Path $OutputDirectory 'wrapper-result.json') -Encoding utf8NoBOM
