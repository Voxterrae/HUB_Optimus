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


def test_required_bootstrap_is_isolated_and_read_only() -> None:
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
        "python .github/scripts/founder_authority_workflow.py --validate-only"
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
        "64ab729a6294000f5aa4a4bc0b73d1f32bc45510 # v3.3.0"
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


def test_generic_workflow_token_cannot_write_check_runs() -> None:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    permissions = document["permissions"]
    assert permissions == {
        "contents": "read", "issues": "read", "pull-requests": "read"
    }
    bootstrap = document["jobs"]["founder-authority"]
    effective = bootstrap.get("permissions", permissions)
    assert effective.get("checks", "none") == "none"


def test_review_and_pull_request_events_have_independent_concurrency() -> None:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    concurrency = document["concurrency"]
    assert concurrency["cancel-in-progress"] is True
    template = concurrency["group"]

    def group(event: str, number: int) -> str:
        rendered = template.replace("${{ github.event_name }}", event)
        rendered = rendered.replace(
            "${{ github.event.pull_request.number }}", str(number)
        )
        assert "${{" not in rendered
        return rendered

    target = group("pull_request_target", 1959)
    review = group("pull_request_review", 1959)
    assert target != review
    assert target == group("pull_request_target", 1959)
    assert review == group("pull_request_review", 1959)
    assert target != group("pull_request_target", 1963)
    assert review != group("pull_request_review", 1963)
