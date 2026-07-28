from __future__ import annotations

import subprocess
from collections.abc import Callable

import pytest

from tools import pr_pro


CommandFake = Callable[[list[str]], subprocess.CompletedProcess[str]]


def _result(
    args: list[str],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


@pytest.fixture(autouse=True)
def _clean_pr_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "PR_NUMBER",
        "GITHUB_HEAD_REF",
        "BRANCH_NAME",
        "MODE",
        "ALLOW_KERNEL",
    ):
        monkeypatch.delenv(name, raising=False)


def _existing_labels_or_success(
    calls: list[list[str]],
    *,
    edit_result: subprocess.CompletedProcess[str] | None = None,
    comment_result: subprocess.CompletedProcess[str] | None = None,
) -> CommandFake:
    def fake(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[:3] == ["gh", "pr", "view"]:
            return _result(cmd, stdout=f"{cmd[3]}\n")
        if cmd[:3] == ["git", "diff", "--name-only"]:
            return _result(cmd, stdout="docs/governance/policy.md\nnotes.md\n")
        if cmd[:3] == ["gh", "label", "list"]:
            for name in ("maintenance", "kernel-change", "i18n"):
                if f'"{name}"' in cmd[-1]:
                    return _result(cmd, stdout=f"{name}\n")
        if cmd[:3] == ["gh", "pr", "edit"]:
            return edit_result or _result(cmd)
        if cmd[:3] == ["gh", "pr", "comment"]:
            return comment_result or _result(cmd)
        raise AssertionError(f"unexpected command: {cmd}")

    return fake


def test_missing_gh_is_explicit_and_runs_no_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: None)

    def unexpected(_cmd: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("no external command should run when gh is missing")

    monkeypatch.setattr(pr_pro, "run_command", unexpected)

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == (
        "[pr-pro-error] GitHub CLI 'gh' is required for write mode"
    )


def test_missing_target_fails_before_any_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")

    def unexpected(_cmd: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("target validation must precede external commands")

    monkeypatch.setattr(pr_pro, "run_command", unexpected)

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert "PR_NUMBER or GITHUB_HEAD_REF/BRANCH_NAME is required" in captured.err
    assert "pr_pro done" not in captured.out


def test_dry_run_never_invokes_gh(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setenv("MODE", "i18n")
    calls: list[list[str]] = []

    def fake(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        assert cmd[0] == "git"
        return _result(cmd, stdout="docs/es/00_start_here.md\n")

    monkeypatch.setattr(pr_pro, "run_command", fake)
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: None)

    assert pr_pro.main(["--dry-run"]) == 0
    captured = capsys.readouterr()
    assert calls == [["git", "diff", "--name-only", "origin/main...HEAD"]]
    assert "[dry-run] target: PR #42" in captured.out
    assert "[dry-run] add labels: maintenance, i18n" in captured.out
    assert "no GitHub commands executed" in captured.out
    assert "pr_pro done" not in captured.out


def test_failed_label_listing_stops_without_mutation_or_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []

    def fake(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[:3] == ["gh", "pr", "view"]:
            return _result(cmd, stdout="42\n")
        if cmd[0] == "git":
            return _result(cmd, stdout="README.md\n")
        if cmd[:3] == ["gh", "label", "list"]:
            return _result(cmd, 1, stderr="API unavailable")
        raise AssertionError(f"unexpected command after label-list failure: {cmd}")

    monkeypatch.setattr(pr_pro, "run_command", fake)

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert "list label 'maintenance' failed (1): API unavailable" in captured.err
    assert not any(cmd[:3] == ["gh", "label", "create"] for cmd in calls)
    assert not any(cmd[:3] == ["gh", "pr", "edit"] for cmd in calls)
    assert "pr_pro done" not in captured.out


def test_failed_label_creation_stops_with_nonzero_status(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []

    def fake(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[:3] == ["gh", "pr", "view"]:
            return _result(cmd, stdout="42\n")
        if cmd[0] == "git":
            return _result(cmd, stdout="README.md\n")
        if cmd[:3] == ["gh", "label", "list"]:
            return _result(cmd)
        if cmd[:3] == ["gh", "label", "create"]:
            return _result(cmd, 1, stderr="permission denied")
        raise AssertionError(f"unexpected command after label-create failure: {cmd}")

    monkeypatch.setattr(pr_pro, "run_command", fake)

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert "create label 'maintenance' failed (1): permission denied" in captured.err
    assert "pr_pro done" not in captured.out


def test_failed_pr_edit_prevents_comment_and_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []
    edit_failure = _result(
        ["gh", "pr", "edit"],
        1,
        stderr="GraphQL mutation failed",
    )
    monkeypatch.setattr(
        pr_pro,
        "run_command",
        _existing_labels_or_success(calls, edit_result=edit_failure),
    )

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert "add labels to PR #42 failed (1): GraphQL mutation failed" in captured.err
    assert not any(cmd[:3] == ["gh", "pr", "comment"] for cmd in calls)
    assert "pr_pro done" not in captured.out


def test_failed_pr_comment_returns_nonzero_without_success_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []
    comment_failure = _result(
        ["gh", "pr", "comment"],
        1,
        stderr="comment rejected",
    )
    monkeypatch.setattr(
        pr_pro,
        "run_command",
        _existing_labels_or_success(calls, comment_result=comment_failure),
    )

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert "comment on PR #42 failed (1): comment rejected" in captured.err
    assert "pr_pro done" not in captured.out


def test_git_diff_failure_is_controlled_without_weaker_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PR_NUMBER", "42")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []

    def fake(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        if cmd[:3] == ["gh", "pr", "view"]:
            return _result(cmd, stdout="42\n")
        if cmd == ["git", "diff", "--name-only", "origin/main...HEAD"]:
            return _result(cmd, 128, stderr="unknown revision")
        raise AssertionError(f"unexpected GitHub mutation after diff failure: {cmd}")

    monkeypatch.setattr(pr_pro, "run_command", fake)

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert "read changed files against origin/main failed" in captured.err
    assert calls == [
        ["gh", "pr", "view", "42", "--json", "number", "--jq", ".number"],
        ["git", "diff", "--name-only", "origin/main...HEAD"],
    ]
    assert "pr_pro done" not in captured.out


def test_numeric_pr_is_validated_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PR_NUMBER", "404")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []

    def fake(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        assert cmd[:3] == ["gh", "pr", "view"]
        return _result(cmd, 1, stderr="no pull requests found")

    monkeypatch.setattr(pr_pro, "run_command", fake)

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert "validate PR #404 failed (1): no pull requests found" in captured.err
    assert len(calls) == 1
    assert "pr_pro done" not in captured.out


def test_branch_is_resolved_before_supported_write_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("BRANCH_NAME", "chore/maintenance-7")
    monkeypatch.setenv("MODE", "full")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []

    base_fake = _existing_labels_or_success(calls)

    def fake(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        if cmd[:3] == ["gh", "pr", "view"]:
            calls.append(cmd)
            return _result(cmd, stdout="73\n")
        return base_fake(cmd)

    monkeypatch.setattr(pr_pro, "run_command", fake)

    assert pr_pro.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "pr_pro done"
    assert calls[0] == [
        "gh",
        "pr",
        "view",
        "chore/maintenance-7",
        "--json",
        "number",
        "--jq",
        ".number",
    ]
    edit = next(cmd for cmd in calls if cmd[:3] == ["gh", "pr", "edit"])
    assert edit[3:6] == ["73", "--add-label", "maintenance,i18n,kernel-change"]


def test_branch_resolution_failure_is_terminal(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("BRANCH_NAME", "chore/missing-pr")
    monkeypatch.setattr(pr_pro.shutil, "which", lambda _name: "/usr/bin/gh")
    calls: list[list[str]] = []

    def fake(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return _result(cmd, 1, stderr="no pull requests found")

    monkeypatch.setattr(pr_pro, "run_command", fake)

    assert pr_pro.main([]) == pr_pro.ERROR_EXIT_CODE
    captured = capsys.readouterr()
    assert "resolve PR for branch 'chore/missing-pr' failed" in captured.err
    assert len(calls) == 1
    assert calls[0][:3] == ["gh", "pr", "view"]
    assert "pr_pro done" not in captured.out


def test_external_command_oserror_becomes_controlled_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_oserror(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("missing executable")

    monkeypatch.setattr(pr_pro.subprocess, "run", raise_oserror)
    with pytest.raises(pr_pro.PrProError, match="cannot execute git"):
        pr_pro.run_command(["git", "status"])
