# HUB_Optimus — Konsensprozess

## Zweck
Dieses Dokument definiert, wie Änderungen an HUB_Optimus-Dokumenten vorgeschlagen, geprüft und angenommen werden.

Konsens wird genutzt, um einseitige Vereinnahmung zu verhindern und die Legitimität des Systems durch nachvollziehbare Einigung zu bewahren.

## Definitionen
- **Vorschlag**: ein dokumentierter Änderungsantrag (Text + Begründung).
- **Einwand**: eine begründete Aussage, dass ein Vorschlag den Kernel verletzt, Neutralität verringert, Verifizierbarkeit schwächt oder Vereinnahmungsrisiko einführt.
- **Aufrechterhaltener Einwand**: ein Einwand, der nach gutgläubigen Überarbeitungsversuchen ungelöst bleibt.
- **Konsens**: Annahme nach Prüfung, wenn keine aufrechterhaltenen Einwände verbleiben.

## Prozessübersicht

### Schritt 1 — Entwurf
Ein Vorschlag wird eingereicht mit:
- einer klaren Beschreibung der Änderungen,
- Begründung und erwarteter Auswirkung,
- Verweisen auf betroffene Abschnitte,
- einer Kompatibilitätserklärung mit dem Kernel.

### Schritt 2 — Prüfungsfenster
Ein definiertes Prüfungsfenster wird eröffnet (zeitlich begrenzt).
Teilnehmende dürfen:
- Klärungsfragen stellen,
- Verbesserungen vorschlagen,
- Einwände erheben (müssen begründet sein).

### Schritt 3 — Behandlung von Einwänden (nach Treu und Glauben)
Wenn Einwände erhoben werden, muss der Vorschlagende:
- den Einwand direkt behandeln,
- den Vorschlag überarbeiten, oder
- dokumentieren, warum der Einwand außerhalb des Geltungsbereichs liegt.

Einwände müssen sich beziehen auf:
- Kernel-Prinzipien, oder
- Verifizierbarkeits-/Vertrauensprobleme, oder
- Anti-Vereinnahmungs-/Neutralitätsrisiken.

### Schritt 4 — Lösung
Ein Vorschlag darf angenommen werden, wenn:
- Einwände durch Überarbeitung gelöst wurden, oder
- Einwände zurückgezogen wurden, oder
- eine klare Aufzeichnung zeigt, dass Einwände ohne Konflikt mit dem Kernel beantwortet wurden.

Wenn aufrechterhaltene Einwände verbleiben, wird der Vorschlag nicht angenommen.

### Schritt 5 — Ratifizierung und Aufzeichnung
Angenommene Vorschläge müssen:
- mit einem nachvollziehbaren Commit gemergt werden,
- mit einer kurzen Änderungszusammenfassung aufgezeichnet werden,
- wo zutreffend mit Diskussionen/Notizen verlinkt werden.

## Sonderregel: Änderungen an Governance-Regeln
Jede Änderung an:
- dem Kernel,
- Konsensregeln,
- Kustodianschaftsregeln,
erfordert erhöhte Prüfung und ausdrückliche Kompatibilitätsbegründung.

## Nicht-Autoritätsklausel
Konsens schafft keine Autorität über Ergebnisse.
Er regelt nur die Integrität der Dokumente und Prozesse des Systems.
