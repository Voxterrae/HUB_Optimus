#requires -Version 7.0
# Owned, disposable Windows fixtures; no system ancestor ACLs are changed.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ScratchDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$source=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Run-RelayInventory.ps1') -Raw
$blocks=[regex]::Matches($source,"(?s)Add-Type -TypeDefinition @'\r?\n(.*?)\r?\n'@")
if ($blocks.Count -ne 2) { throw 'Expected two helper definitions.' }
foreach ($block in $blocks) { Add-Type -TypeDefinition $block.Groups[1].Value }
[void](New-Item -ItemType Directory -Path $ScratchDirectory)
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$lease=$null
try {
    $destination=Join-Path $ScratchDirectory 'private'
    $lease=[HubRelayPrivateDirectory]::Create($destination,$identity)
    if (-not [IO.Directory]::Exists($destination)) { throw 'Atomic private creation failed.' }
    $refused=$false
    try { [IO.Directory]::Move($destination,$destination+'-moved') } catch { $refused=$true }
    if (-not $refused) { throw 'Held namespace allowed rename.' }
    $lease.Dispose()
    if (-not $lease.CleanupComplete) { throw 'Lease cleanup failed.' }
    $lease=$null
    if (-not (Get-Acl -LiteralPath $destination).AreAccessRulesProtected) { throw 'Private DACL was not protected.' }
    [IO.Directory]::Move($destination,$destination+'-moved')
    $refused=$false
    try { $unexpected=[HubRelayPrivateDirectory]::Create($destination+'-moved',$identity); $unexpected.Dispose() } catch { $refused=$true }
    if (-not $refused) { throw 'Existing destination accepted.' }
    # A permissive owned parent must refuse. Never change a system/user ancestor.
    $unsafe=Join-Path $ScratchDirectory 'permissive'
    [void](New-Item -ItemType Directory -Path $unsafe)
    $acl=Get-Acl -LiteralPath $unsafe
    $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new(
        [Security.Principal.SecurityIdentifier]::new('S-1-1-0'),
        [Security.AccessControl.FileSystemRights]::Modify,[Security.AccessControl.AccessControlType]::Allow))
    Set-Acl -LiteralPath $unsafe -AclObject $acl
    $refused=$false
    try { $unexpected=[HubRelayPrivateDirectory]::Create((Join-Path $unsafe 'child'),$identity); $unexpected.Dispose() } catch { $refused=$true }
    if (-not $refused) { throw 'Writable parent accepted.' }
    $junction=Join-Path $ScratchDirectory 'junction'
    [void](New-Item -ItemType Junction -Path $junction -Target ($destination+'-moved'))
    $refused=$false
    try { $unexpected=[HubRelayPrivateDirectory]::Create((Join-Path $junction 'child'),$identity); $unexpected.Dispose() } catch { $refused=$true }
    if (-not $refused) { throw 'Reparse namespace accepted.' }
    Write-Output 'Private namespace fixtures: 5 passed.' 
    $fixture=Join-Path $ScratchDirectory 'fixture.cs'
    @'
using System;
using System.Threading;
public static class Fixture {
    public static void Main(string[] args) {
        string mode=Environment.GetEnvironmentVariable("HUB_RELAY_OWNED_FIXTURE");
        if (mode=="info") {Console.Write("owned informational fixture"); Environment.Exit(7); return;}
        if (mode=="metadata") {Console.Write(new string('a',40)+"\n"); return;}
        if (mode=="arguments") {
            Environment.Exit(args.Length==3 && args[0]=="endslash\\" && args[1]=="space value" && args[2]=="" ? 0 : 3); return;
        }
        if (mode=="timeout") {Thread.Sleep(5000); return;}
        if (mode=="stderr") {byte[] b=new byte[8192]; for(int i=0;i<100;++i) Console.OpenStandardError().Write(b,0,b.Length); return;}
        if (mode=="flood") {byte[] b=new byte[8192]; for(int i=0;i<5000;++i) Console.OpenStandardOutput().Write(b,0,b.Length); return;}
        Console.Write("{}");
    }
}
'@ | Set-Content -LiteralPath $fixture -Encoding utf8
    $fixtureExe=Join-Path $ScratchDirectory 'fixture.exe'
    & (Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe') /nologo /target:exe ('/out:'+$fixtureExe) $fixture *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Owned child fixture compile failed.' }
    # Exercise the actual build-child function with terminal backslash, space
    # and empty arguments. Parse only this reviewed local script definition.
    $tokens=$null; $parseErrors=$null
    $buildAst=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Build-RelayInventory.ps1'),[ref]$tokens,[ref]$parseErrors)
    if ($parseErrors.Count -ne 0) { throw 'Build recipe parse failed.' }
    $functions=@($buildAst.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq 'Invoke-BuildChild'},$false))
    if ($functions.Count -ne 1) { throw 'Build child definition missing.' }
    . ([scriptblock]::Create($functions[0].Extent.Text))
    $script:crate=[IO.Directory]::GetParent($PSScriptRoot).FullName
    [void](Invoke-BuildChild $fixtureExe @('endslash\','space value','') @{ HUB_RELAY_OWNED_FIXTURE='arguments' })
    Write-Output 'Build child argument fixture: 1 passed.'
    $metadata=Invoke-BuildChild $fixtureExe @() @{ HUB_RELAY_OWNED_FIXTURE='metadata' }
    if ($metadata -isnot [string] -or $metadata.Trim() -cne ('a'*40)) { throw 'Build stdout metadata failed.' }
    $previousMode=[Environment]::GetEnvironmentVariable('HUB_RELAY_OWNED_FIXTURE')
    try {
        [Environment]::SetEnvironmentVariable('HUB_RELAY_OWNED_FIXTURE','metadata')
        $metadata=Invoke-BuildChild $fixtureExe @() @{}
        if ($metadata -isnot [string] -or $metadata.Trim() -cne ('a'*40)) { throw 'Build empty environment metadata failed.' }
    } finally { [Environment]::SetEnvironmentVariable('HUB_RELAY_OWNED_FIXTURE',$previousMode) }
    Write-Output 'Build child stdout fixtures: 2 passed.'
    $refused=$false
    try { [void](Invoke-BuildChild $fixtureExe @() @{ HUB_RELAY_OWNED_FIXTURE='info' }) } catch { $refused=$_.Exception.Message -ceq 'Build child failed' }
    if (-not $refused) { throw 'Nonzero build child accepted.' }
    $info=Invoke-BuildChild $fixtureExe @() @{ HUB_RELAY_OWNED_FIXTURE='info' } -InformationalQuery
    if ($info -cne 'owned informational fixture') { throw 'Informational child output failed.' }
    Write-Output 'Build child exit-policy fixtures: 2 passed.'
    $saved=[Environment]::GetEnvironmentVariable('HUB_RELAY_OWNED_FIXTURE')
    try {
        foreach ($mode in @('complete','timeout','flood','stderr')) {
            [Environment]::SetEnvironmentVariable('HUB_RELAY_OWNED_FIXTURE',$mode)
            $output=Join-Path $ScratchDirectory ($mode+'.bin')
            $errorOutput=Join-Path $ScratchDirectory ($mode+'.err')
            $seconds=if ($mode -eq 'timeout') {1} else {15}
            $result=[HubRelayCapture]::Run($fixtureExe,$output,$errorOutput,$seconds)
            if ($mode -eq 'complete') {
                if (-not $result.Complete -or $result.ExitCode -ne 0 -or ([IO.FileInfo]::new($output)).Length -ne 2) { throw 'Complete transfer failed.' }
            } elseif ($result.Complete) { throw 'Incomplete transfer accepted.' }
            $retained=([IO.FileInfo]::new($output)).Length
            $retainedErrors=([IO.FileInfo]::new($errorOutput)).Length
            if ($retained -gt 33554432 -or $retainedErrors -gt 65536) { throw 'Transfer cap exceeded.' }
            if ($mode -eq 'flood' -and $retained -ne 33554432) { throw 'Stdout overflow cap was not reached.' }
            if ($mode -eq 'stderr' -and $retainedErrors -ne 65536) { throw 'Stderr overflow cap was not reached.' }
        }
    } finally { [Environment]::SetEnvironmentVariable('HUB_RELAY_OWNED_FIXTURE',$saved) }
    Write-Output 'Capture transfer fixtures: 4 passed.'
} finally {
    if ($null -ne $lease) {$lease.Dispose(); if (-not $lease.CleanupComplete) {throw 'Lease cleanup failed.'}}
}
