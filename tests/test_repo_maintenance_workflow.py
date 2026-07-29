import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repo_maintenance_bot.yml"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _step(text: str, name: str) -> str:
    start = text.index(f"      - name: {name}")
    end = text.find("\n      - name:", start + 1)
    return text[start:] if end == -1 else text[start:end]


def test_maintenance_workflow_is_schedule_only_and_read_only_by_default():
    text = _workflow_text()

    assert "workflow_dispatch:" not in text
    assert re.search(r"^permissions:\n  contents: read$", text, re.MULTILINE)
    assert "\n  contents: write\n" not in text
    assert "\n  pull-requests: write\n" not in text
    assert "\n  issues: write\n" not in text
    assert "protected Environment" in text
    assert "required reviewers" in text
    assert "trusted default" in text


def test_maintenance_workflow_checks_out_only_trusted_main_without_credentials():
    text = _workflow_text()
    checkout = _step(text, "Checkout trusted default branch")

    assert (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
        in checkout
    )
    assert "ref: main" in checkout
    assert "persist-credentials: false" in checkout
    assert "token:" not in checkout
    assert 'git rev-parse HEAD)" != "$(git rev-parse origin/main)' in text
    assert "GITHUB_SHA" not in text
    assert "SCRIPT_SHA" not in text
    assert "git show" not in text


def test_maintenance_workflow_creates_write_token_only_after_local_checks():
    text = _workflow_text()
    run_bot = text.index("      - name: Run maintenance bot")
    guard = text.index("      - name: Kernel guard")
    commit = text.index("      - name: Commit changes if any")
    create_token = text.index("      - name: Create short-lived GitHub App token")
    push = text.index("      - name: Push maintenance branch")

    assert run_bot < guard < commit < create_token < push
    assert "secrets." not in text[:create_token]
    assert text.count("${{ secrets.GH_APP_ID }}") == 1
    assert text.count("${{ secrets.GH_APP_PRIVATE_KEY }}") == 1
    assert text.count("${{ steps.app-token.outputs.token }}") == 1
    assert "${{ steps.app-token.outputs.token }}" not in text[:push]

    token_step = _step(text, "Create short-lived GitHub App token")
    assert "if: steps.commit.outputs.NO_CHANGES == 'false'" in token_step
    assert "permission-contents: write" in token_step

    push_step = _step(text, "Push maintenance branch with ephemeral App token")
    assert "GH_APP_TOKEN: ${{ steps.app-token.outputs.token }}" in push_step
    assert "GIT_CONFIG_VALUE_0" in push_step
    assert 'git push origin "HEAD:refs/heads/${{ steps.vars.outputs.BRANCH }}"' in push_step

    assert "GH_TOKEN" not in text
    assert "gh pr create" not in text
    assert "pr_pro.py" not in text


def test_maintenance_workflow_actions_are_pinned_to_full_commit_shas():
    text = _workflow_text()
    actions = re.findall(
        r"^\s+uses:\s+([^@\s]+)@([^\s]+)",
        text,
        re.MULTILINE,
    )

    assert actions
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for _, ref in actions)
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in text
    assert (
        "actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1"
        in text
    )
