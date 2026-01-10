# tools/trace_repo.ps1
# Repo snapshot generator (traceability).
# Output: docs/context/TRACEABILITY_SNAPSHOT.md

$ErrorActionPreference = "Stop"

function Run-Git([string[]]$args) {
  $out = & git @args 2>&1
  return ($out | Out-String).TrimEnd()
}

function Try-GetRepoRoot {
  # First try via git
  try {
    $raw = Run-Git @("rev-parse","--show-toplevel")
    if ($raw) {
      $line = ($raw -split "`r?`n")[0].Trim()
      # Accept only path-like results
      if ($line -match "^[A-Za-z]:[\\/]" -or $line -match "^/") { return $line }
    }
  } catch { }

  # Fallback: assume script lives under <repo>/tools
  $candidate = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  return $candidate
}

$repoRoot = Try-GetRepoRoot

if (-not (Test-Path $repoRoot)) {
  throw "Repo root not found. Computed: $repoRoot"
}

Set-Location $repoRoot

# Paths
$timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
$outDir  = Join-Path $repoRoot "docs/context"
$outFile = Join-Path $outDir  "TRACEABILITY_SNAPSHOT.md"

if (-not (Test-Path $outDir)) {
  New-Item -ItemType Directory -Path $outDir | Out-Null
}

# Collect git info (safe: if git fails, capture output)
function Safe([scriptblock]$fn) {
  try { return (& $fn) } catch { return ("ERROR: " + ($_ | Out-String).Trim()) }
}

$branch         = Safe { Run-Git @("branch","--show-current") }
$head           = Safe { Run-Git @("rev-parse","HEAD") }
$remotes        = Safe { Run-Git @("remote","-v") }
$status         = Safe { Run-Git @("status","-sb") }
$log20          = Safe { Run-Git @("log","--oneline","--decorate","-n","20") }
$diffStat       = Safe { Run-Git @("diff","--stat") }
$diffStagedStat = Safe { Run-Git @("diff","--staged","--stat") }

if ([string]::IsNullOrWhiteSpace($diffStat)) { $diffStat = "(no unstaged changes)" }
if ([string]::IsNullOrWhiteSpace($diffStagedStat)) { $diffStagedStat = "(no staged changes)" }

# Workflows dump
$wfPath = Join-Path $repoRoot ".github/workflows"
$workflowFiles = @()
if (Test-Path $wfPath) {
  $workflowFiles = Get-ChildItem -Path $wfPath -File -Filter "*.y*ml" | Sort-Object Name
}

# Top-level inventory
$topLevel = Get-ChildItem -Path $repoRoot -Force |
  Where-Object { $_.Name -ne ".git" } |
  Sort-Object Name

# Build markdown
$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# TRACEABILITY SNAPSHOT") | Out-Null
$lines.Add("") | Out-Null
$lines.Add("- Timestamp: **$timestamp**") | Out-Null
$lines.Add("- Repo root: $repoRoot") | Out-Null
$lines.Add("- Branch: **$branch**") | Out-Null
$lines.Add("- HEAD: $head") | Out-Null
$lines.Add("") | Out-Null

$lines.Add("## Git status") | Out-Null
$lines.Add("~~~text") | Out-Null
$lines.Add($status) | Out-Null
$lines.Add("~~~") | Out-Null
$lines.Add("") | Out-Null

$lines.Add("## Diff stats (unstaged)") | Out-Null
$lines.Add("~~~text") | Out-Null
$lines.Add($diffStat) | Out-Null
$lines.Add("~~~") | Out-Null
$lines.Add("") | Out-Null

$lines.Add("## Diff stats (staged)") | Out-Null
$lines.Add("~~~text") | Out-Null
$lines.Add($diffStagedStat) | Out-Null
$lines.Add("~~~") | Out-Null
$lines.Add("") | Out-Null

$lines.Add("## Recent commits (last 20)") | Out-Null
$lines.Add("~~~text") | Out-Null
$lines.Add($log20) | Out-Null
$lines.Add("~~~") | Out-Null
$lines.Add("") | Out-Null

$lines.Add("## Remotes") | Out-Null
$lines.Add("~~~text") | Out-Null
$lines.Add($remotes) | Out-Null
$lines.Add("~~~") | Out-Null
$lines.Add("") | Out-Null

$lines.Add("## Top-level inventory") | Out-Null
foreach ($item in $topLevel) {
  if ($item.PSIsContainer) { $lines.Add("- dir  $($item.Name)/") | Out-Null }
  else { $lines.Add("- file $($item.Name)") | Out-Null }
}
$lines.Add("") | Out-Null

$lines.Add("## .github/workflows") | Out-Null
if ($workflowFiles.Count -eq 0) {
  $lines.Add("(no workflow files found)") | Out-Null
} else {
  foreach ($wf in $workflowFiles) {
    $lines.Add("") | Out-Null
    $lines.Add("### $($wf.Name)") | Out-Null
    $lines.Add("~~~yaml") | Out-Null
    $lines.Add((Get-Content $wf.FullName -Raw).TrimEnd()) | Out-Null
    $lines.Add("~~~") | Out-Null
  }
}

# Write UTF-8 (no BOM)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($outFile, $lines, $utf8NoBom)

Write-Host ("OK: wrote " + $outFile)
