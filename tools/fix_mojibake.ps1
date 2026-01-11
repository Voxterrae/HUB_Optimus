param(
  [Parameter(Mandatory=$true)]
  [string]$Path
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$cp1252    = [System.Text.Encoding]::GetEncoding(1252)

$files = Get-ChildItem -Path $Path -Recurse -File -Filter *.md

foreach($f in $files){
  $p = $f.FullName
  $txt = Get-Content -LiteralPath $p -Raw

  # Detect typical mojibake / replacement char
  $hasBad = ($txt -match "[ÃÂâ€”â€“â€™â€œâ€ðŸ]" -or $txt -match [regex]::Escape([string][char]0xFFFD))

  if(-not $hasBad){ continue }

  # Fix: reinterpret current text as CP1252 bytes, decode as UTF-8
  $bytes = $cp1252.GetBytes($txt)
  $fixed = [System.Text.Encoding]::UTF8.GetString($bytes)

  if($fixed -ne $txt){
    [System.IO.File]::WriteAllText($p, $fixed, $utf8NoBom)
    Write-Host "FIXED: $p"
  }
}
