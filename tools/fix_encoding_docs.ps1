param(
  [string]$Path = "docs",
  [switch]$DryRun,
  [switch]$Backup,
  [string]$BackupSuffix = ".bak",
  [string[]]$Include = @("*.md"),
  [string[]]$ExcludeDir = @(".git","node_modules","dist","build",".next",".venv","venv")
)

$ErrorActionPreference = "Stop"

$cp1252   = [System.Text.Encoding]::GetEncoding(1252)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Heuristic: detect typical mojibake chars (C3=Ã, E2=â, F0=ð, C2=Â)
$bad = @([char]0x00C3, [char]0x00E2, [char]0x00F0, [char]0x00C2)
$re  = "[" + (($bad | ForEach-Object { [regex]::Escape($_) }) -join "") + "]"

function IsExcludedPath([string]$fullName) {
  foreach ($d in $ExcludeDir) {
    if ($fullName -match ([regex]::Escape([System.IO.Path]::DirectorySeparatorChar + $d + [System.IO.Path]::DirectorySeparatorChar))) { return $true }
    if ($fullName -match ([regex]::Escape("/$d/"))) { return $true }
  }
  return $false
}

$files = @()
foreach ($pat in $Include) {
  $files += Get-ChildItem -Path $Path -Recurse -File -Filter $pat -ErrorAction SilentlyContinue
}
$files = $files | Sort-Object FullName -Unique

$fixedCount = 0
$wouldFixCount = 0

foreach ($f in $files) {
  $p = $f.FullName
  if (IsExcludedPath $p) { continue }

  $t = Get-Content -LiteralPath $p -Raw

  if ($t -match $re) {
    $fixed = $utf8NoBom.GetString($cp1252.GetBytes($t))

    if ($fixed -ne $t) {
      if ($DryRun) {
        Write-Host ("WOULD_FIX: {0}" -f $p)
        $wouldFixCount++
        continue
      }

      if ($Backup) {
        $bak = $p + $BackupSuffix
        Copy-Item -LiteralPath $p -Destination $bak -Force
      }

      [System.IO.File]::WriteAllText($p, $fixed, $utf8NoBom)
      Write-Host ("FIXED: {0}" -f $p)
      $fixedCount++
    }
  }
}

if ($DryRun) {
  Write-Host ("SUMMARY: WOULD_FIX={0}" -f $wouldFixCount)
} else {
  Write-Host ("SUMMARY: FIXED={0}" -f $fixedCount)
}
