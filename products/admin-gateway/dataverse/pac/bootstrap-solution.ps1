#requires -Version 7.4
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)] [string]$EnvironmentUrl,
    [string]$PublisherName = 'Optimus',
    [string]$PublisherPrefix = 'opt',
    [string]$SolutionName = 'OptimusAdminGateway',
    [string]$OutputDirectory = './out/OptimusAdminGateway',
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($PublisherPrefix -notmatch '^[A-Za-z][A-Za-z0-9]{1,7}$') {
    throw 'PublisherPrefix must be 2-8 alphanumeric characters and start with a letter.'
}

$plan = @(
    [ordered]@{
        step = 'CreateOrSelectPacAuthenticationProfile'
        executable = 'pac'
        arguments = @('auth', 'create', '--environment', $EnvironmentUrl)
        display = "pac auth create --environment `"$EnvironmentUrl`""
    },
    [ordered]@{
        step = 'InitializeSolutionWorkspace'
        executable = 'pac'
        arguments = @(
            'solution', 'init',
            '--publisher-name', $PublisherName,
            '--publisher-prefix', $PublisherPrefix,
            '--outputDirectory', $OutputDirectory
        )
        display = "pac solution init --publisher-name `"$PublisherName`" --publisher-prefix `"$PublisherPrefix`" --outputDirectory `"$OutputDirectory`""
    }
)

if (-not $Apply) {
    [ordered]@{
        dryRun = $true
        solution = $SolutionName
        environment = $EnvironmentUrl
        plan = @($plan | ForEach-Object {
            [ordered]@{
                step = $_.step
                command = $_.display
            }
        })
        note = 'Schema creation remains a reviewed follow-up; this bootstrap does not alter Dataverse in DryRun.'
    } | ConvertTo-Json -Depth 8
    return
}

foreach ($step in $plan) {
    if ($step.executable -ne 'pac') {
        throw "Unexpected executable in reviewed plan: $($step.executable)"
    }

    if ($PSCmdlet.ShouldProcess($EnvironmentUrl, $step.display)) {
        [string[]]$arguments = $step.arguments
        & pac @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "PAC step failed: $($step.step)"
        }
    }
}
