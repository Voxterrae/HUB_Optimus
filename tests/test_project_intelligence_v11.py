import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "site" / "obsidian-HUB_Optimus"
VAULT = ROOT / "obsidian-HUB_Optimus"
INDEX = ROUTE / "index.html"
APP_V11 = ROUTE / "app-v11.js"
STYLES_V11 = ROUTE / "styles-v11.css"
LEARNING = ROUTE / "system.learning.json"

BASELINE_COMMIT = "30e985226347b4bc59b0e187b96633a09647ca42"
V1_CANDIDATE = "9c7b5d81b2cf85d349b1ca141d559a75067a9b14"
ALLOWED_STATUSES = {
    "active",
    "partial",
    "experimental",
    "deprecated",
    "planned",
    "unknown",
}
ALLOWED_CONFIDENCE = {"CONFIRMED", "INFERRED", "UNKNOWN"}


def load_learning_model():
    return json.loads(LEARNING.read_text(encoding="utf-8"))


def test_v11_assets_are_additive_and_referenced():
    index = INDEX.read_text(encoding="utf-8")
    assert './styles-v11.css' in index
    assert './app-v11.js' in index
    assert index.index('./app.js') < index.index('./app-v11.js')

    for path in (APP_V11, STYLES_V11, LEARNING):
        assert path.exists()
        assert path.stat().st_size > 0

    # v1.1 remains an additive layer over the reviewed v1 graph renderer.
    assert (ROUTE / "app-graph.js").exists()
    assert (ROUTE / "app.js").exists()


def test_learning_contract_is_evidence_bound_and_versioned():
    model = load_learning_model()
    assert model["fragment_version"] == "hub-optimus-project-intelligence.learning.v1.1"
    assert model["release"]["version"] == "1.1"
    assert model["release"]["status"] == "experimental"
    assert model["release"]["issue"] == 1912
    assert "opaque model training" in model["release"]["boundary"]

    assert model["baseline"]["semantic_model_commit"] == BASELINE_COMMIT
    assert model["baseline"]["v1_candidate_commit"] == V1_CANDIDATE
    assert model["baseline"]["repository"] == "Voxterrae/HUB_Optimus"

    snapshot = model["coverage"]["model_snapshot"]
    assert snapshot == {
        "components": 16,
        "interfaces": 7,
        "entities": 13,
        "relations": 25,
        "risks": 8,
        "confidence": "CONFIRMED",
        "source": [
            "site/obsidian-HUB_Optimus/system.json",
            "site/obsidian-HUB_Optimus/system.runtime.json",
        ],
    }

    contract = model["evidence_contract"]
    assert set(contract["status_vocabulary"]) == ALLOWED_STATUSES
    assert set(contract["confidence_vocabulary"]) == ALLOWED_CONFIDENCE
    assert {
        "claim",
        "source",
        "baseline",
        "status",
        "confidence",
        "freshness",
        "review_state",
    } == set(contract["required_dimensions"])

    capabilities = model["capabilities"]
    assert len(capabilities) >= 6
    assert {item["id"] for item in capabilities} >= {
        "graph-node-search",
        "graph-impact-focus",
        "graph-viewport",
        "relation-evidence",
        "repository-domain-inventory",
        "incremental-model-delta",
    }
    for item in capabilities:
        assert item["status"] in ALLOWED_STATUSES
        assert item["confidence"] in ALLOWED_CONFIDENCE
        assert item["evidence"]


def test_v11_graph_interaction_contracts():
    javascript = APP_V11.read_text(encoding="utf-8")
    styles = STYLES_V11.read_text(encoding="utf-8")

    for contract in (
        'const ADDON_MODEL_URL = "./system.learning.json"',
        '"direct"',
        '"upstream"',
        '"downstream"',
        "bestSearchMatch",
        "reachable",
        "MutationObserver",
        'addEventListener("wheel"',
        'addEventListener("pointerdown"',
        'setAttribute("aria-live", "polite")',
        'setAttribute("tabindex", "0")',
        "prefers-reduced-motion",
    ):
        assert contract in javascript or contract in styles

    assert "innerHTML" not in javascript
    assert "eval(" not in javascript
    assert "new Function" not in javascript
    assert "textContent" in javascript
    assert "replaceChildren" in javascript

    for selector in (
        ".graph-intelligence-toolbar",
        ".graph-node.v11-dimmed",
        ".graph-edge.v11-edge-focus",
        ".learning-capability-grid",
        "@media (max-width: 760px)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert selector in styles


def test_v11_obsidian_notes_define_graph_and_learning_boundaries():
    notes = {
        "02_ARCHITECTURE/Graph Intelligence v1.1.md": (
            "# Graph Intelligence v1.1",
            "No inferred edge is created by the browser.",
        ),
        "98_META/Whole-System Learning.md": (
            "# Whole-System Learning",
            "does not mean autonomous truth adjudication",
        ),
        "98_META/Repository Coverage.md": (
            "# Repository Coverage",
            "does not claim complete machine-measured coverage",
        ),
    }
    for relative, phrases in notes.items():
        path = VAULT / relative
        assert path.exists(), relative
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert BASELINE_COMMIT in content
        assert V1_CANDIDATE in content
        for phrase in phrases:
            assert phrase in content


def test_v11_does_not_claim_planned_inventory_is_complete():
    model = load_learning_model()
    repository_inventory = model["coverage"]["repository_inventory"]
    assert repository_inventory["status"] == "planned"
    assert "not represented as complete" in repository_inventory["description"]

    whole_system = (VAULT / "98_META" / "Whole-System Learning.md").read_text(
        encoding="utf-8"
    )
    assert "Planned capabilities remain labelled `planned`" in whole_system
