(function (root) {
  "use strict";

  const locales = ["es", "en", "de"];
  const nonempty = (value) => typeof value === "string" && value.trim().length > 0;
  const translated = (value) => value && locales.every((locale) => nonempty(value[locale]));
  function safeEmail(value) {
    if (typeof value !== "string" || value.length > 254) return false;
    const parts = value.split("@");
    if (parts.length !== 2 || parts[0].length > 64
      || !/^[A-Za-z0-9_+-]+(?:\.[A-Za-z0-9_+-]+)*$/.test(parts[0])) return false;
    const labels = parts[1].split(".");
    return labels.length >= 2 && /^[A-Za-z]{2,63}$/.test(labels[labels.length - 1])
      && labels.every((label) => /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/.test(label));
  }

  function assessPublication(input) {
    const config = input && typeof input === "object" ? input : {};
    const controller = config.controller?.verified === true && nonempty(config.controller.name);
    const contact = config.contact?.verified === true && safeEmail(config.contact.email);
    const checks = {
      controller,
      contact,
      hosting: config.hosting?.reviewed === true && translated(config.hosting.summary),
      retention: config.retention?.reviewed === true && translated(config.retention.summary),
      review: config.noticeApproved === true
    };
    const missing = Object.keys(checks).filter((key) => !checks[key]);
    return {
      ready: missing.length === 0,
      missing,
      contactHref: controller && contact ? `mailto:${encodeURIComponent(config.contact.email).replace(/%40/g, "@")}` : null
    };
  }

  function resolveLanguage(value) {
    const language = typeof value === "string" ? value.toLowerCase().split("-")[0] : "";
    return locales.includes(language) ? language : "en";
  }

  const messages = {
    es: {
      title: "Privacidad y datos",
      intro: "Conoce qué se guarda en tu dispositivo, qué puedes eliminar y qué información necesita verificación antes de completar el aviso.",
      language: "Idioma", home: "Volver al inicio", operator: "Abrir Operator", skip: "Ir al contenido",
      draft: "Aviso en preparación", draftDetail: "Faltan datos verificados para presentar este aviso como definitivo. La información técnica y los enlaces a controles ya pueden revisarse.",
      ready: "Información revisada para publicación", readyDetail: "Los campos de publicación están completos según la configuración revisada. Este estado no es una certificación de cumplimiento.",
      version: "Versión", reviewed: "Revisión técnica", pendingTitle: "Información pendiente",
      controller: "Identidad del responsable", contact: "Canal privado de privacidad", hosting: "Alojamiento, proveedores y transferencias", retention: "Criterios de conservación", review: "Aprobación del aviso",
      pendingController: "La identidad del responsable está pendiente de verificación.",
      pendingContact: "El canal privado está pendiente de verificación. Esta página no recoge solicitudes ni datos personales.",
      pendingHosting: "Los proveedores activos, posibles transferencias y registros técnicos del alojamiento deben verificarse. La ausencia de analítica en la página no excluye registros del proveedor.",
      pendingRetention: "Los datos locales indicados abajo se conservan hasta su eliminación. Los plazos de otros tratamientos y registros del alojamiento están pendientes de revisión.",
      write: "Contactar por el canal verificado", storage: "Datos en este dispositivo", storageIntro: "Abrir esta página o cambiar su idioma no guarda una preferencia nueva ni modifica los datos de Operator.",
      data: "Datos", purpose: "Finalidad y conservación", controls: "Control disponible",
      languageData: "Idioma elegido", languagePurpose: "El sitio y Operator pueden recordar el idioma que eliges. Permanece en este perfil del navegador hasta eliminarlo desde sus ajustes.",
      draftData: "Borrador guardado", draftPurpose: "Solo se conserva cuando pulsas Guardar. Puede contener el caso completo. Limpiar los campos actuales no elimina ese borrador.",
      learningData: "Candidatos de revisión", learningPurpose: "Los registros creados o importados se guardan en este perfil hasta eliminarlos. La aceptación local no publica ni modifica el proyecto.",
      cacheData: "Archivos para uso sin conexión", cachePurpose: "La superficie pública de Operator puede guardar recursos estáticos. La caché no es un archivo de tus casos; la superficie privada tiene controles distintos.",
      browserControls: "Ajustes de datos del sitio en tu navegador", draftControls: "Abrir controles del borrador", learningControls: "Abrir controles de candidatos",
      controlsHelp: "En Operator, abre la sección avanzada para eliminar el borrador guardado. Para candidatos, selecciona el registro y revisa la eliminación de ese registro o del caso. El navegador permite eliminar los datos completos del sitio; revisa su alcance antes de confirmar.",
      sharing: "Copias y servicios externos", sharingBody: "Copiar, exportar o compartir por WhatsApp puede crear copias fuera de este dispositivo. Borrar el original local no elimina esas copias ni los registros de otros servicios.",
      optional: "Servicios opcionales", optionalBody: "Este centro no incorpora analítica, publicidad, seguimiento ni llamadas a modelos. Una integración futura que requiera consentimiento tendrá su propio control antes de activarse.",
      rights: "Consultas y ejercicio de derechos", rightsBody: "Puedes solicitar información sobre tus datos y, cuando corresponda, acceso, rectificación, supresión, oposición, limitación o portabilidad. La atención requiere revisión humana. Eliminar datos locales y solicitar actuaciones al responsable son acciones diferentes.",
      ai: "Intervención de IA y revisión humana", aiBody: "La superficie pública de Operator organiza información en borradores para revisión humana mediante herramientas locales. Este centro no envía casos a una IA. Una función privada o una integración con un proveedor necesita información específica sobre sus datos, límites y responsables.",
      boundary: "Este aviso se limita al sitio público y sus controles locales. LCDH-OS, las consultas cívicas y los servicios privados necesitan información específica para su propio tratamiento.",
      evidence: "Consultar el proyecto", noForm: "Sin formularios ni recepción automática de solicitudes en esta página."
    },
    en: {
      title: "Privacy and data",
      intro: "See what stays on your device, what you can delete, and what needs verification before the notice can be completed.",
      language: "Language", home: "Back to home", operator: "Open Operator", skip: "Skip to content",
      draft: "Notice in preparation", draftDetail: "Verified information is still missing before this notice can be presented as final. Technical information and links to existing controls are available for review.",
      ready: "Information reviewed for publication", readyDetail: "Publication fields are complete according to the reviewed configuration. This status is not a compliance certification.",
      version: "Version", reviewed: "Technical review", pendingTitle: "Information still to verify",
      controller: "Controller identity", contact: "Private privacy contact", hosting: "Hosting, providers and transfers", retention: "Retention criteria", review: "Notice approval",
      pendingController: "The controller identity is awaiting verification.",
      pendingContact: "The private contact channel is awaiting verification. This page collects no requests or personal data.",
      pendingHosting: "Active providers, potential transfers and hosting logs require verification. The absence of page analytics does not exclude provider logs.",
      pendingRetention: "The local data listed below remains until deleted. Retention for other processing and hosting logs is awaiting review.",
      write: "Use the verified contact channel", storage: "Data on this device", storageIntro: "Opening this page or changing its language saves no new preference and does not modify Operator data.",
      data: "Data", purpose: "Purpose and retention", controls: "Available control",
      languageData: "Chosen language", languagePurpose: "The site and Operator may remember the language you choose. It remains in this browser profile until removed through browser settings.",
      draftData: "Saved draft", draftPurpose: "Stored only when you select Save. It may contain the complete case. Clearing current fields does not delete the saved draft.",
      learningData: "Candidate review records", learningPurpose: "Created or imported records remain in this profile until deleted. Local acceptance neither publishes nor changes the project.",
      cacheData: "Offline files", cachePurpose: "The public Operator may cache static resources. This cache is not an archive of your cases; the private surface has different controls.",
      browserControls: "Your browser's site data settings", draftControls: "Open saved-draft controls", learningControls: "Open candidate controls",
      controlsHelp: "In Operator, open the advanced section to delete the saved draft. For candidates, select a record and review deletion of that record or its case. Your browser can remove all data for a site; check the scope before confirming.",
      sharing: "Copies and external services", sharingBody: "Copying, exporting or sharing through WhatsApp can create copies outside this device. Deleting the local original does not delete those copies or other services' records.",
      optional: "Optional services", optionalBody: "This centre adds no analytics, advertising, tracking or model calls. Any future integration requiring consent needs its own control before activation.",
      rights: "Questions and data rights", rightsBody: "You can request information about your data and, where applicable, access, correction, erasure, objection, restriction or portability. Requests need human review. Local deletion and requests to the controller are different actions.",
      ai: "AI involvement and human review", aiBody: "The public Operator organises information into drafts for human review using local tools. This centre sends no cases to AI. A private function or provider integration needs specific information about its data, limitations and responsible parties.",
      boundary: "This notice covers the public site and its local controls only. LCDH-OS, civic consultations and private services need information specific to their own processing.",
      evidence: "Inspect the project", noForm: "No forms or automatic request intake on this page."
    },
    de: {
      title: "Datenschutz und Daten",
      intro: "Erfahre, welche Daten auf deinem Gerät bleiben, was du löschen kannst und welche Angaben vor Abschluss des Hinweises geprüft werden müssen.",
      language: "Sprache", home: "Zur Startseite", operator: "Operator öffnen", skip: "Zum Inhalt",
      draft: "Datenschutzhinweis in Vorbereitung", draftDetail: "Für einen endgültigen Hinweis fehlen noch verifizierte Angaben. Technische Informationen und Links zu bestehenden Funktionen stehen zur Prüfung bereit.",
      ready: "Angaben zur Veröffentlichung geprüft", readyDetail: "Laut geprüfter Konfiguration sind die Veröffentlichungsangaben vollständig. Dieser Status ist keine Konformitätszertifizierung.",
      version: "Version", reviewed: "Technische Prüfung", pendingTitle: "Noch zu prüfende Angaben",
      controller: "Identität des Verantwortlichen", contact: "Privater Datenschutzkontakt", hosting: "Hosting, Anbieter und Übermittlungen", retention: "Aufbewahrungskriterien", review: "Freigabe des Hinweises",
      pendingController: "Die Identität des Verantwortlichen muss noch verifiziert werden.",
      pendingContact: "Der private Kontaktweg muss noch verifiziert werden. Diese Seite erfasst weder Anfragen noch personenbezogene Daten.",
      pendingHosting: "Aktive Anbieter, mögliche Übermittlungen und Hosting-Protokolle müssen geprüft werden. Fehlende Seitenanalyse schließt Anbieterprotokolle nicht aus.",
      pendingRetention: "Die unten genannten lokalen Daten bleiben bis zur Löschung erhalten. Fristen für andere Verarbeitungen und Hosting-Protokolle müssen noch geprüft werden.",
      write: "Verifizierten Kontaktweg nutzen", storage: "Daten auf diesem Gerät", storageIntro: "Das Öffnen dieser Seite oder ein Sprachwechsel speichert keine neue Einstellung und verändert keine Operator-Daten.",
      data: "Daten", purpose: "Zweck und Aufbewahrung", controls: "Verfügbare Funktion",
      languageData: "Gewählte Sprache", languagePurpose: "Website und Operator können die gewählte Sprache speichern. Sie bleibt in diesem Browserprofil, bis sie über die Browsereinstellungen entfernt wird.",
      draftData: "Gespeicherter Entwurf", draftPurpose: "Wird nur nach Auswahl von Speichern abgelegt und kann den vollständigen Fall enthalten. Das Leeren aktueller Felder löscht diesen Entwurf nicht.",
      learningData: "Prüfkandidaten", learningPurpose: "Erstellte oder importierte Einträge bleiben bis zur Löschung in diesem Profil. Lokale Annahme veröffentlicht nichts und ändert das Projekt nicht.",
      cacheData: "Dateien für die Offline-Nutzung", cachePurpose: "Der öffentliche Operator kann statische Ressourcen zwischenspeichern. Dieser Cache ist kein Fallarchiv; für die private Oberfläche gelten andere Kontrollen.",
      browserControls: "Website-Dateneinstellungen deines Browsers", draftControls: "Entwurfsfunktionen öffnen", learningControls: "Kandidatenfunktionen öffnen",
      controlsHelp: "Öffne im Operator den erweiterten Bereich, um den gespeicherten Entwurf zu löschen. Wähle bei Kandidaten einen Eintrag aus und prüfe die Löschung dieses Eintrags oder seines Falls. Der Browser kann alle Website-Daten entfernen; prüfe den Umfang vor der Bestätigung.",
      sharing: "Kopien und externe Dienste", sharingBody: "Kopieren, Exportieren oder Teilen über WhatsApp kann Kopien außerhalb dieses Geräts erzeugen. Die lokale Löschung entfernt weder diese Kopien noch Aufzeichnungen anderer Dienste.",
      optional: "Optionale Dienste", optionalBody: "Dieses Zentrum fügt keine Analyse, Werbung, Nachverfolgung oder Modellaufrufe hinzu. Eine künftige Integration mit Einwilligungspflicht braucht vor ihrer Aktivierung eine eigene Steuerung.",
      rights: "Fragen und Betroffenenrechte", rightsBody: "Du kannst Informationen zu deinen Daten sowie gegebenenfalls Auskunft, Berichtigung, Löschung, Widerspruch, Einschränkung oder Übertragbarkeit verlangen. Anfragen werden von Menschen geprüft. Lokale Löschung und Anträge an den Verantwortlichen sind unterschiedliche Vorgänge.",
      ai: "KI-Einsatz und menschliche Prüfung", aiBody: "Der öffentliche Operator ordnet Informationen mit lokalen Werkzeugen zu Entwürfen für eine menschliche Prüfung. Dieses Zentrum sendet keine Fälle an eine KI. Private Funktionen oder Anbieterintegrationen brauchen eigene Angaben zu Daten, Grenzen und Verantwortlichen.",
      boundary: "Dieser Hinweis umfasst nur die öffentliche Website und ihre lokalen Funktionen. LCDH-OS, Bürgerbefragungen und private Dienste benötigen eigene Angaben zur jeweiligen Verarbeitung.",
      evidence: "Projekt ansehen", noForm: "Keine Formulare oder automatische Annahme von Anfragen auf dieser Seite."
    }
  };

  const api = Object.freeze({ assessPublication, resolveLanguage });
  root.HUB_OPTIMUS_PRIVACY = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (!root.document?.querySelector("#privacy-centre")) return;

  const config = root.HUB_OPTIMUS_PRIVACY_CONFIG || {};
  const status = assessPublication(config);
  const select = document.querySelector("#privacy-language");

  function render(language) {
    const locale = resolveLanguage(language);
    const text = messages[locale];
    document.documentElement.lang = locale;
    document.title = `${text.title} · HUB_Optimus`;
    select.value = locale;
    document.querySelectorAll("[data-privacy-key]").forEach((element) => {
      const key = element.dataset.privacyKey;
      if (text[key]) element.textContent = text[key];
    });
    document.querySelector("#notice-status").textContent = text[status.ready ? "ready" : "draft"];
    document.querySelector("#notice-status-detail").textContent = text[status.ready ? "readyDetail" : "draftDetail"];
    const pending = document.querySelector("#pending-fields");
    pending.replaceChildren();
    status.missing.forEach((key) => {
      const item = document.createElement("li");
      item.textContent = text[key];
      pending.append(item);
    });
    document.querySelector("#pending-section").hidden = status.ready;
    document.querySelector("#controller-value").textContent = status.missing.includes("controller") ? text.pendingController : config.controller.name;
    document.querySelector("#hosting-value").textContent = status.missing.includes("hosting") ? text.pendingHosting : config.hosting.summary[locale];
    document.querySelector("#retention-value").textContent = status.missing.includes("retention") ? text.pendingRetention : config.retention.summary[locale];
    const contact = document.querySelector("#privacy-contact");
    contact.hidden = !status.contactHref;
    contact.removeAttribute("href");
    if (status.contactHref) contact.setAttribute("href", status.contactHref);
    document.querySelector("#contact-pending").hidden = Boolean(status.contactHref);
    document.querySelector("#notice-version").textContent = typeof config.version === "string" ? config.version : "—";
    document.querySelector("#technical-review-date").textContent = typeof config.technicalReviewDate === "string" ? config.technicalReviewDate : "—";
  }

  select.addEventListener("change", () => render(select.value));
  render(new URLSearchParams(root.location.search).get("lang") || root.navigator.language);
})(globalThis);
