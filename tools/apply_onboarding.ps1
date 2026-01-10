$langs = "es","de","ca","fr","ru"

$langSwitch = @"
<!-- HUB:LANG_SWITCH -->
> **Language:** [ES](../es/00_start_here.md) · [DE](../de/00_start_here.md) · [CA](../ca/00_start_here.md) · [FR](../fr/00_start_here.md) · [RU](../ru/00_start_here.md)
<!-- /HUB:LANG_SWITCH -->

"@

$tracks = @"
<!-- HUB:TRACKS -->
## Choose your path

**90 seconds (executive):**
- What this is / isn’t: [Kernel](governance/KERNEL.md)
- How evaluation works: [Evaluation Standard](governance/EVALUATION_STANDARD.md)
- How scenarios are defined: [Scenario Schema](governance/SCENARIO_SCHEMA.md)

**20 minutes (practitioner):**
- Core spec (ES, canonical v1):  
  [01_base_declaracion](../../v1_core/languages/es/01_base_declaracion.md) → 
  [02_arquitectura_base](../../v1_core/languages/es/02_arquitectura_base.md) → 
  [03_flujo_operativo](../../v1_core/languages/es/03_flujo_operativo.md)
- English reference:  
  [01_base_declaracion (EN)](../../v1_core/languages/en/01_base_declaracion.md)

**Try it (hands-on):**
- Template: [Scenario Template](../../v1_core/workflow/04_scenario_template.md)
- Examples: [Scenario 001](../../v1_core/workflow/scenario_001_partial_ceasefire.md), [Scenario 002](../../v1_core/workflow/scenario_002_verified_ceasefire.md)
- Learning loop: [Meta Learning](../../v1_core/workflow/05_meta_learning.md)
<!-- /HUB:TRACKS -->

"@

foreach($l in $langs){
  $f = "docs/$l/00_start_here.md"
  if (-not (Test-Path $f)) { Write-Host "SKIP (missing): $f"; continue }

  $txt = Get-Content $f -Raw

  if ($txt -notmatch '<!-- HUB:LANG_SWITCH -->') {
    $txt = [regex]::Replace($txt, '^(# .*\r?\n)', "`$1`r`n$langSwitch", 1)
  }

  if ($txt -notmatch '<!-- HUB:TRACKS -->') {
    if ($txt -match '(\r?\n## Governance\r?\n)') {
      $txt = $txt -replace '(\r?\n## Governance\r?\n)', "`r`n$tracks`r`n## Governance`r`n"
    } else {
      $txt = $txt + "`r`n`r`n$tracks"
    }
  }

  Set-Content -Encoding UTF8 $f -Value $txt
  Write-Host "UPDATED: $f"
}
