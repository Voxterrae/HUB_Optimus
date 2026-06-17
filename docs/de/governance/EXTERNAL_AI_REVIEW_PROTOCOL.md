# Externes KI-Überprüfungsprotokoll

Dieses Protokoll definiert die Regeln und Formate für die Verwendung externer KI-Modelle (z. B. Claude, Gemini, Perplexity, Grok und ähnliche Tools) zur Überprüfung von Inhalten, Architektur und Dokumentation innerhalb des HUB_Optimus-Repositorys.

Externe KI-Modelle sind wertvolle Werkzeuge für Analysen, Code-Reviews und Feedback. Ihre Ausgaben müssen jedoch streng beratend bleiben. KI-Ausgaben dürfen niemals die Governance von GitHub-Issues und Pull Requests (PR) umgehen.

Dieses Protokoll stimmt ausdrücklich mit der KI-Zugriffsmatrix überein, die in [Voxterrae/HUB_Optimus#1584](https://github.com/Voxterrae/HUB_Optimus/issues/1584) definiert ist.

## Prinzipien

1. **Nur Beratend:** Externe KI-Modelle bleiben streng beratend und werden niemals zur Quelle der Wahrheit.
2. **GitHub als Quelle der Wahrheit:** Keine externe Erkenntnis kann zu Implementierungsarbeit werden, es sei denn, sie wird durch ein GitHub-Issue oder einen PR repräsentiert. Direkte Aktionen basierend auf externen KI-Ausgaben ohne Governance-Tracking sind strengstens verboten.
3. **Keine Integration:** Dieses Protokoll regelt den manuellen Textaustausch. Automatisierte Integrationen mit externen KI-Anbietern liegen außerhalb des Geltungsbereichs.
4. **Datensicherheit:** Laden Sie niemals private Geheimnisse, Anmeldeinformationen oder nicht öffentliche Repository-Daten in externe Tools hoch.

## Regeln zur Handhabung von Ausgaben

Alle Erkenntnisse, die von externen KI-Modellen generiert werden, müssen in GitHub zurückgeführt werden:

- **Erkenntnisse und Vorschläge:** Wenn eine externe KI-Überprüfung nützliche Erkenntnisse liefert, muss ein menschlicher Mitwirkender oder ein autorisierter interner Agent die relevanten Vorschläge in ein GitHub-Issue oder einen PR-Kommentar kopieren.
- **Unstimmigkeiten:** Wenn das KI-Modell eine Unstimmigkeit oder einen Konflikt hervorhebt, muss dies von einem Menschen oder einem autorisierten Agenten bewertet werden. Wenn es als gültig erachtet wird, sollte es über standardmäßige Konsensprozesse innerhalb eines GitHub-PRs oder -Issues gelöst werden.
- **Folgearbeiten:** Wenn die KI zusätzliche Arbeiten vorschlägt, muss ein explizites GitHub-Issue erstellt werden, um diese zu verfolgen.
- **Direkte Aktion Verboten:** Die Ausgabe einer externen KI kann nicht direkt in Laufzeit-, Roadmap- oder Governance-Verträge eingespeist werden, ohne manuelle Formatierung und GitHub-zentriertes Tracking.

## Format des Überprüfungspakets

Um sicherzustellen, dass externe Modelle die entsprechenden Grenzen und den richtigen Kontext erhalten, müssen alle Überprüfungsanfragen das unten stehende standardisierte Format des Überprüfungspakets verwenden. Dieses Paket kann extern geteilt werden, ohne Autorität zu gewähren.

### Standardvorlage für das Überprüfungspaket

```markdown
### 1. Kontext
[Geben Sie das übergeordnete Ziel der Überprüfung an. Zum Beispiel: "Überprüfen Sie diesen Pull Request auf Dokumentationskonsistenz und Ausrichtung an den HUB_Optimus-Governance-Prinzipien."]

### 2. Dateien und Umfang
[Listen Sie die spezifischen Dateien, Codeausschnitte oder Dokumentationsabschnitte auf, die überprüft werden sollen.]
- Datei 1: `pfad/zur/datei.md`
- Datei 2: `pfad/zum/code.py`

### 3. Fragen
[Geben Sie an, worauf sich die KI konzentrieren soll. Seien Sie explizit, um Halluzinationen oder eine Ausweitung des Umfangs zu vermeiden.]
- Stimmt die Dokumentation ausdrücklich mit den Prinzipien des Layer-0-Kernels überein?
- Gibt es im vorgeschlagenen Szenario logische Inkonsistenzen?
- Entspricht der Code den erforderlichen Sicherheitsprüfungen?

### 4. Einschränkungen
[Legen Sie Grenzen für das KI-Modell fest.]
- Sie handeln nur in einer beratenden Rolle. Sie haben keine Befugnis, diese Änderungen zu genehmigen oder zusammenzuführen.
- Schlagen Sie keine umfassenden architektonischen Umschreibungen vor.
- Konzentrieren Sie sich streng auf die im Umfang bereitgestellten Dateien.
- Behalten Sie die "Integrität-Zuerst"-Perspektive bei.

### 5. Erwartete Ausgabe
[Definieren Sie das Format, das Sie von der KI erwarten.]
- Eine Aufzählungsliste spezifischer Erkenntnisse.
- Geben Sie für jede Erkenntnis den Dateinamen und die vorgeschlagene Änderung an.
- Eine kurze Begründung, die auf einer systemischen Bewertung und nicht auf persönlichen Vorlieben basiert.
```
