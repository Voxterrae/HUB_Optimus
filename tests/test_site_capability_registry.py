import copy
import json
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "site" / "data" / "capability-registry.v1.json"
SCHEMA_PATH = ROOT / "site" / "data" / "capability-registry.v1.schema.json"
INDEX_PATH = ROOT / "site" / "index.html"
DOCUMENT_ROUTES_PATH = ROOT / "site" / "i18n" / "document-routes.v1.js"
PAGES_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "pages.yml"

SHA40 = re.compile(r"^[0-9a-f]{40}$")
COMMIT_PATH_URL = re.compile(
    r"^https://github\.com/Voxterrae/HUB_Optimus/(?:blob|tree)/"
    r"(?P<ref>[0-9a-f]{40})/.+"
)
PULL_REQUEST_URL = re.compile(
    r"^https://github\.com/Voxterrae/HUB_Optimus/pull/(?P<ref>[1-9][0-9]*)$"
)
ISSUE_URL = re.compile(
    r"^https://github\.com/Voxterrae/HUB_Optimus/issues/(?P<ref>[1-9][0-9]*)$"
)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
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
ADMIN_GATEWAY_STACK = {"1870", "1871", "1872", "1873", "1875", "1876"}
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


class PortfolioStatusParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.statuses = {}

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        component_id = attrs.get("data-portfolio-component")
        if not component_id:
            return

        status = attrs.get("data-status")
        assert status, f"public component {component_id!r} must declare data-status"
        assert component_id not in self.statuses, (
            f"duplicate public component status for {component_id!r}"
        )
        self.statuses[component_id] = status


def load_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def component_map(registry):
    return {component["id"]: component for component in registry["components"]}


def parse_public_component_statuses():
    parser = PortfolioStatusParser()
    parser.feed(INDEX_PATH.read_text(encoding="utf-8"))
    return parser.statuses


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def schema_errors(registry, schema):
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(validator.iter_errors(registry), key=lambda error: list(error.path))


def test_registry_is_valid_against_checked_draft_2020_12_schema():
    registry = load_registry()
    schema = load_schema()

    Draft202012Validator.check_schema(schema)
    errors = schema_errors(registry, schema)

    assert not errors, "\n".join(
        f"{'/'.join(map(str, error.absolute_path))}: {error.message}"
        for error in errors
    )
    assert registry["$schema"] == "./capability-registry.v1.schema.json"
    assert registry["schema_version"] == "1.0.0"
    assert registry["registry_id"] == "hub_optimus.public_capabilities.v1"
    assert registry["registry_mode"] == "human-reviewed-static"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == (
        "https://huboptimus.dev/data/capability-registry.v1.schema.json"
    )


def test_baseline_is_a_dated_observation_not_a_self_referential_main_claim():
    registry = load_registry()
    baseline = registry["baseline"]
    pages = baseline["github_pages"]
    sites = baseline["sites_mirror"]

    current_date_boundary = date.today() + timedelta(days=1)
    reviewed_at = date.fromisoformat(registry["reviewed_at"])
    pages_observed_at = date.fromisoformat(pages["observed_at"])
    sites_observed_at = date.fromisoformat(sites["observed_at"])

    assert reviewed_at <= current_date_boundary
    for observed_at in (pages_observed_at, sites_observed_at):
        assert observed_at <= reviewed_at
        assert observed_at <= current_date_boundary

    assert baseline["canonical_repository"] == "Voxterrae/HUB_Optimus"
    assert SHA40.fullmatch(baseline["source_baseline_sha"])
    assert SHA40.fullmatch(baseline["public_evidence_sha"])
    assert "reviewed_main_sha" not in baseline

    assert pages["artifact_path"] == "site"
    assert pages["workflow_path"] == ".github/workflows/pages.yml"
    assert pages["portfolio_generation"] == "manual"
    assert pages["observed_conclusion"] == "success"
    assert pages["observed_source_sha"] == baseline["source_baseline_sha"]
    assert pages["merge_path_triggers_pages"] is True
    assert not any(key.startswith("latest_") for key in pages)

    assert sites["authoritative"] is False
    assert sites["synchronization"] == "manual-deterministic"
    assert sites["matches_source_baseline"] is False
    assert sites["observed_source_sha"] != baseline["source_baseline_sha"]
    assert not any(key.startswith("current_") for key in sites)


def test_pages_side_effect_is_explicitly_bound_to_the_real_workflow():
    registry = load_registry()
    pages = registry["baseline"]["github_pages"]
    workflow = PAGES_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert pages["merge_path_triggers_pages"] is True
    assert '- "site/**"' in workflow
    assert '- "docs/**"' in workflow
    assert "path: site" in workflow


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

    markup_statuses = parse_public_component_statuses()
    expected_public_statuses = {
        component_id: components[component_id]["lifecycle_state"]
        for component_id in PUBLIC_COMPONENTS
    }

    assert set(markup_statuses) == PUBLIC_COMPONENTS
    assert markup_statuses == expected_public_statuses
    assert {
        component["id"]
        for component in registry["components"]
        if component["public_section"] == "what-exists-today"
    } == PUBLIC_COMPONENTS
    assert not (set(markup_statuses) & IN_DEVELOPMENT_COMPONENTS)


def test_evidence_type_ref_and_url_identity_are_exact_and_unique():
    registry = load_registry()
    public_evidence_sha = registry["baseline"]["public_evidence_sha"]
    seen = set()

    patterns = {
        "commit-path": COMMIT_PATH_URL,
        "pull-request": PULL_REQUEST_URL,
        "issue": ISSUE_URL,
    }

    for component in registry["components"]:
        for evidence in component["evidence"]:
            identity = (evidence["type"], evidence["ref"], evidence["url"])
            assert identity not in seen, identity
            seen.add(identity)

            match = patterns[evidence["type"]].fullmatch(evidence["url"])
            assert match, evidence
            assert match.group("ref") == evidence["ref"], evidence
            if evidence["type"] == "commit-path":
                assert evidence["ref"] == public_evidence_sha, evidence

            parsed = urlsplit(evidence["url"])
            assert parsed.scheme == "https"
            assert parsed.netloc == "github.com"
            assert not parsed.query
            assert not parsed.fragment


def test_admin_gateway_stack_lists_only_exact_open_pull_requests():
    registry = load_registry()
    admin_gateway = component_map(registry)["admin-gateway"]

    refs = {evidence["ref"] for evidence in admin_gateway["evidence"]}
    urls = {evidence["url"] for evidence in admin_gateway["evidence"]}

    assert refs == ADMIN_GATEWAY_STACK
    assert urls == {
        f"https://github.com/Voxterrae/HUB_Optimus/pull/{number}"
        for number in ADMIN_GATEWAY_STACK
    }
    assert "1874" not in refs


def test_component_states_and_present_claims_are_bounded():
    registry = load_registry()

    for component in registry["components"]:
        assert component["lifecycle_state"] in ALLOWED_LIFECYCLE_STATES
        assert component["source_status"] in ALLOWED_SOURCE_STATUSES
        assert component["claim_boundary"].strip()
        assert component["evidence"]

        if component["source_status"] == "merged":
            assert component["lifecycle_state"] not in {"draft", "issue-only"}
        elif component["source_status"] == "open-issue":
            assert component["lifecycle_state"] == "issue-only"
        else:
            assert component["lifecycle_state"] == "draft"

        if component["source_status"] in NON_MERGED_SOURCE_STATUSES:
            assert component["public_section"] == "in-development"
            assert component["publicly_listed"] is False
            assert component["public_static_surface_available"] is False
            assert component["public_browser_runtime_available"] is False
            assert component["production_service_deployed"] is False
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
        assert component["public_static_surface_available"] is True

    assert components["operator"]["public_browser_runtime_available"] is True
    assert all(
        component["production_service_deployed"] is False
        for component in components.values()
    )


def test_schema_rejects_non_merged_release_transport_and_write_overclaims():
    registry = load_registry()
    schema = load_schema()

    for component_id, field, value in (
        ("evidence-lab", "public_browser_runtime_available", True),
        ("connect-xai-x", "live_external_transport_enabled", True),
        ("admin-gateway", "production_service_deployed", True),
        ("global-graph", "production_writes_executed", 1),
    ):
        mutated = copy.deepcopy(registry)
        component_map(mutated)[component_id][field] = value
        assert schema_errors(mutated, schema), (component_id, field)


def test_schema_rejects_lifecycle_and_public_section_promotion_without_source_change():
    registry = load_registry()
    schema = load_schema()

    mutated_issue = copy.deepcopy(registry)
    component_map(mutated_issue)["global-graph"]["lifecycle_state"] = "draft"
    assert schema_errors(mutated_issue, schema)

    mutated_draft = copy.deepcopy(registry)
    component_map(mutated_draft)["evidence-lab"]["public_section"] = "what-exists-today"
    component_map(mutated_draft)["evidence-lab"]["public_static_surface_available"] = True
    component_map(mutated_draft)["evidence-lab"]["publicly_listed"] = True
    assert schema_errors(mutated_draft, schema)


def test_registry_contains_no_private_identifiers_or_secret_fields():
    registry = load_registry()
    serialized = REGISTRY_PATH.read_text(encoding="utf-8")
    keys = {key.lower() for key in walk_keys(registry)}

    assert not (keys & FORBIDDEN_FIELD_NAMES)
    assert not EMAIL.search(serialized)
    assert not UUID.search(serialized)


def test_schema_contains_cross_field_fail_closed_rules():
    schema = load_schema()
    component = schema["$defs"]["component"]
    properties = component["properties"]

    assert set(properties["lifecycle_state"]["enum"]) == ALLOWED_LIFECYCLE_STATES
    assert set(properties["source_status"]["enum"]) == ALLOWED_SOURCE_STATUSES
    assert properties["production_writes_executed"]["minimum"] == 0
    assert len(component["allOf"]) >= 8
    assert schema["$defs"]["baseline"]["properties"]["sites_mirror"]["properties"][
        "authoritative"
    ]["const"] is False
