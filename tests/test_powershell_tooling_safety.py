"""Safety contracts for mutation-capable PowerShell repository tools.

Behavior tests run only when PowerShell 7 is available. Source-level tests always
run, so the current Linux CI can enforce preview and containment contracts without
claiming that it executed PowerShell.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS = REPO_ROOT / "tools"
PWSH = shutil.which("pwsh")
MUTATING_SCRIPTS = (
    "resolve_conflict_markers.ps1",
    "fix_mojibake.ps1",
    "fix_encoding_docs.ps1",
)


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _make_test_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    (repo / "docs").mkdir()
    for name in (*MUTATING_SCRIPTS, "RepositoryPathSafety.psm1"):
        shutil.copy2(TOOLS / name, repo / "tools" / name)

    init = _run("git", "init", "-q", str(repo), cwd=tmp_path)
    assert init.returncode == 0, init.stderr
    return repo


def _commit_all(repo: Path) -> None:
    add = _run("git", "add", ".", cwd=repo)
    assert add.returncode == 0, add.stderr
    commit = _run(
        "git",
        "-c",
        "user.name=Tool Test",
        "-c",
        "user.email=tool-test@example.invalid",
        "commit",
        "-qm",
        "fixture",
        cwd=repo,
    )
    assert commit.returncode == 0, commit.stderr


@pytest.mark.parametrize("script_name", MUTATING_SCRIPTS)
def test_mutating_scripts_are_preview_first_and_repository_bound(
    script_name: str,
) -> None:
    script = (TOOLS / script_name).read_text(encoding="utf-8")

    assert "[switch]$Apply" in script
    assert "if (-not $Apply)" in script
    assert "RepositoryPathSafety.psm1" in script
    assert "Resolve-RepositoryPath" in script
    assert '"preview"' in script
    preview_guard = re.search(
        r"if \(-not \$Apply\) \{.*?\n\s+continue\n\s+\}",
        script,
        flags=re.DOTALL,
    )
    assert preview_guard is not None
    assert preview_guard.start() < script.index("WriteAllText")


def test_conflict_detection_uses_real_extended_regex_patterns() -> None:
    script = (TOOLS / "resolve_conflict_markers.ps1").read_text(encoding="utf-8")

    assert "grep -l -E" in script
    assert '-e "^<<<<<<<( .*)?$"' in script
    assert '-e "^=======$"' in script
    assert '-e "^>>>>>>>( .*)?$"' in script
    assert '"(?ms)^<<<<<<<(?: [^\\r\\n]*)?\\r?\\n"' in script
    assert '"^>>>>>>>(?: [^\\r\\n]*)?(?:\\r?\\n|$)"' in script
    assert "^<<<<<<<[^\\r\\n]*" not in script
    assert "^>>>>>>>[^\\r\\n]*" not in script
    assert "'<<<<<<<|=======|>>>>>>>'" not in script


def test_backup_contract_is_filename_only_same_directory_and_no_overwrite() -> None:
    module = (TOOLS / "RepositoryPathSafety.psm1").read_text(encoding="utf-8")

    assert "Resolve-RepositoryBackupPath" in module
    assert "Backup suffix must be a non-empty filename suffix" in module
    assert "Backup destination must remain in the source file directory" in module
    assert "Backup destination already exists" in module
    for script_name in ("fix_mojibake.ps1", "fix_encoding_docs.ps1"):
        script = (TOOLS / script_name).read_text(encoding="utf-8")
        assert "Resolve-RepositoryBackupPath" in script
        assert "[System.IO.File]::Copy($file.FullPath, $backupPath, $false)" in script
        assert "Copy-Item" not in script


def test_ci_requires_real_powershell_tooling_execution() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "powershell-tooling:" in workflow
    assert "command -v pwsh" in workflow
    assert "$PSVersionTable.PSVersion.Major -lt 7" in workflow
    assert "python -m pytest -q tests/test_powershell_tooling_safety.py" in workflow
    powershell_job = workflow.split("  powershell-tooling:", 1)[1].split(
        "\n  benchmarks:", 1
    )[0]
    assert (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
        in powershell_job
    )
    assert "# v7.0.1" in powershell_job
    assert (
        "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
        in powershell_job
    )
    assert "# v7.0.0" in powershell_job


def test_conflict_marker_patterns_detect_a_real_tracked_conflict(
    tmp_path: Path,
) -> None:
    repo = _make_test_repo(tmp_path)
    target = repo / "docs" / "conflict.md"
    target.write_text(
        "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> feature\n",
        encoding="utf-8",
    )
    add = _run("git", "add", ".", cwd=repo)
    assert add.returncode == 0, add.stderr

    detected = _run(
        "git",
        "grep",
        "-l",
        "-E",
        "-e",
        "^<<<<<<<( .*)?$",
        "-e",
        "^=======$",
        "-e",
        "^>>>>>>>( .*)?$",
        "--",
        "docs",
        cwd=repo,
    )

    assert detected.returncode == 0, detected.stderr
    assert detected.stdout.splitlines() == ["docs/conflict.md"]


def test_shared_path_guard_rejects_escape_metadata_and_links() -> None:
    module = (TOOLS / "RepositoryPathSafety.psm1").read_text(encoding="utf-8")

    assert "Path escapes repository boundary" in module
    assert "Repository metadata is not a valid rewrite target" in module
    assert "ReparsePoint" in module
    assert "git -C $root -c core.quotepath=false ls-files" in module


def test_supported_platform_status_is_explicit() -> None:
    policy = (
        REPO_ROOT / "docs" / "architecture" / "platform_compatibility.md"
    ).read_text(encoding="utf-8")

    assert "provisional manual support" in policy
    assert "require PowerShell 7 and Git" in policy
    assert "A skip is not certification" in policy
    assert "A green job certifies" in policy
    assert "covered behavior on that Ubuntu" in policy


@pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is not installed")
def test_conflict_markers_preview_then_apply_in_temp_repository(
    tmp_path: Path,
) -> None:
    repo = _make_test_repo(tmp_path)
    target = repo / "docs" / "conflict.md"
    target.write_text("# clean\n", encoding="utf-8")
    _commit_all(repo)
    conflicted = (
        "before\n"
        "<<<<<<< HEAD\n"
        "ours\n"
        "=======\n"
        "theirs\n"
        ">>>>>>> feature\n"
        "after\n"
    )
    target.write_text(conflicted, encoding="utf-8")
    script = repo / "tools" / "resolve_conflict_markers.ps1"

    preview = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(script),
        "-Path",
        "docs",
        "-Keep",
        "ours",
        cwd=repo,
    )
    assert preview.returncode == 0, preview.stderr
    assert "WOULD_RESOLVE: docs/conflict.md" in preview.stdout
    assert target.read_text(encoding="utf-8") == conflicted

    apply = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(script),
        "-Path",
        "docs",
        "-Keep",
        "ours",
        "-Apply",
        cwd=repo,
    )
    assert apply.returncode == 0, apply.stderr
    assert "FIXED: docs/conflict.md" in apply.stdout
    resolved = target.read_text(encoding="utf-8")
    assert "ours" in resolved
    assert "theirs" not in resolved
    assert "<<<<<<<" not in resolved
    assert "=======" not in resolved
    assert ">>>>>>>" not in resolved


@pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is not installed")
@pytest.mark.parametrize(
    "malformed",
    (
        (
            "before\n"
            "<<<<<<<not-a-marker\n"
            "keep me\n"
            "=======\n"
            "do not select me\n"
            ">>>>>>> feature\n"
            "after\n"
        ),
        (
            "before\n"
            "<<<<<<< HEAD\n"
            "keep me\n"
            "=======\n"
            "do not select me\n"
            ">>>>>>>not-a-marker\n"
            "after\n"
        ),
        "before\n<<<<<<< HEAD\nincomplete\n",
    ),
)
def test_conflict_apply_does_not_write_false_or_malformed_markers(
    tmp_path: Path,
    malformed: str,
) -> None:
    repo = _make_test_repo(tmp_path)
    target = repo / "docs" / "malformed.md"
    target.write_text(malformed, encoding="utf-8")
    _commit_all(repo)

    result = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(repo / "tools" / "resolve_conflict_markers.ps1"),
        "-Path",
        "docs",
        "-Keep",
        "theirs",
        "-Apply",
        cwd=repo,
    )

    assert result.returncode == 0, result.stderr
    assert "SKIP_INCOMPLETE: docs/malformed.md" in (result.stdout + result.stderr)
    assert "FIXED:" not in result.stdout
    assert target.read_text(encoding="utf-8") == malformed


@pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is not installed")
@pytest.mark.parametrize(
    "script_name",
    ("fix_mojibake.ps1", "fix_encoding_docs.ps1"),
)
def test_encoding_tools_preview_then_apply_in_temp_repository(
    tmp_path: Path,
    script_name: str,
) -> None:
    repo = _make_test_repo(tmp_path)
    target = repo / "docs" / "mojibake.md"
    broken = "cafÃ©\n"
    target.write_text(broken, encoding="utf-8")
    _commit_all(repo)
    script = repo / "tools" / script_name

    preview = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(script),
        "-Path",
        "docs",
        cwd=repo,
    )
    assert preview.returncode == 0, preview.stderr
    assert "WOULD_FIX: docs/mojibake.md" in preview.stdout
    assert target.read_text(encoding="utf-8") == broken

    apply = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(script),
        "-Path",
        "docs",
        "-Apply",
        "-Backup",
        cwd=repo,
    )
    assert apply.returncode == 0, apply.stderr
    assert "FIXED: docs/mojibake.md" in apply.stdout
    assert target.read_text(encoding="utf-8") == "café\n"
    assert (repo / "docs" / "mojibake.md.bak").read_text(encoding="utf-8") == broken


@pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is not installed")
@pytest.mark.parametrize(
    "script_name",
    ("fix_mojibake.ps1", "fix_encoding_docs.ps1"),
)
def test_backup_suffix_cannot_escape_the_source_directory(
    tmp_path: Path,
    script_name: str,
) -> None:
    repo = _make_test_repo(tmp_path)
    target = repo / "docs" / "mojibake.md"
    broken = "cafÃ©\n"
    target.write_text(broken, encoding="utf-8")
    protected = repo / "KERNEL_CHARTER.md"
    protected.write_text("protected\n", encoding="utf-8")
    _commit_all(repo)

    result = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(repo / "tools" / script_name),
        "-Path",
        "docs",
        "-Apply",
        "-Backup",
        "-BackupSuffix",
        "/../../KERNEL_CHARTER.md",
        cwd=repo,
    )

    assert result.returncode != 0
    assert "must not contain path separators" in (result.stdout + result.stderr)
    assert target.read_text(encoding="utf-8") == broken
    assert protected.read_text(encoding="utf-8") == "protected\n"


@pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is not installed")
@pytest.mark.parametrize(
    "script_name",
    ("fix_mojibake.ps1", "fix_encoding_docs.ps1"),
)
def test_existing_backup_is_rejected_without_overwrite(
    tmp_path: Path,
    script_name: str,
) -> None:
    repo = _make_test_repo(tmp_path)
    target = repo / "docs" / "mojibake.md"
    broken = "cafÃ©\n"
    target.write_text(broken, encoding="utf-8")
    _commit_all(repo)
    backup = repo / "docs" / "mojibake.md.bak"
    backup.write_text("existing backup\n", encoding="utf-8")

    result = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(repo / "tools" / script_name),
        "-Path",
        "docs",
        "-Apply",
        "-Backup",
        cwd=repo,
    )

    assert result.returncode != 0
    assert "Backup destination already exists" in (result.stdout + result.stderr)
    assert target.read_text(encoding="utf-8") == broken
    assert backup.read_text(encoding="utf-8") == "existing backup\n"


@pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is not installed")
def test_rewrite_rejects_an_outside_repository_path(tmp_path: Path) -> None:
    repo = _make_test_repo(tmp_path)
    tracked = repo / "docs" / "safe.md"
    tracked.write_text("# safe\n", encoding="utf-8")
    _commit_all(repo)
    outside = tmp_path / "outside.md"
    broken = "cafÃ©\n"
    outside.write_text(broken, encoding="utf-8")

    result = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(repo / "tools" / "fix_mojibake.ps1"),
        "-Path",
        str(outside),
        "-Apply",
        cwd=repo,
    )

    assert result.returncode != 0
    assert "escapes repository boundary" in (result.stdout + result.stderr)
    assert outside.read_text(encoding="utf-8") == broken


@pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is not installed")
def test_rewrite_rejects_a_symlink_to_outside_repository(tmp_path: Path) -> None:
    repo = _make_test_repo(tmp_path)
    outside = tmp_path / "outside.md"
    broken = "cafÃ©\n"
    outside.write_text(broken, encoding="utf-8")
    link = repo / "docs" / "linked.md"
    try:
        os.symlink(outside, link)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    _commit_all(repo)

    result = _run(
        PWSH,
        "-NoProfile",
        "-File",
        str(repo / "tools" / "fix_mojibake.ps1"),
        "-Path",
        "docs/linked.md",
        "-Apply",
        cwd=repo,
    )

    assert result.returncode != 0
    assert "Symbolic links and reparse points" in (result.stdout + result.stderr)
    assert outside.read_text(encoding="utf-8") == broken
