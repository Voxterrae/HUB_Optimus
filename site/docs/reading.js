(() => {
  "use strict";
  const copy = {
    es: ["Ir al documento", "Conoce y explora", "Probar Operator", "Idioma de navegación", "Descargar el Markdown original", "En esta página", "Las explicaciones ayudan a leer; los documentos originales mantienen su autoridad y su estado. La interfaz no certifica traducción ni producción.", "Texto en su idioma fuente", "Traducción no disponible: se muestra el texto original", "Traducciones y paridad sujetas a su estado documentado"],
    en: ["Skip to the document", "Meet and explore", "Try Operator", "Navigation language", "Download the original Markdown", "On this page", "Explanations help readers; original documents retain their authority and status. The interface certifies neither translation nor production readiness.", "Text in its source language", "Translation unavailable: showing the original text", "Translations and parity retain their documented status"],
    de: ["Zum Dokument", "Kennenlernen und erkunden", "Operator testen", "Sprache der Navigation", "Original-Markdown herunterladen", "Auf dieser Seite", "Erläuterungen helfen beim Lesen; Originaldokumente behalten ihre Geltung und ihren Status. Die Oberfläche bestätigt weder Übersetzung noch Produktionsreife.", "Text in seiner Quellsprache", "Übersetzung fehlt: Originaltext wird angezeigt", "Übersetzungen und Gleichwertigkeit behalten ihren dokumentierten Status"],
    ca: ["Anar al document", "Coneix i explora", "Provar Operator", "Idioma de navegació", "Descarregar el Markdown original", "En aquesta pàgina", "Les explicacions ajuden a llegir; els originals conserven l'autoritat i l'estat. La interfície no certifica traducció ni producció.", "Text en l'idioma de la font", "Traducció no disponible: es mostra l'original", "Les traduccions i la paritat conserven el seu estat documentat"],
    fr: ["Aller au document", "Découvrir et explorer", "Essayer Operator", "Langue de navigation", "Télécharger le Markdown original", "Sur cette page", "Les explications facilitent la lecture ; les originaux conservent leur autorité et leur statut. L'interface ne certifie ni traduction ni mise en production.", "Texte dans sa langue source", "Traduction indisponible : affichage de l'original", "Les traductions et la parité conservent leur statut documenté"],
    ru: ["К документу", "Узнать и изучить", "Открыть Operator", "Язык навигации", "Скачать исходный Markdown", "На этой странице", "Пояснения помогают читать; исходные документы сохраняют силу и статус. Интерфейс не подтверждает перевод или готовность к эксплуатации.", "Текст на исходном языке", "Перевод недоступен: показан оригинал", "Переводы и эквивалентность сохраняют документированный статус"],
    he: ["מעבר למסמך", "היכרות ועיון", "פתיחת Operator", "שפת הניווט", "הורדת Markdown מקורי", "בדף זה", "ההסברים מסייעים לקריאה; מסמכי המקור שומרים על סמכותם ומצבם. הממשק אינו מאשר תרגום או מוכנות לייצור.", "הטקסט בשפת המקור", "אין תרגום זמין: מוצג המקור", "התרגומים וההתאמה שומרים על מעמדם המתועד"],
    "zh-Hans": ["跳至文档", "了解与探索", "试用 Operator", "导航语言", "下载原始 Markdown", "本页内容", "说明便于阅读；原始文档保留其效力和状态。界面不代表翻译认证或生产就绪。", "以原始语言显示文本", "暂无译文：显示原始文本", "翻译与一致性保留其记录状态"]
  };
  const keys = ["skip", "collection", "operator", "language", "download", "contents", "boundary"];
  let requested = "es";
  try {
    const value = new URLSearchParams(window.location.search).get("lang");
    if (Object.prototype.hasOwnProperty.call(copy, value)) requested = value;
  } catch { /* The source and all links remain readable without the enhancement. */ }
  const dictionary = copy[requested];
  document.querySelectorAll("[data-reader-copy]").forEach((node) => {
    const index = keys.indexOf(node.getAttribute("data-reader-copy"));
    if (index >= 0) node.textContent = dictionary[index];
    node.lang = requested;
    node.dir = requested === "he" ? "rtl" : "ltr";
  });
  document.querySelectorAll("[data-reader-controls]").forEach((node) => {
    node.lang = requested;
    node.dir = requested === "he" ? "rtl" : "ltr";
  });
  document.querySelectorAll("[data-reader-language]").forEach((node) => {
    if (node.getAttribute("data-reader-language") === requested) node.setAttribute("aria-current", "true");
  });
  document.querySelectorAll("[data-reader-home], [data-reader-operator], [data-reader-document]").forEach((node) => {
    const url = new URL(node.getAttribute("href"), window.location.href);
    url.searchParams.set("lang", requested);
    node.setAttribute("href", url.href);
  });
  const source = document.body.getAttribute("data-source-language");
  const multi = document.body.getAttribute("data-source-languages");
  const notice = document.getElementById("reader-language-notice");
  if (notice) {
    notice.lang = requested;
    notice.dir = requested === "he" ? "rtl" : "ltr";
    notice.textContent = `${requested === source ? dictionary[7] : dictionary[8]} (${multi || source}). ${dictionary[9]}.`;
  }
  // Content lang/dir and normative text remain those of the original source.
})();
