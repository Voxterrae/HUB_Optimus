param(
  [string]$Path = "docs",
  [switch]$Apply,
  [switch]$Backup,
  [string]$BackupSuffix = ".bak"
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

Import-Module (Join-Path $PSScriptRoot "RepositoryPathSafety.psm1") -Force

# Detect typical mojibake markers using Unicode code points.
$badChars = @(
  [char]0x00C3,
  [char]0x00C2,
  [char]0x00E2,
  [char]0xFFFD
)

function Get-BadScore([string]$Text) {
  $score = 0
  foreach ($character in $badChars) {
    $score += (
      [regex]::Matches($Text, [regex]::Escape([string]$character))
    ).Count
  }
  return $score
}

$repoRoot = Get-RepositoryRoot -StartPath (Join-Path $PSScriptRoot "..")
$safeTarget = Resolve-RepositoryPath `
  -RepositoryRoot $repoRoot `
  -Path $Path `
  -MustExist
$files = @(
  Get-TrackedRepositoryFiles `
    -RepositoryRoot $repoRoot `
    -Path $safeTarget `
    -Extensions @(".md", ".txt", ".html")
)

# Exception fallbacks prevent a whole multilingual document from being silently
# replaced with "?" when it cannot be represented as ISO-8859-1.
$latin1Strict = [System.Text.Encoding]::GetEncoding(
  "ISO-8859-1",
  [System.Text.EncoderExceptionFallback]::new(),
  [System.Text.DecoderExceptionFallback]::new()
)
$utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)

$wouldFix = 0
$fixed = 0
$skipped = 0

foreach ($file in $files) {
  try {
    $bytes = [System.IO.File]::ReadAllBytes($file.FullPath)
    $text = $utf8Strict.GetString($bytes)
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
    $candidateBytes = $latin1Strict.GetBytes($text)
    $candidate = $utf8Strict.GetString($candidateBytes)
  } catch {
    Write-Warning "SKIP_UNSAFE_TRANSCODE: $($file.RelativePath)"
    $skipped++
    continue
  }
  $candidate = $candidate.Replace([char]0x00A0, " ")
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
