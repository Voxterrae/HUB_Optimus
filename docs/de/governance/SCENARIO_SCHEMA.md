@'
# HUB_Optimus — Szenario-Schema (Eingabeformat)

## Zweck
Dieses Schema definiert die minimalen, vergleichbaren Eingaben für Szenarien in HUB_Optimus.
Was nicht definiert ist, wird zu Ambiguität — und Ambiguität ist ein Eskalationsverstärker.

## 0) Metadaten
- **Szenario-ID:** eindeutiger Identifier
- **Version:** z. B. 0.1 / 1.0
- **Sprache:** z. B. de / en / es
- **Letzte Aktualisierung:** YYYY-MM-DD
- **Autor/in:** Name/Handle
- **Status:** Entwurf / stabil / in Prüfung
- **Vertraulichkeit:** öffentlich / intern / eingeschränkt

## 1) Auslöser (Trigger)
- Was hat den Prozess gestartet?
  - Entscheidung / Ereignis / Muster-Wiederkehr / Incentive-Shift
- Minimaler neutraler Kontext (ohne Narrative, ohne Schuldzuweisung)

## 2) Akteure und Rollen
Für jeden Akteur:
- Ziel(e)
- Beschränkungen (politisch/ökonomisch/sicherheitlich)
- interne Zwänge
- rote Linien
- mögliche Flexibilität

Optionale Rollen:
- Mediator/Beobachter/Verifizierer
- Spoiler / Feldakteure / Öffentlichkeit

## 3) Kontext und Zeithorizont
- struktureller Kontext (3–8 Stichpunkte)
- relevante jüngste Ereignisse (3–6 Stichpunkte)
- Zeithorizont: Stunden / Tage / Wochen (eins wählen)

## 4) Interessen, Positionen, Restriktionen
Für jede Partei:
- **Interessen** (warum)
- **Positionen** (was fordert sie)
- **Restriktionen** (was sie intern nicht kann)
- **Linien/No-Gos**
- **Verhandlungsraum** (mögliche Zugeständnisse)

## 5) Minimales Ziel und Erfolgskriterien
- **Minimaler Erfolg:** 1–3 Sätze, **verifizierbar**
- **Erweiterter Erfolg (optional)**
- **Klarer Misserfolg:** welches Ergebnis ist “nicht hilfreich”

## 6) Initialer Vorschlag (Entwurf)
- Hauptaktion (was)
- Zeitplan (wann)
- geografischer Umfang (wo)
- Ausnahmen (was nicht)
- Verifizierung (wer, wie, Zugang)
- Konsequenzen bei Verstoß (was passiert)

## 7) Verifizierung und Compliance
- Wer verifiziert?
- Was wird verifiziert (beobachtbare Ereignisse)?
- Wie wird verifiziert (Beobachtung, Reports, Sensoren, Zugang)?
- Frequenz (alle X Stunden/Tage)
- Zugang/Sicherheit (Zonen, Genehmigungen, Eskorten)
- Dispute-Handling (bei widersprüchlichen Versionen)

## 8) Risiken und Reibungspunkte
Liste 5–10 realistische Risiken:
- vorhersehbare Missverständnisse
- Anreiz zum “Cheaten”
- absichtliche Ambiguität
- Spoiler/Sabotage
- Vorfälle im Feld

## 9) Empfohlene Runden (Leitfaden)
- Runde 1: Vorschlag ↔ Antwort (teilweise Annahme + Bedingungen)
- Runde 2: Anpassungen (Verifizierung, Sequenz, Garantien)
- Runde 3: Abschluss (Text + offene Punkte)

Finale Lieferung:
- kurzer Agreement-Entwurf (8–15 Zeilen)
- Liste offener Punkte
- nächste Schritte (wer macht was bis wann)

## 10) Bewertung (Post-Mortem)
Bewerte (0–3 oder 0–5) und notiere Evidenz:
- Klarheit
- Verifizierbarkeit
- Umsetzbarkeit
- politischer Preis
- Eskalationsrisiko

## 11) Meta-Learning
- Was hat funktioniert?
- Was ist gescheitert?
- Was war undefiniert?
- Was würdest du beim nächsten Mal ändern?
- Welche neuen Fragen sind entstanden?
'@ | Set-Content -Encoding utf8 docs\de\governance\SCENARIO_SCHEMA.md
