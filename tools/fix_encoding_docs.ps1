param([string]$Path="docs")

$ErrorActionPreference = "Stop"

$cp1252 = [System.Text.Encoding]::GetEncoding(1252)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# Detect mojibake by bad chars (C3 = Ã, E2 = â, F0 = ð, C2 = Â)
$bad = @([char]0x00C3, [char]0x00E2, [char]0x00F0, [char]0x00C2)
$re  = "[" + (($bad | ForEach-Object { [regex]::Escape($_) }) -join "") + "]"

Get-ChildItem -Path $Path -Recurse -File -Filter *.md | ForEach-Object {
  $p = $_.FullName
  $t = Get-Content -LiteralPath $p -Raw

  if ($t -match $re) {
    $fixed = $utf8NoBom.GetString($cp1252.GetBytes($t))
    if ($fixed -ne $t) {
      [System.IO.File]::WriteAllText($p, $fixed, $utf8NoBom)
      Write-Host ("FIXED: {0}" -f $p)
    }
  }
}
