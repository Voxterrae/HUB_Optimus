> 🇬🇧 English source: [../02_how_to_read_this_repo.md](../02_how_to_read_this_repo.md)

# Wie man dieses Repository liest

Dieses Repository ist so organisiert, dass du verstehst **was es ist**, **wo was liegt** und **wie du es nutzt**, ohne dich in Details zu verlieren. Die Idee: Jede Person kann reinkommen, eine Sprache wählen und einem klaren Pfad folgen.

## Empfohlene Lesereihenfolge (je nach Ziel)

### Ich will schnell verstehen, "woran ihr gerade arbeitet"
Folge dieser Reihenfolge:
1) [docs/de/00_start_here.md](00_start_here.md)
2) [docs/de/03_try_a_scenario.md](03_try_a_scenario.md)
3) [../../v1_core/workflow/es/README.md](../../v1_core/workflow/es/README.md)

### Ich will Szenarien praktisch üben (Simulationsmodus)
Geh direkt zu:
- Workflow (ES): [../../v1_core/workflow/es/README.md](../../v1_core/workflow/es/README.md)
- Szenario 001 (ES): [../../v1_core/workflow/es/scenario_001_partial_ceasefire.md](../../v1_core/workflow/es/scenario_001_partial_ceasefire.md)
- Szenario 002 (ES): [../../v1_core/workflow/es/scenario_002_verified_ceasefire.md](../../v1_core/workflow/es/scenario_002_verified_ceasefire.md)
- Vorlage (ES): [../../v1_core/workflow/es/04_scenario_template.md](../../v1_core/workflow/es/04_scenario_template.md)

### Ich will das konzeptionelle Framework und die Methode verstehen
Starte mit:
- [../../v1_core/languages/es/01_base_declaracion.md](../../v1_core/languages/es/01_base_declaracion.md)
- [../../v1_core/languages/es/02_arquitectura_base.md](../../v1_core/languages/es/02_arquitectura_base.md)
- [../../v1_core/languages/es/03_flujo_operativo.md](../../v1_core/languages/es/03_flujo_operativo.md)
und geh danach zurück in den Workflow.

## Repo-Map (was in welchem Ordner liegt)
- `docs/`  
  Einstieg, Lese-Guide und ein geführter Testlauf. Wenn du "von außen" kommst: starte hier.
- `v1_core/`  
  Kernel des Systems: Workflow, Szenarien, Vorlagen, Kriterien und iteratives Lernen.
- `legacy/`  
  Älteres oder experimentelles Material. Nützlich als Referenz, aber nicht immer "up to date".

## Sprachstatus (STATUS)
- Verbindliche Quelle: `docs/context/STATUS.md`
- Kanonisch: `../../v1_core/languages/es/`
- Paritätsreferenz: `../../v1_core/languages/en/`

## Navigieren ohne Kontextverlust
1) Nutze "Start hier" und "Szenario ausprobieren", um das System in Aktion zu sehen.
2) Wenn ein Dokument etwas aus dem Kernel (`v1_core`) zitiert, folge dem Link und komm wieder zurück.
3) Wenn ein Abschnitt auf ES oder EN verweist, ist das Quellen-/Referenzmaterial, keine vollständige deutsche Übersetzung.

## Wo das Wichtige ist (Shortcuts)
- Einstieg (DE): [docs/de/00_start_here.md](00_start_here.md)
- Szenario ausprobieren (DE): [docs/de/03_try_a_scenario.md](03_try_a_scenario.md)
- Kernel-Workflow (ES): [../../v1_core/workflow/es/README.md](../../v1_core/workflow/es/README.md)
- Szenario-Vorlage (ES): [../../v1_core/workflow/es/04_scenario_template.md](../../v1_core/workflow/es/04_scenario_template.md)
- Meta-Lernen (ES): [../../v1_core/workflow/es/05_meta_learning.md](../../v1_core/workflow/es/05_meta_learning.md)

## Wenn du beitragen willst (ohne Links zu brechen)
- Bevorzuge relative Links (damit sie in GitHub und lokal funktionieren).
- Halte EN↔ES Paare mit derselben Ordnerstruktur.
- Wenn du Pfade änderst, führe den Link-Check (Lychee) aus, bevor du pushst.

Weiter: [docs/de/03_try_a_scenario.md](03_try_a_scenario.md)
