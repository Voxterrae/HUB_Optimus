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
NOT_FOUND = SITE / "404.html"
NOT_FOUND_APP = SITE / "404.js"
LOCALE_METADATA = SITE / "i18n" / "locale-metadata.v1.json"
TERMBASE = SITE / "i18n" / "termbase.v1.json"
I18N_README = SITE / "i18n" / "README.md"
GEOJSON = SITE / "assets" / "geo" / "land-110m.geojson"
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


def parse_public_page():
    parser = PublicPageParser()
    parser.feed(INDEX.read_text(encoding="utf-8"))
    return parser


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
    for script in (APP, NOT_FOUND_APP):
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
    assert len(dictionaries["en"]) == 155
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
        "authorityRetrieval",
        "futureTitle",
        "translationReview",
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
    html = INDEX.read_text(encoding="utf-8")

    assert metadata["manifest_version"] == "1.0.0"
    assert metadata["issue"] == 1750
    assert metadata["canonical_v1_language"] == "es"
    assert metadata["constitutional_translation_status"] == "not ratified"
    assert metadata["operator_interface_localized"] is False
    assert metadata["portfolio_translation_key_count"] == 155
    assert set(metadata["locales"]) == PUBLIC_LOCALES
    assert len(metadata["field_status"]) >= 10

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

    assert all(
        set(field_status) == PUBLIC_LOCALES
        for field_status in metadata["field_status"].values()
    )

    metadata_text = LOCALE_METADATA.read_text(encoding="utf-8").lower()
    for unsupported_claim in ("professional", "approved", "native-reviewed"):
        assert unsupported_claim not in metadata_text

    assert termbase["termbase_version"] == "1.0.0"
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
    assert "No constitutional translation is ratified" in readme
    assert "does not execute the Semantic Engine" in readme
    assert "Unverified provenance remains" in readme
    assert './i18n/README.md' in html
    assert './i18n/termbase.v1.json' in html


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
    assert "min-height: 2.25rem" in mobile_section


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
    for route in ("/", "/operator/", "https://github.com/Voxterrae/HUB_Optimus"):
        assert f'href="{route}"' in html

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
        r'<h1 id="hero-title">\s*HUB<span>_</span>Optimus\s*</h1>',
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
            assert parts.fragment in parser.ids, reference


def test_repository_evidence_links_point_to_existing_paths():
    parser = parse_public_page()
    repository_prefixes = (
        "/Voxterrae/HUB_Optimus/blob/main/",
        "/Voxterrae/HUB_Optimus/tree/main/",
    )

    checked = []
    for reference in parser.local_references:
        parts = urlsplit(reference)
        if parts.netloc != "github.com":
            continue
        prefix = next(
            (candidate for candidate in repository_prefixes if parts.path.startswith(candidate)),
            None,
        )
        if not prefix:
            continue
        repository_path = unquote(parts.path.removeprefix(prefix))
        checked.append(repository_path)
        assert (ROOT / repository_path).exists(), reference

    assert len(checked) >= 15


def test_globe_uses_real_geojson_with_attribution_and_accessible_controls():
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

    html = INDEX.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    css = STYLES.read_text(encoding="utf-8")
    assert 'data-geo-source="./assets/geo/land-110m.geojson"' in html
    assert 'href="./assets/geo/README.md"' in html
    assert 'id="world-globe"' in html
    assert 'id="globe-motion"' in html
    assert 'tabindex="0"' in html
    assert '<body class="no-js">' in html
    assert 'document.body.classList.remove("no-js")' in app
    assert "fetch(geographicSource" in app
    assert "spherePoint" in app
    assert "horizonPoint" in app
    assert "greatCircle" in app
    assert '"pointerdown"' in app
    assert '"pointermove"' in app
    assert '"keydown"' in app
    assert "prefers-reduced-motion: reduce" in app
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "touch-action: none" in css
    assert ".no-js #world-globe" in css
    assert "function disableGlobeInteraction()" in app
    assert 'canvas.removeAttribute("tabindex")' in app
    assert "canvas.hidden = true" in app
    assert app.count("disableGlobeInteraction();") == 3


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
