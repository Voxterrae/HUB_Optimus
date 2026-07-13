# HUB_Optimus — Governance-Intelligence-Protokoll

- Status: Aktiv mit dem Merge des ratifizierenden Pull Requests
- Vorschlagsnachweis: [#1694](https://github.com/Voxterrae/HUB_Optimus/issues/1694)
- Geltung: Kanonisches Governance-Protokoll
- Umfang: Nur Dokumentation und analytischer Prozess

## Zweck

Governance Intelligence ist die verbindliche analytische Disziplin zur Trennung von Behauptungen, Evidenz, Schlussfolgerungen, Unsicherheit, narrativer Verstärkung und operativer Relevanz, wenn HUB_Optimus komplexes institutionelles, zivilgesellschaftliches, technologisches oder informationelles Material untersucht.

Dieses Protokoll regelt, wie Analysen strukturiert und geprüft werden. Es legt nicht fest, welche Schlussfolgerungen erreicht werden müssen, schafft keine autonome Autorität und ersetzt kein menschliches Urteil.

## Quelle der Wahrheit und Autorität

GitHub-Issues, Pull Requests, Commits, Checks und versionierte Repository-Dokumente bilden den Projektnachweis. Chat-Nachrichten, Modellausgaben, verborgene Prompts, Gesprächsspeicher, externe KI-Prüfungen, Screenshots und nicht eingecheckte Entwürfe sind beratende Eingaben, solange und bis sie in diesem Nachweis abgebildet sind.

Keine Behauptung erhält Autorität, weil sie wiederholt, populär, dringend, emotional wirksam, von einem leistungsfähigen Modell erzeugt oder einer angesehenen Quelle zugeschrieben wird. Autorität und Vertrauen müssen aus prüfbarer Evidenz, expliziter Begründung, Repository-Governance und menschlich verantworteter Prüfung entstehen.

Wenn der Chat-Zustand dem GitHub-Zustand widerspricht, hat GitHub Vorrang.

## Erforderlicher Analysenachweis

Eine Governance-Intelligence-Analyse MUSS die folgenden sechs Ebenen getrennt halten:

| Ebene | Erforderliche Frage | Erforderliches Ergebnis |
| --- | --- | --- |
| Behauptung | Was genau wird behauptet? | Eine konkrete, abgegrenzte Aussage |
| Evidenz | Welches prüfbare Material stützt oder widerlegt sie? | Quellen, Beobachtungen, Herkunft und Einschränkungen |
| Schlussfolgerung | Welche Begründung geht über die Evidenz hinaus? | Ein expliziter Begründungsschritt, keine als Tatsache getarnte Schlussfolgerung |
| Unsicherheit | Was bleibt unbekannt, umstritten, unvollständig oder nicht verifizierbar? | Lücken, Konflikte, Annahmen und Vertrauensgrenzen |
| Narrative Verstärkung | Was könnte übertrieben, verkürzt, gerahmt oder emotional verstärkt sein? | Der Verzerrungsmechanismus und seine wahrscheinliche Wirkung |
| Operative Relevanz | Warum ist dies für das Repository oder den geprüften Fall relevant? | Ein gültiges Signal, eine begrenzte Folge oder ein explizites Ergebnis ohne Handlungsbedarf |

Alle sechs Ebenen MÜSSEN vorhanden sein. Eine Ebene darf `nichts festgestellt`, `keine Evidenz vorgelegt` oder `keine Handlung gerechtfertigt` angeben; sie darf nicht ausgelassen werden, um künstliche Gewissheit zu erzeugen.

## Behauptungen

Eine Behauptung MUSS erfasst werden, bevor sie bewertet wird. Das Erfassen einer Behauptung bedeutet nicht, sie anzunehmen.

Eine Behauptung SOLLTE, soweit verfügbar, Folgendes identifizieren:

- die Person, den Autor, das System oder die Institution, die sie äußert;
- Zeit und Kontext der Äußerung;
- die betroffene Bevölkerung, das Ereignis, das System oder die Entscheidung;
- den ausgedrückten Gewissheitsgrad;
- die Bedingungen, unter denen die Behauptung prüfbar oder falsifizierbar wäre.

Zusammengesetzte Behauptungen SOLLTEN in unabhängig prüfbare Aussagen zerlegt werden.

## Evidenz und Herkunft

Evidenz MUSS prüfbar und zuordenbar bleiben. Soweit praktikabel, SOLLTE eine Analyse die Quelle, den Repository-Pfad oder externen Verweis, das Datum, den Zugriffskontext und die Einordnung als primär, sekundär, abgeleitet, vom Benutzer bereitgestellt oder modellgeneriert festhalten.

Modellgenerierter Text ist nicht allein deshalb Evidenz, weil ein Modell ihn erzeugt hat. Er kann zusammenfassen, vergleichen oder eine Schlussfolgerung vorschlagen, aber das stützende Material muss getrennt sichtbar bleiben.

Screenshots, Social-Media-Beiträge, Auszüge und Autoritätsaussagen sind Artefakte oder Behauptungen. Ohne ausreichende Herkunft, Kontext und Bestätigung sind sie kein schlüssiger Beweis.

Widersprüchliche Evidenz MUSS erhalten bleiben und darf nicht stillschweigend verworfen werden. Fehlende Evidenz MUSS ausdrücklich benannt werden.

## Schlussfolgerung und Unsicherheit

Jeder Schritt, der über direkt gestützte Evidenz hinausgeht, MUSS als Schlussfolgerung gekennzeichnet werden.

Eine Schlussfolgerung SOLLTE angeben:

- welche Evidenz sie verwendet;
- von welchen Annahmen sie abhängt;
- welche alternativen Erklärungen plausibel bleiben;
- welche neue Evidenz sie stärken, schwächen oder umkehren könnte.

Unsicherheit DARF NICHT zu einem binären Urteil verdichtet werden, nur damit das Ergebnis entschlossener wirkt. Unbekannt, umstritten, unvollständig und nicht verifizierbar sind materiell unterschiedliche Zustände und SOLLTEN getrennt ausgewiesen werden.

## Narrative Verstärkung

Die Analyse narrativer Verstärkung untersucht, wie eine Behauptung über ihre Evidenz hinaus scheinbare Kraft gewinnen kann. Relevante Mechanismen sind Wiederholung, Dringlichkeit, selektive Auslassung, Verdichtung von Unsicherheit, Berufung auf Autorität, emotional aufgeladene Rahmung, falscher Konsens und der Übergang von Möglichkeit zu Gewissheit.

Das Erkennen einer Verstärkung beweist nicht, dass die zugrunde liegende Behauptung falsch ist. Es kennzeichnet ein Prüfungsrisiko, das vom Evidenzstatus der Behauptung getrennt werden muss.

## Operative Relevanz und Signalgate

Operative Relevanz erfasst die begrenzte Folge der Analyse. Sie autorisiert nicht automatisch eine Implementierung und empfiehlt kein Ergebnis.

Eine Repository-Handlung ist nur gerechtfertigt, wenn ein gültiges Signal vorliegt:

- Regression;
- unklare Architektur;
- Reibung für Mitwirkende;
- Dokumentationsdrift;
- CI- oder Laufzeitsignal;
- Governance-Risiko;
- ausdrückliche Benutzeranforderung.

Wenn kein gültiges Signal vorliegt, ist kontrollierte Beobachtung das richtige Ergebnis. Wenn ein Signal vorliegt, MUSS jede Handlung als kleines, nachvollziehbares und prüfbares GitHub-Issue oder als Pull Request mit explizitem Umfang und Validierung dargestellt werden.

## KI- und Chat-Kontrollgrenze

Chat ist eine Interaktionsoberfläche, nicht die Steuerungsebene des Projekts.

KI-Systeme dürfen beobachten, analysieren, entwerfen, prüfen, vergleichen und eine eng autorisierte Repository-Änderung ausführen. Sie DÜRFEN diese Änderung NICHT selbst autorisieren oder zu einer verborgenen Autoritätsquelle werden.

Keine Modellfamilie, Modellversion, kein Anbieter, Prompt, Gespräch, Speichersystem, Ranking und kein verborgener Kontrollpfad darf:

- Governance ratifizieren;
- Repository-Evidenz außer Kraft setzen;
- Roadmap oder Architektur ohne den erforderlichen GitHub-Nachweis ändern;
- die eigene Arbeit genehmigen;
- die eigene Governance-Änderung mergen;
- Schutzregeln für Branches, Review oder CI umgehen;
- Herkunft, Unsicherheit, Modellbeteiligung oder wesentliche Meinungsverschiedenheiten verbergen.

Ein leistungsfähigeres Modell kann die analytische Tiefe verbessern, erhält dadurch aber keine größere Governance-Autorität. Ein Wechsel von Modell oder Anbieter ändert diese Grenze nicht.

Menschliche Verantwortlichkeit bleibt für Ratifikation, Veröffentlichung, Eskalation und sensible Nutzung verpflichtend. KI-Unterstützung muss über Issue, Branch, Commits, Pull Request, Review-Nachweis und Checks sichtbar bleiben, die die Änderung regeln.

## Verbotene Verwendungen

Dieses Protokoll DARF NICHT verwendet werden als:

- Wahr/Falsch-Orakel;
- Ersatz für Primärevidenz oder Fachkompetenz;
- verborgene Bewertungs-, Rangordnungs- oder Entscheidungsautorität;
- Vorwand für Überwachung oder Profiling privater Personen;
- Mechanismus für Zwang, Täuschung, Propaganda, gezielte politische Beeinflussung, Belästigung oder psychologische Manipulation;
- automatisierter Zensur- oder Durchsetzungsmechanismus;
- Grundlage für folgenreiche Entscheidungen über Menschen ohne getrennte rechtliche, Governance- und menschliche Prüfung;
- Methode zur Umgehung rechtmäßiger Aufsicht oder Repository-Governance;
- Mittel, um unsichere Analysen als feststehende Tatsachen darzustellen.

## Beziehung zu bestehenden Repository-Dokumenten

Dieses Protokoll präzisiert die Regeln zur analytischen Zerlegung und zur Mensch-KI-Übergabe, die bereits in Charter, Kernel, Consensus Process, Evaluation Standard, External AI Review Protocol, AGENTS.md und dem KI-Übergabenachweis angelegt sind.

`docs/concepts/governance-intelligence.md` bleibt eine nicht normative konzeptionelle Einführung. Diese Datei ist die kanonische Governance-Quelle für das Protokoll.

`docs/rfc/constitutional_governance_ai_regulatory_boundary.md` bleibt ein separater RFC-Entwurf. Die Ratifikation dieses Protokolls akzeptiert, ersetzt oder implementiert diesen RFC nicht stillschweigend.

Jeder Konflikt oder jede vorgeschlagene Erweiterung MUSS nach den bestehenden Regeln des Repositorys für Quelle der Wahrheit und Konsens gelöst werden.

## Änderungskontrolle

Materielle Änderungen an diesem Protokoll erfordern:

1. ein explizites GitHub-Issue oder RFC, das Signal, Umfang, Risiken und Kompatibilität beschreibt;
2. einen kleinen Pull Request mit sichtbarem Diff;
3. synchronisierte Governance-Spiegel gemäß der Übersetzungsrichtlinie des Repositorys;
4. menschlich verantwortete Prüfung, bei der Einwände dokumentiert und gelöst werden;
5. bestandene Repository-Checks vor dem Merge.

Der Merge des mit Issue #1694 verknüpften Pull Requests ratifiziert diese Version, sofern kein aufrechterhaltener Governance-Einwand besteht.

Dieses Protokoll autorisiert keine Änderungen an Laufzeit, Schema, Benchmarks, CI, Roadmap, Anbieter, Ingestion, Scoring, Dashboard oder Deployment. Jede solche Änderung erfordert ein eigenes abgegrenztes GitHub-Signal und einen eigenen Review-Pfad.

## Validierung

Eine konforme Prüfung kann aus dem Nachweis beantworten:

- Was wird behauptet?
- Welche Evidenz stützt oder widerlegt die Behauptung, und woher stammt sie?
- Was wird geschlossen statt beobachtet?
- Was bleibt unsicher?
- Welche narrative Verstärkung ist vorhanden oder nicht vorhanden?
- Welches operative Signal besteht, falls überhaupt?
- Wer bleibt für die Entscheidung oder nächste Handlung verantwortlich?
- Welches GitHub-Artefakt hält den maßgeblichen Zustand fest?

Das Protokoll ist strukturell gültig, wenn die kanonische Datei und alle erforderlichen Sprachspiegel vorhanden sind, die normative Bedeutung bewahren, keine Platzhalter enthalten und keine nicht abgegrenzte Implementierungsänderung einführen.
