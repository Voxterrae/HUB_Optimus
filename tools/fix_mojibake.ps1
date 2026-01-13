param(
  [string]$Path = "docs"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function WriteUtf8NoBom([string]$file, [string]$content) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($file, $content, $enc)
}

# Detect typical mojibake markers using char codes (ASCII-safe)
$badChars = @(
  [char]0x00C3,  # ?
  [char]0x00C2,  # ?
  [char]0x00E2,  # ?
  [char]0xFFFD   # replacement char
)

function BadScore([string]$s) {
  $n = 0
  foreach ($c in $badChars) {
    $n += ([regex]::Matches($s, [regex]::Escape([string]$c))).Count
  }
  return $n
}

if (!(Test-Path $Path)) { throw "Path not found: $Path" }

$files = @()
if (Test-Path $Path -PathType Leaf) {
  $files = @((Resolve-Path $Path).Path)
} else {
  $files = Get-ChildItem -Recurse $Path -File -Include *.md,*.txt,*.html | Select-Object -ExpandProperty FullName
}

$latin1 = [System.Text.Encoding]::GetEncoding("ISO-8859-1")
$utf8   = [System.Text.Encoding]::UTF8

$fixed = 0
foreach ($f in $files) {
  $bytes = [System.IO.File]::ReadAllBytes($f)
  $txt = $utf8.GetString($bytes)

  $before = BadScore $txt
  if ($before -eq 0) { continue }

  # Undo mojibake: interpret current text as latin1 bytes -> decode as utf8
  $candidate = $utf8.GetString($latin1.GetBytes($txt))

  # Normalize NBSP to space
  $candidate = $candidate.Replace([char]0x00A0, " ")

  $after = BadScore $candidate
  if ($after -lt $before) {
    WriteUtf8NoBom $f $candidate
    $fixed++
    Write-Host ("FIXED: {0} (bad {1} -> {2})" -f $f, $before, $after)
  }
}

Write-Host ("SUMMARY: FIXED={0}" -f $fixed)
