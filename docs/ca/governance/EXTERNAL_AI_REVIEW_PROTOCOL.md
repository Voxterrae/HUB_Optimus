# Protocol de Revisió d'IA Externa

Aquest protocol defineix les regles i el format per utilitzar models d'IA externs (per exemple, Claude, Gemini, Perplexity, Grok i eines similars) per revisar contingut, arquitectura i documentació dins del repositori HUB_Optimus.

Els models d'IA externs són eines valuoses per a l'anàlisi, la revisió de codi i la retroalimentació. Tanmateix, els seus resultats s'han de mantenir estrictament consultius. Els resultats de la IA no han d'eludir mai la governança d'Issues i Pull Requests (PR) de GitHub.

Aquest protocol s'alinea explícitament amb la matriu d'accés d'IA definida a [Voxterrae/HUB_Optimus#1584](https://github.com/Voxterrae/HUB_Optimus/issues/1584).

## Principis

1. **Només Consultiu:** Els models d'IA externs segueixen sent estrictament consultius i no es converteixen mai en la font de la veritat.
2. **GitHub com a Font de la Veritat:** Cap troballa externa no pot convertir-se en treball d'implementació tret que estigui representada per una Issue o PR de GitHub. L'acció directa basada en resultats d'IA externa sense seguiment de governança està estrictament prohibida.
3. **Sense Integració:** Aquest protocol regula l'intercanvi de text manual. La integració automatitzada amb proveïdors d'IA externs està fora de l'abast.
4. **Seguretat de les Dades:** Mai pugeu secrets privats, credencials o dades de repositoris no públics a eines externes.

## Regles de Gestió de Resultats

Totes les troballes generades per models d'IA externs han de ser classificades de nou a GitHub:

- **Troballes i Suggeriments:** Si una revisió d'IA externa genera troballes útils, un col·laborador humà o un agent intern autoritzat ha de copiar els suggeriments rellevants en una Issue de GitHub o un comentari de PR.
- **Desacords:** Si el model d'IA ressalta un desacord o conflicte, ha de ser avaluat per un humà o un agent autoritzat. Si es considera vàlid, s'ha de resoldre mitjançant processos de consens estàndard dins d'un PR o Issue de GitHub.
- **Treball de Seguiment:** Si la IA suggereix treball addicional, s'ha de crear una Issue explícita de GitHub per fer-ne el seguiment.
- **Acció Directa Prohibida:** El resultat d'una IA externa no es pot canalitzar directament als contractes de temps d'execució, full de ruta o governança sense format manual i seguiment centrat en GitHub.

## Format del Paquet de Revisió

Per garantir que als models externs se'ls atorguen els límits i el context adequats, totes les sol·licituds de revisió han d'utilitzar el format de Paquet de Revisió estandarditzat a continuació. Aquest paquet es pot compartir externament sense atorgar autoritat.

### Plantilla Estàndard de Paquet de Revisió

```markdown
### 1. Context
[Proporcioneu l'objectiu d'alt nivell de la revisió. Per exemple: "Revisar aquest pull request per a la consistència de la documentació i l'alineació amb els principis de governança d'HUB_Optimus."]

### 2. Fitxers i Abast
[Llisteu els fitxers específics, fragments de codi o seccions de documentació sota revisió.]
- Fitxer 1: `ruta/al/fitxer.md`
- Fitxer 2: `ruta/al/codi.py`

### 3. Preguntes
[Especifiqueu en què s'ha de centrar la IA. Sigueu explícits per evitar al·lucinacions o l'ampliació de l'abast.]
- La documentació s'alinea explícitament amb els principis del Kernel de Capa 0?
- Hi ha inconsistències lògiques en l'escenari proposat?
- El codi s'adhereix als controls de seguretat requerits?

### 4. Restriccions
[Proporcioneu límits per al model d'IA.]
- Actueu només en un paper consultiu. No teniu autoritat per aprovar o fusionar aquests canvis.
- No proposeu reescriptures arquitectòniques globals.
- Centreu-vos estrictament en els fitxers proporcionats en l'abast.
- Mantingueu la perspectiva d'integritat primer.

### 5. Resultat Esperat
[Definiu el format que espereu que retorni la IA.]
- Una llista amb vinyetes de troballes específiques.
- Per a cada troballa, proporcioneu el nom del fitxer i el canvi suggerit.
- Una breu justificació basada en avaluació sistèmica, no en preferència personal.
```
