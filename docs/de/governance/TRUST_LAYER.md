# HUB_Optimus — Vertrauensebene

## Zweck
Die Vertrauensebene definiert, wie HUB_Optimus **Behauptungen**, **Verpflichtungen** und **Vereinbarungen** auf operative Zuverlässigkeit evaluiert.

Sie evaluiert **nicht** Absicht, Moral oder politische Legitimität.
Sie evaluiert **Verifizierbarkeit**, **Nachvollziehbarkeit** und **strukturelle Vertrauenswürdigkeit**.

## Kernprinzip
Eine Verpflichtung, die nicht verifiziert werden kann, sollte nicht als zuverlässig behandelt werden, unabhängig davon, wer sie eingeht.

Vertrauen wird nicht angenommen.
Vertrauen wird **durch Struktur verdient**.

---

## Nachweisklassen (A/B/C)
### Klasse A — Verifizierbare Verpflichtungen (hohes Vertrauen)
Merkmale:
- Beobachtbare Handlungen oder Zustände
- Unabhängige Verifikation möglich
- Klare Erfolgs-/Fehlschlagsbedingungen
- Zeitlich begrenzte Kontrollpunkte

Beispiele:
- Vereinbarungen mit Inspektions-/Monitoring-Mechanismen
- Öffentlich prüfbare Handlungen
- Reversible Schritte mit Monitoring

### Klasse B — Teilweise verifizierbare Verpflichtungen (bedingtes Vertrauen)
Merkmale:
- Einige beobachtbare Komponenten
- Begrenzter Verifikationsumfang
- Mehrdeutige Durchsetzung oder Abdeckung

Beispiele:
- Verpflichtungen mit Berichterstattung, aber ohne unabhängige Verifikation
- Bedingte Handlungen ohne definierte Sanktionen oder Rückabwicklung

### Klasse C — Nicht verifizierbare Behauptungen (geringes Vertrauen)
Merkmale:
- Keine externe Verifikation
- Abhängig von Absicht oder gutem Willen
- Keine messbaren Kontrollpunkte

Beispiele:
- Mündliche Zusicherungen
- Aussagen über künftige Absichten ohne Mechanismen

---

## Vertrauensprofil (wie HUB_Optimus Zuverlässigkeit bewertet)
Für jede Verpflichtung erstellt HUB_Optimus ein **Vertrauensprofil** anhand der folgenden Dimensionen:

1) **Verifizierbarkeit**
- Kann ein unabhängiger Akteur die Behauptung verifizieren?

2) **Nachvollziehbarkeit**
- Gibt es eine Prüfspur (wer/was/wann/wo)?

3) **Unabhängigkeit**
- Ist die Verifikation unabhängig vom Anspruchsteller?

4) **Abdeckung**
- Deckt die Verifikation die gesamte Verpflichtung ab oder nur Fragmente?

5) **Aktualität**
- Wie aktuell ist der Nachweis im Verhältnis zum Verpflichtungszeitraum?

6) **Reversibilität**
- Kann die Handlung rückgängig gemacht werden, wenn die Verifikation scheitert?

Eine Verpflichtung kann Klasse A sein und dennoch schwach bleiben, wenn Abdeckung/Unabhängigkeit mangelhaft ist.

---

## Mindestprotokoll für Verifikation (MVP)
Eine Verpflichtung wird nur dann als "zuverlässig genug für die Planung" behandelt, wenn sie Folgendes enthält:
- Ein **klares beobachtbares Ergebnis**
- Einen **Kontrollpunkt-Zeitplan**
- Eine **benannte Verifikationsmethode**
- Einen **Streitfallpfad** (was geschieht, wenn Verifikation bestritten wird)

---

## Streitfälle und Herabstufung (nicht zwangsausübende Durchsetzung)
HUB_Optimus setzt keine Ergebnisse durch.
Es setzt **epistemische Disziplin** durch:

- Wenn Verifikation scheitert -> Vertrauen wird herabgestuft.
- Wenn Verifikation blockiert wird -> Vertrauen wird herabgestuft.
- Wenn Nachweise nur teilweise vorliegen -> Vertrauen ist bedingt.
- Wenn Nachweise unabhängig bestätigt werden -> Vertrauen wird gestärkt.

Dies erzeugt Anreizdruck ohne Zwang.

---

## Anti-Gaming-Regel
"Papier-Compliance" (performative Berichterstattung ohne unabhängige Verifikation) wird als Klasse B oder C behandelt,
selbst wenn sie als Klasse A präsentiert wird.

---

## Integrationspunkte
- Szenario-Eingaben sollten Nachweise über `governance/SCENARIO_SCHEMA.md` referenzieren.
- Evaluationen sollten Nachweisklasse + Vertrauensprofil-Dimensionen über `governance/EVALUATION_STANDARD.md` ausdrücklich zitieren.

---

## Kernel-Zugriff und Anti-Vereinnahmungsregeln (Härtung)

### Vertrauensstufen (allgemein)
- Leser: dürfen das System lesen und referenzieren.
- Beitragende: dürfen Änderungen an Nicht-Kernel-Materialien zur Prüfung vorschlagen.
- Kustoden: dürfen Governance-Änderungen unter strengem Prozess genehmigen.

### ## Kernel-Zugriff und Anti-Vereinnahmungsregeln (Härtung)
Direkte Änderungen an Kernel-Dokumenten erfordern:
1) ausdrückliche Begründung mit Bezug auf Kernel-Prinzipien,
2) Konsensprüfung gemäß CONSENSUS_PROCESS,
3) Zustimmung der Kustodianschaft gemäß CUSTODIANSHIP,
4) Synchronisierung über Sprach-Mirrors hinweg.

### Anti-Vereinnahmungsregel
Versuche,
- Drift durch Übersetzung einzuführen,
- die Methode unter Beibehaltung ihrer Ansprüche umzubenennen,
- Governance in Marketing umzuwandeln,
werden als Vereinnahmungsversuche behandelt und zurückgewiesen.
