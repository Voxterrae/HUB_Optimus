param(
  [string]$Path = "docs",
  [ValidateSet("ours","theirs")]
  [string]$Keep = "theirs"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-Text([string]$text, [string]$keepSide) {
  $pattern = '(?s)<<<<<<<.*?\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>>.*?\r?\n'
  while ([regex]::IsMatch($text, $pattern)) {
    $text = [regex]::Replace($text, $pattern, {
      param($m)
      $ours   = $m.Groups[1].Value
      $theirs = $m.Groups[2].Value
      if ($keepSide -eq "theirs") { $theirs } else { $ours }
    }, 1)
  }

  # Remove leftover marker lines (incomplete markers)
  $text = [regex]::Replace($text, '(?m)^(<<<<<<<.*|=======|>>>>>>>.*)\s*$', '')
  return $text
}

# List files that contain markers (use multiple -e for basic regex)
$files = git grep -l -e '<<<<<<<' -e '=======' -e '>>>>>>>' -- $Path
if (-not $files) { Write-Host "No markers found under $Path"; exit 0 }

$enc = New-Object System.Text.UTF8Encoding($false)
$fixed = 0

foreach ($f in $files) {
  $raw = [System.IO.File]::ReadAllText($f)
  $new = Resolve-Text $raw $Keep
  if ($new -ne $raw) {
    [System.IO.File]::WriteAllText($f, $new, $enc)
    $fixed++
    Write-Host "FIXED: $f"
  }
}

Write-Host ("SUMMARY: FIXED={0}" -f $fixed)
