param(
  [string]$OutputPath = "docs/context/TRACEABILITY_SNAPSHOT.md"
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

function Invoke-Git {
  param([string[]]$Args)
  $output = & git @Args 2>$null
  if ($LASTEXITCODE -ne 0) {
    return $null
  }
  return $output
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$branch = Invoke-Git @("rev-parse", "--abbrev-ref", "HEAD")
$head = Invoke-Git @("rev-parse", "HEAD")
$remotes = Invoke-Git @("remote", "-v")
$log = Invoke-Git @("log", "-n", "5", "--oneline")
$status = Invoke-Git @("status", "-sb")
$diffStat = Invoke-Git @("diff", "--stat")
$diffStatStaged = Invoke-Git @("diff", "--stat", "--staged")

$workflowDir = Join-Path $root ".github/workflows"
$workflowFiles = @()
if (Test-Path $workflowDir) {
  $workflowFiles = Get-ChildItem -Force -Path $workflowDir -File | Sort-Object Name
}

$topLevel = Get-ChildItem -Force -Path $root | Sort-Object Name

$content = New-Object System.Collections.Generic.List[string]
$content.Add("# TRACEABILITY SNAPSHOT")
$content.Add("")
$content.Add("Generated: $timestamp")
$content.Add("Repo root: $root")
$content.Add("")
$content.Add("## Git")
$content.Add("Branch: " + ($(if ($branch) { $branch } else { "(git unavailable)" })))
$content.Add("HEAD: " + ($(if ($head) { $head } else { "(git unavailable)" })))
$content.Add("")
$content.Add("### Remotes")
if ($remotes) {
  $content.AddRange($remotes -split "`n")
} else {
  $content.Add("(none)")
}
$content.Add("")
$content.Add("### Status")
if ($status) {
  $content.AddRange($status -split "`n")
} else {
  $content.Add("(clean or git unavailable)")
}
$content.Add("")
$content.Add("### Diff (unstaged) - stat")
if ($diffStat) {
  $content.AddRange($diffStat -split "`n")
} else {
  $content.Add("(clean)")
}
$content.Add("")
$content.Add("### Diff (staged) - stat")
if ($diffStatStaged) {
  $content.AddRange($diffStatStaged -split "`n")
} else {
  $content.Add("(clean)")
}
$content.Add("")
$content.Add("### Recent commits")
if ($log) {
  $content.AddRange($log -split "`n")
} else {
  $content.Add("(git unavailable)")
}
$content.Add("")
$content.Add("## Workflows")
if ($workflowFiles.Count -eq 0) {
  $content.Add("(none)")
} else {
  foreach ($wf in $workflowFiles) {
    $content.Add("")
    $content.Add("### " + $wf.FullName)
    $content.Add("```yaml")
    $content.AddRange((Get-Content -Path $wf.FullName))
    $content.Add("```")
  }
}
$content.Add("")
$content.Add("## Top-level inventory")
foreach ($item in $topLevel) {
  $kind = if ($item.PSIsContainer) { "dir" } else { "file" }
  $content.Add("- $kind $($item.Name)")
}
$content.Add("")

$outPath = Join-Path $root $OutputPath
$outDir = Split-Path -Parent $outPath
if (-not (Test-Path $outDir)) {
  New-Item -ItemType Directory -Path $outDir | Out-Null
}
Set-Content -Path $outPath -Value $content -Encoding UTF8
Write-Output "Wrote snapshot to $outPath"