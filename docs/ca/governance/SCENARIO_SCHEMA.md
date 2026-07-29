# Contractes d'escenari de HUB_Optimus

> **Estat de la traducció: `review-needed`.** Aquest text és una traducció
> candidata sense evidència d'una revisió lingüística humana qualificada. La
> font canònica per a aquesta superfície de governança és
> [la versió anglesa](../../governance/SCENARIO_SCHEMA.md).

## Propòsit

HUB_Optimus manté intencionadament dos contractes d'escenari diferents:

1. la plantilla rica de treball humà que estructura l'anàlisi i la revisió; i
2. l'entrada JSON executable estricta que accepta el simulador prototípic.

Són superfícies d'autoria relacionades, no representacions equivalents.
Convertir un flux humà en JSON executable és una decisió de modelatge manual i
amb pèrdues. El repositori no conté cap convertidor automàtic, i l'acceptació
executable no verifica la narrativa humana ni cap afirmació sobre el món real.

## Límits de les fonts

- Referència del flux humà:
  [`../../../v1_core/workflow/04_scenario_template.md`](../../../v1_core/workflow/04_scenario_template.md)
- Plantilla lleugera d'autoria del repositori:
  [`../../scenarios/scenario_template.md`](../../scenarios/scenario_template.md)
- Estructura executable:
  [`../../../scenario.schema.json`](../../../scenario.schema.json)
- Carregador JSON autoritatiu i validació entre registres:
  [`../../../run_scenario.py`](../../../run_scenario.py)
- Comportament del runtime:
  [`../../architecture/runtime_contract.md`](../../architecture/runtime_contract.md)
- Guia operativa:
  [`../../../SIMULATION_README.md`](../../../SIMULATION_README.md)
- Precedència de les fonts de veritat del projecte:
  [`../../context/SOURCE_OF_TRUTH.md`](../../context/SOURCE_OF_TRUTH.md)
- Política d'idiomes canònics i miralls:
  [`../../context/STATUS.md`](../../context/STATUS.md)

L'schema defineix l'estructura del document. El carregador rebutja, a més,
constants JSON no estàndard i noms d'actor duplicats. L'schema aplicable, el
carregador/codi font, les proves i el contracte de runtime són autoritatius per
al comportament executable. `STATUS.md` governa les qüestions d'idioma canònic.
Aquest document de governança relaciona aquests límits; no substitueix ni
amplia les fonts executables.

## Contracte JSON executable

L'objecte arrel té exactament cinc camps obligatoris. Es rebutgen els camps
desconeguts a l'arrel i dins de `roles[]`.

| Camp JSON | Forma acceptada | Ús actual pel carregador/runtime | Allò que no implica |
|---|---|---|---|
| `title` | Cadena no buida ni formada només per espais | Es desa al `Scenario` del runtime. Actualment no afecta les accions ni l'èxit. | Un ID del flux, una versió, un registre d'evidència o un títol verificat del món real. |
| `description` | Cadena no buida ni formada només per espais | Es desa al `Scenario`. Les polítiques incorporades actuals no la llegeixen. | Context estructurat, una cronologia, verificació de la veritat o una narrativa avaluada. |
| `roles` | Matriu no buida; cada element conté únicament les cadenes no buides `name` i `role` | El carregador exigeix valors `name` únics. `name` identifica l'actor i la seva entrada a l'historial. `role` es passa a la política seleccionada; la política actual `biased` tracta especialment els valors exactes `hardliner` i `mediator`, mentre que la política predeterminada i els altres valors de rol utilitzen ofertes uniformes. | Objectius, restriccions, autoritat, deures de verificació, biografia o una política declarada per actor. |
| `success_criteria` | Objecte no buit amb cadenes, nombres, enters, booleans o `null` de JSON com a valors | Després de cada ronda hi ha èxit quan qualsevol acció de qualsevol actor coincideix amb qualsevol parell clau/valor. Per tant, els criteris tenen semàntica OR, no AND. Les polítiques incorporades només emeten `offer`. El kernel compara `actor_action.get(key)` amb el valor esperat; per això, un criteri `null` també coincideix amb una acció que omet aquesta clau. | La definició humana d'èxit mínim o ampliat, verificació, durabilitat, estabilitat o qualitat de la política. |
| `max_rounds` | Enter superior o igual a `1` | Fixa el nombre màxim de rondes. Es retorna un fracàs si cap criteri mecànic coincideix abans del límit. | Una agenda de rondes, seqüència, termini, pla de negociació o garantia que s'executin totes les rondes previstes. |

Els fitxers executables han de ser JSON estàndard. No s'accepten YAML ni les
constants no estàndard `NaN`, `Infinity` i `-Infinity`. La validació de l'schema
i de la identitat només acredita la integritat de l'entrada; no acredita
l'exactitud factual.

## Relació camp per camp amb el flux humà ric

| Secció del flux humà | Possible projecció manual a JSON | Contingut només narratiu o absent del runtime |
|---|---|---|
| **0. Metadades** — ID, versió, idioma, data d'actualització, autoria, estat | Una persona pot triar un valor breu de presentació per a `title`. No hi ha derivació automàtica. | Versió, idioma, dates, autoria, estat del flux i historial de canvis no tenen camp executable. |
| **1. Resum executiu** — situació, objectiu mínim, origen de la dificultat | Es pot redactar manualment un resum breu com a `description`. | El runtime desa, però no avalua, el resum, l'objectiu, la dificultat ni la seva base factual. |
| **2. Actors i rols** — parts, tercers, objectius, límits, pressió | Els identificadors i les etiquetes breus de rol es poden projectar a `roles[].name` i `roles[].role`. Els noms han de ser únics. | Objectius, límits, pressió interna, autoritat i relacions no tenen representació executable. Es rebutgen les claus addicionals dins d'un rol. |
| **3. Context i cronologia** — context previ, fets recents, horitzó | Una part del context es pot condensar manualment a `description`. | No es modelen esdeveniments, dates, relacions temporals, fites ni horitzons de temps. |
| **4. Interessos, posicions i restriccions** — interessos, demandes, restriccions internes, línies vermelles, flexibilitat | Sense projecció directa. | Tots els camps d'aquesta secció són només narratius. No es poden afegir a `roles[]` sense canviar l'schema. |
| **5. Objectiu mínim i criteris d'èxit** — èxit mínim, èxit ampliat, fracàs clar | Només un criteri expressable com a clau d'acció i valor JSON escalar es pot codificar manualment a `success_criteria`. | No s'avaluen la qualitat humana del resultat, l'èxit ampliat, el fracàs clar, la durabilitat ni la verificació. Diverses entrades JSON són alternatives, no una conjunció. |
| **6. Proposta inicial** — acció, calendari, geografia, excepcions, verificació, mesures davant l'incompliment | Sense projecció directa. | El JSON actual no pot precarregar una proposta, calendari, geografia, excepció o mesura de compliment. Les polítiques incorporades generen accions `offer` simples durant l'execució. |
| **7. Verificació i compliment** — verificador, objecte, mètode, freqüència, accés, disputes | Sense projecció directa. | El simulador no integra evidència, sensors, control d'accés, compliment, resolució de disputes ni Trust Layer. |
| **8. Riscos i punts de fricció** — malentesos, incentius per enganyar, ambigüitat, sabotejadors, incidents | Sense projecció directa. | El runtime actual no consumeix riscos ni dinàmiques causals o adversàries. |
| **9. Rondes recomanades** — fases, esborrany d'acord, punts oberts, passos següents | Una persona pot triar `max_rounds` com a límit mecànic. | El contingut de les fases, la seqüència, els lliurables, els punts oberts, la responsabilitat i els terminis no són executables. |
| **10. Avaluació posterior** — claredat, verificabilitat, viabilitat, cost polític, risc d'escalada | Sense projecció d'entrada. | Els camps de resultat `status`, `rounds`, `history` i `detail` són dades mecàniques d'execució; no calculen aquestes puntuacions. |
| **11. Meta-learning** — lliçons, errors, definicions absents, canvis futurs, preguntes noves | Sense projecció directa. | El runtime no actualitza escenaris, no aprèn de les execucions ni crea conclusions de governança. |

## Relació amb la plantilla lleugera d'autoria

[`../../scenarios/scenario_template.md`](../../scenarios/scenario_template.md)
és una ajuda per proposar i revisar contingut al repositori, no un fitxer
d'entrada del simulador. El títol, el context breu, les etiquetes d'actors i una
condició d'èxit expressable mecànicament poden informar `title`, `description`,
`roles` i `success_criteria` mitjançant autoria manual. No té cap camp específic
per a `max_rounds`; el límit executable s'ha de triar per separat. Família,
tensió, mode de fallada, invariants, pla de benchmark i notes no tenen cap camp
directe al runtime. Una proposta de benchmark no es converteix en benchmark
congelat només perquè existeixi un JSON executable.

## Els controls del runtime no són camps de l'escenari

La CLI suportada exposa controls externs al document JSON:

- la ruta posicional de l'escenari o `--scenario` selecciona el fitxer JSON;
- `--seed` tria un flux aleatori reproduïble;
- `--policy` tria una política suportada per a tots els actors (`uniform` o
  `biased`); i
- `--output` tria la ruta del resultat.

Les estratègies humanes per actor, l'evidència, les regles de verificació i les
fases de negociació no es poden codificar afegint aquests noms al JSON. Els
camps desconeguts es rebutgen.

## Exemple de projecció mínima

Un flux humà pot descriure diverses parts, interessos, riscos, salvaguardes i un
acord verificat. Aquesta projecció executable conserva únicament dues etiquetes
d'actor, una condició mecànica d'oferta i un límit de cinc rondes:

```json
{
  "title": "Alto el foc parcial",
  "description": "Dues faccions negocien un alto el foc parcial.",
  "roles": [
    {"name": "FaccioA", "role": "negotiator"},
    {"name": "FaccioB", "role": "negotiator"}
  ],
  "success_criteria": {"offer": 5},
  "max_rounds": 5
}
```

Una execució reeixida només significa que almenys una acció generada contenia
`"offer": 5` abans del límit. No significa que s'hagi negociat, verificat o
sostingut un alto el foc, ni que sigui legítim o aconsellable.

## Disciplina de canvis

- No introdueixis camps exclusius del flux humà al JSON executable; la
  validació els rebutjarà.
- No descriguis la plantilla humana com a executable ni el JSON com un escenari
  analític complet.
- Tot canvi de camp executable requereix un canvi acotat que actualitzi
  conjuntament `scenario.schema.json`, el carregador/runtime quan correspongui,
  els exemples, les proves i la documentació del runtime.
- Qualsevol traducció més rica del flux humà al runtime requereix un issue de
  schema/runtime aprovat explícitament. Aquest mapa no concedeix aquesta
  capacitat.

## Maduresa de la traducció

Aquest mirall català roman en estat `review-needed`. Els miralls alemany,
espanyol, francès i rus també romanen en `review-needed`; l'hebreu i el xinès
simplificat romanen en `stub`. Aquests estats es declaren a
[`../../i18n/maturity.v1.json`](../../i18n/maturity.v1.json). Les comprovacions
estructurals o automatitzades no certifiquen qualitat lingüística, revisió
professional ni paritat.
