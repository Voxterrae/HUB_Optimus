#requires -Version 7.2
<#
.SYNOPSIS
  Reviewed, fail-closed wrapper for the Optimus Admin Gateway Dataverse schema applicator.

.DESCRIPTION
  With no mode switch, this wrapper performs only an offline contract verification.
  -Inspect performs the existing PAC read-only target preflight and a Web API read-only inspection.
  -Apply is the only metadata-writing mode and requires a private, expiring authorization file,
  the exact approved environment identity, a token file, and a durable evidence directory.
  -Rollback is restricted to components recorded as created by one apply journal and refuses
  deletion when any target table contains a business row.

  This script is published as source only. Committing or parsing it does not execute it.
#>

[CmdletBinding(DefaultParameterSetName = 'Offline')]
param(
    [Parameter(ParameterSetName = 'Inspect', Mandatory)] [switch]$Inspect,
    [Parameter(ParameterSetName = 'Apply', Mandatory)] [switch]$Apply,
    [Parameter(ParameterSetName = 'Rollback', Mandatory)] [switch]$Rollback,

    [Parameter(ParameterSetName = 'Inspect', Mandatory)]
    [Parameter(ParameterSetName = 'Apply', Mandatory)]
    [Parameter(ParameterSetName = 'Rollback', Mandatory)]
    [ValidatePattern('^https:[/][/][^/]+[.]dynamics[.]com/?$')]
    [string]$EnvironmentUrl,

    [Parameter(ParameterSetName = 'Inspect', Mandatory)]
    [Parameter(ParameterSetName = 'Apply', Mandatory)]
    [Parameter(ParameterSetName = 'Rollback', Mandatory)]
    [string]$ExpectedEnvironmentName,

    [Parameter(ParameterSetName = 'Inspect', Mandatory)]
    [Parameter(ParameterSetName = 'Apply', Mandatory)]
    [Parameter(ParameterSetName = 'Rollback', Mandatory)]
    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$ExpectedEnvironmentId,

    [Parameter(ParameterSetName = 'Inspect', Mandatory)]
    [Parameter(ParameterSetName = 'Apply', Mandatory)]
    [Parameter(ParameterSetName = 'Rollback', Mandatory)]
    [string]$AccessTokenFile,

    [Parameter(ParameterSetName = 'Inspect')]
    [Parameter(ParameterSetName = 'Apply')]
    [Parameter(ParameterSetName = 'Rollback')]
    [ValidateRange(0, 1000000)]
    [int]$ExpectedCurrentComponentCount = 0,

    [Parameter(ParameterSetName = 'Apply', Mandatory)]
    [Parameter(ParameterSetName = 'Rollback', Mandatory)]
    [string]$AuthorizationFile,

    [Parameter(ParameterSetName = 'Inspect', Mandatory)]
    [Parameter(ParameterSetName = 'Apply', Mandatory)]
    [Parameter(ParameterSetName = 'Rollback', Mandatory)]
    [string]$OutputDirectory,

    [Parameter(ParameterSetName = 'Rollback', Mandatory)]
    [string]$RollbackJournal,

    [string]$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path,
    [string]$PythonExecutable = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$AuthorizedBaseCommit = '4aab546e503e7bb2fda253eb0b20741b25b13a47'
$AuthorizedContractSha256 = 'ad0275c652f8877c2fc091dcdf66c8ab5fea6db3b2d4b64e847e17716c549d1d'
$AuthorizedPlanSha256 = 'dd1a4c4d2ab24f224172bb8f87f6c89d89f09e86ea36cc3886e8551d12751a06'
$SolutionUniqueName = 'OptimusAdminGateway'
$RepoRoot = (Resolve-Path (Join-Path $PackageRoot '../..')).Path

function Assert-PrivatePath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Description
    )
    $full = [IO.Path]::GetFullPath($Path)
    $root = [IO.Path]::GetFullPath($RepoRoot).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $prefix = $root + [IO.Path]::DirectorySeparatorChar
    if ($full.Equals($root, [StringComparison]::OrdinalIgnoreCase) -or
        $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Description must remain outside the repository: $full"
    }
    return $full
}

function Invoke-NativeText {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$Command,
        [Parameter(Mandatory)] [string[]]$Arguments,
        [string]$WorkingDirectory = ''
    )

    $previous = Get-Location
    try {
        if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
            Set-Location -LiteralPath $WorkingDirectory
        }
        $output = @(& $Command @Arguments 2>&1 | ForEach-Object { "$_" })
        $exitCode = $LASTEXITCODE
        $text = $output -join [Environment]::NewLine
        if ($exitCode -ne 0) {
            throw "Command failed ($exitCode): $Command $($Arguments -join ' ')`n$text"
        }
        return $text
    }
    finally {
        Set-Location -LiteralPath $previous
    }
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $python) {
        $python = Get-Command python3 -ErrorAction Stop
    }
    $PythonExecutable = $python.Source
}

$applicatorPath = Join-Path $PackageRoot 'scripts/apply-dataverse-schema.py'
$dryRunPath = Join-Path $PackageRoot 'dataverse/pac/Test-OptimusDataverseSchemaPlan.ps1'
$contractPath = Join-Path $PackageRoot 'dataverse/schema/optimus-admin-gateway.dataverse.json'
$planPath = Join-Path $PackageRoot 'dataverse/plans/optimus-admin-gateway.schema-plan.json'

foreach ($required in @($applicatorPath, $dryRunPath, $contractPath, $planPath)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required reviewed artifact is missing: $required"
    }
}

if ($PSCmdlet.ParameterSetName -eq 'Offline') {
    Invoke-NativeText -Command $PythonExecutable -Arguments @($applicatorPath) -WorkingDirectory $PackageRoot |
        Write-Host
    Write-Host ''
    Write-Host 'Mode: OFFLINE_REVIEW'
    Write-Host "Authorized base commit: $AuthorizedBaseCommit"
    Write-Host "Contract SHA-256:       $AuthorizedContractSha256"
    Write-Host "Plan SHA-256:           $AuthorizedPlanSha256"
    Write-Host 'Metadata writes:         0'
    exit 0
}

$EnvironmentUrl = $EnvironmentUrl.TrimEnd('/') + '/'
foreach ($path in @($AccessTokenFile, $OutputDirectory)) {
    if ([string]::IsNullOrWhiteSpace($path)) {
        throw 'Live modes require explicit private paths.'
    }
}
$AccessTokenFile = Assert-PrivatePath -Path $AccessTokenFile -Description 'Access-token file'
$OutputDirectory = Assert-PrivatePath -Path $OutputDirectory -Description 'Evidence output directory'
if (-not (Test-Path -LiteralPath $AccessTokenFile -PathType Leaf)) {
    throw "Access-token file was not found: $AccessTokenFile"
}
if ((Get-Item -LiteralPath $AccessTokenFile).Length -eq 0) {
    throw 'Access-token file is empty.'
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$pac = Join-Path $HOME '.dotnet/tools/pac'
if (-not (Test-Path -LiteralPath $pac)) {
    $pacCommand = Get-Command pac -ErrorAction Stop
    $pac = $pacCommand.Source
}

# Reuse the separately tested, PAC-only read boundary before any Web API mode.
& $dryRunPath `
    -EnvironmentUrl $EnvironmentUrl `
    -ExpectedEnvironmentName $ExpectedEnvironmentName `
    -ExpectedCurrentComponentCount $ExpectedCurrentComponentCount `
    -PackageRoot $PackageRoot `
    -PythonExecutable $PythonExecutable `
    -OutputDirectory (Join-Path $OutputDirectory 'target-preflight')
if ($LASTEXITCODE -ne 0) {
    throw 'Read-only PAC target preflight failed.'
}

$whoJson = Invoke-NativeText -Command $pac -Arguments @(
    'env', 'who', '--environment', $EnvironmentUrl, '--json'
)
$who = $whoJson | ConvertFrom-Json
if ([string]$who.EnvironmentId -ne $ExpectedEnvironmentId) {
    throw "Environment ID mismatch. Expected '$ExpectedEnvironmentId', actual '$($who.EnvironmentId)'."
}

$baseArguments = @(
    $applicatorPath,
    '--environment-url', $EnvironmentUrl,
    '--environment-id', $ExpectedEnvironmentId,
    '--access-token-file', $AccessTokenFile,
    '--output-directory', $OutputDirectory,
    '--expected-component-count', [string]$ExpectedCurrentComponentCount
)

if ($Inspect) {
    Invoke-NativeText -Command $PythonExecutable -Arguments @($baseArguments + '--inspect') -WorkingDirectory $PackageRoot |
        Write-Host
    Write-Host 'Inspection complete. Metadata writes: 0.'
    exit 0
}

$AuthorizationFile = Assert-PrivatePath -Path $AuthorizationFile -Description 'Authorization file'
if (-not (Test-Path -LiteralPath $AuthorizationFile -PathType Leaf)) {
    throw "Private authorization file was not found: $AuthorizationFile"
}

if ($Rollback) {
    $RollbackJournal = Assert-PrivatePath -Path $RollbackJournal -Description 'Rollback journal'
    if (-not (Test-Path -LiteralPath $RollbackJournal -PathType Leaf)) {
        throw "Rollback journal was not found: $RollbackJournal"
    }

    $preRollbackDirectory = Join-Path $OutputDirectory 'pre-rollback'
    $postRollbackDirectory = Join-Path $OutputDirectory 'post-rollback'
    New-Item -ItemType Directory -Path $preRollbackDirectory -Force | Out-Null
    New-Item -ItemType Directory -Path $postRollbackDirectory -Force | Out-Null
    $preRollbackZip = Join-Path $preRollbackDirectory 'OptimusAdminGateway.pre-rollback.unmanaged.zip'
    $postRollbackZip = Join-Path $postRollbackDirectory 'OptimusAdminGateway.post-rollback.unmanaged.zip'

    Invoke-NativeText -Command $pac -Arguments @(
        'solution', 'export',
        '--name', $SolutionUniqueName,
        '--path', $preRollbackZip,
        '--managed', 'false',
        '--environment', $EnvironmentUrl
    ) | Write-Host
    $preRollbackHash = (Get-FileHash -LiteralPath $preRollbackZip -Algorithm SHA256).Hash.ToLowerInvariant()
    $preRollbackHash | Set-Content -LiteralPath "$preRollbackZip.sha256.txt" -Encoding utf8NoBOM

    Invoke-NativeText -Command $PythonExecutable -Arguments @(
        $baseArguments +
        @('--authorization-file', $AuthorizationFile, '--rollback-journal', $RollbackJournal)
    ) -WorkingDirectory $PackageRoot | Write-Host

    Invoke-NativeText -Command $pac -Arguments @(
        'solution', 'export',
        '--name', $SolutionUniqueName,
        '--path', $postRollbackZip,
        '--managed', 'false',
        '--environment', $EnvironmentUrl
    ) | Write-Host
    $postRollbackHash = (Get-FileHash -LiteralPath $postRollbackZip -Algorithm SHA256).Hash.ToLowerInvariant()
    $postRollbackHash | Set-Content -LiteralPath "$postRollbackZip.sha256.txt" -Encoding utf8NoBOM

    [ordered]@{
        schemaVersion = '1.0'
        mode = 'ROLLBACK_COMPLETE'
        completedAtUtc = [DateTime]::UtcNow.ToString('o')
        authorizedBaseCommit = $AuthorizedBaseCommit
        contractSha256 = $AuthorizedContractSha256
        planSha256 = $AuthorizedPlanSha256
        environmentId = $ExpectedEnvironmentId
        solution = $SolutionUniqueName
        journalSha256 = (Get-FileHash -LiteralPath $RollbackJournal -Algorithm SHA256).Hash.ToLowerInvariant()
        preRollbackExportSha256 = $preRollbackHash
        postRollbackExportSha256 = $postRollbackHash
        rowsDeleted = 0
        merge = $false
        deployment = $false
    } | ConvertTo-Json -Depth 10 |
        Set-Content -LiteralPath (Join-Path $OutputDirectory 'rollback-wrapper-result.json') -Encoding utf8NoBOM

    Write-Host 'OPTIMUS DATAVERSE SCHEMA ROLLBACK — PASS' -ForegroundColor Green
    Write-Host "Pre-rollback export:  $preRollbackZip"
    Write-Host "Post-rollback export: $postRollbackZip"
    Write-Host 'Rows deleted:          0'
    Write-Host 'Merge:                 no'
    Write-Host 'Deployment:            no'
    exit 0
}

# Apply is deliberately gated by a pre-export. The exported ZIP remains private.
$preApplyDirectory = Join-Path $OutputDirectory 'pre-apply'
$postApplyDirectory = Join-Path $OutputDirectory 'post-apply'
New-Item -ItemType Directory -Path $preApplyDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $postApplyDirectory -Force | Out-Null
$preApplyZip = Join-Path $preApplyDirectory 'OptimusAdminGateway.pre-apply.unmanaged.zip'
$postApplyZip = Join-Path $postApplyDirectory 'OptimusAdminGateway.post-apply.unmanaged.zip'

Invoke-NativeText -Command $pac -Arguments @(
    'solution', 'export',
    '--name', $SolutionUniqueName,
    '--path', $preApplyZip,
    '--managed', 'false',
    '--environment', $EnvironmentUrl
) | Write-Host
$preHash = (Get-FileHash -LiteralPath $preApplyZip -Algorithm SHA256).Hash.ToLowerInvariant()
$preHash | Set-Content -LiteralPath "$preApplyZip.sha256.txt" -Encoding utf8NoBOM

Invoke-NativeText -Command $PythonExecutable -Arguments @(
    $baseArguments + @('--authorization-file', $AuthorizationFile, '--apply')
) -WorkingDirectory $PackageRoot | Write-Host

Invoke-NativeText -Command $pac -Arguments @(
    'solution', 'export',
    '--name', $SolutionUniqueName,
    '--path', $postApplyZip,
    '--managed', 'false',
    '--environment', $EnvironmentUrl
) | Write-Host
$postHash = (Get-FileHash -LiteralPath $postApplyZip -Algorithm SHA256).Hash.ToLowerInvariant()
$postHash | Set-Content -LiteralPath "$postApplyZip.sha256.txt" -Encoding utf8NoBOM

[ordered]@{
    schemaVersion = '1.0'
    mode = 'APPLY_COMPLETE'
    completedAtUtc = [DateTime]::UtcNow.ToString('o')
    authorizedBaseCommit = $AuthorizedBaseCommit
    contractSha256 = $AuthorizedContractSha256
    planSha256 = $AuthorizedPlanSha256
    environmentId = $ExpectedEnvironmentId
    solution = $SolutionUniqueName
    preApplyExportSha256 = $preHash
    postApplyExportSha256 = $postHash
    rowsCreated = 0
    merge = $false
    deployment = $false
} | ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath (Join-Path $OutputDirectory 'apply-wrapper-result.json') -Encoding utf8NoBOM

Write-Host 'OPTIMUS DATAVERSE SCHEMA APPLY — PASS' -ForegroundColor Green
Write-Host "Pre-apply export:  $preApplyZip"
Write-Host "Post-apply export: $postApplyZip"
Write-Host 'Rows created:      0'
Write-Host 'Merge:             no'
Write-Host 'Deployment:        no'
