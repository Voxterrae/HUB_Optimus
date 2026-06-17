import os

files = {
    'es': """# Protocolo de Revisión por IA Externa

Este protocolo define las reglas y el formato para utilizar modelos de IA externos (por ejemplo, Claude, Gemini, Perplexity, Grok y herramientas similares) en la revisión de contenido, arquitectura y documentación dentro del repositorio HUB_Optimus.

Los modelos de IA externos son herramientas valiosas para el análisis, la revisión de código y la retroalimentación. Sin embargo, sus resultados deben mantenerse estrictamente como consultivos. Los resultados de la IA nunca deben eludir la gobernanza de Issues y Pull Requests (PR) de GitHub.

Este protocolo se alinea explícitamente con la matriz de acceso de IA definida en [Voxterrae/HUB_Optimus#1584](https://github.com/Voxterrae/HUB_Optimus/issues/1584).

## Principios

1. **Solo Consultivo:** Los modelos de IA externos siguen siendo estrictamente consultivos y nunca se convierten en la fuente de verdad.
2. **GitHub como Fuente de Verdad:** Ningún hallazgo externo puede convertirse en trabajo de implementación a menos que esté representado por un Issue o PR de GitHub. La acción directa basada en resultados de IA externa sin seguimiento de gobernanza está estrictamente prohibida.
3. **Sin Integración:** Este protocolo rige el intercambio de texto manual. La integración automatizada con proveedores de IA externos está fuera de alcance.
4. **Seguridad de Datos:** Nunca suba secretos privados, credenciales o datos de repositorios no públicos a herramientas externas.

## Reglas de Manejo de Resultados

Todos los hallazgos generados por modelos de IA externos deben ser clasificados de vuelta a GitHub:

- **Hallazgos y Sugerencias:** Si una revisión de IA externa genera hallazgos útiles, un contribuyente humano o un agente interno autorizado debe copiar las sugerencias relevantes en un Issue de GitHub o en un comentario de PR.
- **Desacuerdos:** Si el modelo de IA resalta un desacuerdo o conflicto, debe ser evaluado por un humano o un agente autorizado. Si se considera válido, debe resolverse mediante procesos estándar de consenso dentro de un PR o Issue de GitHub.
- **Trabajo de Seguimiento:** Si la IA sugiere trabajo adicional, se debe crear un Issue explícito de GitHub para su seguimiento.
- **Acción Directa Prohibida:** El resultado de una IA externa no puede canalizarse directamente a contratos de tiempo de ejecución, hoja de ruta o gobernanza sin un formato manual y seguimiento centrado en GitHub.

## Formato del Paquete de Revisión

Para garantizar que los modelos externos reciban los límites y el contexto adecuados, todas las solicitudes de revisión deben utilizar el formato estandarizado del Paquete de Revisión a continuación. Este paquete puede compartirse externamente sin otorgar autoridad.

### Plantilla Estándar del Paquete de Revisión

```markdown
### 1. Contexto
[Proporcione el objetivo de alto nivel de la revisión. Por ejemplo: "Revisar este pull request para consistencia de la documentación y alineación con los principios de gobernanza de HUB_Optimus."]

### 2. Archivos y Alcance
[Enumere los archivos específicos, fragmentos de código o secciones de documentación bajo revisión.]
- Archivo 1: `ruta/al/archivo.md`
- Archivo 2: `ruta/al/codigo.py`

### 3. Preguntas
[Especifique en qué debe enfocarse la IA. Sea explícito para evitar alucinaciones o la desviación del alcance.]
- ¿La documentación se alinea explícitamente con los principios del Kernel de Capa 0?
- ¿Existen inconsistencias lógicas en el escenario propuesto?
- ¿El código cumple con los controles de seguridad requeridos?

### 4. Restricciones
[Proporcione límites para el modelo de IA.]
- Usted actúa solo en un rol consultivo. No tiene autoridad para aprobar o fusionar estos cambios.
- No proponga reescrituras arquitectónicas radicales.
- Concéntrese estrictamente en los archivos proporcionados en el alcance.
- Mantenga la perspectiva de integridad primero.

### 5. Resultado Esperado
[Defina el formato que espera que la IA devuelva.]
- Una lista con viñetas de hallazgos específicos.
- Para cada hallazgo, proporcione el nombre del archivo y el cambio sugerido.
- Una breve justificación basada en evaluación sistémica, no en preferencia personal.
```
""",
    'fr': """# Protocole de Révision par IA Externe

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
""",
    'de': """# Externes KI-Überprüfungsprotokoll

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
""",
    'ca': """# Protocol de Revisió d'IA Externa

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
""",
    'ru': """# Протокол внешнего обзора ИИ

Этот протокол определяет правила и форматы использования внешних моделей ИИ (например, Claude, Gemini, Perplexity, Grok и аналогичных инструментов) для анализа контента, архитектуры и документации в репозитории HUB_Optimus.

Внешние модели ИИ — это ценные инструменты для анализа, проверки кода и обратной связи. Однако их результаты должны носить строго рекомендательный характер. Выводы ИИ никогда не должны обходить правила управления проблемами (Issues) и запросами на слияние (Pull Requests) в GitHub.

Этот протокол явно согласуется с матрицей доступа ИИ, определенной в [Voxterrae/HUB_Optimus#1584](https://github.com/Voxterrae/HUB_Optimus/issues/1584).

## Принципы

1. **Только рекомендации:** Внешние модели ИИ носят строго рекомендательный характер и никогда не становятся источником истины.
2. **GitHub как источник истины:** Ни один внешний вывод не может стать работой по реализации, если он не представлен проблемой (Issue) или PR на GitHub. Прямые действия на основе вывода внешнего ИИ без отслеживания управления строго запрещены.
3. **Без интеграции:** Этот протокол регулирует ручной обмен текстом. Автоматизированная интеграция с внешними поставщиками ИИ выходит за рамки протокола.
4. **Безопасность данных:** Никогда не загружайте закрытые секреты, учетные данные или непубличные данные репозитория во внешние инструменты.

## Правила обработки результатов

Все выводы, сгенерированные внешними моделями ИИ, должны быть отсортированы обратно в GitHub:

- **Выводы и предложения:** Если внешняя проверка ИИ дает полезные результаты, участник-человек или авторизованный внутренний агент должен скопировать соответствующие предложения в Issue или комментарий PR на GitHub.
- **Разногласия:** Если модель ИИ выявляет разногласия или конфликты, их должен оценить человек или уполномоченный агент. Если они признаны обоснованными, их следует решать с помощью стандартных процессов консенсуса в рамках PR или Issue на GitHub.
- **Последующая работа:** Если ИИ предлагает дополнительную работу, необходимо создать явное Issue на GitHub для ее отслеживания.
- **Прямые действия запрещены:** Вывод внешнего ИИ не может быть направлен напрямую в контракты времени выполнения, дорожной карты или управления без ручного форматирования и отслеживания, ориентированного на GitHub.

## Формат пакета проверки

Чтобы гарантировать, что внешним моделям заданы соответствующие границы и контекст, во всех запросах на проверку должен использоваться стандартизированный формат пакета проверки, приведенный ниже. Этим пакетом можно делиться извне без предоставления полномочий.

### Стандартный шаблон пакета проверки

```markdown
### 1. Контекст
[Опишите цель проверки на высоком уровне. Например: «Проверьте этот pull request на предмет единообразия документации и соответствия принципам управления HUB_Optimus».]

### 2. Файлы и область применения
[Укажите конкретные файлы, фрагменты кода или разделы документации, подлежащие проверке.]
- Файл 1: `path/to/file.md`
- Файл 2: `path/to/code.py`

### 3. Вопросы
[Укажите, на чем должен сосредоточиться ИИ. Будьте откровенны, чтобы предотвратить галлюцинации или размывание рамок.]
- Согласуется ли документация с принципами ядра уровня 0?
- Есть ли какие-либо логические несоответствия в предложенном сценарии?
- Соответствует ли код необходимым проверкам безопасности?

### 4. Ограничения
[Укажите границы для модели ИИ.]
- Вы действуете только в качестве консультанта. У вас нет полномочий одобрять или объединять эти изменения.
- Не предлагайте масштабных архитектурных переписываний.
- Сосредоточьтесь исключительно на файлах, представленных в области применения.
- Поддерживайте принцип «целостность прежде всего».

### 5. Ожидаемый результат
[Определите формат, в котором ИИ должен вернуть результат.]
- Маркированный список конкретных выводов.
- Для каждого вывода укажите имя файла и предлагаемое изменение.
- Краткое обоснование на основе системной оценки, а не личных предпочтений.
```
""",
    'he': """# פרוטוקול סקירת בינה מלאכותית (AI) חיצונית

פרוטוקול זה מגדיר את הכללים והפורמטים לשימוש במודלי בינה מלאכותית חיצוניים (למשל, Claude, Gemini, Perplexity, Grok וכלים דומים) לבדיקת תוכן, ארכיטקטורה ותיעוד בתוך המאגר HUB_Optimus.

מודלי AI חיצוניים הם כלים בעלי ערך לניתוח, סקירת קוד ומשוב. עם זאת, התוצרים שלהם חייבים להישאר בגדר המלצה בלבד. תוצרי AI לעולם לא יעקפו את כללי הניהול (Governance) של Issues ו-Pull Requests (PR) ב-GitHub.

פרוטוקול זה מתיישר במפורש עם מטריצת הגישה של AI המוגדרת ב-[Voxterrae/HUB_Optimus#1584](https://github.com/Voxterrae/HUB_Optimus/issues/1584).

## עקרונות

1. **המלצה בלבד:** מודלי AI חיצוניים נשארים בגדר ממליצים בלבד ולעולם לא הופכים למקור האמת.
2. **GitHub כמקור האמת:** שום ממצא חיצוני לא יכול להפוך לעבודת יישום אלא אם הוא מיוצג על ידי Issue או PR ב-GitHub. פעולה ישירה המבוססת על פלט AI חיצוני ללא מעקב ניהולי אסורה בהחלט.
3. **ללא אינטגרציה:** פרוטוקול זה מנהל חילופי טקסט ידניים. אינטגרציה אוטומטית עם ספקי AI חיצוניים היא מחוץ לתחום.
4. **אבטחת נתונים:** לעולם אל תעלה סודות פרטיים, אישורים (credentials) או נתוני מאגר שאינם פומביים לכלים חיצוניים.

## כללי טיפול בתוצרים

כל הממצאים שנוצרו על ידי מודלי AI חיצוניים חייבים להיות מנותבים בחזרה ל-GitHub:

- **ממצאים והצעות:** אם סקירת AI חיצונית מניבה ממצאים שימושיים, תורם אנושי או סוכן פנימי מורשה חייב להעתיק את ההצעות הרלוונטיות ל-Issue או להערת PR ב-GitHub.
- **אי-הסכמות:** אם מודל ה-AI מדגיש חוסר הסכמה או קונפליקט, הדבר חייב להיבדק על ידי אדם או סוכן מורשה. אם נמצא תקף, יש לפתור אותו באמצעות תהליכי קונצנזוס סטנדרטיים בתוך PR או Issue ב-GitHub.
- **עבודת המשך:** אם ה-AI מציע עבודה נוספת, יש ליצור Issue מפורש ב-GitHub למעקב.
- **פעולה ישירה אסורה:** לא ניתן להעביר את הפלט של AI חיצוני ישירות לחוזי זמן-ריצה (runtime), מפת דרכים או ניהול ללא עיצוב ידני ומעקב ממוקד ב-GitHub.

## פורמט חבילת סקירה

כדי להבטיח שלמודלים חיצוניים ניתנים הגבולות וההקשר המתאימים, כל בקשות הסקירה חייבות להשתמש בפורמט חבילת הסקירה המתוקנן שלהלן. ניתן לשתף חבילה זו מחוץ לארגון מבלי להעניק סמכות.

### תבנית סטנדרטית לחבילת סקירה

```markdown
### 1. הקשר
[ספק את המטרה ברמה הגבוהה של הסקירה. לדוגמה: "סקור pull request זה עבור עקביות התיעוד והתאמה לעקרונות הניהול של HUB_Optimus."]

### 2. קבצים והיקף
[פרט את הקבצים הספציפיים, קטעי הקוד או קטעי התיעוד הנבדקים.]
- קובץ 1: `path/to/file.md`
- קובץ 2: `path/to/code.py`

### 3. שאלות
[ציין במה ה-AI צריך להתמקד. היה מפורש כדי למנוע הזיות (hallucination) או חריגה מההיקף.]
- האם התיעוד מתיישר במפורש עם עקרונות Kernel בשכבה 0?
- האם יש חוסר עקביות לוגית בתרחיש המוצע?
- האם הקוד עומד בבדיקות האבטחה הנדרשות?

### 4. אילוצים
[ספק גבולות למודל ה-AI.]
- אתה פועל בתפקיד מייעץ בלבד. אין לך סמכות לאשר או למזג (merge) שינויים אלו.
- אל תציע שכתובים ארכיטקטוניים גורפים.
- התמקד אך ורק בקבצים שסופקו בהיקף.
- שמור על נקודת המבט של "יושרה תחילה" (integrity-first).

### 5. פלט צפוי
[הגדר את הפורמט שאתה מצפה שה-AI יחזיר.]
- רשימת תבליטים של ממצאים ספציפיים.
- עבור כל ממצא, ספק את שם הקובץ ואת השינוי המוצע.
- רציונל קצר המבוסס על הערכה מערכתית, לא העדפה אישית.
```
""",
    'zh': """# 外部 AI 审查协议

本协议定义了在 HUB_Optimus 存储库中利用外部 AI 模型（如 Claude、Gemini、Perplexity、Grok 及类似工具）审查内容、架构和文档的规则与格式。

外部 AI 模型是用于分析、代码审查和提供反馈的宝贵工具。然而，它们的输出必须严格保持咨询性质。AI 的输出绝不能绕过 GitHub 的问题（Issue）和拉取请求（PR）治理流程。

本协议明确符合 [Voxterrae/HUB_Optimus#1584](https://github.com/Voxterrae/HUB_Optimus/issues/1584) 中定义的 AI 访问矩阵。

## 原则

1. **仅限咨询：** 外部 AI 模型严格保持咨询作用，绝不成为事实的唯一来源。
2. **GitHub 作为单一事实来源：** 除非有 GitHub 的 Issue 或 PR 代表，否则任何外部发现均不得直接转化为实施工作。严禁在没有治理跟踪的情况下，基于外部 AI 的输出采取直接行动。
3. **无自动化集成：** 本协议仅规管人工文本交换。与外部 AI 供应商的自动化集成不在范围内。
4. **数据安全：** 切勿将私密密钥、凭证或非公开存储库数据上传至外部工具。

## 输出处理规则

外部 AI 模型生成的所有发现必须在 GitHub 中进行分类处理：

- **发现和建议：** 如果外部 AI 审查产生了有用的发现，人类贡献者或授权的内部代理必须将相关建议复制到 GitHub 的 Issue 或 PR 评论中。
- **分歧：** 如果 AI 模型强调了分歧或冲突，必须由人类或授权代理进行评估。如果认为合理，应通过 GitHub PR 或 Issue 中的标准共识流程予以解决。
- **后续工作：** 如果 AI 建议开展额外工作，必须创建一个明确的 GitHub Issue 以便跟踪。
- **禁止直接操作：** 在没有人工格式化和以 GitHub 为中心的跟踪前提下，外部 AI 的输出不能直接导入到运行时、路线图或治理契约中。

## 审查包格式

为确保外部模型被赋予适当的边界和上下文，所有审查请求都必须使用下面标准化的“审查包”（Review Packet）格式。该包裹可向外部共享，而无需授予权限。

### 审查包标准模板

```markdown
### 1. 语境
[提供此次审查的高级别目标。例如：“审查此拉取请求的文档一致性以及与 HUB_Optimus 治理原则的契合度。”]

### 2. 文件及范围
[列出待审查的具体文件、代码片段或文档部分。]
- 文件 1: `path/to/file.md`
- 文件 2: `path/to/code.py`

### 3. 问题
[说明 AI 应该关注的重点。请务必明确，以防出现幻觉或范围蔓延。]
- 文档是否明确符合 Layer 0 Kernel 原则？
- 提议的场景中是否存在任何逻辑不一致之处？
- 代码是否遵守了所需的安全检查？

### 4. 约束条件
[提供给 AI 模型的边界限制。]
- 您仅担任咨询角色。您没有批准或合并这些更改的权限。
- 请勿提议大规模的架构重写。
- 请严格关注范围内提供的文件。
- 坚持“诚信优先”的视角。

### 5. 预期输出
[定义您期望 AI 返回的格式。]
- 一份包含具体发现的列表。
- 对于每个发现，提供文件名及建议更改的内容。
- 基于系统评估而非个人偏好的简短理由。
```
"""
}

for lang, content in files.items():
    dir_path = f"docs/{lang}/governance"
    if os.path.exists(dir_path):
        with open(os.path.join(dir_path, "EXTERNAL_AI_REVIEW_PROTOCOL.md"), "w", encoding='utf-8') as f:
            f.write(content)
            
print("Translated files created successfully.")
