#requires -Version 5.1
<# Reproducible-build recipe candidate; version/hash metadata are claims, not trust. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{40}$')][string]$SourceCommit,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{64}$')][string]$PolicySha256,
    [Parameter(Mandatory = $true)][string]$LinkerVersion,
    [Parameter(Mandatory = $true)][string]$SdkVersion,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [string]$PythonExecutable = 'python.exe'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-BuildChild([string]$Executable, [string[]]$Arguments, [hashtable]$EnvironmentValues) {
    # All arguments below are fixed or validated paths/metadata; no shell/evaluation.
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.WorkingDirectory = $script:crate
    $quoted = foreach ($argument in $Arguments) {
        if ($argument.Contains('"') -or $argument.Contains("`r") -or $argument.Contains("`n")) { throw 'Invalid build argument' }
        '"' + $argument + '"'
    }
    $start.Arguments = $quoted -join ' '
    foreach ($name in $EnvironmentValues.Keys) { $start.EnvironmentVariables[$name] = $EnvironmentValues[$name] }
    $child = [Diagnostics.Process]::new()
    $child.StartInfo = $start
    try {
        [void]$child.Start()
        $stdout = $child.StandardOutput.ReadToEndAsync()
        $stderr = $child.StandardError.ReadToEndAsync()
        if (-not $child.WaitForExit(600000)) { try { $child.Kill() } catch {}; throw 'Build timeout' }
        $text = $stdout.GetAwaiter().GetResult()
        $diagnostics = $stderr.GetAwaiter().GetResult()
        if ($child.ExitCode -ne 0) { throw 'Build child failed' }
        return $text + $diagnostics
    } finally { $child.Dispose() }
}

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or -not [Environment]::Is64BitProcess) { throw 'Unsupported platform' }
    foreach ($name in @('RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS', 'RUSTC_WRAPPER', 'RUSTC_WORKSPACE_WRAPPER', 'RUSTC')) {
        if (-not [string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($name))) { throw 'Conflicting Rust settings' }
    }
    $script:crate = [IO.Directory]::GetParent($PSScriptRoot).FullName
    $sourceRoot = [IO.Path]::GetFullPath((Join-Path $crate '../../../..'))
    $output = [IO.Path]::GetFullPath($OutputDirectory)
    if ($output -notmatch '^[A-Za-z]:\\' -or [IO.Directory]::Exists($output) -or [IO.File]::Exists($output)) { throw 'New local output directory required' }
    $parent = [IO.Directory]::GetParent($output)
    if ($null -eq $parent -or -not $parent.Exists) { throw 'Existing output parent required' }
    $node = $parent
    while ($null -ne $node) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Reparse output refused' }
        $node = $node.Parent
    }
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($output))
    if ($drive.DriveType -ne [IO.DriveType]::Fixed -or $drive.AvailableFreeSpace -lt 2147483648) { throw 'Capacity floor not met' }
    $cargo = (Get-Command cargo.exe -CommandType Application -ErrorAction Stop).Source
    $rustc = (Get-Command rustc.exe -CommandType Application -ErrorAction Stop).Source
    $rustup = (Get-Command rustup.exe -CommandType Application -ErrorAction Stop).Source
    $linker = (Get-Command link.exe -CommandType Application -ErrorAction Stop).Source
    $git = (Get-Command git.exe -CommandType Application -ErrorAction Stop).Source
    $python = (Get-Command $PythonExecutable -CommandType Application -ErrorAction Stop).Source
    $actualSource = (Invoke-BuildChild $git @('-C', $sourceRoot, 'rev-parse', 'HEAD') @{}).Trim()
    if ($actualSource -cne $SourceCommit) { throw 'Source mismatch' }
    [void](Invoke-BuildChild $git @('-C', $sourceRoot, 'diff', '--quiet', 'HEAD', '--', $crate, 'IP_NOTICE.md') @{})
    $untracked = Invoke-BuildChild $git @('-C', $sourceRoot, 'ls-files', '--others', '--exclude-standard', '--', $crate) @{}
    if (-not [string]::IsNullOrWhiteSpace($untracked)) { throw 'Uncommitted source refused' }
    $actualPolicy = (Get-FileHash -LiteralPath (Join-Path $crate 'src/os_policy.rs') -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualPolicy -cne $PolicySha256) { throw 'Policy mismatch' }
    $installed = Invoke-BuildChild $rustup @('toolchain', 'list') @{}
    if ($installed -notmatch '(?m)^1\.99\.0-x86_64-pc-windows-msvc(?:\s|$)') { throw 'Pinned toolchain must already be installed' }
    $rustVersion = (Invoke-BuildChild $rustc @('+1.99.0', '--version') @{}).Trim()
    $cargoVersion = (Invoke-BuildChild $cargo @('+1.99.0', '--version') @{}).Trim()
    if ($rustVersion -notmatch '^rustc 1\.99\.0 ' -or $cargoVersion -notmatch '^cargo 1\.99\.0 ') { throw 'Toolchain mismatch' }
    $linkText = Invoke-BuildChild $linker @('/?') @{}
    if ($linkText -notmatch ('Version\s+' + [regex]::Escape($LinkerVersion) + '(\s|$)')) { throw 'Linker mismatch' }
    $sdkObserved = [Environment]::GetEnvironmentVariable('WindowsSDKVersion')
    if ([string]::IsNullOrEmpty($sdkObserved) -or $sdkObserved.TrimEnd('\') -cne $SdkVersion) { throw 'SDK mismatch' }
    $sdkRoot = [Environment]::GetEnvironmentVariable('WindowsSdkDir')
    if ([string]::IsNullOrEmpty($sdkRoot) -or -not [IO.File]::Exists((Join-Path $sdkRoot ('Include/' + $SdkVersion + '/um/Windows.h')))) { throw 'SDK unavailable' }
    [void](New-Item -ItemType Directory -Path $output -ErrorAction Stop)
    $stage = Join-Path $output 'stage'
    [void](New-Item -ItemType Directory -Path $stage -ErrorAction Stop)
    $targetDirectory = Join-Path $output 'target'
    $cargoCache = [Environment]::GetEnvironmentVariable('CARGO_HOME')
    if ([string]::IsNullOrEmpty($cargoCache)) { $cargoCache = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.cargo' }
    $rustOptions = @('-C', 'link-arg=/Brepro', '-C', 'debuginfo=0',
        ('--remap-path-prefix=' + $sourceRoot + '=/src'), ('--remap-path-prefix=' + $cargoCache + '=/cargo'))
    $childEnvironment = @{
        HUB_RELAY_SOURCE_COMMIT = $SourceCommit; HUB_RELAY_POLICY_SHA256 = $PolicySha256;
        CARGO_TARGET_DIR = $targetDirectory; CARGO_INCREMENTAL = '0';
        CARGO_ENCODED_RUSTFLAGS = ($rustOptions -join [char]31);
        CARGO_TARGET_X86_64_PC_WINDOWS_MSVC_LINKER = $linker
    }
    [void](Invoke-BuildChild $cargo @('+1.99.0', 'build', '--locked', '--offline', '--release', '--target', 'x86_64-pc-windows-msvc',
        '--manifest-path', (Join-Path $crate 'Cargo.toml')) $childEnvironment)
    Copy-Item -LiteralPath (Join-Path $targetDirectory 'x86_64-pc-windows-msvc/release/hub-relay-bootstrap-inventory.exe') -Destination (Join-Path $stage 'hub-relay-bootstrap-inventory.exe')
    foreach ($name in @('README.md', 'THIRD_PARTY_NOTICES.txt', 'activation-plan.template.json')) {
        Copy-Item -LiteralPath (Join-Path $crate $name) -Destination (Join-Path $stage $name)
    }
    Copy-Item -LiteralPath (Join-Path $sourceRoot 'IP_NOTICE.md') -Destination (Join-Path $stage 'LICENSE')
    foreach ($name in @('scripts', 'tools')) { [void](New-Item -ItemType Directory -Path (Join-Path $stage $name) -ErrorAction Stop) }
    foreach ($name in @('Build-RelayInventory.ps1', 'Run-RelayInventory.ps1')) {
        Copy-Item -LiteralPath (Join-Path $crate ('scripts/' + $name)) -Destination (Join-Path $stage ('scripts/' + $name))
    }
    foreach ($name in @('verify_inventory.py', 'package_inventory.py')) {
        Copy-Item -LiteralPath (Join-Path $crate ('tools/' + $name)) -Destination (Join-Path $stage ('tools/' + $name))
    }
    [void](Invoke-BuildChild $python @((Join-Path $crate 'tools/package_inventory.py'), '--stage', $stage,
        '--output', (Join-Path $output 'hub-relay-bootstrap-inventory-windows-amd64.zip'), '--source-commit', $SourceCommit,
        '--policy-sha256', $PolicySha256, '--rustc-version', $rustVersion, '--cargo-version', $cargoVersion,
        '--linker-version', $LinkerVersion, '--sdk-version', $SdkVersion) @{})
    Write-Output 'Diagnostic bundle built; artifact metadata are unverified claims; activation blocked.'
    exit 0
} catch {
    Write-Output 'Diagnostic build or package validation failed; no authority established.'
    exit 1
}
