# HUB_Optimus — Konsensprozess

## Zweck
Dieser Prozess definiert, wie Governance-Änderungen vorgeschlagen, diskutiert, entschieden und protokolliert werden.
Ziel ist Nachvollziehbarkeit, Drift-Vermeidung und Schutz vor Capture.

## Geltungsbereich
Der Konsensprozess gilt für:
- Governance-Dokumente,
- Prozessregeln,
- Kernel-nahe Änderungen.

Er gilt NICHT für:
- reine Übersetzungs-/Formatkorrekturen ohne Bedeutungsänderung.

## Prinzipien
- **Transparenz:** Vorschläge und Einwände sind sichtbar.
- **Begründungspflicht:** Änderungen müssen mit Kernel-Prinzipien begründet werden.
- **Nachvollziehbarkeit:** Entscheidungen müssen dokumentiert werden.
- **Drift-Block:** Änderungen, die Bedeutung verwässern oder Capture ermöglichen, werden zurückgewiesen.

## Ablauf (Standard)
1) **Vorschlag**
   - klare Beschreibung: was ändert sich?
   - warum (Kernel-/Stabilitätsbezug)?
   - erwartete Auswirkungen / Risiken

2) **Review-Phase**
   - Einwände, Alternativen, Präzisierungen
   - Fokus: Verifizierbarkeit, Anreize, Lock-in-Risiko, Klarheit

3) **Entscheidung**
   - dokumentierter Ausgang: angenommen / abgelehnt / zurück zur Überarbeitung
   - Begründung kurz und prüfbar

4) **Protokoll**
   - Referenz auf PR/Commit
   - zusammengefasste Einwände + Auflösung

## Mindestanforderungen
Eine Änderung ist ungültig, wenn:
- sie nicht begründet ist,
- sie Definitionsdrift einführt,
- sie Verifizierbarkeit/Anreiz-Logik untergräbt,
- sie Übersetzung als Hintertür nutzt.

## Sprach-Synchronisierung
Bei Governance-Änderungen:
- canonical Version aktualisieren,
- Übersetzungen synchronisieren (Meaning 1:1),
- Drift ist nicht zulässig.
