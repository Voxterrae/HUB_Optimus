# Contrats de scénario HUB_Optimus

> **État de traduction : `review-needed`.** Ce texte est une traduction
> candidate sans preuve de révision linguistique humaine qualifiée. La source
> canonique de cette surface de gouvernance est
> [la version anglaise](../../governance/SCENARIO_SCHEMA.md).

## Objet

HUB_Optimus maintient intentionnellement deux contrats de scénario distincts :

1. le modèle riche de travail humain qui structure l'analyse et la révision ;
   et
2. l'entrée JSON exécutable stricte acceptée par le simulateur prototype.

Ce sont des surfaces de rédaction liées, et non des représentations
équivalentes. Convertir un flux humain en JSON exécutable est une décision de
modélisation manuelle avec perte d'information. Le dépôt ne contient aucun
convertisseur automatique, et l'acceptation exécutable ne vérifie ni le récit
humain ni une quelconque affirmation sur le monde réel.

## Limites des sources

- Référence du flux humain :
  [`../../../v1_core/workflow/04_scenario_template.md`](../../../v1_core/workflow/04_scenario_template.md)
- Modèle léger de rédaction du dépôt :
  [`../../scenarios/scenario_template.md`](../../scenarios/scenario_template.md)
- Structure exécutable :
  [`../../../scenario.schema.json`](../../../scenario.schema.json)
- Chargeur JSON faisant autorité et validation inter-enregistrements :
  [`../../../run_scenario.py`](../../../run_scenario.py)
- Comportement du runtime :
  [`../../architecture/runtime_contract.md`](../../architecture/runtime_contract.md)
- Guide opérateur :
  [`../../../SIMULATION_README.md`](../../../SIMULATION_README.md)
- Ordre de priorité des sources de vérité du projet :
  [`../../context/SOURCE_OF_TRUTH.md`](../../context/SOURCE_OF_TRUTH.md)
- Politique des langues canoniques et des miroirs :
  [`../../context/STATUS.md`](../../context/STATUS.md)

Le schéma définit la structure du document. Le chargeur rejette en plus les
constantes JSON non standard et les noms d'acteurs en double. Le schéma
applicable, le chargeur/code source, les tests et le contrat du runtime font
autorité pour le comportement exécutable. `STATUS.md` régit les questions de
langue canonique. Le présent document de gouvernance établit la correspondance
entre ces limites ; il ne remplace ni n'étend les sources exécutables.

## Contrat JSON exécutable

L'objet racine comporte exactement cinq champs obligatoires. Les champs
inconnus à la racine et dans `roles[]` sont rejetés.

| Champ JSON | Forme acceptée | Utilisation actuelle par le chargeur/runtime | Ce que cela n'implique pas |
|---|---|---|---|
| `title` | Chaîne non vide et ne contenant pas uniquement des espaces | Stocké dans le `Scenario` du runtime. N'affecte actuellement ni les actions des acteurs ni la réussite. | Identifiant de flux, version, enregistrement de preuve ou titre vérifié dans le monde réel. |
| `description` | Chaîne non vide et ne contenant pas uniquement des espaces | Stockée dans le `Scenario`. Les politiques intégrées actuelles ne la lisent pas. | Contexte structuré, chronologie, vérification de la vérité ou récit évalué. |
| `roles` | Tableau non vide ; chaque élément contient uniquement les chaînes non vides `name` et `role` | Le chargeur exige des valeurs `name` uniques. `name` identifie l'acteur et son entrée dans l'historique. `role` est transmis à la politique choisie ; la politique actuelle `biased` traite spécialement les valeurs exactes `hardliner` et `mediator`, tandis que la politique par défaut et les autres rôles utilisent des offres uniformes. | Objectifs, contraintes, autorité, obligations de vérification, biographie ou déclaration de politique propre à chaque acteur. |
| `success_criteria` | Objet non vide dont les valeurs sont des chaînes, nombres, entiers, booléens ou `null` JSON | Après chaque tour, il y a réussite lorsqu'une action quelconque d'un acteur quelconque correspond à une paire clé/valeur quelconque. Les critères ont donc une sémantique OR et non AND. Les politiques intégrées actuelles n'émettent que `offer`. Le noyau compare `actor_action.get(key)` à la valeur attendue ; un critère `null` correspond donc aussi à une action qui omet cette clé. | Définition humaine de la réussite minimale ou étendue, vérification, durabilité, stabilité ou qualité de la politique. |
| `max_rounds` | Entier supérieur ou égal à `1` | Fixe le nombre maximal de tours. Un échec est renvoyé si aucun critère mécanique ne correspond avant la limite. | Ordre du jour des tours, séquence, échéance, plan de négociation ou garantie que tous les tours prévus auront lieu. |

Les fichiers exécutables doivent être du JSON standard. YAML et les constantes
non standard `NaN`, `Infinity` et `-Infinity` ne sont pas acceptés. La
validation du schéma et de l'identité établit uniquement l'intégrité de
l'entrée ; elle n'établit pas l'exactitude factuelle.

## Correspondance champ par champ avec le flux humain riche

| Section du flux humain | Projection manuelle possible vers JSON | Contenu uniquement narratif ou absent du runtime |
|---|---|---|
| **0. Métadonnées** — identifiant, version, langue, date de mise à jour, auteur, état | Une personne peut choisir une courte valeur d'affichage pour `title`. Il n'existe aucune dérivation automatique. | Version, langue, dates, auteur, état du flux et historique des modifications n'ont aucun champ exécutable. |
| **1. Résumé exécutif** — situation, objectif minimal, source de difficulté | Un court résumé contextuel peut être rédigé manuellement dans `description`. | Le runtime stocke mais n'évalue ni le résumé, ni l'objectif, ni la difficulté, ni leur base factuelle. |
| **2. Acteurs et rôles** — parties, tiers, objectifs, limites, pression | Les identifiants d'acteurs et les libellés courts de rôle peuvent être projetés dans `roles[].name` et `roles[].role`. Les noms doivent être uniques. | Objectifs, limites, pression interne, autorité et relations n'ont aucune représentation exécutable. Les clés supplémentaires dans un rôle sont rejetées. |
| **3. Contexte et chronologie** — contexte antérieur, événements récents, horizon | Une partie du contexte peut être condensée manuellement dans `description`. | Les événements, dates, relations temporelles, jalons et horizons ne sont pas modélisés. |
| **4. Intérêts, positions et contraintes** — intérêts, demandes, contraintes internes, lignes rouges, flexibilité | Aucune projection directe. | Tous les champs de cette section sont uniquement narratifs. Ils ne peuvent pas être ajoutés à `roles[]` sans modification du schéma. |
| **5. Objectif minimal et critères de réussite** — réussite minimale, réussite étendue, échec clair | Seul un critère exprimable comme clé d'action et valeur JSON scalaire peut être encodé manuellement dans `success_criteria`. | La qualité humaine du résultat, la réussite étendue, l'échec clair, la durabilité et la vérification ne sont pas évalués. Plusieurs entrées JSON sont des alternatives, pas une conjonction. |
| **6. Proposition initiale** — action, calendrier, géographie, exceptions, vérification, mesures en cas de non-respect | Aucune projection directe. | Le JSON actuel ne peut précharger ni proposition, ni calendrier, ni géographie, ni exception, ni mesure d'exécution. Les politiques intégrées génèrent des actions `offer` simples pendant l'exécution. |
| **7. Vérification et conformité** — vérificateur, objet, méthode, fréquence, accès, différends | Aucune projection directe. | Le simulateur n'intègre ni preuves, ni capteurs, ni contrôle d'accès, ni conformité, ni résolution des différends, ni Trust Layer. |
| **8. Risques et points de friction** — malentendus, incitations à tricher, ambiguïté, acteurs perturbateurs, incidents | Aucune projection directe. | Les risques et les dynamiques causales ou adverses ne sont pas consommés par le runtime actuel. |
| **9. Tours recommandés** — phases, projet d'accord, points ouverts, prochaines étapes | Une personne peut choisir `max_rounds` comme limite mécanique. | Le contenu des phases, la séquence, les livrables, les points ouverts, la responsabilité et les délais ne sont pas exécutables. |
| **10. Évaluation a posteriori** — clarté, vérifiabilité, faisabilité, coût politique, risque d'escalade | Aucune projection d'entrée. | Les champs de résultat `status`, `rounds`, `history` et `detail` sont des données mécaniques d'exécution ; ils ne calculent pas ces évaluations. |
| **11. Méta-apprentissage** — enseignements, échecs, définitions manquantes, changements futurs, nouvelles questions | Aucune projection directe. | Le runtime ne met pas à jour les scénarios, n'apprend pas des exécutions et ne produit pas de conclusions de gouvernance. |

## Relation avec le modèle léger de rédaction

[`../../scenarios/scenario_template.md`](../../scenarios/scenario_template.md)
est une aide à la proposition et à la révision dans le dépôt, et non un fichier
d'entrée du simulateur. Son titre, son contexte bref, ses libellés d'acteurs et
une condition de réussite exprimable mécaniquement peuvent informer `title`,
`description`, `roles` et `success_criteria` par une rédaction manuelle. Le
modèle n'a pas de champ dédié à `max_rounds` ; la limite exécutable doit être
choisie séparément. La famille du scénario, la tension, le mode d'échec, les
invariants, le plan de benchmark et les notes n'ont aucun champ direct dans le
runtime. Une proposition de benchmark ne devient pas un benchmark figé du seul
fait qu'un JSON exécutable existe.

## Les contrôles du runtime ne sont pas des champs du scénario

La CLI prise en charge expose des contrôles extérieurs au document JSON :

- le chemin positionnel du scénario ou `--scenario` sélectionne le fichier JSON ;
- `--seed` sélectionne un flux aléatoire reproductible ;
- `--policy` sélectionne une politique prise en charge pour tous les acteurs
  (`uniform` ou `biased`) ; et
- `--output` sélectionne le chemin du résultat.

Les stratégies humaines propres à chaque acteur, les preuves, les règles de
vérification et les phases de négociation ne peuvent pas être encodées en
ajoutant ces noms au JSON. Les champs inconnus sont rejetés.

## Exemple de projection minimale

Un flux humain peut décrire plusieurs parties, intérêts, risques, garanties et
un accord vérifié. La projection exécutable suivante ne conserve que deux
libellés d'acteurs, une condition mécanique d'offre et une limite de cinq tours :

```json
{
  "title": "Cessez-le-feu partiel",
  "description": "Deux factions négocient un cessez-le-feu partiel.",
  "roles": [
    {"name": "FactionA", "role": "negotiator"},
    {"name": "FactionB", "role": "negotiator"}
  ],
  "success_criteria": {"offer": 5},
  "max_rounds": 5
}
```

Une exécution réussie signifie uniquement qu'au moins une action générée
contenait `"offer": 5` avant la limite. Elle ne signifie pas qu'un
cessez-le-feu a été négocié, vérifié, rendu durable, légitime ou souhaitable.

## Discipline de modification

- N'ajoutez pas au JSON exécutable des champs réservés au flux humain ; la
  validation les rejettera.
- Ne décrivez ni le modèle humain comme exécutable, ni le JSON comme un
  scénario analytique complet.
- Toute modification d'un champ exécutable exige une modification ciblée qui
  mette à jour ensemble `scenario.schema.json`, le chargeur/runtime selon le
  cas, les exemples, les tests et la documentation du runtime.
- Toute traduction plus riche du flux humain vers le runtime exige une issue
  de schéma/runtime explicitement approuvée. Cette correspondance n'accorde
  aucune capacité de ce type.

## Maturité de la traduction

Ce miroir français reste dans l'état `review-needed`. Les miroirs allemand,
espagnol, catalan et russe restent également dans `review-needed` ; l'hébreu et
le chinois simplifié restent dans `stub`. Ces états sont déclarés dans
[`../../i18n/maturity.v1.json`](../../i18n/maturity.v1.json). Les contrôles
structurels ou automatisés ne certifient ni qualité linguistique, ni révision
professionnelle, ni parité.
