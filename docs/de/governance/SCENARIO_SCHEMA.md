# HUB_Optimus-Szenarioverträge

> **Übersetzungsstatus: `review-needed`.** Dieser Text ist eine
> Übersetzungskandidatin ohne Nachweis einer qualifizierten menschlichen
> Sprachprüfung. Die kanonische Quelle für diese Governance-Oberfläche ist
> [die englische Fassung](../../governance/SCENARIO_SCHEMA.md).

## Zweck

HUB_Optimus hält absichtlich zwei verschiedene Szenarioverträge getrennt:

1. die umfangreiche menschliche Workflow-Vorlage zur Strukturierung von
   Analyse und Review; und
2. die strikte ausführbare JSON-Eingabe, die der prototypische Simulator
   akzeptiert.

Sie sind verwandte Autorenoberflächen, aber keine gleichwertigen
Darstellungen. Die Übertragung eines menschlichen Workflows in ausführbares
JSON ist eine manuelle, verlustbehaftete Modellierungsentscheidung. Das
Repository enthält keinen automatischen Konverter, und die Annahme als
ausführbare Eingabe verifiziert weder die menschliche Darstellung noch
irgendeine Aussage über die reale Welt.

## Quellengrenzen

- Referenz für den menschlichen Workflow:
  [`../../../v1_core/workflow/04_scenario_template.md`](../../../v1_core/workflow/04_scenario_template.md)
- Leichtgewichtige Autorenvorlage des Repositorys:
  [`../../scenarios/scenario_template.md`](../../scenarios/scenario_template.md)
- Ausführbare Struktur:
  [`../../../scenario.schema.json`](../../../scenario.schema.json)
- Maßgeblicher JSON-Loader und datensatzübergreifende Validierung:
  [`../../../run_scenario.py`](../../../run_scenario.py)
- Laufzeitverhalten:
  [`../../architecture/runtime_contract.md`](../../architecture/runtime_contract.md)
- Bedienungsanleitung:
  [`../../../SIMULATION_README.md`](../../../SIMULATION_README.md)
- Vorrangordnung der projektweiten Wahrheitsquellen:
  [`../../context/SOURCE_OF_TRUTH.md`](../../context/SOURCE_OF_TRUTH.md)
- Richtlinie zu kanonischen Sprachen und Spiegeln:
  [`../../context/STATUS.md`](../../context/STATUS.md)

Das Schema definiert die Dokumentstruktur. Der Loader verwirft zusätzlich
nicht standardkonforme JSON-Konstanten und doppelte Akteursnamen. Das
anwendbare Schema, Loader/Quellcode, Tests und Laufzeitvertrag sind für das
ausführbare Verhalten maßgeblich. `STATUS.md` regelt Fragen zur kanonischen
Sprache. Dieses Governance-Dokument ordnet diese Grenzen ein; es ersetzt oder
erweitert die ausführbaren Quellen nicht.

## Ausführbarer JSON-Vertrag

Das Wurzelobjekt enthält genau fünf Pflichtfelder. Unbekannte Felder auf
Wurzelebene und innerhalb von `roles[]` werden verworfen.

| JSON-Feld | Akzeptierte Form | Aktuelle Nutzung durch Loader/Laufzeit | Was daraus nicht folgt |
|---|---|---|---|
| `title` | Nicht leere Zeichenkette, die nicht nur aus Leerraum besteht | Wird im Laufzeitobjekt `Scenario` gespeichert. Wirkt sich derzeit nicht auf Akteursaktionen oder Erfolg aus. | Workflow-ID, Version, Evidenzdatensatz oder verifizierter Titel aus der realen Welt. |
| `description` | Nicht leere Zeichenkette, die nicht nur aus Leerraum besteht | Wird im `Scenario` gespeichert. Die aktuellen eingebauten Policies lesen sie nicht. | Strukturierter Kontext, Zeitachse, Wahrheitsprüfung oder bewertete Darstellung. |
| `roles` | Nicht leeres Array; jedes Element enthält ausschließlich die nicht leeren Zeichenketten `name` und `role` | Der Loader verlangt eindeutige `name`-Werte. `name` identifiziert den Akteur und seinen Verlaufseintrag. `role` wird an die gewählte Policy übergeben; die aktuelle Policy `biased` behandelt die exakten Werte `hardliner` und `mediator` gesondert, während die Standard-Policy und andere Rollenwerte gleichverteilte Angebote verwenden. | Ziele, Einschränkungen, Befugnisse, Prüfpflichten, Biografie oder eine akteursspezifische Policy-Deklaration. |
| `success_criteria` | Nicht leeres Objekt mit JSON-Zeichenketten, Zahlen, Ganzzahlen, booleschen Werten oder `null` als Werten | Nach jeder Runde tritt Erfolg ein, wenn irgendeine Akteursaktion mit irgendeinem einzelnen Kriteriums-Schlüssel/Wert-Paar übereinstimmt. Kriterien besitzen daher OR-, nicht AND-Semantik. Die aktuellen eingebauten Policies geben nur `offer` aus. Der Kernel vergleicht `actor_action.get(key)` mit dem erwarteten Wert; deshalb stimmt ein `null`-Kriterium auch mit einer Aktion überein, in der der Schlüssel fehlt. | Menschliche Definition von Mindest- oder erweitertem Erfolg, Verifikation, Dauerhaftigkeit, Stabilität oder Policy-Qualität. |
| `max_rounds` | Ganzzahl größer oder gleich `1` | Legt die maximale Rundenzahl fest. Wenn vor der Obergrenze kein mechanisches Kriterium übereinstimmt, wird ein Fehlschlag zurückgegeben. | Rundenagenda, Reihenfolge, Frist, Verhandlungsplan oder Garantie, dass alle geplanten Runden stattfinden. |

Ausführbare Dateien müssen Standard-JSON sein. YAML und die nicht
standardkonformen Konstanten `NaN`, `Infinity` und `-Infinity` werden nicht
akzeptiert. Schema- und Identitätsvalidierung belegen nur Eingabeintegrität,
nicht sachliche Richtigkeit.

## Feldweise Beziehung zum umfangreichen menschlichen Workflow

| Abschnitt des menschlichen Workflows | Mögliche manuelle Projektion in JSON | Nur narrativ oder anderweitig nicht in der Laufzeit vorhanden |
|---|---|---|
| **0. Metadaten** — ID, Version, Sprache, Aktualisierungsdatum, Autorenschaft, Status | Ein Mensch kann einen kurzen Anzeigewert für `title` wählen. Eine automatische Ableitung gibt es nicht. | Version, Sprache, Daten, Autorenschaft, Workflow-Status und Änderungsverlauf haben kein ausführbares Feld. |
| **1. Kurzfassung** — Situation, Mindestziel, Ursache der Schwierigkeit | Eine kurze Zusammenfassung kann manuell als `description` verfasst werden. | Die Laufzeit speichert, bewertet aber weder Zusammenfassung, Ziel, Schwierigkeit noch deren faktische Grundlage. |
| **2. Akteure und Rollen** — Parteien, Dritte, Ziele, Grenzen, Druck | Akteurskennungen und kurze Rollenbezeichnungen können in `roles[].name` und `roles[].role` projiziert werden. Namen müssen eindeutig sein. | Ziele, Grenzen, interner Druck, Befugnisse und Beziehungen haben keine ausführbare Darstellung. Zusätzliche Schlüssel in einer Rolle werden verworfen. |
| **3. Kontext und Zeitachse** — Vorgeschichte, jüngste Ereignisse, Zeithorizont | Ausgewählter Kontext kann manuell in `description` verdichtet werden. | Ereignisse, Daten, zeitliche Beziehungen, Meilensteine und Zeithorizonte werden nicht modelliert. |
| **4. Interessen, Positionen und Einschränkungen** — Interessen, Forderungen, interne Einschränkungen, rote Linien, Flexibilität | Keine direkte Projektion. | Alle Felder dieses Abschnitts sind rein narrativ. Ohne Schemaänderung können sie nicht zu `roles[]` hinzugefügt werden. |
| **5. Mindestziel und Erfolgskriterien** — Mindesterfolg, erweiterter Erfolg, klarer Fehlschlag | Nur ein Kriterium, das sich als Aktionsschlüssel und skalarer JSON-Wert ausdrücken lässt, kann manuell in `success_criteria` codiert werden. | Menschliche Ergebnisqualität, erweiterter Erfolg, klarer Fehlschlag, Dauerhaftigkeit und Verifikation werden nicht bewertet. Mehrere JSON-Einträge sind Alternativen, keine Konjunktion. |
| **6. Ausgangsvorschlag** — Handlung, Zeitplan, Geografie, Ausnahmen, Verifikation, Maßnahmen bei Verstößen | Keine direkte Projektion. | Das aktuelle JSON kann keinen Vorschlag, Zeitplan, geografischen Bezug, keine Ausnahme oder Durchsetzungsmaßnahme vorgeben. Eingebaute Policies erzeugen zur Laufzeit einfache `offer`-Aktionen. |
| **7. Verifikation und Einhaltung** — Prüfer, Prüfgegenstand, Methode, Häufigkeit, Zugang, Streitfälle | Keine direkte Projektion. | Der Simulator besitzt keine Evidenz-, Sensor-, Zugangs-, Compliance-, Streitbeilegungs- oder Trust-Layer-Integration. |
| **8. Risiken und Reibungspunkte** — Missverständnisse, Täuschungsanreize, Mehrdeutigkeit, Störakteure, Vorfälle | Keine direkte Projektion. | Risiken sowie kausale oder adversariale Dynamiken werden von der aktuellen Laufzeit nicht verarbeitet. |
| **9. Empfohlene Runden** — Phasen, Vereinbarungsentwurf, offene Punkte, nächste Schritte | Ein Mensch kann `max_rounds` als mechanische Obergrenze wählen. | Phaseninhalte, Reihenfolge, Liefergegenstände, offene Punkte, Zuständigkeiten und Fristen sind nicht ausführbar. |
| **10. Nachträgliche Bewertung** — Klarheit, Verifizierbarkeit, Machbarkeit, politische Kosten, Eskalationsrisiko | Keine Eingabeprojektion. | Die Ergebnisfelder `status`, `rounds`, `history` und `detail` sind mechanische Laufdaten; sie berechnen diese Bewertungen nicht. |
| **11. Meta-Lernen** — Erkenntnisse, Fehlschläge, fehlende Definitionen, künftige Änderungen, neue Fragen | Keine direkte Projektion. | Die Laufzeit aktualisiert keine Szenarien, lernt nicht aus Läufen und erzeugt keine Governance-Schlussfolgerungen. |

## Beziehung zur leichtgewichtigen Autorenvorlage

[`../../scenarios/scenario_template.md`](../../scenarios/scenario_template.md)
ist eine Hilfe für Vorschlag und Review im Repository, keine Eingabedatei des
Simulators. Titel, kurzer Kontext, Akteursbezeichnungen und eine mechanisch
ausdrückbare Erfolgsbedingung können durch manuelle Autorenschaft in `title`,
`description`, `roles` und `success_criteria` einfließen. Die Vorlage besitzt
kein eigenes `max_rounds`-Feld; die ausführbare Obergrenze muss separat gewählt
werden. Szenariofamilie, Spannung, Fehlermodus, Invarianten, Benchmark-Plan und
Notizen besitzen kein direktes Laufzeitfeld. Ein Benchmark-Vorschlag wird nicht
allein durch die Existenz einer ausführbaren JSON-Datei zu einem eingefrorenen
Benchmark.

## Laufzeitsteuerungen sind keine Szenariofelder

Die unterstützte CLI stellt Steuerungen außerhalb des JSON-Dokuments bereit:

- Der positionale Szenariopfad oder `--scenario` wählt die JSON-Eingabedatei;
- `--seed` wählt einen reproduzierbaren Zufallsstrom;
- `--policy` wählt eine unterstützte Policy für alle Akteure (`uniform` oder
  `biased`); und
- `--output` wählt den Ergebnispfad.

Menschliche akteursspezifische Strategien, Evidenz, Verifikationsregeln und
Verhandlungsphasen lassen sich nicht durch Hinzufügen dieser Namen zum JSON
codieren. Unbekannte Felder werden verworfen.

## Beispiel einer minimalen Projektion

Ein menschlicher Workflow kann mehrere Parteien, Interessen, Risiken,
Schutzmaßnahmen und eine verifizierte Vereinbarung beschreiben. Die folgende
ausführbare Projektion erhält lediglich zwei Akteursbezeichnungen, eine
mechanische Angebotsbedingung und eine Obergrenze von fünf Runden:

```json
{
  "title": "Partielle Waffenruhe",
  "description": "Zwei Fraktionen verhandeln eine partielle Waffenruhe.",
  "roles": [
    {"name": "FraktionA", "role": "negotiator"},
    {"name": "FraktionB", "role": "negotiator"}
  ],
  "success_criteria": {"offer": 5},
  "max_rounds": 5
}
```

Ein erfolgreicher Lauf bedeutet nur, dass mindestens eine erzeugte Aktion vor
der Obergrenze `"offer": 5` enthielt. Er bedeutet nicht, dass eine Waffenruhe
ausgehandelt, verifiziert, dauerhaft, legitim oder ratsam war.

## Änderungsdisziplin

- Füge keine nur für den menschlichen Workflow vorgesehenen Felder in das
  ausführbare JSON ein; die Validierung wird sie verwerfen.
- Beschreibe weder die menschliche Vorlage als ausführbar noch das JSON als
  vollständiges analytisches Szenario.
- Jede Änderung eines ausführbaren Felds erfordert eine abgegrenzte Änderung,
  die `scenario.schema.json`, gegebenenfalls Loader/Laufzeit, Beispiele, Tests
  und Laufzeitdokumentation gemeinsam aktualisiert.
- Eine reichhaltigere Übersetzung vom menschlichen Workflow in die Laufzeit
  erfordert ein ausdrücklich genehmigtes Schema-/Laufzeit-Issue. Diese
  Zuordnung gewährt keine solche Fähigkeit.

## Übersetzungsreife

Dieser deutsche Spiegel verbleibt im Status `review-needed`. Der spanische,
katalanische, französische und russische Spiegel verbleibt ebenfalls in
`review-needed`; Hebräisch und vereinfachtes Chinesisch verbleiben in `stub`.
Diese Zustände sind in
[`../../i18n/maturity.v1.json`](../../i18n/maturity.v1.json) festgelegt.
Strukturelle oder automatisierte Prüfungen zertifizieren weder sprachliche
Qualität noch professionelle Prüfung oder Parität.
