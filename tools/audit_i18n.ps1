param(
  [string]$Root = "docs",
  [string]$Base = "es",
  [switch]$ListMissing
)

$ErrorActionPreference = "Stop"

# Resolve repo root
$repoRoot = (git rev-parse --show-toplevel) 2>$null
if (-not $repoRoot) { $repoRoot = (Get-Location).Path }

$rootPath = Join-Path $repoRoot $Root
if (-not (Test-Path $rootPath)) { throw "Root not found: $rootPath" }

# Find language dirs like /xx
$langDirs = Get-ChildItem $rootPath -Directory | Where-Object { $_.Name -match '^[a-z]{2}$' } | Sort-Object Name
if (-not $langDirs) { throw "No language folders found under: $rootPath (expected $Root/<lang>)" }

$baseDir = $langDirs | Where-Object { $_.Name -eq $Base }
if (-not $baseDir) {
  throw "Base language folder not found: $Root/$Base"
}

# Collect base files
$baseFiles = Get-ChildItem $baseDir.FullName -Recurse -File -Filter *.md |
  ForEach-Object { $_.FullName.Substring($baseDir.FullName.Length + 1).Replace('\','/') } |
  Sort-Object -Unique

$rows = @()

foreach ($ld in $langDirs) {
  $files = Get-ChildItem $ld.FullName -Recurse -File -Filter *.md |
    ForEach-Object { $_.FullName.Substring($ld.FullName.Length + 1).Replace('\','/') } |
    Sort-Object -Unique

  $missing = Compare-Object -ReferenceObject $baseFiles -DifferenceObject $files -PassThru |
    Where-Object { $_ -in $baseFiles }

  $extra = Compare-Object -ReferenceObject $baseFiles -DifferenceObject $files -PassThru |
    Where-Object { $_ -in $files }

  $rows += [PSCustomObject]@{
    Root        = $Root
    Lang        = $ld.Name
    Base        = $Base
    BaseMdCount = $baseFiles.Count
    MdCount     = $files.Count
    Missing     = $missing.Count
    Extra       = $extra.Count
  }

  if ($ListMissing -and $missing.Count -gt 0) {
    Write-Host ""
    Write-Host "=== Missing in $($ld.Name) relative to $Base ($Root) ===" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host $_ }
  }
}

# Print table
$rows | Sort-Object Lang | Format-Table -AutoSize

# Write report files under docs/context (if exists)
$ctx = Join-Path $repoRoot "docs\context"
if (Test-Path $ctx) {
  $csv = Join-Path $ctx ("I18N_AUDIT_{0}.csv" -f ($Root -replace '[\\/:\s]','_'))
  $md  = Join-Path $ctx ("I18N_AUDIT_{0}.md"  -f ($Root -replace '[\\/:\s]','_'))

  $rows | Sort-Object Lang | Export-Csv -NoTypeInformation -Encoding UTF8 $csv

  @(
    "# I18N Audit"
    ""
    "- Root: $Root"
    "- Base: **$Base**"
    "- Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    ""
    "## Summary"
    ""
  ) + ($rows | Sort-Object Lang | ForEach-Object {
    "| $($_.Lang) | md=$($_.MdCount)/$($_.BaseMdCount) | missing=$($_.Missing) | extra=$($_.Extra) |"
  }) | Set-Content -Encoding UTF8 $md

  Write-Host ""
  Write-Host "OK -> $csv"
  Write-Host "OK -> $md"
}
