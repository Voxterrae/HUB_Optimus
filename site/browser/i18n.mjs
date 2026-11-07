/** UI language is a user preference; it never describes the user's identity or ability. */
export const LANGUAGES = Object.freeze([
  {code:'es', name:'Español', locale:'es-ES', wikiHost:'es.wikipedia.org'},
  {code:'ca', name:'Català', locale:'ca-ES', wikiHost:'ca.wikipedia.org'},
  {code:'en', name:'English', locale:'en-GB', wikiHost:'en.wikipedia.org'},
  {code:'de', name:'Deutsch', locale:'de-DE', wikiHost:'de.wikipedia.org'},
  {code:'fr', name:'Français', locale:'fr-FR', wikiHost:'fr.wikipedia.org'},
  {code:'ru', name:'Русский', locale:'ru-RU', wikiHost:'ru.wikipedia.org'},
].map(Object.freeze));

// Columns: key | Spanish | Catalan | English | German | French | Russian.
const rows = `
app.name|Optimus|Optimus|Optimus|Optimus|Optimus|Optimus
app.tagline|Tu punto de partida en la web|El teu punt de partida al web|Your starting point on the web|Dein Startpunkt im Web|Votre point de départ sur le Web|Ваша отправная точка в интернете
nav.home|Inicio|Inici|Home|Start|Accueil|Главная
nav.saved|Guardados|Desats|Saved|Gespeichert|Favoris|Сохранённое
nav.guide|Guía|Guia|Guide|Anleitung|Guide|Руководство
nav.settings|Ajustes|Configuració|Settings|Einstellungen|Réglages|Настройки
action.cancel|Cancelar|Cancel·la|Cancel|Abbrechen|Annuler|Отменить
action.close|Cerrar|Tanca|Close|Schließen|Fermer|Закрыть
action.retry|Reintentar|Torna-ho a provar|Try again|Erneut versuchen|Réessayer|Повторить
action.delete|Eliminar|Elimina|Delete|Löschen|Supprimer|Удалить
action.save|Guardar|Desa|Save|Speichern|Enregistrer|Сохранить
action.open|Abrir|Obre|Open|Öffnen|Ouvrir|Открыть
action.clear|Borrar|Esborra|Clear|Leeren|Effacer|Очистить
action.stop|Detener|Atura|Stop|Stoppen|Arrêter|Остановить
common.on|Activado|Activat|On|Ein|Activé|Включено
common.off|Desactivado|Desactivat|Off|Aus|Désactivé|Выключено
common.optional|Opcional|Opcional|Optional|Optional|Facultatif|Необязательно
home.title|¿Qué quieres explorar?|Què vols explorar?|What would you like to explore?|Was möchtest du entdecken?|Que souhaitez-vous explorer ?|Что вы хотите найти?
home.intro|Busca en Wikipedia o abre tus enlaces guardados.|Cerca a la Viquipèdia o obre els teus enllaços desats.|Search Wikipedia or open your saved links.|Suche in Wikipedia oder öffne deine gespeicherten Links.|Recherchez sur Wikipédia ou ouvrez vos liens enregistrés.|Ищите в Википедии или открывайте сохранённые ссылки.
search.label|Buscar en Wikipedia|Cerca a la Viquipèdia|Search Wikipedia|Wikipedia durchsuchen|Rechercher sur Wikipédia|Поиск в Википедии
search.placeholder|Escribe lo que quieres buscar|Escriu què vols cercar|Type what you want to find|Gib deinen Suchbegriff ein|Saisissez votre recherche|Введите поисковый запрос
search.submit|Buscar|Cerca|Search|Suchen|Rechercher|Найти
search.notice|Al buscar, tu consulta se envía a Wikipedia. No se envía mientras escribes.|En cercar, la consulta s'envia a la Viquipèdia. No s'envia mentre escrius.|Searching sends your query to Wikipedia. Nothing is sent while you type.|Beim Suchen wird deine Anfrage an Wikipedia gesendet. Beim Tippen wird nichts gesendet.|La recherche envoie votre requête à Wikipédia. Rien n'est envoyé pendant la saisie.|При поиске запрос отправляется в Википедию. При вводе ничего не отправляется.
search.loading|Buscando en Wikipedia…|S'està cercant a la Viquipèdia…|Searching Wikipedia…|Wikipedia wird durchsucht…|Recherche sur Wikipédia…|Поиск в Википедии…
search.empty|No hay resultados. Prueba con otras palabras.|No hi ha resultats. Prova altres paraules.|No results. Try different words.|Keine Ergebnisse. Versuche andere Suchbegriffe.|Aucun résultat. Essayez d'autres mots.|Ничего не найдено. Попробуйте другие слова.
search.results|Resultados|Resultats|Results|Ergebnisse|Résultats|Результаты
search.cancelled|Búsqueda cancelada. Puedes volver a buscar.|Cerca cancel·lada. Pots tornar a cercar.|Search cancelled. You can search again.|Suche abgebrochen. Du kannst erneut suchen.|Recherche annulée. Vous pouvez relancer la recherche.|Поиск отменён. Можно повторить запрос.
search.error|No se pudo completar la búsqueda. Revisa tu conexión e inténtalo de nuevo.|No s'ha pogut completar la cerca. Revisa la connexió i torna-ho a provar.|Search could not be completed. Check your connection and try again.|Die Suche konnte nicht abgeschlossen werden. Prüfe deine Verbindung und versuche es erneut.|La recherche n'a pas abouti. Vérifiez votre connexion et réessayez.|Не удалось завершить поиск. Проверьте соединение и повторите попытку.
search.queryTooLong|Usa una consulta de hasta {max} caracteres.|Fes servir una consulta de fins a {max} caràcters.|Use a query of up to {max} characters.|Verwende höchstens {max} Zeichen für die Suche.|Utilisez une requête de {max} caractères au maximum.|Запрос должен содержать не более {max} символов.
search.noQuery|Escribe algo para buscar.|Escriu alguna cosa per cercar.|Enter something to search for.|Gib einen Suchbegriff ein.|Saisissez un terme à rechercher.|Введите поисковый запрос.
search.source|Fuente: Wikipedia|Font: Viquipèdia|Source: Wikipedia|Quelle: Wikipedia|Source : Wikipédia|Источник: Википедия
search.save|Guardar enlace|Desa l'enllaç|Save link|Link speichern|Enregistrer le lien|Сохранить ссылку
search.saved|Enlace guardado|Enllaç desat|Link saved|Link gespeichert|Lien enregistré|Ссылка сохранена
search.resultCount|{count} resultados|{count} resultats|{count} results|{count} Ergebnisse|{count} résultats|Результатов: {count}
saved.title|Tus enlaces guardados|Els teus enllaços desats|Your saved links|Deine gespeicherten Links|Vos liens enregistrés|Ваши сохранённые ссылки
saved.intro|Guarda enlaces para volver a abrirlos. Activa el recuerdo en este dispositivo para conservarlos al cerrar.|Desa enllaços per tornar-los a obrir. Activa el record en aquest dispositiu per conservar-los en tancar.|Save links to open them again. Enable remembering on this device to keep them after closing.|Speichere Links, um sie wieder zu öffnen. Aktiviere das Merken auf diesem Gerät, um sie nach dem Schließen zu behalten.|Enregistrez des liens pour les retrouver. Activez la mémorisation sur cet appareil pour les conserver après fermeture.|Сохраняйте ссылки, чтобы открывать их снова. Включите сохранение на этом устройстве, чтобы они оставались после закрытия.
saved.empty|Aún no has guardado enlaces.|Encara no has desat cap enllaç.|You have no saved links yet.|Du hast noch keine Links gespeichert.|Vous n'avez pas encore de liens enregistrés.|У вас пока нет сохранённых ссылок.
saved.linkTitle|Título del enlace|Títol de l'enllaç|Link title|Linktitel|Titre du lien|Название ссылки
saved.linkUrl|Dirección web (https:// o http://)|Adreça web (https:// o http://)|Web address (https:// or http://)|Webadresse (https:// oder http://)|Adresse Web (https:// ou http://)|Веб-адрес (https:// или http://)
saved.add|Añadir enlace|Afegeix un enllaç|Add link|Link hinzufügen|Ajouter un lien|Добавить ссылку
saved.invalidUrl|Introduce una dirección http:// o https:// válida y sin credenciales.|Introdueix una adreça http:// o https:// vàlida i sense credencials.|Enter a valid http:// or https:// address without credentials.|Gib eine gültige http://- oder https://-Adresse ohne Zugangsdaten ein.|Saisissez une adresse http:// ou https:// valide sans identifiants.|Введите допустимый адрес http:// или https:// без учётных данных.
saved.limit|Puedes guardar hasta {max} enlaces. Elimina uno para añadir otro.|Pots desar fins a {max} enllaços. Elimina'n un per afegir-ne un altre.|You can save up to {max} links. Delete one to add another.|Du kannst bis zu {max} Links speichern. Lösche einen, um einen weiteren hinzuzufügen.|Vous pouvez enregistrer jusqu'à {max} liens. Supprimez-en un pour en ajouter un autre.|Можно сохранить до {max} ссылок. Удалите одну, чтобы добавить новую.
saved.removed|Enlace eliminado|Enllaç eliminat|Link deleted|Link gelöscht|Lien supprimé|Ссылка удалена
guide.title|Cómo usar Optimus|Com fer servir Optimus|Using Optimus|Optimus verwenden|Utiliser Optimus|Как пользоваться Optimus
guide.intro|Este piloto es una página de inicio y búsqueda para tu navegador.|Aquest pilot és una pàgina d'inici i cerca per al teu navegador.|This pilot is a home and search page for your browser.|Dieser Pilot ist eine Start- und Suchseite für deinen Browser.|Ce pilote est une page d'accueil et de recherche pour votre navigateur.|Эта пилотная версия — стартовая страница с поиском для вашего браузера.
guide.search|Escribe una consulta y pulsa Buscar o Intro. Los resultados abren páginas de Wikipedia.|Escriu una consulta i prem Cerca o Retorn. Els resultats obren pàgines de la Viquipèdia.|Type a query and press Search or Enter. Results open Wikipedia pages.|Gib eine Anfrage ein und drücke Suchen oder die Eingabetaste. Ergebnisse öffnen Wikipedia-Seiten.|Saisissez une requête et appuyez sur Rechercher ou Entrée. Les résultats ouvrent des pages Wikipédia.|Введите запрос и нажмите «Найти» или Enter. Результаты открывают страницы Википедии.
guide.voice|La lectura y el dictado son opcionales y dependen del soporte local del navegador y del idioma instalado.|La lectura i el dictat són opcionals i depenen del suport local del navegador i de l'idioma instal·lat.|Reading aloud and dictation are optional and depend on local browser support and the installed language.|Vorlesen und Diktieren sind optional und hängen von der lokalen Browserunterstützung und der installierten Sprache ab.|La lecture à voix haute et la dictée sont facultatives et dépendent du navigateur et de la langue installée localement.|Чтение вслух и диктовка необязательны и зависят от локальной поддержки браузера и установленного языка.
guide.devices|La ayuda sobre dispositivos es informativa. No hay dispositivos conectados ni controles de domótica.|L'ajuda sobre dispositius és informativa. No hi ha dispositius connectats ni controls de domòtica.|Device guidance is informational. No devices are connected and there are no home automation controls.|Gerätehinweise dienen zur Information. Es sind keine Geräte verbunden und keine Smart-Home-Steuerungen vorhanden.|Les informations sur les appareils sont indicatives. Aucun appareil n'est connecté et aucune commande domotique n'est disponible.|Сведения об устройствах носят справочный характер. Устройства не подключены, управление умным домом недоступно.
guide.browser|Usa los controles de tu navegador para pestañas, descargas y navegación privada. Este piloto no incorpora un asistente de IA.|Fes servir els controls del navegador per a pestanyes, baixades i navegació privada. Aquest pilot no incorpora cap assistent d'IA.|Use your browser controls for tabs, downloads and private browsing. This pilot has no AI assistant connection.|Verwende die Browserfunktionen für Tabs, Downloads und privates Surfen. Dieser Pilot ist mit keinem KI-Assistenten verbunden.|Utilisez votre navigateur pour les onglets, les téléchargements et la navigation privée. Ce pilote n'est connecté à aucun assistant IA.|Для вкладок, загрузок и приватного просмотра используйте средства браузера. Эта версия не подключена к ИИ-помощнику.
guide.offline|La búsqueda necesita conexión. Este piloto no garantiza acceso sin conexión.|La cerca necessita connexió. Aquest pilot no garanteix l'accés sense connexió.|Search needs an internet connection. This pilot does not guarantee offline access.|Die Suche benötigt eine Internetverbindung. Dieser Pilot garantiert keinen Offlinezugriff.|La recherche nécessite une connexion Internet. Ce pilote ne garantit pas l'accès hors connexion.|Для поиска нужен интернет. Работа без сети не гарантируется.
settings.title|Ajustes a tu medida|Configuració al teu gust|Make it comfortable|Passende Einstellungen|À votre convenance|Настройте для себя
settings.intro|Elige cómo ver y usar la página. Puedes cambiarlo cuando quieras.|Tria com vols veure i fer servir la pàgina. Ho pots canviar quan vulguis.|Choose how the page looks and works. You can change this at any time.|Wähle, wie die Seite aussieht und funktioniert. Du kannst dies jederzeit ändern.|Choisissez l'apparence et le fonctionnement de la page. Vous pouvez les modifier à tout moment.|Выберите удобный вид и способ работы страницы. Настройки можно изменить в любой момент.
settings.language|Idioma de la interfaz|Idioma de la interfície|Interface language|Sprache der Oberfläche|Langue de l'interface|Язык интерфейса
settings.speechLanguage|Idioma de voz|Idioma de veu|Speech language|Sprache für Sprachfunktionen|Langue de la voix|Язык речи
settings.mode|Densidad de la página|Densitat de la pàgina|Page density|Seitendichte|Densité de la page|Плотность страницы
settings.simple|Sencilla|Senzilla|Simple|Einfach|Simple|Простая
settings.balanced|Equilibrada|Equilibrada|Balanced|Ausgewogen|Équilibrée|Средняя
settings.advanced|Ampliada|Ampliada|Expanded|Erweitert|Étendue|Расширенная
settings.fontSize|Tamaño del texto|Mida del text|Text size|Textgröße|Taille du texte|Размер текста
settings.theme|Tema|Tema|Theme|Design|Thème|Тема
settings.dark|Oscuro|Fosc|Dark|Dunkel|Sombre|Тёмная
settings.light|Claro|Clar|Light|Hell|Clair|Светлая
settings.contrast|Contraste alto|Contrast alt|High contrast|Hoher Kontrast|Contraste élevé|Высокая контрастность
settings.reducedMotion|Reducir movimiento|Redueix el moviment|Reduce motion|Bewegung reduzieren|Réduire les animations|Уменьшить анимацию
settings.remember|Recordar ajustes y enlaces en este dispositivo|Recorda la configuració i els enllaços en aquest dispositiu|Remember settings and links on this device|Einstellungen und Links auf diesem Gerät merken|Mémoriser les réglages et les liens sur cet appareil|Сохранять настройки и ссылки на этом устройстве
settings.clearData|Borrar los datos de Optimus de este dispositivo|Esborra les dades d'Optimus d'aquest dispositiu|Clear Optimus data from this device|Optimus-Daten von diesem Gerät löschen|Effacer les données Optimus de cet appareil|Удалить данные Optimus с этого устройства
settings.dataCleared|Se han borrado los datos guardados por Optimus en este dispositivo.|S'han esborrat les dades desades per Optimus en aquest dispositiu.|Optimus data saved on this device has been cleared.|Die auf diesem Gerät gespeicherten Optimus-Daten wurden gelöscht.|Les données Optimus enregistrées sur cet appareil ont été effacées.|Сохранённые на этом устройстве данные Optimus удалены.
settings.storageError|No se pudo acceder al almacenamiento del dispositivo. Los cambios siguen en esta sesión; los datos anteriores pueden permanecer.|No s'ha pogut accedir a l'emmagatzematge del dispositiu. Els canvis es mantenen en aquesta sessió; les dades anteriors poden romandre.|Device storage could not be accessed. Changes remain in this session; previous data may remain.|Auf den Gerätespeicher konnte nicht zugegriffen werden. Änderungen gelten für diese Sitzung; frühere Daten können bestehen bleiben.|Le stockage de l'appareil est inaccessible. Les modifications restent dans cette session ; les données précédentes peuvent subsister.|Нет доступа к хранилищу устройства. Изменения действуют в этом сеансе; прежние данные могут сохраниться.
settings.savedLimit|Hasta 50 enlaces guardados|Fins a 50 enllaços desats|Up to 50 saved links|Bis zu 50 gespeicherte Links|Jusqu'à 50 liens enregistrés|До 50 сохранённых ссылок
voice.title|Voz opcional|Veu opcional|Optional voice|Optionale Sprachfunktionen|Voix facultative|Речь по желанию
voice.read|Leer la ayuda en voz alta|Llegeix l'ajuda en veu alta|Read help aloud|Hilfe vorlesen|Lire l'aide à voix haute|Прочитать справку вслух
voice.dictate|Dictar una búsqueda|Dicta una cerca|Dictate a search|Suchanfrage diktieren|Dicter une recherche|Продиктовать запрос
voice.rate|Velocidad de lectura|Velocitat de lectura|Reading speed|Vorlesegeschwindigkeit|Vitesse de lecture|Скорость чтения
voice.idle|Voz detenida|Veu aturada|Voice stopped|Sprachfunktion gestoppt|Voix arrêtée|Речь остановлена
voice.speaking|Leyendo la ayuda…|S'està llegint l'ajuda…|Reading help aloud…|Hilfe wird vorgelesen…|Lecture de l'aide…|Чтение справки…
voice.listening|Escuchando. Detén el dictado cuando termines.|S'està escoltant. Atura el dictat quan acabis.|Listening. Stop dictation when you finish.|Aufnahme läuft. Beende das Diktat, wenn du fertig bist.|Écoute en cours. Arrêtez la dictée quand vous avez terminé.|Идёт запись. Остановите диктовку, когда закончите.
voice.unsupported|Este navegador no admite esta función de voz local. Puedes seguir escribiendo y buscando.|Aquest navegador no admet aquesta funció de veu local. Pots continuar escrivint i cercant.|This browser does not support this local voice feature. You can still type and search.|Dieser Browser unterstützt diese lokale Sprachfunktion nicht. Du kannst weiterhin tippen und suchen.|Ce navigateur ne prend pas en charge cette fonction vocale locale. Vous pouvez toujours saisir une recherche.|Этот браузер не поддерживает эту локальную речевую функцию. Вы можете вводить запросы вручную.
voice.unavailable|No hay voz o dictado local disponible para este idioma. Prueba otro idioma o escribe tu búsqueda.|No hi ha veu o dictat local disponible per a aquest idioma. Prova un altre idioma o escriu la cerca.|No local voice or dictation is available for this language. Try another language or type your search.|Für diese Sprache ist keine lokale Stimme oder Diktierfunktion verfügbar. Wähle eine andere Sprache oder tippe deine Suche.|Aucune voix ni dictée locale n'est disponible pour cette langue. Essayez une autre langue ou saisissez votre recherche.|Для этого языка недоступны локальный голос или диктовка. Выберите другой язык или введите запрос вручную.
voice.downloadRequired|El dictado local requiere un idioma instalado. Este piloto no descarga modelos; puedes escribir la búsqueda.|El dictat local requereix un idioma instal·lat. Aquest pilot no baixa models; pots escriure la cerca.|Local dictation needs an installed language. This pilot does not download models; you can type your search.|Lokales Diktieren benötigt eine installierte Sprache. Dieser Pilot lädt keine Modelle herunter; du kannst deine Suche tippen.|La dictée locale nécessite une langue installée. Ce pilote ne télécharge pas de modèles ; vous pouvez saisir votre recherche.|Для локальной диктовки нужен установленный язык. Эта версия не загружает модели; введите запрос вручную.
voice.permissionDenied|No se ha permitido usar el micrófono. Puedes escribir tu búsqueda.|No s'ha permès fer servir el micròfon. Pots escriure la cerca.|Microphone access was denied. You can type your search.|Der Mikrofonzugriff wurde verweigert. Du kannst deine Suche tippen.|L'accès au microphone a été refusé. Vous pouvez saisir votre recherche.|Доступ к микрофону запрещён. Введите запрос вручную.
voice.error|La función de voz se ha detenido por un error. Puedes reintentarlo o escribir.|La funció de veu s'ha aturat per un error. Pots tornar-ho a provar o escriure.|Voice stopped because of an error. You can retry or type.|Die Sprachfunktion wurde wegen eines Fehlers gestoppt. Versuche es erneut oder tippe.|La fonction vocale s'est arrêtée à cause d'une erreur. Vous pouvez réessayer ou saisir du texte.|Речевая функция остановлена из-за ошибки. Повторите попытку или введите текст.
voice.localNotice|Solo se usan voces instaladas que el navegador identifica como locales.|Només es fan servir veus instal·lades que el navegador identifica com a locals.|Only installed voices identified by the browser as local are used.|Es werden nur installierte Stimmen verwendet, die der Browser als lokal kennzeichnet.|Seules les voix installées identifiées comme locales par le navigateur sont utilisées.|Используются только установленные голоса, которые браузер определяет как локальные.
voice.dictationNotice|El dictado es local y dura hasta 30 segundos. El texto se puede editar y nunca se busca automáticamente.|El dictat és local i dura fins a 30 segons. El text es pot editar i mai no se cerca automàticament.|Dictation is local and lasts up to 30 seconds. You can edit the text; it never starts a search automatically.|Das Diktat erfolgt lokal und dauert bis zu 30 Sekunden. Der Text ist bearbeitbar; eine Suche startet nie automatisch.|La dictée est locale et dure au maximum 30 secondes. Le texte est modifiable ; aucune recherche ne démarre automatiquement.|Диктовка выполняется локально и длится до 30 секунд. Текст можно изменить; поиск никогда не запускается автоматически.
voice.transcriptReady|Dictado añadido. Revisa el texto antes de buscar.|Dictat afegit. Revisa el text abans de cercar.|Dictation added. Check the text before searching.|Diktat eingefügt. Prüfe den Text vor der Suche.|Dictée ajoutée. Vérifiez le texte avant de rechercher.|Диктовка добавлена. Проверьте текст перед поиском.
privacy.title|Datos y privacidad|Dades i privadesa|Data and privacy|Daten und Datenschutz|Données et confidentialité|Данные и конфиденциальность
privacy.search|Las consultas se envían a Wikipedia solo al buscar. Optimus no guarda un historial de consultas.|Les consultes s'envien a la Viquipèdia només en cercar. Optimus no desa cap historial de consultes.|Queries are sent to Wikipedia only when you search. Optimus keeps no query history.|Anfragen werden nur beim Suchen an Wikipedia gesendet. Optimus speichert keinen Suchverlauf.|Les requêtes sont envoyées à Wikipédia uniquement lors d'une recherche. Optimus ne conserve pas d'historique des requêtes.|Запросы отправляются в Википедию только при поиске. Optimus не сохраняет историю запросов.
privacy.storage|El recuerdo es opcional y está desactivado al empezar. Solo guarda ajustes y hasta 50 enlaces en este dispositivo; nunca consultas, resultados, audio ni transcripciones.|El record és opcional i està desactivat a l'inici. Només desa la configuració i fins a 50 enllaços en aquest dispositiu; mai consultes, resultats, àudio ni transcripcions.|Remembering is optional and starts off. It saves only settings and up to 50 links on this device; never queries, results, audio or transcripts.|Das Merken ist optional und anfangs deaktiviert. Es speichert nur Einstellungen und bis zu 50 Links auf diesem Gerät; niemals Anfragen, Ergebnisse, Audio oder Transkripte.|La mémorisation est facultative et désactivée au départ. Elle conserve uniquement les réglages et jusqu'à 50 liens sur cet appareil ; jamais les requêtes, résultats, sons ou transcriptions.|Сохранение необязательно и изначально выключено. На устройстве сохраняются только настройки и до 50 ссылок; запросы, результаты, аудио и расшифровки не сохраняются.
privacy.voice|La voz requiere una acción explícita. No hay escucha permanente, alternativa remota ni instalación automática de modelos.|La veu requereix una acció explícita. No hi ha escolta permanent, alternativa remota ni instal·lació automàtica de models.|Voice requires an explicit action. There is no continuous listening, remote fallback or automatic model installation.|Sprachfunktionen erfordern eine ausdrückliche Aktion. Es gibt kein dauerhaftes Zuhören, keinen entfernten Ersatzdienst und keine automatische Modellinstallation.|La voix nécessite une action explicite. Il n'y a ni écoute permanente, ni service distant de secours, ni installation automatique de modèles.|Речевые функции включаются только по вашему действию. Нет постоянного прослушивания, перехода на удалённый сервис или автоматической установки моделей.
privacy.external|Al abrir un enlace, visitas un sitio externo con sus propias condiciones y prácticas de datos.|En obrir un enllaç, visites un lloc extern amb les seves condicions i pràctiques de dades.|Opening a link takes you to an external site with its own terms and data practices.|Ein Link führt zu einer externen Website mit eigenen Bedingungen und Datenschutzpraktiken.|Un lien vous mène vers un site externe qui applique ses propres conditions et pratiques de données.|Ссылка ведёт на внешний сайт с собственными условиями и правилами обработки данных.
privacy.scope|Este piloto no usa analítica, cookies ni cuentas. Los controles y la privacidad del navegador dependen de tu navegador.|Aquest pilot no fa servir analítica, galetes ni comptes. Els controls i la privadesa del navegador depenen del teu navegador.|This pilot uses no analytics, cookies or accounts. Browser controls and browser privacy depend on your browser.|Dieser Pilot verwendet keine Analysewerkzeuge, Cookies oder Konten. Browserfunktionen und Browserdatenschutz hängen von deinem Browser ab.|Ce pilote n'utilise ni analyse d'audience, ni cookies, ni comptes. Les commandes et la confidentialité du navigateur dépendent de votre navigateur.|Эта версия не использует аналитику, файлы cookie или учётные записи. Средства управления и конфиденциальность браузера зависят от вашего браузера.
accessibility.skip|Saltar al contenido|Salta al contingut|Skip to content|Zum Inhalt springen|Aller au contenu|Перейти к содержимому
accessibility.main|Contenido principal|Contingut principal|Main content|Hauptinhalt|Contenu principal|Основное содержимое
accessibility.navigation|Navegación principal|Navegació principal|Main navigation|Hauptnavigation|Navigation principale|Основная навигация
accessibility.newTab|Se abre en otra pestaña|S'obre en una altra pestanya|Opens in a new tab|Öffnet in einem neuen Tab|S'ouvre dans un nouvel onglet|Откроется в новой вкладке
`.trim().split('\n').map(line => line.split('|'));

export const dictionaries = Object.freeze(Object.fromEntries(LANGUAGES.map(({code}, index) => [
  code, Object.freeze(Object.fromEntries(rows.map(([key, ...values]) => [key, values[index]]))),
])));

export function normalizeLanguage(value) {
  const code = typeof value === 'string' ? value.trim().toLowerCase().split(/[-_]/)[0] : '';
  return LANGUAGES.some(language => language.code === code) ? code : 'es';
}

/** Returns text, not markup. Consumers must insert it using textContent. */
export function t(language, key, params = {}) {
  if (typeof key !== 'string') return '';
  const selected = dictionaries[normalizeLanguage(language)];
  const template = Object.hasOwn(selected, key) ? selected[key]
    : Object.hasOwn(dictionaries.es, key) ? dictionaries.es[key] : key;
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (placeholder, name) =>
    params != null && Object.hasOwn(params, name) ? String(params[name]) : placeholder);
}

/** Diagnostic strings; an empty array means every supported locale is complete. */
export function validateDictionaries(candidate = dictionaries) {
  const errors = [];
  const keys = Object.keys(dictionaries.es);
  const placeholders = value => [...value.matchAll(/\{([a-zA-Z0-9_]+)\}/g)].map(x => x[1]).sort().join(',');
  for (const {code} of LANGUAGES) {
    const dictionary = candidate?.[code];
    for (const key of keys) {
      if (!dictionary || !Object.hasOwn(dictionary, key)) { errors.push(`${code}: missing ${key}`); continue; }
      if (typeof dictionary[key] !== 'string' || !dictionary[key].trim()) { errors.push(`${code}: empty ${key}`); continue; }
      if (placeholders(dictionary[key]) !== placeholders(dictionaries.es[key])) errors.push(`${code}: placeholder mismatch ${key}`);
    }
    for (const key of Object.keys(dictionary ?? {})) if (!keys.includes(key)) errors.push(`${code}: extra ${key}`);
  }
  for (const code of Object.keys(candidate ?? {})) if (!LANGUAGES.some(x => x.code === code)) errors.push(`${code}: extra language`);
  return errors;
}
