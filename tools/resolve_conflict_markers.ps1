param(
  [string]$Path = "docs",
  [ValidateSet("ours", "theirs")]
  [string]$Keep = "theirs",
  [switch]$Apply
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

function Resolve-Text([string]$Text, [string]$KeepSide) {
  $pattern = (
    "(?ms)^<<<<<<<(?: [^\r\n]*)?\r?\n" +
    "(.*?)" +
    "^=======\r?\n" +
    "(.*?)" +
    "^>>>>>>>(?: [^\r\n]*)?(?:\r?\n|$)"
  )

  while ([regex]::IsMatch($Text, $pattern)) {
    $Text = [regex]::Replace(
      $Text,
      $pattern,
      {
        param($Match)
        if ($KeepSide -eq "theirs") {
          return $Match.Groups[2].Value
        }
        return $Match.Groups[1].Value
      },
      1
    )
  }
  return $Text
}

$repoRoot = Get-RepositoryRoot -StartPath (Join-Path $PSScriptRoot "..")
$safeTarget = Resolve-RepositoryPath `
  -RepositoryRoot $repoRoot `
  -Path $Path `
  -MustExist
$pathSpec = Get-RepositoryRelativePath `
  -RepositoryRoot $repoRoot `
  -Path $safeTarget

# Use extended regex explicitly. Three -e patterns avoid treating "|" literally
# and anchor matches to genuine seven-character conflict marker lines.
$files = @(
  & git -C $repoRoot -c core.quotepath=false grep -l -E `
    -e "^<<<<<<<( .*)?$" `
    -e "^=======$" `
    -e "^>>>>>>>( .*)?$" `
    -- $pathSpec 2>$null
)
$grepExit = $LASTEXITCODE
if ($grepExit -gt 1) {
  throw "git grep failed while scanning repository path: $pathSpec"
}
if ($files.Count -eq 0) {
  Write-Host "No markers found under $pathSpec"
  exit 0
}

$utf8NoBom = [System.Text.UTF8Encoding]::new($false, $true)
$detected = $files.Count
$wouldResolve = 0
$fixed = 0
$skipped = 0

foreach ($relativePath in $files) {
  $filePath = Resolve-RepositoryPath `
    -RepositoryRoot $repoRoot `
    -Path ([string]$relativePath) `
    -MustExist
  $raw = [System.IO.File]::ReadAllText($filePath, $utf8NoBom)

  if ($raw -match "(?m)^\|\|\|\|\|\|\|(?: .*)?$") {
    Write-Warning "SKIP_DIFF3: $relativePath"
    $skipped++
    continue
  }

  $new = Resolve-Text $raw $Keep
  if ($new -eq $raw) {
    Write-Warning "SKIP_INCOMPLETE: $relativePath"
    $skipped++
    continue
  }
  if ($new -match "(?m)^(<<<<<<<(?: .*)?|=======|>>>>>>>(?: .*)?)$") {
    Write-Warning "SKIP_UNRESOLVED: $relativePath"
    $skipped++
    continue
  }

  if (-not $Apply) {
    Write-Host "WOULD_RESOLVE: $relativePath (keep=$Keep)"
    $wouldResolve++
    continue
  }

  [System.IO.File]::WriteAllText($filePath, $new, $utf8NoBom)
  Write-Host "FIXED: $relativePath (keep=$Keep)"
  $fixed++
}

$mode = if ($Apply) { "apply" } else { "preview" }
Write-Host (
  "SUMMARY: MODE={0} DETECTED={1} WOULD_RESOLVE={2} FIXED={3} SKIPPED={4}" -f
    $mode,
    $detected,
    $wouldResolve,
    $fixed,
    $skipped
)
