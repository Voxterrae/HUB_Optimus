# HUB_Optimus — Vertrauensebene (Trust Layer)

## Zweck
Die Trust Layer definiert, wie HUB_Optimus Aussagen, Zusagen und „Beweise“ bewertet.
Sie trennt verifizierbare Signale von Narrativdruck und verhindert, dass Dringlichkeit oder moralische Rahmung als Ersatz für Evidenz dienen.

## Kernidee
Nicht alles ist gleich „wahr“. HUB_Optimus klassifiziert Vertrauen anhand von:
- Verifizierbarkeit,
- Zugriff auf Beobachtung,
- Anreizstrukturen,
- Manipulationsresistenz.

## Evidenzklassen (Beispielrahmen)
- **Klasse A (direkt verifizierbar):** unabhängige Beobachtung, nachprüfbare Daten, reproduzierbare Prüfung.
- **Klasse B (teilweise verifizierbar):** verifizierbare Teilstücke, aber Lücken bei Zugriff/Abdeckung.
- **Klasse C (nicht verifizierbar):** Absichtserklärungen, Behauptungen ohne Prüfpfad.

> Hinweis: Diese Klassen sind ein operatives Raster. Entscheidend ist die Begründung samt Prüfpfad.

## Vertrauensprofil-Dimensionen (operativ)
Bewerte Aussagen entlang von:
1) **Zugriff** (wer kann was beobachten?)
2) **Integrität** (Anreiz zu täuschen vs. Anreiz zur Genauigkeit)
3) **Abdeckung** (wie vollständig ist die Beobachtung?)
4) **Zeit** (wie frisch/zeitkritisch ist die Evidenz?)
5) **Störbarkeit** (wie leicht ist die Evidenz manipulierbar?)

## Anti-Gaming-Regel
Wenn ein Akteur versucht:
- Prüfpfade zu blockieren,
- Definitionslücken auszunutzen,
- „Belege“ selektiv zu liefern,
- Beobachtung zu verzögern,
dann wird die Vertrauensklassifikation herabgestuft,
auch wenn das Narrativ überzeugend wirkt.

## Integrationspunkte
- Szenarioeingaben sollen Evidenz mit dem Schema referenzieren: `governance/SCENARIO_SCHEMA.md`
- Bewertungen sollen Evidenzklasse + Trust-Profil explizit zitieren: `governance/EVALUATION_STANDARD.md`

---

## Kernelzugang & Anti-Capture-Regeln (Hardening)

### Vertrauensstufen (High-Level)
- **Reader:** darf lesen und referenzieren.
- **Contributor:** darf Änderungen an Nicht-Kernel-Materialien zur Prüfung vorschlagen.
- **Custodian:** darf Governance-Änderungen unter strengem Prozess genehmigen.

### Kernel-Zugangsregel
Direkte Änderungen an Kernel-Dokumenten erfordern:
1) explizite Begründung mit Bezug auf Kernel-Prinzipien,
2) Consensus-Review gemäß CONSENSUS_PROCESS,
3) Custodianship-Zustimmung gemäß CUSTODIANSHIP,
4) Synchronisierung über Sprach-Spiegel hinweg.

### Anti-Capture-Regel
Versuche,
- Drift über Übersetzung einzuschleusen,
- die Methode umzubranden, während Ansprüche übernommen werden,
- Governance in Marketing umzuwandeln,
werden als Capture-Versuche behandelt und zurückgewiesen.
