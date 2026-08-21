import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "obsidian-HUB_Optimus"
ROUTE = ROOT / "site" / "obsidian-HUB_Optimus"
MODEL_PATH = ROUTE / "system.json"
INDEX = ROUTE / "index.html"
HANDOFF = ROOT / "docs" / "context" / "AI_HANDOFF.md"
STYLE_PATHS = [
    ROUTE / "styles.css",
    ROUTE / "styles-explorer.css",
    ROUTE / "styles-content.css",
]
APP_GRAPH = ROUTE / "app-graph.js"
APP = ROUTE / "app.js"

BASELINE_COMMIT = "30e985226347b4bc59b0e187b96633a09647ca42"
BASELINE_TREE = "fabb9da1fdb6979df0bc764017752f118088e69f"
ALLOWED_STATUSES = {
    "active",
    "partial",
    "experimental",
    "deprecated",
    "planned",
    "unknown",
}
ALLOWED_CONFIDENCE = {"CONFIRMED", "INFERRED", "UNKNOWN"}


class ProjectIntelligenceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicate_ids = set()
        self.references = []
        self.asset_references = []
        self.mode_buttons = set()
        self.filter_buttons = set()
        self.skip_targets = []
        self.text_parts = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        element_id = attrs.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)

        if attrs.get("data-mode"):
            self.mode_buttons.add(attrs["data-mode"])
        if attrs.get("data-filter"):
            self.filter_buttons.add(attrs["data-filter"])

        reference = None
        if tag in {"a", "link"}:
            reference = attrs.get("href")
        elif tag in {"script", "img"}:
            reference = attrs.get("src")
        if reference:
            self.references.append(reference)
            if tag in {"link", "script", "img"}:
                self.asset_references.append(reference)

        if tag == "a" and "skip-link" in attrs.get("class", "").split():
            self.skip_targets.append(attrs.get("href"))

    def handle_data(self, data):
        compact = " ".join(data.split())
        if compact:
            self.text_parts.append(compact)

    @property
    def visible_text(self):
        return " ".join(self.text_parts)


def load_model():
    core = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    model = dict(core)
    for reference in core.get("includes", []):
        split = urlsplit(reference)
        assert not split.scheme and not split.netloc, reference
        fragment_path = (ROUTE / unquote(split.path)).resolve()
        assert fragment_path.is_relative_to(ROUTE.resolve())
        assert fragment_path.exists(), reference
        model.update(json.loads(fragment_path.read_text(encoding="utf-8")))
    return model


def all_source_paths(model):
    for section in ("components", "interfaces", "entities", "deployment", "dependencies"):
        for item in model[section]:
            for path in item.get("source", []):
                yield path


def test_structured_model_baseline_and_vocabulary():
    model = load_model()
    assert model["schema_version"] == "hub-optimus-project-intelligence.v1"
    assert model["analysis"]["repository"] == "Voxterrae/HUB_Optimus"
    assert model["analysis"]["branch"] == "main"
    assert model["analysis"]["commit"] == BASELINE_COMMIT
    assert model["analysis"]["tree"] == BASELINE_TREE
    assert model["analysis"]["status_vocabulary"] == [
        "active",
        "partial",
        "experimental",
        "deprecated",
        "planned",
        "unknown",
    ]
    assert set(model["analysis"]["confidence_vocabulary"]) == ALLOWED_CONFIDENCE

    assert len(model["components"]) >= 12
    assert len(model["interfaces"]) == 7
    assert len(model["entities"]) >= 10
    assert len(model["relations"]) >= 20
    assert len(model["risks"]) >= 6

    for section in (
        "components",
        "external_systems",
        "dependencies",
        "interfaces",
        "entities",
        "runtime_flows",
        "deployment",
        "risks",
    ):
        for item in model[section]:
            if "status" in item:
                assert item["status"] in ALLOWED_STATUSES, (section, item["id"], item["status"])
            if "confidence" in item:
                assert item["confidence"] in ALLOWED_CONFIDENCE, (
                    section,
                    item["id"],
                    item["confidence"],
                )


def test_graph_integrity_and_required_concepts():
    model = load_model()
    node_sections = ("components", "external_systems", "dependencies")
    nodes = [item for section in node_sections for item in model[section]]
    node_ids = [item["id"] for item in nodes]
    assert len(node_ids) == len(set(node_ids))

    component_ids = {item["id"] for item in model["components"]}
    assert {
        "governance",
        "methodology",
        "scenario-loader",
        "simulator",
        "semantic-engine",
        "operator",
        "learning-store",
        "controlled-intake",
        "local-http-api",
        "hub-core",
        "ec2-release",
        "public-site",
        "pages-pipeline",
        "quality-gates",
        "control-prototype",
    } <= component_ids

    relation_ids = [item["id"] for item in model["relations"]]
    assert len(relation_ids) == len(set(relation_ids))
    node_id_set = set(node_ids)
    relations_by_id = {item["id"]: item for item in model["relations"]}
    for relation in model["relations"]:
        assert relation["from"] in node_id_set
        assert relation["to"] in node_id_set
        assert relation["status"] in ALLOWED_STATUSES
        assert relation["confidence"] in ALLOWED_CONFIDENCE

    assert set(model["views"]) == {
        "system",
        "data",
        "api",
        "deployment",
        "dependencies",
    }
    relation_id_set = set(relation_ids)
    for view_id, view in model["views"].items():
        view_nodes = set(view["nodes"])
        assert view_nodes <= node_id_set
        assert set(view["relations"]) <= relation_id_set
        assert view_nodes <= set(model["layouts"][view_id])
        for node_id in view["nodes"]:
            x, y = model["layouts"][view_id][node_id]
            assert 0 <= x <= 940
            assert 0 <= y <= 600
        for relation_id in view["relations"]:
            relation = relations_by_id[relation_id]
            assert relation["from"] in view_nodes, (view_id, relation_id, relation["from"])
            assert relation["to"] in view_nodes, (view_id, relation_id, relation["to"])

    interface_ids = {item["id"] for item in model["interfaces"]}
    assert {
        "get-health",
        "get-status",
        "post-intake-url",
        "post-analyze",
        "scenario-cli",
        "semantic-cli",
        "hub-core-cli",
    } == interface_ids


def test_source_map_paths_are_safe_and_resolve_in_a_full_checkout():
    model = load_model()
    paths = list(all_source_paths(model))
    assert paths
    for source in paths:
        assert source
        assert not source.startswith("/")
        assert "\\" not in source
        assert ".." not in Path(source).parts

    # The generated-worktree validation can run without the original checkout.
    # CI runs this branch inside the complete repository and therefore verifies
    # every source-map target.
    if (ROOT / "AGENTS.md").exists():
        for source in paths:
            target = ROOT / source.rstrip("/")
            assert target.exists(), source

    for section in ("components", "interfaces", "entities", "deployment"):
        for item in model[section]:
            for link in item.get("source_links", []):
                assert link["path"] in item["source"]
                assert BASELINE_COMMIT in link["url"]
                assert link["url"].startswith("https://github.com/Voxterrae/HUB_Optimus/")


def test_obsidian_required_notes_and_wikilinks_resolve():
    notes = sorted(VAULT.rglob("*.md"))
    assert len(notes) >= 50
    required = {
        "00_HOME/Home.md",
        "00_HOME/System Dashboard.md",
        "00_HOME/Current State.md",
        "00_HOME/Architecture Map.md",
        "00_HOME/Navigation.md",
        "98_META/Repository Analysis.md",
        "98_META/Documentation Standard.md",
        "98_META/Status Definitions.md",
        "98_META/Update Protocol.md",
        "18_SOURCE_MAP/Source Map.md",
    }
    assert required <= {str(path.relative_to(VAULT)) for path in notes}

    stems = {}
    for note in notes:
        assert note.read_text(encoding="utf-8").startswith("---\n")
        assert BASELINE_COMMIT in note.read_text(encoding="utf-8")
        assert note.stem not in stems, f"Duplicate Obsidian note stem: {note.stem}"
        stems[note.stem] = note

    unresolved = []
    for note in notes:
        source = note.read_text(encoding="utf-8")
        for raw_target in re.findall(r"\[\[([^\]]+)\]\]", source):
            target = raw_target.split("|", 1)[0].split("#", 1)[0].strip()
            if target and target not in stems:
                unresolved.append((str(note.relative_to(VAULT)), target))
    assert unresolved == []


def test_home_and_current_state_have_required_navigation_sections():
    home = (VAULT / "00_HOME" / "Home.md").read_text(encoding="utf-8")
    for heading in (
        "## System Status",
        "## What This Project Does",
        "## Architecture",
        "## Main Components",
        "## Runtime Flow",
        "## Data Flow",
        "## Deployment",
        "## Current State",
        "## Key Risks",
        "## Navigation",
    ):
        assert heading in home

    current = (VAULT / "00_HOME" / "Current State.md").read_text(encoding="utf-8")
    for phrase in (
        "Qué hace el proyecto",
        "Qué funciona",
        "Cómo está organizado",
        "Qué está incompleto",
        "Cómo se ejecuta",
        "Cómo se prueba",
        "Cómo se despliega",
        "Riesgos prioritarios",
        "Dónde mirar",
    ):
        assert phrase in current


def test_operational_handoff_records_project_intelligence_surface():
    handoff = HANDOFF.read_text(encoding="utf-8")
    for phrase in (
        "## Project intelligence surface",
        "Governance issue `#1901` and PR `#1903`",
        "obsidian-HUB_Optimus/",
        "/obsidian-HUB_Optimus/",
        "98_META/Update Protocol.md",
        "tests/test_project_intelligence_site.py",
        "tests/test_public_site_links_and_contrast.py",
        "Repository state,\nPages deployment state, and externally served bytes remain separate claims.",
    ):
        assert phrase in handoff


def test_web_route_is_static_accessible_and_self_contained():
    parser = ProjectIntelligenceParser()
    parser.feed(INDEX.read_text(encoding="utf-8"))

    assert parser.duplicate_ids == set()
    assert {
        "main",
        "overview",
        "architecture",
        "components",
        "runtime",
        "data-flow",
        "interfaces",
        "dependencies",
        "deployment",
        "source-map",
        "technical-notes",
        "architecture-graph",
        "node-detail",
    } <= parser.ids
    assert parser.skip_targets == ["#main"]
    assert parser.mode_buttons == {
        "system",
        "data",
        "api",
        "deployment",
        "dependencies",
    }
    assert parser.filter_buttons == {"all", "active", "partial", "experimental"}

    for asset in (
        "./styles.css",
        "./styles-explorer.css",
        "./styles-content.css",
        "./app-graph.js",
        "./app.js",
    ):
        assert asset in parser.asset_references
    for reference in parser.asset_references:
        split = urlsplit(reference)
        assert not split.scheme and not split.netloc, reference
        target = (ROUTE / unquote(split.path)).resolve()
        assert target.is_relative_to(ROUTE.resolve())
        assert target.exists(), reference

    visible = parser.visible_text
    for heading in (
        "Overview",
        "Architecture",
        "Components",
        "DATA FLOW",
        "APIs & COMMANDS",
        "DEPENDENCIES",
        "DEPLOYMENT",
        "SOURCE MAP",
        "TECHNICAL NOTES",
        "PROJECT STATE",
    ):
        assert heading in visible


def test_web_css_and_javascript_contracts():
    styles = "\n".join(path.read_text(encoding="utf-8") for path in STYLE_PATHS)
    app_graph = APP_GRAPH.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    javascript = app_graph + "\n" + app

    for contract in (
        ":focus-visible",
        "@media (prefers-reduced-motion: reduce)",
        "@media (max-width: 760px)",
        "overflow-x: hidden",
        ".mobile-graph-list",
        ".graph-edge",
    ):
        assert contract in styles

    card_layer_colors = re.findall(
        r"\.card-layer\s*\{[^{}]*color\s*:\s*([^;]+);",
        styles,
        re.DOTALL,
    )
    assert card_layer_colors[-1].strip() == "var(--muted)"

    assert 'const MODEL_URL = "./system.json"' in app_graph
    assert "fetch(MODEL_URL" in app
    assert app.index("setControlsDisabled(true)") < app.index("fetch(MODEL_URL")
    assert app.index("state.model = validateModel") < app.rindex("bindControls();")
    assert "findModeForNode" in app
    assert "renderStaticFallback();" in app
    assert "static-architecture-fallback" in app
    assert '"data-node-id": nodeId' in app_graph
    assert "restoreGraphFocus" in app_graph
    assert "textContent" in javascript
    assert "replaceChildren" in javascript
    assert "matchMedia" in javascript
    assert "animateMotion" in javascript
    assert "aria-pressed" in javascript
    assert "innerHTML" not in javascript
    assert BASELINE_COMMIT in app


def test_model_and_vault_names_remain_synchronized():
    model = load_model()
    notes = {path.stem: path for path in VAULT.rglob("*.md")}
    for component in model["components"]:
        assert component["name"] in notes
        note = VAULT / component["note"]
        assert note.exists()
        assert f"# {component['name']}" in note.read_text(encoding="utf-8")


def test_new_files_do_not_contain_common_secret_markers():
    patterns = (
        "BEGIN " + "PRIVATE KEY",
        "BEGIN OPENSSH " + "PRIVATE KEY",
        "AKIA[0-9A-Z]{16}",
        "ghp_[A-Za-z0-9]{20,}",
        "sk-proj-[A-Za-z0-9_-]{20,}",
    )
    files = [*VAULT.rglob("*.md"), *ROUTE.glob("*"), HANDOFF, Path(__file__)]
    for path in files:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for pattern in patterns:
            assert re.search(pattern, content) is None, (path, pattern)
