import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repo_maintenance_bot.yml"
DRIFT_CHECK = ROOT / "tools" / "check_maintenance_drift.py"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _step(text: str, name: str) -> str:
    start = text.index(f"      - name: {name}")
    end = text.find("\n      - name:", start + 1)
    return text[start:] if end == -1 else text[start:end]


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _fixture_repository(tmp_path: Path, bot_source: str) -> Path:
    repository = tmp_path / "repository"
    tools = repository / "tools"
    tools.mkdir(parents=True)
    shutil.copyfile(DRIFT_CHECK, tools / DRIFT_CHECK.name)
    (tools / "maintenance_bot.py").write_text(bot_source, encoding="utf-8")
    (repository / "README.md").write_text("# Fixture\n", encoding="utf-8")

    _git(repository, "init", "-b", "main")
    _git(repository, "add", ".")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Maintenance Test",
            "-c",
            "user.email=maintenance-test@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return repository


def _run_check(repository: Path, summary: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repository / "tools" / DRIFT_CHECK.name),
            "--mode",
            "full",
        ],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary)},
    )


def test_maintenance_workflow_is_schedule_only_and_read_only():
    text = _workflow_text()

    assert "workflow_dispatch:" not in text
    assert 'cron: "15 6 * * 1"' in text
    assert re.search(r"^permissions:\n  contents: read$", text, re.MULTILINE)
    assert "\n  contents: write\n" not in text
    assert "\n  pull-requests: write\n" not in text
    assert "\n  issues: write\n" not in text
    assert "timeout-minutes: 10" in text


def test_maintenance_workflow_verifies_only_trusted_clean_main():
    text = _workflow_text()
    checkout = _step(text, "Checkout trusted default branch")
    verify = _step(text, "Verify trusted main checkout")

    assert (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
        in checkout
    )
    assert "ref: main" in checkout
    assert "fetch-depth: 1" in checkout
    assert "persist-credentials: false" in checkout
    assert "token:" not in checkout

    assert "set -euo pipefail" in verify
    assert '"${GITHUB_REF}" != "refs/heads/main"' in verify
    assert '"${checked_out}" != "${GITHUB_SHA}"' in verify
    assert 'git rev-parse origin/main' in verify
    assert "git diff --quiet" in verify
    assert "git diff --cached --quiet" in verify
    assert "git ls-files --others --exclude-standard" in verify


def test_maintenance_workflow_has_no_token_commit_push_or_branch_path():
    text = _workflow_text()
    lower = text.lower()
    forbidden = (
        "actions/create-github-app-token",
        "secrets.",
        "gh_app",
        "github_run_number",
        "git checkout -b",
        "git commit",
        "git push",
        "gh pr",
        "pr_pro.py",
        "permission-contents: write",
    )
    assert all(value not in lower for value in forbidden)

    checkout = text.index("      - name: Checkout trusted default branch")
    verify = text.index("      - name: Verify trusted main checkout")
    setup = text.index("      - name: Setup Python")
    drift = text.index("      - name: Check maintenance drift without writes")
    assert checkout < verify < setup < drift
    assert "python tools/check_maintenance_drift.py --mode full" in text

    checker = DRIFT_CHECK.read_text(encoding="utf-8")
    assert '["git", "archive", "--format=tar", "HEAD"]' in checker
    assert 'TemporaryDirectory(prefix="hub-optimus-maintenance-")' in checker
    assert 'baseline_root = temporary_root / "baseline"' in checker
    assert 'candidate_root = temporary_root / "candidate"' in checker
    assert "GITHUB_STEP_SUMMARY" in checker
    assert "git push" not in checker
    assert "github" not in checker.lower().replace("github_step_summary", "")


def test_maintenance_workflow_actions_are_pinned_to_full_commit_shas():
    text = _workflow_text()
    actions = re.findall(
        r"^\s+uses:\s+([^@\s]+)@([^\s]+)",
        text,
        re.MULTILINE,
    )

    assert actions == [
        (
            "actions/checkout",
            "3d3c42e5aac5ba805825da76410c181273ba90b1",
        ),
        (
            "actions/setup-python",
            "5fda3b95a4ea91299a34e894583c3862153e4b97",
        ),
    ]
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for _, ref in actions)


def test_read_only_drift_check_reports_clean_without_touching_checkout(tmp_path):
    repository = _fixture_repository(
        tmp_path,
        'print("maintenance helper completed")\n',
    )
    summary = tmp_path / "summary.md"
    before = _git(repository, "status", "--porcelain=v1", "--untracked-files=all")

    result = _run_check(repository, summary)

    assert result.returncode == 0, result.stderr
    assert before == ""
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == before
    report = summary.read_text(encoding="utf-8")
    assert "Status: **clean**" in report
    assert "No repository files, commits, or refs were modified." in report
    assert "maintenance helper completed" in report


def test_read_only_drift_check_fails_with_actionable_added_path(tmp_path):
    repository = _fixture_repository(
        tmp_path,
        (
            "from pathlib import Path\n"
            'Path("generated.md").write_text("drift\\n", encoding="utf-8")\n'
            'print("proposed generated.md")\n'
        ),
    )
    summary = tmp_path / "summary.md"

    result = _run_check(repository, summary)

    assert result.returncode == 1, result.stderr
    assert not (repository / "generated.md").exists()
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""
    report = summary.read_text(encoding="utf-8")
    assert "Status: **drift detected**" in report
    assert "proposed 1 changed path(s)" in report
    assert "| `A` | `generated.md` |" in report
    assert "proposed generated.md" in report


def test_read_only_drift_check_fails_closed_on_helper_error(tmp_path):
    repository = _fixture_repository(
        tmp_path,
        'print("helper failed")\nraise SystemExit(7)\n',
    )
    summary = tmp_path / "summary.md"

    result = _run_check(repository, summary)

    assert result.returncode == 2
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""
    report = summary.read_text(encoding="utf-8")
    assert "Status: **error**" in report
    assert "exited 7" in report
    assert "stopped fail-closed" in report
    assert "helper failed" in report


def test_read_only_drift_check_fails_closed_on_dirty_source(tmp_path):
    repository = _fixture_repository(
        tmp_path,
        'print("must not run")\n',
    )
    (repository / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    summary = tmp_path / "summary.md"

    result = _run_check(repository, summary)

    assert result.returncode == 2
    report = summary.read_text(encoding="utf-8")
    assert "Status: **error**" in report
    assert "source checkout is not clean" in report
    assert "must not run" not in report
