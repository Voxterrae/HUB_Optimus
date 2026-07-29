param(
  [string]$Path = "docs",
  [switch]$Apply,
  [switch]$DryRun,
  [switch]$Backup,
  [string]$BackupSuffix = ".bak",
  [string[]]$Include = @("*.md"),
  [string[]]$ExcludeDir = @(
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".venv",
    "venv"
  )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (
  Get-Variable `
    -Name PSNativeCommandUseErrorActionPreference `
    -ErrorAction SilentlyContinue
) {
  $PSNativeCommandUseErrorActionPreference = $false
}
if ($Apply -and $DryRun) {
  throw "-Apply and -DryRun cannot be used together"
}

Import-Module (Join-Path $PSScriptRoot "RepositoryPathSafety.psm1") -Force

function Get-BadScore([string]$Text) {
  $badCharacters = @(
    [char]0x00C3,
    [char]0x00E2,
    [char]0x00F0,
    [char]0x00C2,
    [char]0xFFFD
  )
  $score = 0
  foreach ($character in $badCharacters) {
    $score += (
      [regex]::Matches($Text, [regex]::Escape([string]$character))
    ).Count
  }
  return $score
}

function Test-Include([string]$RelativePath) {
  $name = [System.IO.Path]::GetFileName($RelativePath)
  foreach ($pattern in $Include) {
    $wildcard = [System.Management.Automation.WildcardPattern]::new(
      $pattern,
      [System.Management.Automation.WildcardOptions]::IgnoreCase
    )
    if ($wildcard.IsMatch($RelativePath) -or $wildcard.IsMatch($name)) {
      return $true
    }
  }
  return $false
}

function Test-Excluded([string]$RelativePath) {
  $segments = $RelativePath.Replace("\", "/").Split("/")
  foreach ($directory in $ExcludeDir) {
    if ($directory -in $segments) {
      return $true
    }
  }
  return $false
}

$repoRoot = Get-RepositoryRoot -StartPath (Join-Path $PSScriptRoot "..")
$safeTarget = Resolve-RepositoryPath `
  -RepositoryRoot $repoRoot `
  -Path $Path `
  -MustExist
$tracked = @(
  Get-TrackedRepositoryFiles `
    -RepositoryRoot $repoRoot `
    -Path $safeTarget
)

$cp1252Strict = [System.Text.Encoding]::GetEncoding(
  1252,
  [System.Text.EncoderExceptionFallback]::new(),
  [System.Text.DecoderExceptionFallback]::new()
)
$utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)

$wouldFix = 0
$fixed = 0
$skipped = 0

foreach ($file in $tracked) {
  if (
    -not (Test-Include $file.RelativePath) -or
    (Test-Excluded $file.RelativePath)
  ) {
    continue
  }

  try {
    $text = $utf8Strict.GetString(
      [System.IO.File]::ReadAllBytes($file.FullPath)
    )
  } catch {
    Write-Warning "SKIP_INVALID_UTF8: $($file.RelativePath)"
    $skipped++
    continue
  }

  $before = Get-BadScore $text
  if ($before -eq 0) {
    continue
  }
  try {
    $candidate = $utf8Strict.GetString($cp1252Strict.GetBytes($text))
  } catch {
    Write-Warning "SKIP_UNSAFE_TRANSCODE: $($file.RelativePath)"
    $skipped++
    continue
  }
  $after = Get-BadScore $candidate
  if ($after -ge $before) {
    continue
  }

  if (-not $Apply) {
    Write-Host (
      "WOULD_FIX: {0} (bad {1} -> {2})" -f
        $file.RelativePath,
        $before,
        $after
    )
    $wouldFix++
    continue
  }

  if ($Backup) {
    $backupPath = Resolve-RepositoryBackupPath `
      -RepositoryRoot $repoRoot `
      -SourcePath $file.FullPath `
      -BackupSuffix $BackupSuffix
    [System.IO.File]::Copy($file.FullPath, $backupPath, $false)
  }
  [System.IO.File]::WriteAllText($file.FullPath, $candidate, $utf8Strict)
  Write-Host (
    "FIXED: {0} (bad {1} -> {2})" -f
      $file.RelativePath,
      $before,
      $after
  )
  $fixed++
}

$mode = if ($Apply) { "apply" } else { "preview" }
Write-Host (
  "SUMMARY: MODE={0} WOULD_FIX={1} FIXED={2} SKIPPED={3}" -f
    $mode,
    $wouldFix,
    $fixed,
    $skipped
)
