#!/usr/bin/env pwsh
# HUB_Optimus - Maintainer health check (30-second sweep)

Write-Host "=== HUB_Optimus Repository Health ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Open PRs:" -ForegroundColor Yellow
$prs = gh pr list --limit 10 --json number,title,author --jq 'length'
if ($prs -eq "0") { Write-Host "  None" } else { gh pr list --limit 10 }

Write-Host ""
Write-Host "Open Issues:" -ForegroundColor Yellow
gh issue list --limit 10

Write-Host ""
Write-Host "Recent CI Runs:" -ForegroundColor Yellow
gh run list --limit 5

Write-Host ""
Write-Host "Dependabot Alerts:" -ForegroundColor Yellow
$alerts = gh api repos/Voxterrae/HUB_Optimus/dependabot/alerts?state=open --jq 'length' 2>$null
if ($null -eq $alerts -or $alerts -eq "") {
    Write-Host "  Check https://github.com/Voxterrae/HUB_Optimus/security/dependabot"
} elseif ($alerts -eq "0") {
    Write-Host "  None"
} else {
    Write-Host "  $alerts open alert(s) - check security tab"
}

Write-Host ""
Write-Host "Latest Commit:" -ForegroundColor Yellow
git log -1 --oneline

Write-Host ""
Write-Host "Branch:" -ForegroundColor Yellow
git branch --show-current

Write-Host ""
Write-Host "Working Tree:" -ForegroundColor Yellow
$status = git status --porcelain
if ($status) { Write-Host "  $($status.Count) modified file(s)" } else { Write-Host "  Clean" }

Write-Host ""
Write-Host "=== End ===" -ForegroundColor Cyan
