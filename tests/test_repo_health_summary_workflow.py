import os
import stat
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "repo-health-summary.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _run_script() -> str:
    document = _workflow()
    steps = document["jobs"]["summary"]["steps"]
    return next(
        step["run"]
        for step in steps
        if step.get("name") == "Gather and post health summary"
    )


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _fake_commands(tmp_path: Path) -> tuple[Path, Path]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    captured_body = tmp_path / "captured-body.md"

    _write_executable(
        fake_bin / "gh",
        """#!/usr/bin/env python3
import json
import os
import shutil
import sys

args = sys.argv[1:]
failure = os.environ.get("FAKE_GH_FAILURE")
if failure and " ".join(args).startswith(failure):
    print('[{"number": 1}]')
    print("simulated GitHub CLI failure", file=sys.stderr)
    raise SystemExit(23)
invalid_response = os.environ.get("FAKE_GH_INVALID_RESPONSE")
if invalid_response and " ".join(args).startswith(invalid_response):
    print('{"not": "an array"}')
    raise SystemExit(0)

if args[:2] == ["issue", "comment"]:
    source = args[args.index("--body-file") + 1]
    shutil.copyfile(source, os.environ["CAPTURED_BODY"])
    raise SystemExit(0)

if args[:2] == ["run", "list"]:
    expression = args[args.index("--jq") + 1]
    if "failure" in expression:
        print("2")
    else:
        print("success")
        print("failure")
        print("success")
        print("failure")
        print("success")
    raise SystemExit(0)

if len(args) < 2 or args[1] != "list":
    print(f"unsupported gh invocation: {args}", file=sys.stderr)
    raise SystemExit(64)

limit = int(args[args.index("--limit") + 1])
fields = args[args.index("--json") + 1].split(",")
state = args[args.index("--state") + 1]

if args[0] == "pr" and state == "open":
    total = int(os.environ.get("FAKE_OPEN_PRS", "45"))
elif args[0] == "issue" and state == "open":
    total = int(os.environ.get("FAKE_OPEN_ISSUES", "67"))
elif args[0] == "pr" and state == "closed":
    total = int(os.environ.get("FAKE_CLOSED_PRS", "41"))
elif args[0] == "pr" and state == "all":
    total = int(os.environ.get("FAKE_ALL_PRS", "83"))
elif args[0] == "issue" and state == "all":
    total = int(os.environ.get("FAKE_ALL_ISSUES", "91"))
else:
    print(f"unsupported gh list invocation: {args}", file=sys.stderr)
    raise SystemExit(64)

records = []
for number in range(1, min(total, limit) + 1):
    record = {}
    for field in fields:
        if field == "number":
            record[field] = number
        elif field == "author":
            dependabot_total = int(os.environ.get("FAKE_DEPENDABOT_PRS", "34"))
            if args[0] == "pr" and state == "open" and number <= dependabot_total:
                login = "dependabot[bot]"
            else:
                login = "alice" if number % 3 else "bob"
            record[field] = {"login": login}
        elif field in {"createdAt", "closedAt"}:
            record[field] = "9999-01-01T00:00:00Z"
        else:
            print(f"unsupported field: {field}", file=sys.stderr)
            raise SystemExit(64)
    records.append(record)
print(json.dumps(records))
""",
    )

    _write_executable(
        fake_bin / "git",
        """#!/usr/bin/env python3
import os
import sys

args = sys.argv[1:]
if args[:2] == ["log", "-1"]:
    print("abcdef0 fixture commit")
elif args[:2] == ["ls-remote", "--heads"]:
    if os.environ.get("FAKE_GIT_LS_REMOTE_FAILURE"):
        print("0000000000000000000000000000000000000001\\trefs/heads/partial")
        print("simulated git failure", file=sys.stderr)
        raise SystemExit(29)
    for number in range(1, 206):
        prefix = "chore/maintenance-" if number <= 25 else "feature/"
        print(f"{number:040x}\\trefs/heads/{prefix}{number}")
else:
    print(f"unsupported git invocation: {args}", file=sys.stderr)
    raise SystemExit(64)
""",
    )
    return fake_bin, captured_body


def _run_health_summary(
    tmp_path: Path,
    *,
    extra_env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    fake_bin, captured_body = _fake_commands(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "CAPTURED_BODY": str(captured_body),
        "GITHUB_ACTOR": "fixture-actor",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
    }
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        ["bash", "-c", _run_script()],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return result, captured_body


def test_workflow_preserves_permissions_and_documents_fail_closed_ceiling() -> None:
    document = _workflow()
    script = _run_script()

    assert document["permissions"] == {"contents": "read", "issues": "write"}
    assert "GH_LIST_COUNT_CEILING=10000" in script
    assert "GH_LIST_FETCH_LIMIT=$((GH_LIST_COUNT_CEILING + 1))" in script
    assert "fetch_gh_list pr number,author --state open" in script
    assert "fetch_gh_list issue number --state open" in script
    assert "fetch_gh_list pr closedAt --state closed" in script
    assert "fetch_gh_list pr createdAt,author --state all" in script
    assert "fetch_gh_list issue createdAt --state all" in script
    assert 'select(.author.login == "dependabot[bot]")' in script
    assert "gh pr list" not in script
    assert "gh issue list" not in script
    assert 'if [ "$PRS" -gt 10 ]; then' in script
    assert 'if [ "$FAILURES" -gt 3 ]; then' in script
    assert 'if [ "$BRANCHES" -gt 200 ]; then' in script
    assert 'if [ "$BOT_BRANCHES" -gt 20 ]; then' in script
    assert (
        'if [ "$PRS_OPENED_WEEK" -gt 5 ] '
        '&& [ "$PRS_CLOSED_WEEK" -gt "$((PRS_OPENED_WEEK * 8 / 10))" ]; then'
        in script
    )
    assert 'if [ "$ISSUES_OPENED_WEEK" -gt 20 ]; then' in script
    assert 'if [ "$DEPENDABOT_PRS" -gt 10 ]; then' in script


def test_counts_above_thirty_are_not_truncated(tmp_path: Path) -> None:
    result, captured_body = _run_health_summary(tmp_path)

    assert result.returncode == 0, result.stderr
    body = captured_body.read_text(encoding="utf-8")
    assert "| Open PRs | 45 |" in body
    assert "| Open Issues | 67 |" in body
    assert "| PRs opened (7d) | 83 |" in body
    assert "| PRs closed (7d) | 41 |" in body
    assert "| Issues opened (7d) | 91 |" in body
    assert "| Dependabot open PRs | 34 |" in body
    assert "High open PRs (45)" in body
    assert "Issue burst (91 new issues this week)" in body
    assert "Dependabot storm (34 open PRs)" in body


def test_github_cli_failure_cannot_publish_a_plausible_zero(tmp_path: Path) -> None:
    result, captured_body = _run_health_summary(
        tmp_path,
        extra_env={"FAKE_GH_FAILURE": "issue list"},
    )

    assert result.returncode != 0
    assert not captured_body.exists()
    assert "Failed to fetch GitHub issue list" in result.stderr


def test_count_above_ceiling_fails_without_partial_summary(tmp_path: Path) -> None:
    result, captured_body = _run_health_summary(
        tmp_path,
        extra_env={"FAKE_OPEN_ISSUES": "10001"},
    )

    assert result.returncode != 0
    assert not captured_body.exists()
    assert "exceeds the 10000-item audit ceiling" in result.stderr


def test_invalid_github_response_cannot_publish_a_count(tmp_path: Path) -> None:
    result, captured_body = _run_health_summary(
        tmp_path,
        extra_env={"FAKE_GH_INVALID_RESPONSE": "pr list"},
    )

    assert result.returncode != 0
    assert not captured_body.exists()
    assert "GitHub pr list returned invalid JSON" in result.stderr


def test_partial_remote_branch_fetch_cannot_publish_a_count(tmp_path: Path) -> None:
    result, captured_body = _run_health_summary(
        tmp_path,
        extra_env={"FAKE_GIT_LS_REMOTE_FAILURE": "1"},
    )

    assert result.returncode != 0
    assert not captured_body.exists()
    assert "Failed to fetch remote branch refs" in result.stderr
