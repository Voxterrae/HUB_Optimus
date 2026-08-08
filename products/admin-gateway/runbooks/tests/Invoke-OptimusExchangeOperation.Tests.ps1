#requires -Version 7.4
Describe 'Optimus Exchange runbook safety contract' {
    $scriptPath = Join-Path $PSScriptRoot '..' 'Invoke-OptimusExchangeOperation.ps1'
    $content = Get-Content -Raw -LiteralPath $scriptPath

    It 'uses an allowlisted ValidateSet' {
        $content | Should -Match '\[ValidateSet\('
        $content | Should -Match 'exchange\.diagnose_mailbox'
        $content | Should -Not -Match 'Invoke-Expression'
    }

    It 'defaults to DryRun' {
        $content | Should -Match '\[bool\]\$DryRun = \$true'
    }

    It 'requires approval material for live mutations' {
        $content | Should -Match 'Mutation requires ApprovalId, PlanHash, Reason and ChangeTicket'
    }
}
