(() => {
  "use strict";

  const translations = {
    en: {
      title: "Page not found — HUB_Optimus",
      heading: "Page not found",
      copy: "This address is not part of the versioned public site. Return to the portfolio or inspect the repository, which remains the project source of truth.",
      languageAria: "Language",
      routesAria: "Available routes",
      portfolio: "Return to portfolio",
      operator: "Open Operator",
      github: "View GitHub",
      review: "English, Spanish, and German received an AI-assisted terminology and register audit; named qualified human review is still required. Russian, Hebrew, and Simplified Chinese remain machine-assisted drafts."
    },
    es: {
      title: "Página no encontrada — HUB_Optimus",
      heading: "Página no encontrada",
      copy: "Esta dirección no forma parte de la web pública versionada. Vuelve al portfolio o consulta el repositorio, que sigue siendo la fuente de verdad del proyecto.",
      languageAria: "Idioma",
      routesAria: "Rutas disponibles",
      portfolio: "Volver al portfolio",
      operator: "Abrir Operator",
      github: "Ver GitHub",
      review: "El inglés, el español y el alemán han pasado una auditoría terminológica y de registro asistida por IA; todavía requieren una revisión humana cualificada con revisor identificado. El ruso, el hebreo y el chino simplificado siguen siendo borradores asistidos por máquina."
    },
    de: {
      title: "Seite nicht gefunden — HUB_Optimus",
      heading: "Seite nicht gefunden",
      copy: "Diese Adresse gehört nicht zur versionierten öffentlichen Website. Kehren Sie zum Portfolio zurück oder prüfen Sie das Repository, das die maßgebliche Projektquelle bleibt.",
      languageAria: "Sprache",
      routesAria: "Verfügbare Ziele",
      portfolio: "Zum Portfolio",
      operator: "Operator öffnen",
      github: "GitHub öffnen",
      review: "Englisch, Spanisch und Deutsch wurden einer KI-gestützten Terminologie- und Registerprüfung unterzogen; eine qualifizierte menschliche Prüfung durch namentlich benannte Prüfende steht weiterhin aus. Russisch, Hebräisch und vereinfachtes Chinesisch bleiben maschinell unterstützte Entwürfe."
    },
    ru: {
      title: "Страница не найдена — HUB_Optimus",
      heading: "Страница не найдена",
      copy: "Этот адрес не относится к версионируемой публичной поверхности. Вернитесь к портфелю или изучите репозиторий, который остаётся источником истины проекта.",
      languageAria: "Язык",
      routesAria: "Доступные маршруты",
      portfolio: "Вернуться к портфелю",
      operator: "Открыть Operator",
      github: "Открыть GitHub",
      review: "Русская, ивритская и упрощённая китайская версии являются черновиками, созданными с машинной поддержкой. Требуется квалифицированная проверка человеком."
    },
    he: {
      title: "הדף לא נמצא — HUB_Optimus",
      heading: "הדף לא נמצא",
      copy: "כתובת זו אינה חלק מן המשטח הציבורי המנוהל בגרסאות. חזרו לפורטפוליו או בדקו את המאגר, שנשאר מקור האמת של הפרויקט.",
      languageAria: "שפה",
      routesAria: "נתיבים זמינים",
      portfolio: "חזרה לפורטפוליו",
      operator: "פתיחת Operator",
      github: "צפייה ב-GitHub",
      review: "רוסית, עברית וסינית מפושטת הן טיוטות בסיוע מכונה. נדרשת ביקורת אנושית מוסמכת."
    },
    "zh-Hans": {
      title: "找不到页面 — HUB_Optimus",
      heading: "找不到页面",
      copy: "此地址不属于版本化公开界面。请返回项目组合，或检查仍作为项目事实依据来源的仓库。",
      languageAria: "语言",
      routesAria: "可用路径",
      portfolio: "返回项目组合",
      operator: "打开 Operator",
      github: "查看 GitHub",
      review: "俄语、希伯来语和简体中文均为机器辅助草稿，需要合格的人工审核。"
    }
  };

  const supportedLanguages = Object.keys(translations);

  function normalizeLanguage(language) {
    const value = String(language || "").trim();
    if (supportedLanguages.includes(value)) return value;

    const normalized = value.toLowerCase().replace(/_/g, "-");
    if (
      normalized === "zh-hans"
      || normalized.startsWith("zh-hans-")
      || normalized === "zh-cn"
      || normalized.startsWith("zh-cn-")
      || normalized === "zh-sg"
      || normalized.startsWith("zh-sg-")
    ) {
      return "zh-Hans";
    }
    if (normalized === "zh" || normalized.startsWith("zh-")) return "en";

    const baseLanguage = normalized.split("-")[0];
    return supportedLanguages.includes(baseLanguage) ? baseLanguage : "en";
  }

  function chooseInitialLanguage() {
    let saved = "";
    try {
      saved = window.localStorage.getItem("hub_optimus_language") || "";
    } catch {
      saved = "";
    }

    if (supportedLanguages.includes(saved)) return saved;
    return normalizeLanguage(window.navigator.language || "en");
  }

  function applyLanguage(language) {
    const nextLanguage = supportedLanguages.includes(language) ? language : "en";
    const dictionary = translations[nextLanguage];

    document.documentElement.lang = nextLanguage;
    document.documentElement.dir = nextLanguage === "he" ? "rtl" : "ltr";
    document.title = dictionary.title;

    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      if (Object.prototype.hasOwnProperty.call(dictionary, key)) {
        node.textContent = dictionary[key];
      }
    });

    document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
      const key = node.getAttribute("data-i18n-aria");
      if (Object.prototype.hasOwnProperty.call(dictionary, key)) {
        node.setAttribute("aria-label", dictionary[key]);
      }
    });

    document.querySelectorAll("[data-language]").forEach((button) => {
      const selected = button.getAttribute("data-language") === nextLanguage;
      button.setAttribute("aria-pressed", String(selected));
    });

    try {
      window.localStorage.setItem("hub_optimus_language", nextLanguage);
    } catch {
      // Language switching remains functional when storage is unavailable.
    }
  }

  document.querySelectorAll("[data-language]").forEach((button) => {
    button.addEventListener("click", () => applyLanguage(button.getAttribute("data-language")));
  });

  applyLanguage(chooseInitialLanguage());
})();
