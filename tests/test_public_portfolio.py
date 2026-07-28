import json
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
GEOJSON = SITE / "assets" / "geo" / "land-110m.geojson"
GEO_ATTRIBUTION = SITE / "assets" / "geo" / "README.md"


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


def extract_translation_keys(source):
    blocks = {}
    pattern = re.compile(
        r"^    (en|es|de): \{\n(?P<body>.*?)(?=^    \}(?:,)?$)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(source):
        blocks[match.group(1)] = set(
            re.findall(r"^      ([A-Za-z][A-Za-z0-9]*):", match.group("body"), re.MULTILINE)
        )
    return blocks


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
    result = subprocess.run(
        [node, "--check", str(APP)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    source = APP.read_text(encoding="utf-8")
    dictionaries = extract_translation_keys(source)
    assert set(dictionaries) == {"en", "es", "de"}
    assert dictionaries["en"] == dictionaries["es"] == dictionaries["de"]

    parser = parse_public_page()
    assert parser.i18n_keys <= dictionaries["en"]
    assert {"title", "description", "resumeGlobe"} <= dictionaries["en"]


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


def test_public_files_exclude_rejected_branding_and_aggressive_language():
    public_source = "\n".join(
        path.read_text(encoding="utf-8") for path in (INDEX, STYLES, APP)
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
