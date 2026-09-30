#requires -Version 7.4
Describe 'Optimus Exchange runbook safety contract' {
    BeforeAll {
        $scriptPath = Join-Path $PSScriptRoot '..' 'Invoke-OptimusExchangeOperation.ps1'
        $content = Get-Content -Raw -LiteralPath $scriptPath
    }

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


Describe 'Optimus Exchange offline behavior' {
    BeforeAll {
        $scriptPath = Join-Path $PSScriptRoot '..' 'Invoke-OptimusExchangeOperation.ps1'
        function Connect-ExchangeOnline {
            [CmdletBinding()]
            param([switch]$ManagedIdentity, [string]$Organization, [bool]$ShowBanner, [string]$AppId, $Certificate)
            throw 'Unexpected real connection'
        }
        function Disconnect-ExchangeOnline {
            [CmdletBinding()]
            param([switch]$Confirm)
        }
        function Get-AutomationCertificate {
            param([string]$Name)
            throw 'Unexpected certificate access'
        }
        function Get-EXORecipient {
            [CmdletBinding()]
            param([string]$Identity)
        }
        function Get-EXOMailbox {
            [CmdletBinding()]
            param([string]$Identity, [string[]]$PropertySets)
        }
        function Get-EXOMailboxStatistics {
            [CmdletBinding()]
            param([string]$Identity)
        }
        function Get-EXOMailboxFolderStatistics {
            [CmdletBinding()]
            param([string]$Identity)
        }
    }

    BeforeEach {
        Mock Import-Module { throw 'Unexpected Exchange module access' } -ParameterFilter { $Name -eq 'ExchangeOnlineManagement' }
        Mock Connect-ExchangeOnline { throw 'Unexpected Exchange connection' }
        Mock Disconnect-ExchangeOnline {}
        Mock Get-AutomationCertificate { throw 'Unexpected certificate access' }
    }

    It 'returns both mutation previews without importing or connecting to Exchange' {
        foreach ($operation in @('exchange.grant_full_access', 'exchange.revoke_full_access')) {
            $result = & $scriptPath -OperationId $operation -Mailbox 'pilot@example.invalid' -Delegate 'owner@example.invalid' -Organization 'synthetic.invalid'
            $result.state | Should -Be 'PLANNED'
            $result.dryRun | Should -BeTrue
            $result.mailbox | Should -Be 'pilot@example.invalid'
        }
        Should -Invoke Import-Module -Times 0 -Exactly -ParameterFilter { $Name -eq 'ExchangeOnlineManagement' }
        Should -Invoke Connect-ExchangeOnline -Times 0 -Exactly
    }

    It 'does not read a certificate for a mutation preview' {
        $result = & $scriptPath -OperationId 'exchange.grant_full_access' -Mailbox 'pilot@example.invalid' -Delegate 'owner@example.invalid' -Organization 'synthetic.invalid' -AuthenticationMode Certificate
        $result.state | Should -Be 'PLANNED'
        Should -Invoke Get-AutomationCertificate -Times 0 -Exactly
        Should -Invoke Connect-ExchangeOnline -Times 0 -Exactly
    }

    It 'rejects a missing delegate before any connection' {
        { & $scriptPath -OperationId 'exchange.test_delegated_access' -Mailbox 'pilot@example.invalid' -Organization 'synthetic.invalid' } | Should -Throw '*Delegate is required*'
        Should -Invoke Connect-ExchangeOnline -Times 0 -Exactly
    }

    It 'rejects a live mutation without approval before any connection' {
        { & $scriptPath -OperationId 'exchange.grant_full_access' -Mailbox 'pilot@example.invalid' -Delegate 'owner@example.invalid' -Organization 'synthetic.invalid' -DryRun:$false } | Should -Throw '*Mutation requires*'
        Should -Invoke Connect-ExchangeOnline -Times 0 -Exactly
    }

    It 'returns diagnostic warnings when the mailbox and store probes fail' {
        Mock Import-Module {} -ParameterFilter { $Name -eq 'ExchangeOnlineManagement' }
        Mock Connect-ExchangeOnline {}
        Mock Get-EXORecipient {
            [pscustomobject]@{
                RecipientType = 'User'
                RecipientTypeDetails = 'UserMailbox'
                ExternalDirectoryObjectId = 'synthetic-object'
                PrimarySmtpAddress = 'pilot@example.invalid'
            }
        }
        Mock Get-EXOMailbox { throw 'Synthetic mailbox probe failure' }
        Mock Get-EXOMailboxStatistics { throw 'Synthetic statistics probe failure' }
        Mock Get-EXOMailboxFolderStatistics { throw 'Synthetic folder probe failure' }

        $result = & $scriptPath -OperationId 'exchange.diagnose_mailbox' -Mailbox 'pilot@example.invalid' -Organization 'synthetic.invalid'
        $result.state | Should -Be 'SUCCEEDED'
        $result.data.mailboxFound | Should -BeFalse
        $result.data.storeFound | Should -BeFalse
        $result.data.exchangeGuid | Should -BeNullOrEmpty
        $result.warnings.Count | Should -Be 3
        Should -Invoke Disconnect-ExchangeOnline -Times 1 -Exactly
    }
}
