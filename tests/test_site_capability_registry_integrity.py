import copy
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import yaml
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "site" / "data" / "capability-registry.v1.json"
SCHEMA_PATH = ROOT / "site" / "data" / "capability-registry.v1.schema.json"
PAGES_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "pages.yml"
AI_HANDOFF_PATH = ROOT / "docs" / "context" / "AI_HANDOFF.md"

COMMIT_PATH_URL = re.compile(
    r"^https://github\.com/Voxterrae/HUB_Optimus/"
    r"(?P<kind>blob|tree)/(?P<ref>[0-9a-f]{40})/(?P<path>.+)$"
)
EXPECTED_EVIDENCE_TYPE = {
    "merged": "commit-path",
    "draft-pr": "pull-request",
    "draft-pr-stack": "pull-request",
    "open-issue": "issue",
}


def load_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def component_map(registry):
    return {component["id"]: component for component in registry["components"]}


def schema_errors(registry):
    validator = Draft202012Validator(
        load_schema(),
        format_checker=FormatChecker(),
    )
    return list(validator.iter_errors(registry))


def load_pages_workflow():
    workflow = yaml.safe_load(PAGES_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)

    # PyYAML follows YAML 1.1 and may parse the unquoted key `on` as True.
    if "on" not in workflow and True in workflow:
        workflow["on"] = workflow.pop(True)
    return workflow


def git_object_type(ref, path):
    result = subprocess.run(
        ["git", "cat-file", "-t", f"{ref}:{path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"missing evidence object {ref}:{path}: {result.stderr.strip()}"
    )
    return result.stdout.strip()


def test_source_status_matches_every_evidence_type():
    registry = load_registry()

    for component in registry["components"]:
        expected_type = EXPECTED_EVIDENCE_TYPE[component["source_status"]]
        actual_types = {evidence["type"] for evidence in component["evidence"]}
        assert actual_types == {expected_type}, component["id"]

    assert len(component_map(registry)["admin-gateway"]["evidence"]) >= 2


def test_schema_rejects_source_status_and_evidence_type_mismatches():
    registry = load_registry()

    relabeled_stack = copy.deepcopy(registry)
    component = component_map(relabeled_stack)["admin-gateway"]
    component["source_status"] = "merged"
    component["lifecycle_state"] = "active-methodology"
    assert schema_errors(relabeled_stack)

    relabeled_issue = copy.deepcopy(registry)
    component = component_map(relabeled_issue)["global-graph"]
    component["source_status"] = "draft-pr"
    component["lifecycle_state"] = "draft"
    assert schema_errors(relabeled_issue)

    wrong_draft_evidence = copy.deepcopy(registry)
    component = component_map(wrong_draft_evidence)["evidence-lab"]
    component["evidence"] = [
        {
            "type": "issue",
            "ref": "1880",
            "url": "https://github.com/Voxterrae/HUB_Optimus/issues/1880",
        }
    ]
    assert schema_errors(wrong_draft_evidence)


def test_every_commit_evidence_path_exists_at_the_declared_object_type():
    registry = load_registry()

    for component in registry["components"]:
        for evidence in component["evidence"]:
            if evidence["type"] != "commit-path":
                continue

            match = COMMIT_PATH_URL.fullmatch(evidence["url"])
            assert match, evidence
            assert match.group("ref") == evidence["ref"]

            path = unquote(match.group("path"))
            path_parts = PurePosixPath(path)
            assert path and not path_parts.is_absolute()
            assert ".." not in path_parts.parts

            expected_type = "blob" if match.group("kind") == "blob" else "tree"
            assert git_object_type(evidence["ref"], path) == expected_type, evidence


def test_pages_workflow_uploads_the_exact_declared_artifact_path():
    registry = load_registry()
    pages = registry["baseline"]["github_pages"]
    workflow = load_pages_workflow()

    triggers = workflow["on"]
    push_paths = set(triggers["push"]["paths"])
    assert {"site/**", "docs/**"} <= push_paths

    steps = workflow["jobs"]["deploy"]["steps"]
    upload_steps = [
        step
        for step in steps
        if str(step.get("uses", "")).startswith("actions/upload-pages-artifact@")
    ]
    assert len(upload_steps) == 1
    assert upload_steps[0]["with"]["path"] == pages["artifact_path"] == "site"


def test_ai_handoff_records_the_registry_flow_and_outstanding_slices():
    handoff = AI_HANDOFF_PATH.read_text(encoding="utf-8")

    required_markers = {
        "## Public surface capability registry boundary",
        "#1888",
        "#1889",
        "site/data/capability-registry.v1.json",
        "GitHub Pages",
        "visible presentation",
        "Sites synchronization",
    }
    missing = sorted(marker for marker in required_markers if marker not in handoff)
    assert not missing, f"AI handoff is missing registry markers: {missing}"
