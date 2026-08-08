#requires -Version 7.4
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)]
    [ValidateSet(
        'exchange.diagnose_mailbox',
        'exchange.get_mailbox_state',
        'exchange.get_mailbox_folder_health',
        'exchange.get_mailbox_permissions',
        'exchange.test_delegated_access',
        'exchange.grant_full_access',
        'exchange.revoke_full_access',
        'exchange.get_shared_mailbox_configuration',
        'exchange.check_forwarding',
        'exchange.verify_recipient_alignment'
    )]
    [string]$OperationId,

    [Parameter(Mandatory)]
    [ValidatePattern('^[^\s@]+@[^\s@]+\.[^\s@]+$')]
    [string]$Mailbox,

    [ValidatePattern('^$|^[^\s@]+@[^\s@]+\.[^\s@]+$')]
    [string]$Delegate = '',

    [bool]$AutoMapping = $false,
    [bool]$DryRun = $true,

    [ValidateSet('ManagedIdentity', 'Certificate')]
    [string]$AuthenticationMode = 'ManagedIdentity',

    [Parameter(Mandatory)]
    [string]$Organization,

    [string]$AppId = '',
    [string]$CertificateAssetName = '',
    [string]$ApprovalId = '',
    [string]$PlanHash = '',
    [string]$Reason = '',
    [string]$ChangeTicket = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-MutationApproval {
    param([string]$CurrentOperation)
    $mutations = @('exchange.grant_full_access', 'exchange.revoke_full_access')
    if ($CurrentOperation -in $mutations -and -not $DryRun) {
        if ([string]::IsNullOrWhiteSpace($ApprovalId) -or
            $PlanHash -notmatch '^[a-f0-9]{64}$' -or
            [string]::IsNullOrWhiteSpace($Reason) -or
            [string]::IsNullOrWhiteSpace($ChangeTicket)) {
            throw 'Mutation requires ApprovalId, PlanHash, Reason and ChangeTicket.'
        }
    }
}

function Connect-OptimusExchangeOnline {
    Import-Module ExchangeOnlineManagement -ErrorAction Stop
    if ($AuthenticationMode -eq 'ManagedIdentity') {
        Connect-ExchangeOnline -ManagedIdentity -Organization $Organization -ShowBanner:$false
        return
    }
    if ([string]::IsNullOrWhiteSpace($AppId) -or [string]::IsNullOrWhiteSpace($CertificateAssetName)) {
        throw 'Certificate authentication requires AppId and CertificateAssetName.'
    }
    $certificate = Get-AutomationCertificate -Name $CertificateAssetName
    if ($null -eq $certificate) {
        throw "Automation certificate asset '$CertificateAssetName' was not found."
    }
    Connect-ExchangeOnline -AppId $AppId -Certificate $certificate -Organization $Organization -ShowBanner:$false
}

function New-Result {
    param(
        [string]$State,
        [hashtable]$Data,
        [string[]]$Warnings = @()
    )
    [ordered]@{
        schemaVersion = '1.0'
        operationId = $OperationId
        state = $State
        dryRun = $DryRun
        mailbox = $Mailbox.ToLowerInvariant()
        delegate = if ($Delegate) { $Delegate.ToLowerInvariant() } else { $null }
        approvalId = if ($ApprovalId) { $ApprovalId } else { $null }
        planHash = if ($PlanHash) { $PlanHash } else { $null }
        data = $Data
        warnings = $Warnings
        completedAtUtc = [DateTimeOffset]::UtcNow.ToString('o')
    }
}

Assert-MutationApproval -CurrentOperation $OperationId
Connect-OptimusExchangeOnline
try {
    switch ($OperationId) {
        'exchange.diagnose_mailbox' {
            $warnings = [System.Collections.Generic.List[string]]::new()
            $recipient = Get-EXORecipient -Identity $Mailbox -ErrorAction Stop
            $mailboxObject = $null
            $statistics = $null
            $folderCount = $null
            try { $mailboxObject = Get-EXOMailbox -Identity $Mailbox -PropertySets Minimum,Delivery -ErrorAction Stop }
            catch { $warnings.Add("Mailbox probe failed: $($_.Exception.Message)") }
            try { $statistics = Get-EXOMailboxStatistics -Identity $Mailbox -ErrorAction Stop }
            catch { $warnings.Add("Store statistics probe failed: $($_.Exception.Message)") }
            try { $folderCount = @(Get-EXOMailboxFolderStatistics -Identity $Mailbox -ErrorAction Stop).Count }
            catch { $warnings.Add("Folder probe failed: $($_.Exception.Message)") }
            New-Result -State 'SUCCEEDED' -Warnings $warnings.ToArray() -Data ([ordered]@{
                recipientType = $recipient.RecipientType
                recipientTypeDetails = $recipient.RecipientTypeDetails
                externalDirectoryObjectId = $recipient.ExternalDirectoryObjectId
                exchangeGuid = $mailboxObject.ExchangeGuid
                primarySmtpAddress = $recipient.PrimarySmtpAddress
                mailboxFound = $null -ne $mailboxObject
                storeFound = $null -ne $statistics
                folderCount = $folderCount
            })
        }
        'exchange.get_mailbox_state' {
            $item = Get-EXOMailbox -Identity $Mailbox -PropertySets Minimum,Delivery -ErrorAction Stop
            New-Result -State 'SUCCEEDED' -Data ([ordered]@{
                displayName = $item.DisplayName
                recipientTypeDetails = $item.RecipientTypeDetails
                primarySmtpAddress = $item.PrimarySmtpAddress
                exchangeGuid = $item.ExchangeGuid
                forwardingAddress = $item.ForwardingAddress
                forwardingSmtpAddress = $item.ForwardingSmtpAddress
                deliverToMailboxAndForward = $item.DeliverToMailboxAndForward
            })
        }
        'exchange.get_mailbox_folder_health' {
            $folders = @(Get-EXOMailboxFolderStatistics -Identity $Mailbox -ErrorAction Stop)
            New-Result -State 'SUCCEEDED' -Data ([ordered]@{
                folderCount = $folders.Count
                standardFolders = @($folders | Where-Object FolderType -ne 'User Created' | Select-Object Name, FolderType, ItemsInFolder)
            })
        }
        'exchange.get_mailbox_permissions' {
            $permissions = @(Get-EXOMailboxPermission -Identity $Mailbox -ErrorAction Stop |
                Where-Object { -not $_.IsInherited } |
                Select-Object User, AccessRights, Deny, InheritanceType)
            New-Result -State 'SUCCEEDED' -Data ([ordered]@{ permissions = $permissions })
        }
        'exchange.test_delegated_access' {
            if ([string]::IsNullOrWhiteSpace($Delegate)) { throw 'Delegate is required.' }
            $permission = @(Get-EXOMailboxPermission -Identity $Mailbox -User $Delegate -ErrorAction SilentlyContinue |
                Where-Object { -not $_.Deny -and $_.AccessRights -contains 'FullAccess' })
            New-Result -State 'SUCCEEDED' -Data ([ordered]@{ hasFullAccess = $permission.Count -gt 0 })
        }
        'exchange.grant_full_access' {
            if ([string]::IsNullOrWhiteSpace($Delegate)) { throw 'Delegate is required.' }
            if ($DryRun) {
                New-Result -State 'PLANNED' -Data ([ordered]@{ action = 'Add-MailboxPermission'; autoMapping = $AutoMapping })
            }
            elseif ($PSCmdlet.ShouldProcess($Mailbox, "Grant FullAccess to $Delegate")) {
                Add-MailboxPermission -Identity $Mailbox -User $Delegate -AccessRights FullAccess -AutoMapping:$AutoMapping -Confirm:$false -ErrorAction Stop | Out-Null
                New-Result -State 'SUCCEEDED' -Data ([ordered]@{ granted = $true; autoMapping = $AutoMapping })
            }
        }
        'exchange.revoke_full_access' {
            if ([string]::IsNullOrWhiteSpace($Delegate)) { throw 'Delegate is required.' }
            if ($DryRun) {
                New-Result -State 'PLANNED' -Data ([ordered]@{ action = 'Remove-MailboxPermission' })
            }
            elseif ($PSCmdlet.ShouldProcess($Mailbox, "Revoke FullAccess from $Delegate")) {
                Remove-MailboxPermission -Identity $Mailbox -User $Delegate -AccessRights FullAccess -Confirm:$false -ErrorAction Stop
                New-Result -State 'SUCCEEDED' -Data ([ordered]@{ revoked = $true })
            }
        }
        'exchange.get_shared_mailbox_configuration' {
            $item = Get-EXOMailbox -Identity $Mailbox -PropertySets Minimum,Delivery -ErrorAction Stop
            New-Result -State 'SUCCEEDED' -Data ([ordered]@{
                recipientTypeDetails = $item.RecipientTypeDetails
                primarySmtpAddress = $item.PrimarySmtpAddress
                forwardingAddress = $item.ForwardingAddress
                forwardingSmtpAddress = $item.ForwardingSmtpAddress
                deliverToMailboxAndForward = $item.DeliverToMailboxAndForward
            })
        }
        'exchange.check_forwarding' {
            $item = Get-EXOMailbox -Identity $Mailbox -PropertySets Delivery -ErrorAction Stop
            New-Result -State 'SUCCEEDED' -Data ([ordered]@{
                forwardingAddress = $item.ForwardingAddress
                forwardingSmtpAddress = $item.ForwardingSmtpAddress
                deliverToMailboxAndForward = $item.DeliverToMailboxAndForward
            })
        }
        'exchange.verify_recipient_alignment' {
            $recipient = Get-EXORecipient -Identity $Mailbox -ErrorAction Stop
            $mailboxObject = Get-EXOMailbox -Identity $Mailbox -PropertySets Minimum -ErrorAction Stop
            New-Result -State 'SUCCEEDED' -Data ([ordered]@{
                smtpAligned = $recipient.PrimarySmtpAddress -eq $mailboxObject.PrimarySmtpAddress
                externalDirectoryObjectId = $recipient.ExternalDirectoryObjectId
                exchangeGuid = $mailboxObject.ExchangeGuid
                recipientTypeDetails = $mailboxObject.RecipientTypeDetails
            })
        }
    }
}
finally {
    Disconnect-ExchangeOnline -Confirm:$false -ErrorAction SilentlyContinue
}
