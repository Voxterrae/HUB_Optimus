# HUB_Optimus Szenario-Schema

## Zweck
Die Mindeststruktur definieren, die erforderlich ist, um `run_scenario.py` sicher auszuführen.
Ein Szenario ist ein strukturierter Eingabevertrag, keine argumentative Erzählung.

## Kanonischer maschinenlesbarer Vertrag
- JSON-Schema-Datei: [../../../scenario.schema.json](../../../scenario.schema.json)
- Quelle der Vertragsversionierung: Git-Historie für `scenario.schema.json`

## Erforderliche Felder
- `title`: nicht leerer String
- `description`: nicht leerer String
- `roles`: nicht leeres Array von `{ "name": string, "role": string }`
- `success_criteria`: nicht leeres Objekt
- `max_rounds`: Integer >= 1

## Validierungsverhalten
- Unbekannte Top-Level-Felder werden zurückgewiesen (`additionalProperties: false`).
- Leere Rollen-Arrays werden zurückgewiesen.
- Fehlende Pflichtfelder werden zurückgewiesen.

## Typische ungültige Eingaben (müssen fehlschlagen)
- Fehlendes `success_criteria`.
- `roles` ist ein leeres Array.
- `max_rounds` ist `0` oder ein Nicht-Integer-Wert.

## Erweiterungshinweise
- Rückwärtskompatibilität nach Möglichkeit bewahren; optionale Felder zuerst hinzufügen.
- Wenn ein neues Pflichtfeld erforderlich ist, Schema-Version erhöhen und Beispiele/Tests im selben PR aktualisieren.
- Dieses Dokument und `scenario.schema.json` gemeinsam aktualisieren; niemals eines ohne das andere aktualisieren.
