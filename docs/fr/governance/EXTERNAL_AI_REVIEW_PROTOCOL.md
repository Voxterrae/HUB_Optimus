# Protocole de Révision par IA Externe

Ce protocole définit les règles et le format d'utilisation des modèles d'IA externes (par exemple, Claude, Gemini, Perplexity, Grok et outils similaires) pour réviser le contenu, l'architecture et la documentation au sein du dépôt HUB_Optimus.

Les modèles d'IA externes sont des outils précieux pour l'analyse, la révision de code et le retour d'information. Cependant, leurs résultats doivent rester strictement consultatifs. Les résultats de l'IA ne doivent jamais contourner la gouvernance des Issues et des Pull Requests (PR) de GitHub.

Ce protocole s'aligne explicitement sur la matrice d'accès de l'IA définie dans [Voxterrae/HUB_Optimus#1584](https://github.com/Voxterrae/HUB_Optimus/issues/1584).

## Principes

1. **Uniquement Consultatif :** Les modèles d'IA externes restent strictement consultatifs et ne deviennent jamais la source de vérité.
2. **GitHub comme Source de Vérité :** Aucune conclusion externe ne peut devenir un travail d'implémentation à moins d'être représentée par une Issue ou une PR GitHub. L'action directe basée sur les résultats d'une IA externe sans suivi de gouvernance est strictement interdite.
3. **Aucune Intégration :** Ce protocole régit l'échange manuel de texte. L'intégration automatisée avec des fournisseurs d'IA externes est hors de portée.
4. **Sécurité des Données :** Ne téléchargez jamais de secrets privés, d'informations d'identification ou de données de dépôt non publiques vers des outils externes.

## Règles de Traitement des Résultats

Toutes les conclusions générées par des modèles d'IA externes doivent être triées et renvoyées vers GitHub :

- **Conclusions et Suggestions :** Si une révision par une IA externe génère des conclusions utiles, un contributeur humain ou un agent interne autorisé doit copier les suggestions pertinentes dans une Issue GitHub ou un commentaire de PR.
- **Désaccords :** Si le modèle d'IA souligne un désaccord ou un conflit, il doit être évalué par un humain ou un agent autorisé. S'il est jugé valide, il doit être résolu via des processus de consensus standards au sein d'une PR ou d'une Issue GitHub.
- **Travail de Suivi :** Si l'IA suggère un travail supplémentaire, une Issue GitHub explicite doit être créée pour le suivre.
- **Action Directe Interdite :** Le résultat d'une IA externe ne peut pas être injecté directement dans l'exécution, la feuille de route ou les contrats de gouvernance sans un formatage manuel et un suivi centré sur GitHub.

## Format du Paquet de Révision

Pour s'assurer que les modèles externes reçoivent les limites et le contexte appropriés, toutes les demandes de révision doivent utiliser le format standardisé du Paquet de Révision ci-dessous. Ce paquet peut être partagé en externe sans accorder d'autorité.

### Modèle Standard du Paquet de Révision

```markdown
### 1. Contexte
[Fournissez l'objectif global de la révision. Par exemple : "Réviser cette pull request pour assurer la cohérence de la documentation et l'alignement avec les principes de gouvernance de HUB_Optimus."]

### 2. Fichiers et Portée
[Listez les fichiers spécifiques, les extraits de code ou les sections de documentation en cours de révision.]
- Fichier 1 : `chemin/vers/fichier.md`
- Fichier 2 : `chemin/vers/code.py`

### 3. Questions
[Précisez sur quoi l'IA doit se concentrer. Soyez explicite pour éviter les hallucinations ou le dépassement de la portée.]
- La documentation s'aligne-t-elle explicitement avec les principes du Noyau de Couche 0 ?
- Y a-t-il des incohérences logiques dans le scénario proposé ?
- Le code respecte-t-il les contrôles de sécurité requis ?

### 4. Contraintes
[Fournissez des limites au modèle d'IA.]
- Vous agissez uniquement dans un rôle consultatif. Vous n'avez pas l'autorité d'approuver ou fusionner ces changements.
- Ne proposez pas de réécritures architecturales radicales.
- Concentrez-vous strictement sur les fichiers fournis dans la portée.
- Maintenez la perspective d'intégrité en premier.

### 5. Résultat Attendu
[Définissez le format que vous attendez de l'IA.]
- Une liste à puces de conclusions spécifiques.
- Pour chaque conclusion, fournissez le nom du fichier et le changement suggéré.
- Une brève justification basée sur une évaluation systémique, et non sur une préférence personnelle.
```
