import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "site" / "data" / "capability-registry.v1.json"
SCHEMA_PATH = ROOT / "site" / "data" / "capability-registry.v1.schema.json"
INDEX_PATH = ROOT / "site" / "index.html"
DOCUMENT_ROUTES_PATH = ROOT / "site" / "i18n" / "document-routes.v1.js"

SHA40 = re.compile(r"^[0-9a-f]{40}$")
GITHUB_EVIDENCE = re.compile(
    r"^https://github\.com/Voxterrae/HUB_Optimus/(?:blob|tree|pull|issues)/"
)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)

PUBLIC_COMPONENTS = {
    "core",
    "simulator",
    "semantic-engine",
    "operator",
    "controlled-url-intake",
    "research",
    "governance-intelligence",
    "labs",
}
IN_DEVELOPMENT_COMPONENTS = {
    "admin-gateway",
    "evidence-lab",
    "connect-xai-x",
    "global-graph",
}
ALLOWED_LIFECYCLE_STATES = {
    "active-methodology",
    "working-deterministic-prototype",
    "early-implementation",
    "browser-prototype",
    "implementation-present-deployment-unverified",
    "experimental-tooling",
    "active-ratified-protocol",
    "official-empty-incubation",
    "draft",
    "issue-only",
}
ALLOWED_SOURCE_STATUSES = {
    "merged",
    "draft-pr",
    "draft-pr-stack",
    "open-issue",
}
NON_MERGED_SOURCE_STATUSES = {"draft-pr", "draft-pr-stack", "open-issue"}
FORBIDDEN_FIELD_NAMES = {
    "access_token",
    "api_key",
    "certificate",
    "client_secret",
    "email",
    "environment_id",
    "password",
    "phone",
    "private_key",
    "refresh_token",
    "secret",
    "tenant_id",
}


def load_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def component_map(registry):
    return {component["id"]: component for component in registry["components"]}


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def test_registry_and_schema_are_parseable_versioned_json():
    registry = load_registry()
    schema = load_schema()

    assert registry["$schema"] == "./capability-registry.v1.schema.json"
    assert registry["schema_version"] == "1.0.0"
    assert registry["registry_id"] == "hub_optimus.public_capabilities.v1"
    assert registry["registry_mode"] == "human-reviewed-static"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "https://huboptimus.dev/data/capability-registry.v1.schema.json"


def test_registry_baseline_is_explicit_and_sites_is_not_claimed_current():
    registry = load_registry()
    baseline = registry["baseline"]
    pages = baseline["github_pages"]
    sites = baseline["sites_mirror"]

    date.fromisoformat(registry["reviewed_at"])
    assert baseline["canonical_repository"] == "Voxterrae/HUB_Optimus"
    assert SHA40.fullmatch(baseline["reviewed_main_sha"])
    assert SHA40.fullmatch(baseline["public_evidence_sha"])
    assert pages["artifact_path"] == "site"
    assert pages["workflow_path"] == ".github/workflows/pages.yml"
    assert pages["portfolio_generation"] == "manual"
    assert pages["latest_verified_conclusion"] == "success"
    assert pages["latest_verified_source_sha"] == baseline["reviewed_main_sha"]
    assert sites["authoritative"] is False
    assert sites["synchronization"] == "manual-deterministic"
    assert sites["current_with_reviewed_main"] is False
    assert sites["last_verified_source_sha"] != baseline["reviewed_main_sha"]


def test_public_evidence_sha_matches_document_route_resolver():
    registry = load_registry()
    route_source = DOCUMENT_ROUTES_PATH.read_text(encoding="utf-8")
    match = re.search(r'const EVIDENCE_SHA = "([0-9a-f]{40})";', route_source)

    assert match, "document route resolver must expose one immutable evidence SHA"
    assert match.group(1) == registry["baseline"]["public_evidence_sha"]


def test_registry_contains_exact_current_and_development_component_sets():
    registry = load_registry()
    components = component_map(registry)

    assert len(components) == len(registry["components"]), "component IDs must be unique"
    assert set(components) == PUBLIC_COMPONENTS | IN_DEVELOPMENT_COMPONENTS

    public_markup = INDEX_PATH.read_text(encoding="utf-8")
    markup_components = set(
        re.findall(r'data-portfolio-component="([a-z0-9-]+)"', public_markup)
    )

    assert markup_components == PUBLIC_COMPONENTS
    assert {
        component["id"]
        for component in registry["components"]
        if component["public_section"] == "what-exists-today"
    } == PUBLIC_COMPONENTS
    assert not (markup_components & IN_DEVELOPMENT_COMPONENTS)


def test_component_states_and_evidence_are_bounded():
    registry = load_registry()

    for component in registry["components"]:
        assert component["lifecycle_state"] in ALLOWED_LIFECYCLE_STATES
        assert component["source_status"] in ALLOWED_SOURCE_STATUSES
        assert component["claim_boundary"].strip()
        assert component["evidence"]

        for evidence in component["evidence"]:
            assert GITHUB_EVIDENCE.match(evidence["url"]), evidence
            assert evidence["ref"].strip()

        if component["source_status"] == "merged":
            assert component["lifecycle_state"] not in {"draft", "issue-only"}
        elif component["source_status"] == "open-issue":
            assert component["lifecycle_state"] == "issue-only"
        else:
            assert component["lifecycle_state"] == "draft"


def test_non_merged_work_cannot_claim_release_deployment_or_transport():
    registry = load_registry()

    for component in registry["components"]:
        if component["source_status"] not in NON_MERGED_SOURCE_STATUSES:
            continue

        assert component["public_section"] == "in-development"
        assert component["publicly_listed"] is False
        assert component["released_public_artifact"] is False
        assert component["public_runtime_deployed"] is False
        assert component["production_deployed"] is False
        assert component["production_writes_executed"] == 0
        assert component["live_external_transport_enabled"] is False


def test_current_public_components_are_merged_and_truthfully_listed():
    registry = load_registry()
    components = component_map(registry)

    for component_id in PUBLIC_COMPONENTS:
        component = components[component_id]
        assert component["source_status"] == "merged"
        assert component["public_section"] == "what-exists-today"
        assert component["publicly_listed"] is True
        assert component["released_public_artifact"] is True

    assert components["operator"]["public_runtime_deployed"] is True
    assert all(
        component["production_deployed"] is False
        for component in components.values()
    )


def test_registry_contains_no_private_identifiers_or_secret_fields():
    registry = load_registry()
    serialized = REGISTRY_PATH.read_text(encoding="utf-8")
    keys = {key.lower() for key in walk_keys(registry)}

    assert not (keys & FORBIDDEN_FIELD_NAMES)
    assert not EMAIL.search(serialized)
    assert not UUID.search(serialized)


def test_schema_enumerates_the_registry_state_contract():
    schema = load_schema()
    component_properties = schema["$defs"]["component"]["properties"]

    assert set(component_properties["lifecycle_state"]["enum"]) == ALLOWED_LIFECYCLE_STATES
    assert set(component_properties["source_status"]["enum"]) == ALLOWED_SOURCE_STATUSES
    assert component_properties["production_writes_executed"]["minimum"] == 0
    assert schema["$defs"]["baseline"]["properties"]["sites_mirror"]["properties"][
        "authoritative"
    ]["const"] is False
