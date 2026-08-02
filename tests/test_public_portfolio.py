import hashlib
import json
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
INDEX = SITE / "index.html"
STYLES = SITE / "styles.css"
APP = SITE / "app.js"
DOCUMENT_ROUTES = SITE / "i18n" / "document-routes.v1.js"
GLOBE = SITE / "globe.js"
NOT_FOUND = SITE / "404.html"
NOT_FOUND_APP = SITE / "404.js"
LOCALE_METADATA = SITE / "i18n" / "locale-metadata.v1.json"
TERMBASE = SITE / "i18n" / "termbase.v1.json"
I18N_README = SITE / "i18n" / "README.md"
I18N_MATURITY = ROOT / "docs" / "i18n" / "maturity.v1.json"
GEOJSON = SITE / "assets" / "geo" / "land-110m.geojson"
GEOJSON_CHECKSUM = SITE / "assets" / "geo" / "land-110m.geojson.sha256"
GEO_ATTRIBUTION = SITE / "assets" / "geo" / "README.md"
PUBLIC_LOCALES = {"en", "es", "de", "ru", "he", "zh-Hans"}


class PublicPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicate_ids = set()
        self.local_references = []
        self.i18n_keys = set()
        self.portfolio_statuses = {}
        self.future_statuses = []
        self.text_parts = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        element_id = attrs.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)

        for attribute in ("data-i18n", "data-i18n-aria", "data-i18n-alt"):
            if attrs.get(attribute):
                self.i18n_keys.add(attrs[attribute])

        component = attrs.get("data-portfolio-component")
        if component:
            self.portfolio_statuses[component] = attrs.get("data-status")

        if tag == "a" and attrs.get("data-status"):
            self.future_statuses.append(attrs["data-status"])

        reference = None
        if tag in {"a", "link"}:
            reference = attrs.get("href")
        elif tag in {"img", "script"}:
            reference = attrs.get("src")
        if reference:
            self.local_references.append(reference)

    def handle_data(self, data):
        value = " ".join(data.split())
        if value:
            self.text_parts.append(value)

    @property
    def visible_text(self):
        return " ".join(self.text_parts)


class DocumentRouteParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = {}
        self.duplicates = set()
        self._active_route = None
        self._in_badge = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a" and attrs.get("data-document-route"):
            route_id = attrs["data-document-route"]
            if route_id in self.links:
                self.duplicates.add(route_id)
            self.links[route_id] = {"attributes": attrs, "badge": "", "content": ""}
            self._active_route = route_id
        elif (
            tag == "small"
            and self._active_route
            and "document-language-badge" in attrs.get("class", "").split()
        ):
            self._in_badge = True

    def handle_data(self, data):
        if self._active_route:
            self.links[self._active_route]["content"] += data
            if self._in_badge:
                self.links[self._active_route]["badge"] += data

    def handle_endtag(self, tag):
        if tag == "small":
            self._in_badge = False
        elif tag == "a":
            self._active_route = None
            self._in_badge = False


def parse_public_page():
    parser = PublicPageParser()
    parser.feed(INDEX.read_text(encoding="utf-8"))
    return parser


def parse_document_route_markup():
    parser = DocumentRouteParser()
    parser.feed(INDEX.read_text(encoding="utf-8"))
    return parser


def resolve_document_routes():
    node = shutil.which("node")
    assert node, "Node.js is required to validate document route resolution"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const context = {};
vm.runInNewContext(fs.readFileSync(process.env.ROUTE_SCRIPT, "utf8"), context);
const api = context.HUB_OPTIMUS_DOCUMENT_ROUTES;
const locales = ["en", "es", "de", "ru", "he", "zh-Hans"];
const resolved = {};
for (const routeId of api.routeIds) {
  resolved[routeId] = {};
  for (const locale of locales) resolved[routeId][locale] = api.resolve(routeId, locale);
}
process.stdout.write(JSON.stringify({
  evidenceSha: api.evidenceSha,
  routeIds: api.routeIds,
  unknown: api.resolve("missing.route", "en"),
  resolved
}));
"""
    result = subprocess.run(
        [node, "-e", harness],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "ROUTE_SCRIPT": str(DOCUMENT_ROUTES)},
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def extract_translation_dictionaries(source):
    blocks = {}
    pattern = re.compile(
        r'^    (?:"(?P<quoted>zh-Hans)"|(?P<plain>en|es|de|ru|he)): '
        r"\{\n(?P<body>.*?)(?=^    \}(?:,)?$)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(source):
        locale = match.group("quoted") or match.group("plain")
        entries = re.findall(
            r'^      ([A-Za-z][A-Za-z0-9]*): "((?:\\.|[^"\\])*)",?$',
            match.group("body"),
            re.MULTILINE,
        )
        blocks[locale] = dict(entries)
    return blocks


def run_locale_dom_probe(script, *, saved="", browser="en-US", click="", key):
    node = shutil.which("node")
    assert node, "Node.js is required to validate locale DOM behavior"
    harness = r"""
const fs = require("fs");
const vm = require("vm");

class Element {
  constructor(attributes = {}) {
    this.attributes = {...attributes};
    this.textContent = "";
    this.listeners = {};
    this.classList = {
      add() {},
      remove() {},
      toggle() {}
    };
  }
  getAttribute(name) { return this.attributes[name] || null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

const localeCodes = ["es", "en", "de", "ru", "he", "zh-Hans"];
const buttons = localeCodes.map((code) => new Element({"data-language": code}));
const textNode = new Element({"data-i18n": process.env.PROBE_KEY});
const ariaNode = new Element({"data-i18n-aria": "languageAria"});
const altNode = new Element({"data-i18n-alt": "globeFallbackAlt"});
const storage = {};
if (process.env.SAVED_LANGUAGE) storage.hub_optimus_language = process.env.SAVED_LANGUAGE;

const document = {
  body: new Element(),
  documentElement: {lang: "en", dir: "ltr"},
  title: "",
  querySelector() { return null; },
  querySelectorAll(selector) {
    if (selector === "[data-language]") return buttons;
    if (selector === "[data-i18n]") return [textNode];
    if (selector === "[data-i18n-aria]") return [ariaNode];
    if (selector === "[data-i18n-alt]") return [altNode];
    return [];
  },
  getElementById() { return null; }
};
const window = {
  localStorage: {
    getItem(key) { return storage[key] || null; },
    setItem(key, value) { storage[key] = String(value); }
  },
  navigator: {language: process.env.BROWSER_LANGUAGE}
};
const context = {document, window};
vm.runInNewContext(fs.readFileSync(process.env.SCRIPT_PATH, "utf8"), context);

function snapshot() {
  return {
    lang: document.documentElement.lang,
    dir: document.documentElement.dir,
    title: document.title,
    text: textNode.textContent,
    aria: ariaNode.attributes["aria-label"] || "",
    selected: buttons
      .filter((button) => button.attributes["aria-pressed"] === "true")
      .map((button) => button.attributes["data-language"]),
    saved: storage.hub_optimus_language || ""
  };
}

const initial = snapshot();
const clicked = buttons.find(
  (button) => button.attributes["data-language"] === process.env.CLICK_LANGUAGE
);
if (clicked && clicked.listeners.click) clicked.listeners.click();
process.stdout.write(JSON.stringify({initial, after: snapshot()}));
"""
    environment = {
        **os.environ,
        "SCRIPT_PATH": str(script),
        "SAVED_LANGUAGE": saved,
        "BROWSER_LANGUAGE": browser,
        "CLICK_LANGUAGE": click,
        "PROBE_KEY": key,
    }
    result = subprocess.run(
        [node, "-e", harness],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def run_operator_route_dom_probe(*, query="", saved="", browser="en-US", click=""):
    node = shutil.which("node")
    assert node, "Node.js is required to validate locale route continuity"
    harness = r"""
const fs = require("fs");
const vm = require("vm");

class Element {
  constructor(attributes = {}) {
    this.attributes = {...attributes};
    this.listeners = {};
    this.classList = {add() {}, remove() {}, toggle() {}};
  }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

const localeCodes = ["es", "en", "de", "ru", "he", "zh-Hans"];
const buttons = localeCodes.map((code) => new Element({"data-language": code}));
const operatorLinks = [new Element({"data-operator-route": "", href: "./operator/?lang=en#product_intake"})];
const storage = {};
if (process.env.SAVED_LANGUAGE) storage.hub_optimus_language = process.env.SAVED_LANGUAGE;
const location = {
  href: `https://huboptimus.dev/${process.env.QUERY || ""}`,
  search: process.env.QUERY || ""
};
let replacedPath = "";
const window = {
  location,
  history: {replaceState(_state, _title, path) { replacedPath = String(path); }},
  localStorage: {
    getItem(key) { return storage[key] || null; },
    setItem(key, value) { storage[key] = String(value); }
  },
  navigator: {language: process.env.BROWSER_LANGUAGE}
};
const document = {
  body: new Element(),
  documentElement: {lang: "en", dir: "ltr"},
  title: "",
  querySelector() { return null; },
  querySelectorAll(selector) {
    if (selector === "[data-language]") return buttons;
    if (selector === "[data-operator-route]") return operatorLinks;
    return [];
  },
  getElementById() { return null; }
};
const context = {document, window, URL, URLSearchParams};
vm.runInNewContext(fs.readFileSync(process.env.APP_SCRIPT, "utf8"), context);

function snapshot() {
  return {
    lang: document.documentElement.lang,
    href: operatorLinks[0].attributes.href,
    hreflang: operatorLinks[0].attributes.hreflang,
    replacedPath,
    saved: storage.hub_optimus_language
  };
}
const initial = snapshot();
const clicked = buttons.find((button) => button.attributes["data-language"] === process.env.CLICK_LANGUAGE);
if (clicked?.listeners.click) clicked.listeners.click();
process.stdout.write(JSON.stringify({initial, after: snapshot()}));
"""
    result = subprocess.run(
        [node, "-e", harness],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "APP_SCRIPT": str(APP),
            "QUERY": query,
            "SAVED_LANGUAGE": saved,
            "BROWSER_LANGUAGE": browser,
            "CLICK_LANGUAGE": click,
        },
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def run_not_found_route_dom_probe(*, query="", saved="", browser="en-US", click=""):
    node = shutil.which("node")
    assert node, "Node.js is required to validate 404 locale continuity"
    harness = r"""
const fs = require("fs");
const vm = require("vm");

class Element {
  constructor(attributes = {}) {
    this.attributes = {...attributes};
    this.textContent = "";
    this.listeners = {};
  }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

const localeCodes = ["es", "en", "de", "ru", "he", "zh-Hans"];
const buttons = localeCodes.map((code) => new Element({"data-language": code}));
const heading = new Element({"data-i18n": "heading"});
const ariaNode = new Element({"data-i18n-aria": "languageAria"});
const portfolio = new Element({href: "/?lang=en", hreflang: "en"});
const operator = new Element({href: "/operator/?lang=en#product_intake", hreflang: "en"});
const storage = {};
if (process.env.SAVED_LANGUAGE) storage.hub_optimus_language = process.env.SAVED_LANGUAGE;
const location = new URL(`https://huboptimus.dev/404.html${process.env.QUERY || ""}`);
let replacedPath = "";
const window = {
  location,
  history: {replaceState(_state, _title, path) { replacedPath = String(path); }},
  localStorage: {
    getItem(key) { return storage[key] || null; },
    setItem(key, value) { storage[key] = String(value); }
  },
  navigator: {language: process.env.BROWSER_LANGUAGE}
};
const document = {
  documentElement: {lang: "en", dir: "ltr"},
  title: "",
  querySelectorAll(selector) {
    if (selector === "[data-language]") return buttons;
    if (selector === "[data-i18n]") return [heading];
    if (selector === "[data-i18n-aria]") return [ariaNode];
    return [];
  },
  getElementById(id) {
    if (id === "not_found_portfolio_link") return portfolio;
    if (id === "not_found_operator_link") return operator;
    return null;
  }
};
vm.runInNewContext(
  fs.readFileSync(process.env.NOT_FOUND_SCRIPT, "utf8"),
  {document, window, URL, URLSearchParams, encodeURIComponent}
);

function snapshot() {
  return {
    lang: document.documentElement.lang,
    dir: document.documentElement.dir,
    heading: heading.textContent,
    portfolioHref: portfolio.attributes.href,
    portfolioHreflang: portfolio.attributes.hreflang,
    operatorHref: operator.attributes.href,
    operatorHreflang: operator.attributes.hreflang,
    replacedPath,
    saved: storage.hub_optimus_language
  };
}
const initial = snapshot();
const clicked = buttons.find((button) => button.attributes["data-language"] === process.env.CLICK_LANGUAGE);
if (clicked?.listeners.click) clicked.listeners.click();
process.stdout.write(JSON.stringify({initial, after: snapshot()}));
"""
    result = subprocess.run(
        [node, "-e", harness],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "NOT_FOUND_SCRIPT": str(NOT_FOUND_APP),
            "QUERY": query,
            "SAVED_LANGUAGE": saved,
            "BROWSER_LANGUAGE": browser,
            "CLICK_LANGUAGE": click,
        },
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def run_document_route_dom_probe(*, saved="en", click="", load_route_api=True):
    node = shutil.which("node")
    assert node, "Node.js is required to validate document route DOM behavior"
    harness = r"""
const fs = require("fs");
const vm = require("vm");

class Element {
  constructor(attributes = {}) {
    this.attributes = {...attributes};
    this.textContent = "";
    this.listeners = {};
    this.classList = {add() {}, remove() {}, toggle() {}};
  }
  getAttribute(name) { return this.attributes[name] ?? null; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
}

class RouteLink extends Element {
  constructor(routeId, label) {
    super({
      "data-document-route": routeId,
      href: "about:blank",
      hreflang: "xx",
      "aria-label": "stale synthetic label"
    });
    this.badge = new Element({class: "document-language-badge"});
    this.label = new Element({"data-i18n": `label-${routeId}`});
    this.label.textContent = label;
  }
  querySelector(selector) {
    if (selector === ".document-language-badge") return this.badge;
    if (selector === "[data-i18n]" || selector === "span") return this.label;
    return null;
  }
}

const localeCodes = ["es", "en", "de", "ru", "he", "zh-Hans"];
const buttons = localeCodes.map((code) => new Element({"data-language": code}));
const links = [
  new RouteLink("core.canonical", "Canonical core"),
  new RouteLink("core.meta-learning", "Meta-learning workflow"),
  new RouteLink("status.policy", "Status policy"),
  new RouteLink("simulator.guide", "Scenario guide"),
  new RouteLink("governance.protocol", "Governance protocol"),
  new RouteLink("operator.intake.rfc", "How URL intake works"),
  new RouteLink("translation.termbase", "Versioned termbase")
];
const storage = {hub_optimus_language: process.env.SAVED_LANGUAGE};
const document = {
  body: new Element(),
  documentElement: {lang: "en", dir: "ltr"},
  title: "",
  querySelector() { return null; },
  querySelectorAll(selector) {
    if (selector === "[data-language]") return buttons;
    if (selector === "[data-document-route]") return links;
    return [];
  },
  getElementById() { return null; }
};
const window = {
  localStorage: {
    getItem(key) { return storage[key] || null; },
    setItem(key, value) { storage[key] = String(value); }
  },
  navigator: {language: "en-US"}
};
const context = {document, window};
if (process.env.LOAD_ROUTE_API === "1") {
  vm.runInNewContext(fs.readFileSync(process.env.ROUTE_SCRIPT, "utf8"), context);
}
vm.runInNewContext(fs.readFileSync(process.env.APP_SCRIPT, "utf8"), context);

function snapshot() {
  return Object.fromEntries(links.map((link) => [
    link.attributes["data-document-route"],
    {
      href: link.attributes.href,
      hreflang: link.attributes.hreflang ?? null,
      badge: link.badge.textContent,
      aria: link.attributes["aria-label"] ?? null,
      state: link.attributes["data-document-route-state"] ?? null,
      relation: link.attributes["data-document-relation"] ?? null,
      maturity: link.attributes["data-document-maturity"] ?? null
    }
  ]));
}

const initial = snapshot();
const clicked = buttons.find(
  (button) => button.attributes["data-language"] === process.env.CLICK_LANGUAGE
);
if (clicked?.listeners.click) clicked.listeners.click();
process.stdout.write(JSON.stringify({initial, after: snapshot()}));
"""
    result = subprocess.run(
        [node, "-e", harness],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ROUTE_SCRIPT": str(DOCUMENT_ROUTES),
            "APP_SCRIPT": str(APP),
            "SAVED_LANGUAGE": saved,
            "CLICK_LANGUAGE": click,
            "LOAD_ROUTE_API": "1" if load_route_api else "0",
        },
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def iter_positions(value):
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        yield value[0], value[1]
        return
    if isinstance(value, list):
        for child in value:
            yield from iter_positions(child)


def test_public_javascript_syntax_and_translation_key_parity():
    node = shutil.which("node")
    assert node, "Node.js is required to validate the public JavaScript syntax"
    for script in (APP, DOCUMENT_ROUTES, GLOBE, NOT_FOUND_APP):
        result = subprocess.run(
            [node, "--check", str(script)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    source = APP.read_text(encoding="utf-8")
    dictionaries = extract_translation_dictionaries(source)
    assert set(dictionaries) == PUBLIC_LOCALES
    assert len(dictionaries["en"]) == 165
    assert all(set(dictionary) == set(dictionaries["en"]) for dictionary in dictionaries.values())
    assert all(
        value.strip()
        for dictionary in dictionaries.values()
        for value in dictionary.values()
    )

    parser = parse_public_page()
    assert parser.i18n_keys <= set(dictionaries["en"])
    assert {"title", "description", "resumeGlobe"} <= set(dictionaries["en"])

    not_found_dictionaries = extract_translation_dictionaries(
        NOT_FOUND_APP.read_text(encoding="utf-8")
    )
    assert set(not_found_dictionaries) == PUBLIC_LOCALES
    assert all(
        set(dictionary) == set(not_found_dictionaries["en"])
        for dictionary in not_found_dictionaries.values()
    )
    assert all(
        value.strip()
        for dictionary in not_found_dictionaries.values()
        for value in dictionary.values()
    )


def test_locale_selection_persistence_fallback_and_rtl_dom_behavior():
    hebrew_then_russian = run_locale_dom_probe(
        APP,
        saved="he",
        browser="en-US",
        click="ru",
        key="navMethod",
    )
    assert hebrew_then_russian["initial"] == {
        "lang": "he",
        "dir": "rtl",
        "title": "HUB_Optimus — פורטפוליו ציבורי מנוהל בגרסאות",
        "text": "שיטה",
        "aria": "שפה",
        "selected": ["he"],
        "saved": "he",
    }
    assert hebrew_then_russian["after"]["lang"] == "ru"
    assert hebrew_then_russian["after"]["dir"] == "ltr"
    assert hebrew_then_russian["after"]["text"] == "Метод"
    assert hebrew_then_russian["after"]["selected"] == ["ru"]
    assert hebrew_then_russian["after"]["saved"] == "ru"

    unknown_locale = run_locale_dom_probe(
        APP,
        saved="unsupported",
        browser="xx-YY",
        key="navMethod",
    )
    assert unknown_locale["initial"]["lang"] == "en"
    assert unknown_locale["initial"]["dir"] == "ltr"
    assert unknown_locale["initial"]["text"] == "Method"
    assert unknown_locale["initial"]["saved"] == "en"

    simplified_chinese = run_locale_dom_probe(
        APP,
        browser="zh-CN",
        key="navMethod",
    )
    assert simplified_chinese["initial"]["lang"] == "zh-Hans"
    assert simplified_chinese["initial"]["dir"] == "ltr"
    assert simplified_chinese["initial"]["text"] == "方法"

    traditional_chinese_is_not_implied = run_locale_dom_probe(
        APP,
        browser="zh-TW",
        key="navMethod",
    )
    assert traditional_chinese_is_not_implied["initial"]["lang"] == "en"
    assert traditional_chinese_is_not_implied["initial"]["text"] == "Method"

    legacy_hebrew_alias = run_locale_dom_probe(
        APP,
        browser="iw-IL",
        key="navMethod",
    )
    assert legacy_hebrew_alias["initial"]["lang"] == "he"
    assert legacy_hebrew_alias["initial"]["dir"] == "rtl"

    not_found_hebrew = run_locale_dom_probe(
        NOT_FOUND_APP,
        saved="he",
        click="de",
        key="heading",
    )
    assert not_found_hebrew["initial"]["lang"] == "he"
    assert not_found_hebrew["initial"]["dir"] == "rtl"
    assert not_found_hebrew["initial"]["text"] == "הדף לא נמצא"
    assert not_found_hebrew["after"]["lang"] == "de"
    assert not_found_hebrew["after"]["dir"] == "ltr"
    assert not_found_hebrew["after"]["text"] == "Seite nicht gefunden"


def test_landing_locale_query_and_operator_route_remain_continuous():
    query_wins = run_operator_route_dom_probe(
        query="?lang=he",
        saved="de",
        browser="ru-RU",
        click="zh-Hans",
    )
    assert query_wins["initial"] == {
        "lang": "he",
        "href": "./operator/?lang=he#product_intake",
        "hreflang": "he",
        "replacedPath": "/?lang=he",
        "saved": "he",
    }
    assert query_wins["after"] == {
        "lang": "zh-Hans",
        "href": "./operator/?lang=zh-Hans#product_intake",
        "hreflang": "zh-Hans",
        "replacedPath": "/?lang=zh-Hans",
        "saved": "zh-Hans",
    }

    html = INDEX.read_text(encoding="utf-8")
    assert html.count("data-operator-route") == 2
    assert html.count('href="./operator/?lang=en#product_intake"') == 2


def test_not_found_query_aliases_and_routes_preserve_locale_end_to_end():
    query_wins = run_not_found_route_dom_probe(
        query="?lang=he",
        saved="de",
        browser="ru-RU",
        click="zh-Hans",
    )
    assert query_wins["initial"] == {
        "lang": "he",
        "dir": "rtl",
        "heading": "הדף לא נמצא",
        "portfolioHref": "/?lang=he",
        "portfolioHreflang": "he",
        "operatorHref": "/operator/?lang=he#product_intake",
        "operatorHreflang": "he",
        "replacedPath": "/404.html?lang=he",
        "saved": "he",
    }
    assert query_wins["after"]["lang"] == "zh-Hans"
    assert query_wins["after"]["operatorHref"] == "/operator/?lang=zh-Hans#product_intake"
    assert query_wins["after"]["operatorHreflang"] == "zh-Hans"
    assert query_wins["after"]["replacedPath"] == "/404.html?lang=zh-Hans"

    empty_query_still_wins = run_not_found_route_dom_probe(
        query="?lang=",
        saved="de",
        browser="ru-RU",
    )
    assert empty_query_still_wins["initial"]["lang"] == "en"

    legacy_hebrew = run_not_found_route_dom_probe(browser="iw-IL")
    assert legacy_hebrew["initial"]["lang"] == "he"
    assert legacy_hebrew["initial"]["operatorHref"] == "/operator/?lang=he#product_intake"

    simplified_chinese = run_not_found_route_dom_probe(browser="zh-CN")
    assert simplified_chinese["initial"]["lang"] == "zh-Hans"
    traditional_chinese = run_not_found_route_dom_probe(browser="zh-TW")
    assert traditional_chinese["initial"]["lang"] == "en"


def test_locale_controls_statuses_limitations_and_operator_disclosure_are_translated():
    dictionaries = extract_translation_dictionaries(APP.read_text(encoding="utf-8"))
    required_keys = {
        "navMethod",
        "languageAria",
        "pauseGlobe",
        "resumeGlobe",
        "globeAria",
        "statusSimulator",
        "statusIntake",
        "truthNote",
        "operatorCopy",
        "operatorDisclosure",
        "metaLearningGuide",
        "intakeContract",
        "authorityRetrieval",
        "futureTitle",
        "translationReview",
        "documentSource",
        "documentFallback",
        "documentCanonical",
        "documentReviewNeeded",
        "documentRouterUnavailable",
    }
    for locale in ("ru", "he", "zh-Hans"):
        assert required_keys <= set(dictionaries[locale])
        for key in required_keys:
            assert dictionaries[locale][key].strip()
            assert dictionaries[locale][key] != dictionaries["en"][key]

        disclosure = dictionaries[locale]["operatorDisclosure"]
        assert "Operator" in disclosure
        assert "Semantic Engine" in disclosure

    html = INDEX.read_text(encoding="utf-8")
    locale_buttons = re.findall(r'data-language="([^"]+)"', html)
    assert locale_buttons == ["es", "en", "de", "ru", "he", "zh-Hans"]
    assert html.count('type="button" data-language=') == len(PUBLIC_LOCALES)
    assert 'lang="zh-Hans"' in html
    assert 'data-i18n="operatorDisclosure"' in html
    assert 'data-i18n="translationReview"' in html


def test_static_english_fallback_matches_the_runtime_dictionary():
    class EnglishFallbackParser(HTMLParser):
        VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack = []
            self.values = {}

        def handle_starttag(self, tag, attributes):
            attrs = dict(attributes)
            if tag in self.VOID:
                return
            self.stack.append(
                {
                    "tag": tag,
                    "key": attrs.get("data-i18n"),
                    "hidden": attrs.get("aria-hidden") == "true",
                    "parts": [],
                }
            )

        def handle_data(self, data):
            if self.stack and not any(item["hidden"] for item in self.stack):
                self.stack[-1]["parts"].append(data)

        def handle_endtag(self, tag):
            if not self.stack:
                return
            item = self.stack.pop()
            assert item["tag"] == tag
            normalized = " ".join("".join(item["parts"]).split())
            if item["key"]:
                self.values[item["key"]] = normalized
            if self.stack and not item["hidden"]:
                self.stack[-1]["parts"].append(normalized)

    parser = EnglishFallbackParser()
    parser.feed(INDEX.read_text(encoding="utf-8"))
    english = extract_translation_dictionaries(APP.read_text(encoding="utf-8"))["en"]

    assert parser.values
    assert set(parser.values) <= set(english)
    assert parser.values == {key: english[key] for key in parser.values}


def test_public_observability_copy_bounds_client_instrumentation_and_host_logs():
    app = APP.read_text(encoding="utf-8")
    dictionaries = extract_translation_dictionaries(app)
    expected_footer_copy = {
        "en": (
            "No embedded client-side analytics or advertising tracking. "
            "No hidden scoring. Hosting providers may retain operational logs. "
            "GitHub remains authoritative."
        ),
        "es": (
            "Este sitio no integra analítica en el navegador ni seguimiento "
            "publicitario. No hay puntuación oculta. Los proveedores de "
            "alojamiento pueden conservar registros operativos. GitHub sigue "
            "siendo la fuente autoritativa."
        ),
        "de": (
            "Diese Website bindet weder clientseitige Analysedienste noch "
            "Werbetracking ein. Es findet keine verborgene Bewertung statt. "
            "Hosting-Anbieter können Betriebsprotokolle aufbewahren. GitHub "
            "bleibt maßgeblich."
        ),
        "ru": (
            "На сайте нет встроенной клиентской аналитики и рекламного "
            "отслеживания. Скрытое оценивание не применяется. "
            "Хостинг-провайдеры могут сохранять служебные журналы. GitHub "
            "остаётся авторитетным источником."
        ),
        "he": (
            "האתר אינו כולל כלי ניתוח בצד הלקוח או מעקב לצורכי פרסום. אין "
            "ניקוד נסתר. ספקי האירוח עשויים לשמור יומנים תפעוליים. GitHub "
            "נשאר מקור הסמכות."
        ),
        "zh-Hans": (
            "本站未嵌入客户端分析工具或广告跟踪功能，也不进行隐藏评分。"
            "托管服务商可能保留运维日志。GitHub 仍是权威依据。"
        ),
    }
    assert {
        locale: dictionaries[locale]["footerBoundary"]
        for locale in PUBLIC_LOCALES
    } == expected_footer_copy

    index = INDEX.read_text(encoding="utf-8")
    assert expected_footer_copy["en"] in index

    operator = (SITE / "operator" / "index.html").read_text(encoding="utf-8")
    assert (
        "This page embeds no client-side analytics or advertising tracking, "
        "performs no hidden scoring, and loads no third-party JavaScript. "
        "Hosting providers may retain operational logs."
    ) in operator

    unqualified_claims = (
        "No analytics.",
        "Sin analítica.",
        "Keine Analytik.",
        "Без аналитики.",
        "ללא ניתוח התנהגות.",
        "无分析跟踪。",
    )
    canonical_copy = "\n".join((app, index, operator))
    for claim in unqualified_claims:
        assert claim not in canonical_copy


def test_hebrew_uses_document_rtl_and_logical_layout_properties_only_for_hebrew():
    html = INDEX.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    css = STYLES.read_text(encoding="utf-8")
    not_found = NOT_FOUND.read_text(encoding="utf-8")

    assert '<html lang="en" dir="ltr">' in html
    assert 'document.documentElement.dir = nextLanguage === "he" ? "rtl" : "ltr"' in app
    assert '[dir="rtl"] [data-i18n]' in css
    assert "unicode-bidi: isolate" in css
    assert "unicode-bidi: plaintext" not in css
    assert "unicode-bidi: isolate" in not_found
    assert "unicode-bidi: plaintext" not in not_found
    assert "inset-inline-start" in css
    assert "inset-inline-end" in css
    assert "border-inline-start" in css
    assert "border-inline-end" in css
    assert "padding-inline" in css
    assert "text-align: start" in css

    metadata = json.loads(LOCALE_METADATA.read_text(encoding="utf-8"))
    assert metadata["locales"]["he"]["direction"] == "rtl"
    assert all(
        locale["direction"] == "ltr"
        for code, locale in metadata["locales"].items()
        if code != "he"
    )


def test_hebrew_ltr_leading_product_tokens_keep_an_rtl_paragraph_base():
    dictionaries = extract_translation_dictionaries(APP.read_text(encoding="utf-8"))
    hebrew = dictionaries["he"]
    ltr_leading_sentence_keys = {
        "truthNote": "Operator",
        "labsLead": "Labs",
        "boundariesLead": "GitHub",
        "providerCopy": "GitHub",
    }
    for key, product_name in ltr_leading_sentence_keys.items():
        assert hebrew[key].startswith(product_name)
        probe = run_locale_dom_probe(
            APP,
            saved="he",
            key=key,
        )
        assert probe["initial"]["lang"] == "he"
        assert probe["initial"]["dir"] == "rtl"
        assert probe["initial"]["text"] == hebrew[key]

    css = STYLES.read_text(encoding="utf-8")
    assert '[dir="rtl"] [data-i18n]' in css
    assert "unicode-bidi: isolate" in css
    assert "unicode-bidi: plaintext" not in css


def test_translation_review_metadata_and_termbase_are_versioned_and_linked():
    metadata = json.loads(LOCALE_METADATA.read_text(encoding="utf-8"))
    termbase = json.loads(TERMBASE.read_text(encoding="utf-8"))
    readme = I18N_README.read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.split())
    html = INDEX.read_text(encoding="utf-8")

    assert metadata["manifest_version"] == "1.3.2"
    assert metadata["issue"] == 1750
    assert metadata["latest_audit_issue"] == 1834
    assert metadata["canonical_v1_language"] == "es"
    assert metadata["constitutional_translation_status"] == "not ratified"
    assert "complete Operator interface" in metadata["scope"]
    assert "language-neutral" in metadata["scope"]
    operator_localization = metadata["operator_interface_localization"]
    assert operator_localization["primary_flow"] is True
    assert operator_localization["advanced_audit_console"] is True
    assert set(operator_localization["advanced_audit_console_locales"]) == PUBLIC_LOCALES
    assert set(operator_localization["supported_locales"]) == PUBLIC_LOCALES
    assert "human" in operator_localization["review_status"]
    assert metadata["portfolio_translation_key_count"] == 165
    assert set(metadata["locales"]) == PUBLIC_LOCALES
    assert len(metadata["field_status"]) >= 10
    for record in metadata["locales"].values():
        assert "complete Operator interface" in record["scope"]

    for locale in ("ru", "he", "zh-Hans"):
        record = metadata["locales"][locale]
        assert record["translation_method"] == "machine-assisted draft"
        assert record["review_status"] == "qualified human review required"
        assert record["named_reviewer"] is None
        assert all(
            field_status[locale]
            == "machine-assisted draft; qualified human review required"
            for field_status in metadata["field_status"].values()
        )

    audited_status = (
        "AI-assisted terminology and register audit; "
        "named qualified human review required"
    )
    for locale in ("en", "es", "de"):
        record = metadata["locales"][locale]
        assert "AI-assisted terminology and register audit" in record[
            "translation_method"
        ]
        assert record["review_status"] == "named qualified human review required"
        assert record["named_reviewer"] is None
        assert all(
            field_status[locale] == audited_status
            for field_name, field_status in metadata["field_status"].items()
            if field_name != "operator_advanced_audit_console"
        )
        assert (
            metadata["field_status"]["operator_advanced_audit_console"][locale]
            == "AI-assisted draft; named qualified human review required"
        )

    assert all(
        record["named_reviewer"] is None
        for record in metadata["locales"].values()
    )

    assert all(
        set(field_status) == PUBLIC_LOCALES
        for field_status in metadata["field_status"].values()
    )

    metadata_text = LOCALE_METADATA.read_text(encoding="utf-8").lower()
    for unsupported_claim in ("professional", "approved", "native-reviewed"):
        assert unsupported_claim not in metadata_text

    assert termbase["termbase_version"] == "1.1.0"
    assert termbase["latest_audit_issue"] == 1736
    assert termbase["canonical_v1_language"] == "es"
    assert termbase["terms"]
    for term in termbase["terms"]:
        assert PUBLIC_LOCALES <= set(term)
        assert all(term[locale].strip() for locale in PUBLIC_LOCALES)

    assert "Semantic Engine" in termbase["protected_product_names"]
    assert "GitHub Issues" in termbase["protected_product_names"]
    assert {
        record["label"] for record in termbase["protected_interface_labels"]
    } == {"Labs", "Issues"}
    assert "Machine-assisted draft; qualified human review required" in readme
    assert "terminology audit under #1736" in readme
    assert "Advanced is an AI-assisted draft" in readme
    assert "No named reviewer is recorded for any locale" in readme
    assert (
        "do not establish certified or professional human review"
        in normalized_readme
    )
    assert "No constitutional translation is ratified" in readme
    assert "does not execute the Semantic Engine" in readme
    assert "Triage does not verify stated" in readme
    assert './i18n/README.md' in html
    assert './i18n/termbase.v1.json' in html


def test_en_es_de_capability_claims_preserve_maturity_and_clear_register():
    dictionaries = extract_translation_dictionaries(APP.read_text(encoding="utf-8"))
    termbase = json.loads(TERMBASE.read_text(encoding="utf-8"))
    terms = {term["id"]: term for term in termbase["terms"]}

    expected_statuses = {
        "en": {
            "statusActive": "Active methodology",
            "statusSimulator": "Working deterministic prototype",
            "statusSemantic": "Early implementation",
            "statusBrowser": "Browser prototype",
            "statusIntake": "Implementation present · deployment unverified",
            "statusResearch": "Experimental tooling",
            "statusGovernance": "Active · ratified protocol",
        },
        "es": {
            "statusActive": "Metodología activa",
            "statusSimulator": "Prototipo determinista funcional",
            "statusSemantic": "Implementación inicial",
            "statusBrowser": "Prototipo en navegador",
            "statusIntake": "Implementación presente · despliegue sin verificar",
            "statusResearch": "Herramientas experimentales",
            "statusGovernance": "Activo · protocolo ratificado",
        },
        "de": {
            "statusActive": "Aktive Methodik",
            "statusSimulator": "Funktionsfähiger deterministischer Prototyp",
            "statusSemantic": "Frühe Implementierung",
            "statusBrowser": "Browser-Prototyp",
            "statusIntake": "Implementierung vorhanden · Deployment ungeprüft",
            "statusResearch": "Experimentelle Werkzeuge",
            "statusGovernance": "Aktiv · ratifiziertes Protokoll",
        },
    }
    for locale, statuses in expected_statuses.items():
        assert {
            key: dictionaries[locale][key]
            for key in statuses
        } == statuses

    truth_markers = {
        "en": {
            "coreCopy": "English is the parity target.",
            "semanticCopy": "It does not evaluate or score claims.",
            "operatorDisclosure": "does not execute the Semantic Engine",
            "intakeCopy": "Retrieved text is not verified evidence.",
            "truthNote": "Retrieval is not verification.",
            "labsTruth": "currently empty",
            "boundariesLead": "cannot redefine it.",
            "enterpriseCopy": "No enterprise product or public service exists.",
            "postQuantumCopy": "No cryptographic implementation.",
            "translationReview": "named qualified human review is still required",
        },
        "es": {
            "coreCopy": "el inglés es el objetivo de paridad.",
            "semanticCopy": "No evalúa ni puntúa afirmaciones.",
            "operatorDisclosure": "no ejecuta el Semantic Engine",
            "intakeCopy": "El texto recuperado no es evidencia verificada.",
            "truthNote": "Recuperar una fuente no equivale a verificarla.",
            "labsTruth": "actualmente está vacío",
            "boundariesLead": "no redefinirlo.",
            "enterpriseCopy": "No existe ningún producto empresarial ni servicio público.",
            "postQuantumCopy": "Sin implementación criptográfica.",
            "translationReview": "todavía requieren una revisión humana cualificada",
        },
        "de": {
            "coreCopy": "Englisch ist das Paritätsziel.",
            "semanticCopy": "Sie bewertet oder bepunktet keine Behauptungen.",
            "operatorDisclosure": "die Semantic Engine wird dabei nicht ausgeführt",
            "intakeCopy": "Abgerufener Text ist keine verifizierte Evidenz.",
            "truthNote": "Abruf ist keine Verifizierung.",
            "labsTruth": "derzeit leer",
            "boundariesLead": "nicht neu definieren.",
            "enterpriseCopy": "weder ein Unternehmensprodukt noch einen öffentlichen Dienst",
            "postQuantumCopy": "Keine kryptografische Implementierung.",
            "translationReview": "qualifizierte menschliche Prüfung",
        },
    }
    for locale, markers in truth_markers.items():
        for key, marker in markers.items():
            assert marker in dictionaries[locale][key]

    term_to_key = {
        "source_of_truth": "truthSource",
        "implementation_signal_gate": "noBuild",
        "operator_draft_authority": "authorityAdvisory",
        "post_quantum_control_plane": "postQuantumTitle",
    }
    for term_id, key in term_to_key.items():
        for locale in ("en", "es", "de"):
            interface_value = dictionaries[locale][key].rstrip(".").casefold()
            assert interface_value == terms[term_id][locale].casefold()

    provenance_term = terms["triage_does_not_verify_provenance"]
    for locale in ("en", "es", "de"):
        assert (
            provenance_term[locale].casefold()
            in dictionaries[locale]["operatorDisclosure"].casefold()
        )

    rejected_calques = {
        "en": (
            "No build without signal.",
            "English is the parity reference.",
            "Unverified provenance remains unverified.",
            "Versioned / reviewed",
            "Advisory output",
            "Contract-bound draft",
            "Standards-only planning.",
        ),
        "es": (
            "No construir sin señal.",
            "referencia de paridad",
            "La procedencia no verificada sigue sin verificar.",
            "Versionado / revisado",
            "Salida consultiva",
            "Borrador sujeto a contrato",
            "Plano de control poscuántico",
        ),
        "de": (
            "Quelle der Wahrheit",
            "Quelle der Projektwahrheit",
            "Paritätsreferenz",
            "Ungeprüfte Herkunft bleibt ungeprüft.",
            "Versioniert / geprüft",
            "Beratende Ausgabe",
            "Vertragsgebundener Entwurf",
            "Postquanten-Kontrollplan",
        ),
    }
    for locale, rejected in rejected_calques.items():
        localized_text = "\n".join(dictionaries[locale].values())
        for phrase in rejected:
            assert phrase not in localized_text


def test_small_screen_header_preserves_home_and_language_controls():
    css = STYLES.read_text(encoding="utf-8")
    mobile_section = css.split("@media (max-width: 540px)", 1)[1].split(
        "@media (prefers-reduced-motion: reduce)",
        1,
    )[0]
    assert ".site-header" in mobile_section
    assert ".language-switcher button" in mobile_section
    assert ".site-header > .brand" not in mobile_section
    assert "display: none" not in mobile_section
    assert "min-height: 2.75rem" in mobile_section


def test_not_found_page_has_six_locales_and_resolving_routes():
    html = NOT_FOUND.read_text(encoding="utf-8")
    assert '<html lang="en" dir="ltr">' in html
    assert 'src="/404.js"' in html
    assert re.findall(r'data-language="([^"]+)"', html) == [
        "es",
        "en",
        "de",
        "ru",
        "he",
        "zh-Hans",
    ]
    for route in ("/?lang=en", "/operator/?lang=en#product_intake", "https://github.com/Voxterrae/HUB_Optimus"):
        assert f'href="{route}"' in html
    assert 'id="not_found_portfolio_link"' in html
    assert 'id="not_found_operator_link"' in html
    assert html.count('hreflang="en"') >= 2

    assert (SITE / "index.html").is_file()
    assert (SITE / "operator" / "index.html").is_file()


def test_public_identity_uses_approved_repository_brand():
    html = INDEX.read_text(encoding="utf-8")
    css = STYLES.read_text(encoding="utf-8").lower()
    tokens = json.loads(
        (ROOT / "assets" / "brand" / "source" / "brand-tokens.json").read_text(
            encoding="utf-8"
        )
    )

    assert re.search(
        r'<h1 id="hero-title">\s*HUB<span>_</span><wbr>Optimus\s*</h1>',
        html,
    )
    assert "Reality → Evidence → Inference → Narrative → Operational Signal" in html
    assert "./assets/brand/hub-optimus-hero.jpg" in html
    assert "./assets/brand/hub-optimus-logo-lockup.png" in html
    assert (
        SITE / "assets" / "brand" / "hub-optimus-hero.jpg"
    ).read_bytes() == (ROOT / tokens["readme_hero"]).read_bytes()
    assert (
        SITE / "assets" / "brand" / "hub-optimus-logo-lockup.png"
    ).read_bytes() == (
        ROOT / "assets" / "brand" / "logo" / "hub-optimus-logo-lockup.png"
    ).read_bytes()

    expected_css_tokens = {
        "graphite": tokens["graphite"],
        "mediterranean": tokens["deep_mediterranean_blue"],
        "copper": tokens["copper"],
        "off-white": tokens["off_white"],
        "signal-amber": tokens["signal_amber"],
    }
    for css_name, value in expected_css_tokens.items():
        assert f"--{css_name}: {value.lower()};" in css


def test_public_portfolio_matches_repository_maturity():
    parser = parse_public_page()
    assert parser.portfolio_statuses == {
        "core": "active-methodology",
        "simulator": "working-deterministic-prototype",
        "semantic-engine": "early-implementation",
        "operator": "browser-prototype",
        "controlled-url-intake": "implementation-present-deployment-unverified",
        "research": "experimental-tooling",
        "governance-intelligence": "active-ratified-protocol",
        "labs": "official-empty-incubation",
    }
    assert parser.future_statuses == ["rfc-not-implemented"] * 3

    html = INDEX.read_text(encoding="utf-8")
    no_javascript_status_copy = {
        "statusActive": "Active methodology",
        "statusSimulator": "Working deterministic prototype",
        "statusSemantic": "Early implementation",
        "statusBrowser": "Browser prototype",
        "statusIntake": "Implementation present · deployment unverified",
        "statusResearch": "Experimental tooling",
        "statusGovernance": "Active · ratified protocol",
    }
    for key, value in no_javascript_status_copy.items():
        assert f'data-i18n="{key}">{value}</strong>' in html

    evidence_paths = (
        "v1_core/languages/es",
        "SIMULATION_README.md",
        "/semantic_engine",
        "/site/operator",
        "test_hub_api_controlled_url_intake.py",
        "/tools",
        "GOVERNANCE_INTELLIGENCE.md",
        "Voxterrae/HUB-Optimus-labs",
    )
    for path in evidence_paths:
        assert path in html

    text = parser.visible_text
    assert "It does not evaluate or score claims." in text
    assert "GitHub does not confirm a live deployment." in text
    assert "Repository exists · no released artifacts" in text
    assert "No cryptographic implementation." in text
    assert "It is not an authority, a prediction engine, or a replacement for diplomacy." in text

    unsupported_phrases = (
        "complete Python Semantic Engine",
        "source-backed reports",
        "verified release",
        "verified core",
        "secured runtime",
        "protected runtime",
        "what action is safe",
        "active specification",
        "browser interface",
    )
    lowered_text = text.lower()
    for phrase in unsupported_phrases:
        assert phrase.lower() not in lowered_text


def test_public_internal_anchors_and_local_assets_resolve():
    parser = parse_public_page()
    assert not parser.duplicate_ids

    for reference in parser.local_references:
        parts = urlsplit(reference)
        if parts.scheme or parts.netloc:
            continue
        if not parts.path:
            if parts.fragment:
                assert parts.fragment in parser.ids, reference
            continue

        relative_path = unquote(parts.path)
        target = (
            SITE / relative_path.lstrip("/")
            if relative_path.startswith("/")
            else SITE / relative_path
        ).resolve()
        assert target.is_relative_to(SITE.resolve()), reference
        if target.is_dir() or relative_path.endswith("/"):
            target = target / "index.html"
        assert target.is_file(), reference
        if parts.fragment:
            target_parser = PublicPageParser()
            target_parser.feed(target.read_text(encoding="utf-8"))
            assert parts.fragment in target_parser.ids, reference


def test_repository_evidence_links_point_to_existing_paths():
    parser = parse_public_page()
    evidence_pattern = re.compile(
        r"^/Voxterrae/HUB_Optimus/(?:blob|tree)/"
        r"(?P<ref>[0-9a-f]{40})/(?P<path>.+)$"
    )

    checked = []
    for reference in parser.local_references:
        parts = urlsplit(reference)
        if parts.netloc != "github.com":
            continue
        match = evidence_pattern.match(parts.path)
        if not match:
            continue
        repository_path = unquote(match.group("path"))
        checked.append(repository_path)
        assert (ROOT / repository_path).exists(), reference

    assert len(checked) >= 15


def test_document_route_resolver_has_complete_explicit_locale_matrix():
    probe = resolve_document_routes()
    locales = PUBLIC_LOCALES
    expected_route_ids = {
        "core.canonical",
        "core.meta-learning",
        "status.policy",
        "simulator.guide",
        "runtime.contract",
        "semantic.cli",
        "lab.state",
        "governance.protocol",
        "governance.protection",
        "operator.intake.rfc",
        "platform.policy",
        "future.hermes",
        "future.enterprise",
        "future.postquantum",
        "capability.status",
        "legal.ip",
        "security.policy",
        "translation.status",
        "geo.data",
        "translation.termbase",
    }
    assert set(probe["routeIds"]) == expected_route_ids
    assert probe["unknown"] is None
    assert probe["evidenceSha"] == "8426b08e5f88b650c4d79e41d3ce3afd7d42746b"

    resolved = probe["resolved"]
    assert all(
        set(route) == {"href", "language", "relation", "maturity"}
        and "status" not in route
        for variants in resolved.values()
        for route in variants.values()
    )

    for locale in locales:
        core = resolved["core.canonical"][locale]
        assert core["language"] == "es"
        assert core["relation"] == ("source" if locale == "es" else "fallback")
        assert core["maturity"] == "canonical"

        meta_learning = resolved["core.meta-learning"][locale]
        assert meta_learning["language"] == "es"
        assert meta_learning["relation"] == ("source" if locale == "es" else "fallback")
        assert meta_learning["maturity"] is None
        assert meta_learning["href"].endswith("/v1_core/workflow/05_meta_learning.md")

        assert resolved["translation.termbase"][locale] == {
            "href": "./i18n/termbase.v1.json",
            "language": "data",
            "relation": "data",
            "maturity": None,
        }

        simulator = resolved["simulator.guide"][locale]
        assert simulator["language"] == "es"
        assert simulator["relation"] == ("source" if locale == "es" else "fallback")
        assert simulator["maturity"] is None

        governance = resolved["governance.protocol"][locale]
        if locale == "de":
            assert governance["language"] == "de"
            assert governance["relation"] == "source"
            assert governance["maturity"] == "review-needed"
            assert "/docs/de/governance/GOVERNANCE_INTELLIGENCE.md" in governance["href"]
        else:
            assert governance["language"] == "en"
            assert governance["relation"] == ("source" if locale == "en" else "fallback")
            assert governance["maturity"] == "canonical"

        protection = resolved["governance.protection"][locale]
        assert protection["language"] == "en"
        assert protection["relation"] == ("source" if locale == "en" else "fallback")
        assert protection["maturity"] == "canonical"

        intake_rfc = resolved["operator.intake.rfc"][locale]
        assert intake_rfc["language"] == "en"
        assert intake_rfc["relation"] == ("source" if locale == "en" else "fallback")
        assert intake_rfc["maturity"] is None
        assert intake_rfc["href"].endswith("/docs/rfc/operator_controlled_url_intake.md")

    english_source_routes = expected_route_ids - {
        "core.canonical",
        "core.meta-learning",
        "simulator.guide",
        "governance.protocol",
        "governance.protection",
        "translation.termbase",
    }
    for route_id in english_source_routes:
        for locale in locales:
            route = resolved[route_id][locale]
            assert route["language"] == "en"
            assert route["relation"] == ("source" if locale == "en" else "fallback")
            assert route["maturity"] is None

    for route_id, variants in resolved.items():
        for route in variants.values():
            if route["href"].startswith("https://github.com/"):
                assert f"/{probe['evidenceSha']}/" in route["href"]
                assert "/main/" not in route["href"]


def test_governance_route_maturity_matches_versioned_i18n_manifest():
    resolved = resolve_document_routes()["resolved"]["governance.protocol"]
    maturity = json.loads(I18N_MATURITY.read_text(encoding="utf-8"))
    governance = maturity["surfaces"]["governance"]
    filename = "GOVERNANCE_INTELLIGENCE.md"

    def expected_maturity(locale):
        locale_policy = governance["maturity"][locale]
        return locale_policy.get("overrides", {}).get(
            filename,
            locale_policy["default"],
        )

    assert governance["source_locale"] == "en"
    assert governance["source_state"] == "canonical"
    assert filename in governance["files"]
    assert resolved["en"]["maturity"] == expected_maturity("en") == "canonical"
    assert resolved["de"]["maturity"] == expected_maturity("de") == "review-needed"


def test_document_routes_do_not_promote_byte_identical_language_placeholders():
    probe = resolve_document_routes()
    evidence_sha = probe["evidenceSha"]
    routes = probe["resolved"]["governance.protection"]
    placeholders = []

    for locale in ("es", "de", "ru"):
        placeholder = subprocess.run(
            ["git", "show", f"{evidence_sha}:docs/{locale}/governance/SYSTEM_PROTECTION_MATRIX.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        placeholders.append(placeholder)
        assert routes[locale]["language"] == "en"
        assert routes[locale]["relation"] == "fallback"
        assert routes[locale]["maturity"] == "canonical"

    assert len(set(placeholders)) == 1
    assert b"## Purpose" in placeholders[0]


def test_document_route_targets_exist_in_the_pinned_git_tree():
    probe = resolve_document_routes()
    evidence_sha = probe["evidenceSha"]
    commit = subprocess.run(
        ["git", "cat-file", "-e", f"{evidence_sha}^{{commit}}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert commit.returncode == 0, commit.stderr

    checked = set()
    github_target = re.compile(
        r"^/Voxterrae/HUB_Optimus/(?:blob|tree)/"
        r"(?P<ref>[0-9a-f]{40})/(?P<path>.+)$"
    )
    for variants in probe["resolved"].values():
        for route in variants.values():
            href = route["href"]
            if href in checked:
                continue
            checked.add(href)
            parts = urlsplit(href)
            if parts.netloc == "github.com":
                match = github_target.match(parts.path)
                assert match, href
                assert match.group("ref") == evidence_sha
                repository_path = unquote(match.group("path"))
            else:
                assert not parts.scheme and not parts.netloc, href
                repository_path = (
                    Path("site") / unquote(parts.path).removeprefix("./")
                ).as_posix()

            target = subprocess.run(
                ["git", "cat-file", "-e", f"{evidence_sha}:{repository_path}"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            assert target.returncode == 0, f"{href}: {target.stderr}"

    assert len(checked) == 21


def test_document_route_markup_covers_map_and_matches_no_javascript_english():
    probe = resolve_document_routes()
    parser = parse_document_route_markup()
    html = INDEX.read_text(encoding="utf-8")
    tracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            str(DOCUMENT_ROUTES.relative_to(ROOT)),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    english_relation = {
        "source": "source",
        "fallback": "fallback",
        "data": "data",
    }
    english_maturity = {
        "canonical": "canonical",
        "review-needed": "review needed",
    }

    assert not parser.duplicates
    assert tracked.returncode == 0, "document route script must be versioned"
    assert set(parser.links) == set(probe["routeIds"])
    assert html.index("./i18n/document-routes.v1.js") < html.index("./app.js")

    for route_id, record in parser.links.items():
        attributes = record["attributes"]
        resolved = probe["resolved"][route_id]["en"]
        language_label = (
            "DATA" if resolved["language"] == "data" else resolved["language"].upper()
        )
        expected_badge_parts = [language_label]
        if resolved["relation"] != "data":
            expected_badge_parts.append(english_relation[resolved["relation"]])
        if resolved["maturity"]:
            expected_badge_parts.append(english_maturity[resolved["maturity"]])

        assert attributes["href"] == resolved["href"]
        assert record["badge"].strip() == " · ".join(expected_badge_parts)
        assert "aria-label" not in attributes
        if resolved["language"] == "data":
            assert "hreflang" not in attributes
        else:
            assert attributes.get("hreflang") == resolved["language"]


def test_document_route_dom_switches_relation_and_maturity_without_aria_override():
    routes = resolve_document_routes()["resolved"]
    probe = run_document_route_dom_probe(saved="de", click="es")
    initial = probe["initial"]
    after = probe["after"]

    assert initial["core.canonical"]["href"] == routes["core.canonical"]["de"]["href"]
    assert initial["core.canonical"]["hreflang"] == "es"
    assert initial["core.canonical"]["badge"] == "ES · Fallback · kanonisch"
    assert initial["core.canonical"]["relation"] == "fallback"
    assert initial["core.canonical"]["maturity"] == "canonical"
    assert initial["status.policy"]["hreflang"] == "en"
    assert initial["status.policy"]["badge"] == "EN · Fallback"
    assert initial["simulator.guide"]["badge"] == "ES · Fallback"
    assert initial["governance.protocol"]["href"] == routes["governance.protocol"]["de"]["href"]
    assert initial["governance.protocol"]["hreflang"] == "de"
    assert initial["governance.protocol"]["badge"] == "DE · Quelle · Prüfung erforderlich"
    assert initial["governance.protocol"]["relation"] == "source"
    assert initial["governance.protocol"]["maturity"] == "review-needed"

    assert after["core.canonical"]["badge"] == "ES · fuente · canónico"
    assert after["core.canonical"]["relation"] == "source"
    assert after["core.canonical"]["maturity"] == "canonical"
    assert after["status.policy"]["badge"] == "EN · alternativa"
    assert after["simulator.guide"]["badge"] == "ES · fuente"
    assert after["governance.protocol"]["href"] == routes["governance.protocol"]["es"]["href"]
    assert after["governance.protocol"]["hreflang"] == "en"
    assert after["governance.protocol"]["badge"] == "EN · alternativa · canónico"
    assert after["governance.protocol"]["relation"] == "fallback"
    assert after["governance.protocol"]["maturity"] == "canonical"
    assert after["translation.termbase"]["href"] == "./i18n/termbase.v1.json"
    assert after["translation.termbase"]["hreflang"] is None
    assert after["translation.termbase"]["badge"] == "DATA"
    assert after["translation.termbase"]["relation"] == "data"
    assert after["translation.termbase"]["maturity"] is None
    assert all(record["aria"] is None for record in initial.values())
    assert all(record["aria"] is None for record in after.values())


def test_document_route_api_failure_is_visible_and_does_not_invent_accessible_names():
    probe = run_document_route_dom_probe(saved="es", load_route_api=False)

    for snapshot in (probe["initial"], probe["after"]):
        for record in snapshot.values():
            assert record["href"] == "about:blank"
            assert record["hreflang"] == "xx"
            assert record["badge"] == "? · ruta lingüística no disponible"
            assert record["state"] == "unavailable"
            assert record["relation"] is None
            assert record["maturity"] is None
            assert record["aria"] is None


def test_future_cards_keep_non_implementation_copy_in_their_accessible_content():
    parser = parse_document_route_markup()
    expected_copy = {
        "future.hermes": "Future PWA interface boundary. Not implemented.",
        "future.enterprise": "No enterprise product or public service exists.",
        "future.postquantum": "No cryptographic implementation.",
    }

    for route_id, marker in expected_copy.items():
        record = parser.links[route_id]
        content = " ".join(record["content"].split())
        assert marker in content
        assert record["attributes"].get("data-status") == "rfc-not-implemented"
        assert "aria-label" not in record["attributes"]


def test_globe_uses_real_geojson_with_attribution_and_accessible_controls():
    expected_digest = GEOJSON_CHECKSUM.read_text(encoding="utf-8").split()[0]
    actual_digest = hashlib.sha256(GEOJSON.read_bytes()).hexdigest()
    assert actual_digest == expected_digest

    data = json.loads(GEOJSON.read_text(encoding="utf-8"))
    assert data["type"] == "FeatureCollection"
    assert data["features"]
    assert {
        feature["geometry"]["type"] for feature in data["features"]
    } <= {"Polygon", "MultiPolygon"}

    positions = [
        position
        for feature in data["features"]
        for position in iter_positions(feature["geometry"]["coordinates"])
    ]
    assert len(positions) > 1_000
    assert all(-180 <= longitude <= 180 for longitude, _ in positions)
    assert all(-90 <= latitude <= 90 for _, latitude in positions)

    attribution = " ".join(
        GEO_ATTRIBUTION.read_text(encoding="utf-8").lower().split()
    )
    assert "natural earth" in attribution
    assert "world-atlas" in attribution
    assert "public domain" in attribution
    assert "do not represent live telemetry" in attribution
    assert "native webgl" in attribution
    assert "not used as a geographic texture" in attribution

    html = INDEX.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    globe = GLOBE.read_text(encoding="utf-8")
    css = STYLES.read_text(encoding="utf-8")
    assert 'data-geo-source="./assets/geo/land-110m.geojson"' in html
    assert 'href="./assets/geo/README.md"' in html
    assert '<script src="./globe.js" defer></script>' in html
    assert 'id="world-globe"' in html
    assert 'id="globe-motion"' in html
    assert 'aria-hidden="true"' in html
    assert '<body class="no-js">' in html
    assert 'document.body.classList.remove("no-js")' in app
    assert "fetch(geographicSource" in app
    assert 'canvas.setAttribute("tabindex", "0")' in app
    assert 'canvas.removeAttribute("tabindex")' in app
    assert 'fallback.setAttribute("aria-hidden", "true")' in app
    assert 'interactiveNote.hidden = true' in app
    assert 'fallbackNote.hidden = false' in app
    assert 'data-globe-interactive-note data-i18n="globeControls" hidden' in html
    assert 'data-globe-fallback-note data-i18n="globeFallbackNotice">' in html
    assert "showStaticFallback" in app
    assert "webglcontextlost" in app
    assert "webglcontextrestored" in app
    assert '"pointerdown"' in app
    assert '"pointermove"' in app
    assert '"keydown"' in app
    assert "prefers-reduced-motion: reduce" in app
    assert 'getContext("webgl"' in globe
    assert "gl.enable(gl.DEPTH_TEST)" in globe
    assert "perspectiveMatrix" in globe
    assert "gl.drawElements(gl.TRIANGLES" in globe
    assert "spherePoint" in globe
    assert "greatCircle" in globe
    assert "buildGraticule" in globe
    assert "lineSegmentsFromRings" in globe
    assert "world-atlas" not in globe
    assert "three.js" not in globe.lower()
    assert "https://" not in globe
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "touch-action: pan-y pinch-zoom" in css
    globe_core_rule = re.search(r"\.globe-core\s*\{(?P<body>.*?)\}", css, re.DOTALL)
    assert globe_core_rule
    assert "left: 50%" in globe_core_rule.group("body")
    assert "inset-inline-start" not in globe_core_rule.group("body")
    assert "touch-action: none" not in css
    assert ".no-js #world-globe" in css
    assert "function showStaticFallback()" in app
    assert 'canvas.removeAttribute("tabindex")' in app
    assert "canvas.hidden = true" in app
    assert "canvas.hidden = false" in app
    assert "canvas.blur()" in app
    assert app.count("showStaticFallback();") == 3


def test_mobile_hero_keeps_brand_visible_and_prioritizes_operator():
    html = INDEX.read_text(encoding="utf-8")
    css = STYLES.read_text(encoding="utf-8")

    operator_cta = (
        '<a class="button button-primary" href="./operator/?lang=en#product_intake" hreflang="en" '
        'data-operator-route data-i18n="tryOperator">Try Operator</a>'
    )
    method_cta = (
        '<a class="button button-secondary" href="#method" '
        'data-i18n="howItWorks">How it works</a>'
    )

    assert operator_cta in html
    assert method_cta in html
    assert html.index(operator_cta) < html.index(method_cta)
    assert re.search(r"\.hero-copy\s*\{[^}]*min-width:\s*0;", css, re.DOTALL)
    assert re.search(r"\.hero h1\s*\{[^}]*max-width:\s*100%;", css, re.DOTALL)
    assert re.search(r"body\s*\{[^}]*overflow-wrap:\s*anywhere;", css, re.DOTALL)
    mobile_rule = css.split("@media (max-width: 760px)", 1)[1]
    assert "font-size: clamp(1.75rem, 18vw, 5.8rem);" in mobile_rule
    compact_rule = css.split("@media (max-width: 540px)", 1)[1]
    assert re.search(r"\.site-header\s*\{[^}]*position:\s*static;", compact_rule, re.DOTALL)
    assert re.search(r"\.language-switcher\s*\{[^}]*flex-wrap:\s*wrap;", compact_rule, re.DOTALL)
    assert re.search(r"\.language-switcher button\s*\{[^}]*min-height:\s*2\.75rem;", compact_rule, re.DOTALL)
    assert re.search(r"\.language-switcher button\s*\{[^}]*min-width:\s*2\.75rem;", compact_rule, re.DOTALL)
    assert re.search(r"\.hero-actions\s*\{[^}]*flex-direction:\s*column;", compact_rule, re.DOTALL)
    assert re.search(r"\.hero-actions \.button\s*\{[^}]*width:\s*100%;", compact_rule, re.DOTALL)
    assert re.search(r"\.globe-stage\s*\{[^}]*width:\s*100%;", mobile_rule, re.DOTALL)
    assert re.search(r"\.globe-stage\s*\{[^}]*aspect-ratio:\s*auto;", mobile_rule, re.DOTALL)
    assert "min-height: clamp(18rem, 80vw, 23rem);" in css
    zoom_reflow_rule = css.split("@media (max-width: 360px)", 1)[1]
    assert re.search(r"\.truth-strip\s*\{[^}]*grid-template-columns:\s*1fr;", zoom_reflow_rule, re.DOTALL)
    assert re.search(r"\.globe-toolbar\s*\{[^}]*flex-direction:\s*column;", zoom_reflow_rule, re.DOTALL)
    assert "min-height: clamp(14rem, 100vw, 18rem);" in zoom_reflow_rule


def test_webgl_globe_geometry_is_spherical_depth_ready_and_reproducible():
    node = shutil.which("node")
    assert node, "Node.js is required to validate the WebGL geometry"
    harness = r"""
const assert = require("assert");
const fs = require("fs");
const globe = require(process.env.GLOBE_PATH);
const geometry = globe.geometry;

assert.deepStrictEqual(geometry.spherePoint(0, 0), [0, 0, 1]);
assert(Math.abs(geometry.vectorLength(geometry.spherePoint(90, 0)) - 1) < 1e-9);
assert(Math.abs(geometry.vectorLength(geometry.spherePoint(0, 90)) - 1) < 1e-9);

const sphere = geometry.buildSphere(24, 36);
assert.strictEqual(sphere.positions.length, sphere.normals.length);
assert.strictEqual(sphere.indices.length, 24 * 36 * 6);
assert(Math.max(...sphere.indices) < sphere.positions.length / 3);
for (let index = 0; index < sphere.positions.length; index += 3) {
  const point = sphere.positions.slice(index, index + 3);
  assert(Math.abs(geometry.vectorLength(point) - 1) < 1e-5);
}

const route = geometry.greatCircle([0, 0], [90, 0], 8, 0.1);
assert.strictEqual(route.length, 9);
assert(Math.abs(geometry.vectorLength(route[0]) - 1) < 1e-9);
assert(geometry.vectorLength(route[4]) > 1.09);
assert(Math.abs(geometry.vectorLength(route[8]) - 1) < 1e-9);

const geographicData = JSON.parse(fs.readFileSync(process.env.GEOJSON_PATH, "utf8"));
const rings = geometry.extractRings(geographicData);
const coast = geometry.lineSegmentsFromRings(rings);
assert(rings.length > 100);
assert(coast.length / 3 > 9000);
assert.strictEqual((coast.length / 3) % 2, 0);

const graticule = geometry.buildGraticule();
assert(graticule.length / 3 > 2000);
assert.strictEqual((graticule.length / 3) % 2, 0);

const perspective = geometry.perspectiveMatrix(Math.PI / 4, 1.5, 0.1, 10);
assert(perspective[0] > 0);
assert(perspective[5] > perspective[0]);
assert.strictEqual(perspective[11], -1);

assert.strictEqual(globe.create({getContext() { return null; }}), null);

const enabled = new Set();
const drawElementModes = [];
const drawArrayModes = [];
const gl = {
  VERTEX_SHADER: 1,
  FRAGMENT_SHADER: 2,
  COMPILE_STATUS: 3,
  LINK_STATUS: 4,
  ARRAY_BUFFER: 5,
  ELEMENT_ARRAY_BUFFER: 6,
  STATIC_DRAW: 7,
  DEPTH_TEST: 8,
  LEQUAL: 9,
  CULL_FACE: 10,
  BACK: 11,
  SRC_ALPHA: 12,
  ONE_MINUS_SRC_ALPHA: 13,
  FLOAT: 14,
  TRIANGLES: 15,
  UNSIGNED_SHORT: 16,
  BLEND: 17,
  LINES: 18,
  POINTS: 19,
  COLOR_BUFFER_BIT: 0x4000,
  DEPTH_BUFFER_BIT: 0x0100,
  createShader() { return {}; },
  shaderSource() {},
  compileShader() {},
  getShaderParameter() { return true; },
  getShaderInfoLog() { return ""; },
  deleteShader() {},
  createProgram() { return {}; },
  attachShader() {},
  linkProgram() {},
  getProgramParameter() { return true; },
  getProgramInfoLog() { return ""; },
  deleteProgram() {},
  createBuffer() { return {}; },
  bindBuffer() {},
  bufferData() {},
  deleteBuffer() {},
  getAttribLocation(program, name) { return name === "a_normal" ? 1 : 0; },
  getUniformLocation() { return {}; },
  enable(value) { enabled.add(value); },
  disable() {},
  depthFunc() {},
  clearDepth() {},
  cullFace() {},
  blendFunc() {},
  viewport() {},
  useProgram() {},
  uniformMatrix4fv() {},
  uniform4fv() {},
  uniform1f() {},
  uniform1i() {},
  enableVertexAttribArray() {},
  vertexAttribPointer() {},
  drawElements(mode) { drawElementModes.push(mode); },
  drawArrays(mode) { drawArrayModes.push(mode); },
  clearColor() {},
  clear() {}
};
const canvas = {
  width: 0,
  height: 0,
  getContext(name, options) {
    assert.strictEqual(name, "webgl");
    assert.strictEqual(options.depth, true);
    return gl;
  },
  getBoundingClientRect() { return {width: 400, height: 300}; }
};
const renderer = globe.create(canvas);
assert(renderer);
renderer.loadGeography({
  type: "FeatureCollection",
  features: [{
    type: "Feature",
    properties: {},
    geometry: {
      type: "Polygon",
      coordinates: [[[-10, -10], [10, -10], [10, 10], [-10, 10], [-10, -10]]]
    }
  }]
});
renderer.draw({rotation: 12, tilt: -7});
assert(enabled.has(gl.DEPTH_TEST));
assert(drawElementModes.includes(gl.TRIANGLES));
assert(drawArrayModes.filter((mode) => mode === gl.LINES).length >= 3);
assert(drawArrayModes.includes(gl.POINTS));
assert.strictEqual(canvas.width, 400);
assert.strictEqual(canvas.height, 300);
renderer.destroy();
"""
    result = subprocess.run(
        [node, "-e", harness],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GLOBE_PATH": str(GLOBE),
            "GEOJSON_PATH": str(GEOJSON),
        },
    )
    assert result.returncode == 0, result.stderr


def test_public_files_exclude_rejected_branding_and_aggressive_language():
    public_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            INDEX,
            STYLES,
            APP,
            NOT_FOUND,
            NOT_FOUND_APP,
            I18N_README,
            LOCALE_METADATA,
            TERMBASE,
        )
    )
    rejected_patterns = (
        r"signal[\s_-]*atlas",
        r"human\s*(?:×|x)\s*machine",
        r"\breactor\b",
        r"\bnuclear\b",
        r"\bnuke\b",
        r"\bmelon\b",
        r"\bmilitari\w*",
    )
    for pattern in rejected_patterns:
        assert re.search(pattern, public_source, re.IGNORECASE) is None

    visible_text = parse_public_page().visible_text
    assert re.search(
        r"\b(?:aws|azure|microsoft)\b",
        visible_text,
        re.IGNORECASE,
    ) is None
