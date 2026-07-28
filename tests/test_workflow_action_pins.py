from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

PINNED_WORKFLOWS = {
    "ci.yml",
    "link-check.yml",
    "pages.yml",
    "pr-safety-check.yml",
    "repo-health-summary.yml",
}

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

USES_PATTERN = re.compile(
    r"^\s*uses:\s*([^@\s]+)@([^\s#]+)(?:\s+#\s+(\S+))?\s*$",
    re.MULTILINE,
)
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def test_non_overlapping_workflows_pin_actions_to_reviewed_commits() -> None:
    observed_actions: set[str] = set()

    for workflow_name in PINNED_WORKFLOWS:
        source = (WORKFLOW_DIR / workflow_name).read_text(encoding="utf-8")
        references = USES_PATTERN.findall(source)
        assert references, f"{workflow_name} must contain at least one action"

        for action, ref, version in references:
            assert action in EXPECTED_ACTION_PINS, (
                f"{workflow_name} introduces unreviewed action {action}"
            )
            assert COMMIT_SHA_PATTERN.fullmatch(ref), (
                f"{workflow_name} uses mutable action ref {action}@{ref}"
            )
            expected_ref, expected_version = EXPECTED_ACTION_PINS[action]
            assert ref == expected_ref, (
                f"{workflow_name} changed the reviewed commit for {action}"
            )
            assert version == expected_version, (
                f"{workflow_name} must identify {action}@{ref} as {expected_version}"
            )
            observed_actions.add(action)

    assert observed_actions == set(EXPECTED_ACTION_PINS)
