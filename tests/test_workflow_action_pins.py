from pathlib import Path
import re

import pytest
import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

EXPECTED_ACTION_PINS = {
    "actions/checkout": (
        "3d3c42e5aac5ba805825da76410c181273ba90b1",
        "v7.0.1",
    ),
    "actions/setup-python": (
        "5fda3b95a4ea91299a34e894583c3862153e4b97",
        "v7.0.0",
    ),
    "actions/configure-pages": (
        "45bfe0192ca1faeb007ade9deae92b16b8254a0d",
        "v6.0.0",
    ),
    "actions/upload-pages-artifact": (
        "fc324d3547104276b827a68afc52ff2a11cc49c9",
        "v5.0.0",
    ),
    "actions/deploy-pages": (
        "cd2ce8fcbc39b97be8ca5fce6e763baed58fa128",
        "v5.0.0",
    ),
    "lycheeverse/lychee-action": (
        "e7477775783ea5526144ba13e8db5eec57747ce8",
        "v2.9.0",
    ),
}

COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _uses_references(workflow_path: Path) -> list[tuple[str, str]]:
    source = workflow_path.read_text(encoding="utf-8")
    lines = source.splitlines()
    document = yaml.compose(source, Loader=yaml.SafeLoader)
    assert document is not None, f"{workflow_path.name} must be valid YAML"
    references: list[tuple[str, str]] = []

    def visit(node: Node) -> None:
        if isinstance(node, MappingNode):
            for key, value in node.value:
                if isinstance(key, ScalarNode) and key.value == "uses":
                    assert isinstance(value, ScalarNode), (
                        f"{workflow_path.name}:{key.start_mark.line + 1} "
                        "must use a literal Action reference"
                    )
                    assert value.start_mark.line == key.start_mark.line, (
                        f"{workflow_path.name}:{key.start_mark.line + 1} "
                        "must keep the Action and reviewed version on one line"
                    )
                    raw_line = lines[key.start_mark.line]
                    _code, marker, comment = raw_line.partition("#")
                    assert marker and comment.strip(), (
                        f"{workflow_path.name}:{key.start_mark.line + 1} "
                        "must include the reviewed release as an inline comment"
                    )
                    references.append((value.value, comment.strip()))
                visit(value)
        elif isinstance(node, SequenceNode):
            for value in node.value:
                visit(value)

    visit(document)
    return references


def test_every_workflow_pins_actions_to_reviewed_commits() -> None:
    observed_actions: set[str] = set()
    workflow_paths = sorted(WORKFLOW_DIR.glob("*.yml"))
    workflow_paths.extend(sorted(WORKFLOW_DIR.glob("*.yaml")))
    assert workflow_paths

    for workflow_path in workflow_paths:
        for reference, version in _uses_references(workflow_path):
            action, separator, ref = reference.partition("@")
            assert separator and action and ref, (
                f"{workflow_path.name} has invalid Action reference {reference!r}"
            )
            assert action in EXPECTED_ACTION_PINS, (
                f"{workflow_path.name} introduces unreviewed action {action}"
            )
            assert COMMIT_SHA_PATTERN.fullmatch(ref), (
                f"{workflow_path.name} uses mutable action ref {action}@{ref}"
            )
            expected_ref, expected_version = EXPECTED_ACTION_PINS[action]
            assert ref == expected_ref, (
                f"{workflow_path.name} changed the reviewed commit for {action}"
            )
            assert version == expected_version, (
                f"{workflow_path.name} must identify "
                f"{action}@{ref} as {expected_version}"
            )
            observed_actions.add(action)

    assert observed_actions == set(EXPECTED_ACTION_PINS)


@pytest.mark.parametrize("uses_key", ["uses :", '"uses":'])
def test_yaml_parser_finds_equivalent_uses_key_spellings(
    tmp_path: Path,
    uses_key: str,
) -> None:
    workflow_path = tmp_path / "syntax.yaml"
    workflow_path.write_text(
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        f"      - {uses_key} actions/checkout@main # unreviewed\n",
        encoding="utf-8",
    )

    assert _uses_references(workflow_path) == [
        ("actions/checkout@main", "unreviewed")
    ]
