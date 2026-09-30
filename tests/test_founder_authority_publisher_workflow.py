from __future__ import annotations

import pathlib

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "founder-authority-guard.yml"


def workflow_jobs() -> dict[str, object]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    jobs = document.get("jobs")
    assert isinstance(jobs, dict)
    return jobs


def test_required_legacy_job_remains_isolated_and_unchanged() -> None:
    jobs = workflow_jobs()
    legacy = jobs["founder-authority"]
    assert isinstance(legacy, dict)
    assert legacy["name"] == "founder-authority-bootstrap"
    assert "continue-on-error" not in legacy
    assert "needs" not in legacy

    steps = legacy["steps"]
    assert isinstance(steps, list)
    assert [step["name"] for step in steps] == [
        "Checkout trusted base policy",
        "Validate exact pull-request head from trusted base",
    ]
    validation = steps[1]
    assert validation["env"] == {
        "GITHUB_TOKEN": "${{ github.token }}",
        "PYTHONPATH": ".",
    }
    assert validation["run"] == (
        "python .github/scripts/founder_authority_workflow.py"
    )


def test_app_canary_is_separate_tolerated_pinned_and_least_privilege() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    jobs = workflow_jobs()
    canary = jobs["founder-authority-app-canary"]
    assert isinstance(canary, dict)
    assert canary["name"] == "founder-authority-app-canary"
    assert canary["continue-on-error"] is True
    assert canary["permissions"] == {"contents": "read"}
    assert "needs" not in canary

    steps = canary["steps"]
    assert isinstance(steps, list)
    checkout = steps[0]
    assert checkout["name"] == "Checkout trusted base policy"
    assert checkout["with"] == {
        "ref": "${{ github.event.pull_request.base.sha }}",
        "fetch-depth": 1,
        "persist-credentials": False,
    }

    assert (
        "actions/create-github-app-token@"
        "bcd2ba49218906704ab6c1aa796996da409d3eb1 # v3.2.0"
    ) in text
    assert "client-id: ${{ vars.FOUNDER_AUTHORITY_APP_CLIENT_ID }}" in text
    assert "private-key: ${{ secrets.FOUNDER_AUTHORITY_APP_PRIVATE_KEY }}" in text
    assert "permission-checks: write" in text
    assert "permission-contents: read" in text
    assert "permission-issues: read" in text
    assert "permission-pull-requests: read" in text
    assert "permission-contents: write" not in text
    assert "permission-issues: write" not in text
    assert "permission-pull-requests: write" not in text
    assert "owner: ${{" not in text
    assert "repositories: ${{" not in text


def test_app_canary_pins_expected_identity_and_installation() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert (
        "FOUNDER_AUTHORITY_EXPECTED_APP_ID: "
        "${{ vars.FOUNDER_AUTHORITY_APP_ID }}"
    ) in text
    assert (
        "FOUNDER_AUTHORITY_EXPECTED_APP_SLUG: "
        "${{ vars.FOUNDER_AUTHORITY_APP_SLUG }}"
    ) in text
    assert (
        "EXPECTED_INSTALLATION_ID: "
        "${{ vars.FOUNDER_AUTHORITY_APP_INSTALLATION_ID }}"
    ) in text
    assert (
        "ACTUAL_APP_SLUG: "
        "${{ steps.founder-authority-app-token.outputs.app-slug }}"
    ) in text
    assert text.count("python .github/scripts/founder_authority_workflow.py") == 2
