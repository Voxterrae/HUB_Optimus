#requires -Version 7.2
<#
.SYNOPSIS
  Performs a read-only, fail-closed Dataverse schema dry-run preflight.

.DESCRIPTION
  This script:
  - verifies the exact target environment and solution/publisher baseline;
  - verifies the deterministic public schema contract and plan;
  - counts current solution components;
  - writes private dry-run evidence outside the repository.

  It never creates or updates Dataverse metadata or rows. It contains no Apply
  switch and invokes only PAC read operations (`env who` and `env fetch --xmlFile`).
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$EnvironmentUrl,
    [Parameter(Mandatory)] [string]$ExpectedEnvironmentName,
    [string]$ExpectedSolutionUniqueName = 'OptimusAdminGateway',
    [string]$ExpectedPublisherUniqueName = 'HUB_Optimus',
    [string]$ExpectedPublisherPrefix = 'opt',
    [string]$ExpectedVersion = '0.1.0.0',
    [int]$ExpectedCurrentComponentCount = 0,
    [string]$PackageRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path,
    [string]$PythonExecutable = '',
    [string]$OutputDirectory = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-NativeText {
    param(
        [Parameter(Mandatory)] [string]$Command,
        [Parameter(Mandatory)] [string[]]$Arguments
    )
    $output = @(& $Command @Arguments 2>&1 | ForEach-Object { "$_" })
    $exitCode = $LASTEXITCODE
    $text = $output -join [Environment]::NewLine
    if ($exitCode -ne 0) {
        throw "Read-only command failed ($exitCode): $Command $($Arguments -join ' ')`n$text"
    }
    return $text
}

$pac = Join-Path $HOME '.dotnet/tools/pac'
if (-not (Test-Path -LiteralPath $pac)) {
    $pacCommand = Get-Command pac -ErrorAction SilentlyContinue
    if ($null -eq $pacCommand) {
        throw 'PAC CLI was not found.'
    }
    $pac = $pacCommand.Source
}

if ([string]::IsNullOrWhiteSpace($PythonExecutable)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        $pythonCommand = Get-Command python3 -ErrorAction Stop
    }
    $PythonExecutable = $pythonCommand.Source
}
if (-not (Test-Path -LiteralPath $PythonExecutable) -and $null -eq (Get-Command $PythonExecutable -ErrorAction SilentlyContinue)) {
    throw "Python executable was not found: $PythonExecutable"
}

$contractPath = Join-Path $PackageRoot 'dataverse/schema/optimus-admin-gateway.dataverse.json'
$metaSchemaPath = Join-Path $PackageRoot 'dataverse/schema/optimus-admin-gateway.dataverse.schema.json'
$planPath = Join-Path $PackageRoot 'dataverse/plans/optimus-admin-gateway.schema-plan.json'
$builderPath = Join-Path $PackageRoot 'scripts/build-dataverse-schema-plan.py'

foreach ($requiredPath in @($contractPath, $metaSchemaPath, $planPath, $builderPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required reviewed artifact not found: $requiredPath"
    }
}

$whoText = Invoke-NativeText -Command $pac -Arguments @(
    'env', 'who',
    '--environment', $EnvironmentUrl,
    '--json'
)
$who = $whoText | ConvertFrom-Json

$normalizedExpectedUrl = $EnvironmentUrl.TrimEnd('/') + '/'
$normalizedActualUrl = ([string]$who.OrgUrl).TrimEnd('/') + '/'
if ($normalizedActualUrl -ne $normalizedExpectedUrl) {
    throw "Environment URL mismatch. Expected '$normalizedExpectedUrl', actual '$normalizedActualUrl'."
}
if ([string]$who.FriendlyName -ne $ExpectedEnvironmentName) {
    throw "Environment name mismatch. Expected '$ExpectedEnvironmentName', actual '$($who.FriendlyName)'."
}

$solutionFetch = @"
<fetch mapping='logical'>
  <entity name='solution'>
    <attribute name='friendlyname'/>
    <attribute name='uniquename'/>
    <attribute name='version'/>
    <attribute name='ismanaged'/>
    <filter>
      <condition attribute='uniquename' operator='eq' value='$ExpectedSolutionUniqueName'/>
    </filter>
    <link-entity name='publisher' from='publisherid' to='publisherid' link-type='inner'>
      <attribute name='uniquename' alias='publisher_unique'/>
      <attribute name='customizationprefix' alias='publisher_prefix'/>
      <attribute name='customizationoptionvalueprefix' alias='choice_prefix'/>
    </link-entity>
  </entity>
</fetch>
"@

$componentFetch = @"
<fetch mapping='logical' aggregate='true'>
  <entity name='solutioncomponent'>
    <attribute name='solutioncomponentid' alias='component_count' aggregate='count'/>
    <link-entity name='solution' from='solutionid' to='solutionid' link-type='inner'>
      <filter>
        <condition attribute='uniquename' operator='eq' value='$ExpectedSolutionUniqueName'/>
      </filter>
    </link-entity>
  </entity>
</fetch>
"@

# PAC 1.52.x can split multiline FetchXML passed through --xml when invoked
# from PowerShell. Use the documented --xmlFile transport so each query is
# handed to PAC as one unambiguous file path. The files are session-local and
# contain only the reviewed solution unique name, never tenant credentials.
$fetchXmlRoot = Join-Path ([IO.Path]::GetTempPath()) (
    'optimus-dataverse-fetchxml-' + [Guid]::NewGuid().ToString('N')
)
$solutionFetchPath = Join-Path $fetchXmlRoot 'solution-baseline.fetch.xml'
$componentFetchPath = Join-Path $fetchXmlRoot 'solution-components.fetch.xml'
$solutionText = ''
$componentText = ''

New-Item -ItemType Directory -Path $fetchXmlRoot -Force | Out-Null
try {
    $solutionFetch | Set-Content -LiteralPath $solutionFetchPath -Encoding utf8NoBOM
    $componentFetch | Set-Content -LiteralPath $componentFetchPath -Encoding utf8NoBOM

    $solutionText = Invoke-NativeText -Command $pac -Arguments @(
        'env', 'fetch',
        '--environment', $EnvironmentUrl,
        '--xmlFile', $solutionFetchPath
    )

    $componentText = Invoke-NativeText -Command $pac -Arguments @(
        'env', 'fetch',
        '--environment', $EnvironmentUrl,
        '--xmlFile', $componentFetchPath
    )
}
finally {
    Remove-Item -LiteralPath $fetchXmlRoot -Recurse -Force -ErrorAction SilentlyContinue
}

foreach ($requiredValue in @(
    $ExpectedSolutionUniqueName,
    $ExpectedPublisherUniqueName,
    $ExpectedPublisherPrefix,
    $ExpectedVersion
)) {
    if ($solutionText -notmatch [regex]::Escape($requiredValue)) {
        throw "Expected solution baseline value was not found: $requiredValue"
    }
}

$numberMatches = [regex]::Matches($componentText, '(?m)^\s*([0-9]+)\s*$')
if ($numberMatches.Count -eq 0) {
    throw "Could not parse the current solution component count.`n$componentText"
}
$currentComponentCount = [int]$numberMatches[$numberMatches.Count - 1].Groups[1].Value
if ($currentComponentCount -ne $ExpectedCurrentComponentCount) {
    throw "Solution component count drift. Expected $ExpectedCurrentComponentCount, actual $currentComponentCount."
}

$builderResult = Invoke-NativeText -Command $PythonExecutable -Arguments @(
    $builderPath
)

$contract = Get-Content -LiteralPath $contractPath -Raw | ConvertFrom-Json
$plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json

if ($plan.mode -ne 'DRY_RUN' -or $plan.apply -ne $false) {
    throw 'Reviewed plan is not a non-applying dry run.'
}
if ($plan.safety.containsExecutableMutationCommands -ne $false) {
    throw 'Reviewed plan unexpectedly declares executable mutation commands.'
}
if ($plan.safety.tablesCreatedByThisPlan -ne 0 -or $plan.safety.rowsCreatedByThisPlan -ne 0) {
    throw 'Reviewed dry-run plan claims environment creation.'
}

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
    $OutputDirectory = Join-Path $HOME "clouddrive/Optimus/Dataverse/DryRuns/OptimusAdminGateway/$stamp"
}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$privateBinding = [ordered]@{
    schemaVersion = '1.0'
    generatedAtUtc = [DateTime]::UtcNow.ToString('o')
    mode = 'READ_ONLY_DRY_RUN'
    environment = [ordered]@{
        friendlyName = $who.FriendlyName
        environmentId = $who.EnvironmentId
        organizationId = $who.OrgId
        organizationUniqueName = $who.UniqueName
        url = $normalizedActualUrl
        userEmail = $who.UserEmail
    }
    solution = [ordered]@{
        uniqueName = $ExpectedSolutionUniqueName
        publisher = $ExpectedPublisherUniqueName
        prefix = $ExpectedPublisherPrefix
        version = $ExpectedVersion
        currentComponentCount = $currentComponentCount
    }
    publicPlan = [ordered]@{
        contractSha256 = $plan.contractSha256
        planHash = $plan.planHash
        counts = $plan.counts
    }
    result = 'PASS'
    changesPerformed = @(
        'Read environment identity.',
        'Read solution and publisher baseline.',
        'Read current solution component count.',
        'Verified deterministic public contract and dry-run plan.'
    )
    changesNotPerformed = @(
        'No global choice created.',
        'No table or column created.',
        'No alternate key or relationship created.',
        'No row created or updated.',
        'No customization published.',
        'No solution imported, exported or deployed.'
    )
}

$privateBindingPath = Join-Path $OutputDirectory 'private-environment-binding.json'
$privateBinding | ConvertTo-Json -Depth 20 |
    Set-Content -LiteralPath $privateBindingPath -Encoding utf8NoBOM

Copy-Item -LiteralPath $planPath -Destination (Join-Path $OutputDirectory 'public-schema-plan.json') -Force
Copy-Item -LiteralPath $contractPath -Destination (Join-Path $OutputDirectory 'public-schema-contract.json') -Force
$solutionText | Set-Content -LiteralPath (Join-Path $OutputDirectory 'solution-baseline.txt') -Encoding utf8NoBOM
$componentText | Set-Content -LiteralPath (Join-Path $OutputDirectory 'solution-components.txt') -Encoding utf8NoBOM

$summary = @"
OPTIMUS ADMIN GATEWAY — DATAVERSE SCHEMA DRY RUN
Status:                  PASS
Mode:                    READ_ONLY_DRY_RUN
Environment:             $($who.FriendlyName)
Environment ID:          $($who.EnvironmentId)
Dataverse URL:           $normalizedActualUrl
Solution:                $ExpectedSolutionUniqueName
Publisher:               $ExpectedPublisherUniqueName
Prefix:                  $ExpectedPublisherPrefix
Current components:      $currentComponentCount
Planned global choices:  $($plan.counts.globalChoices)
Planned tables:          $($plan.counts.tables)
Planned scalar columns:  $($plan.counts.scalarColumns)
Planned lookup columns:  $($plan.counts.lookupColumns)
Planned alternate keys:  $($plan.counts.alternateKeys)
Planned relationships:   $($plan.counts.relationships)
Planned actions:         $($plan.counts.plannedActions)
Contract SHA-256:        $($plan.contractSha256)
Plan SHA-256:            $($plan.planHash)
Tables created:          0
Rows created:            0
Merge:                   no
Deployment:              no
Private evidence:        $OutputDirectory
"@

$summaryPath = Join-Path $OutputDirectory 'SUMMARY.txt'
$summary | Set-Content -LiteralPath $summaryPath -Encoding utf8NoBOM
Write-Host $summary
