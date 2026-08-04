from __future__ import annotations

import json
import os
import stat
import subprocess
import zlib
from dataclasses import dataclass
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "ops" / "ec2" / "verify-release-worktree.py"
PYTHON = Path("/usr/bin/python3")
GIT = Path("/usr/bin/git")


@dataclass(frozen=True)
class Verification:
    returncode: int
    stdout: str
    stderr: str


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [str(GIT), "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _git_object_payload(repository: Path, object_type: str, object_id: str) -> bytes:
    completed = subprocess.run(
        [str(GIT), "-C", str(repository), "cat-file", object_type, object_id],
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    return completed.stdout


def _replace_loose_object(
    repository: Path,
    object_id: str,
    object_type: str,
    payload: bytes,
) -> None:
    object_path = repository / ".git" / "objects" / object_id[:2] / object_id[2:]
    assert object_path.is_file(), f"expected one loose test object at {object_path}"
    canonical = (
        object_type.encode("ascii")
        + b" "
        + str(len(payload)).encode("ascii")
        + b"\0"
        + payload
    )
    object_path.write_bytes(zlib.compress(canonical))


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "release"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "Release Verifier Test")
    _git(repository, "config", "user.email", "release-verifier@example.invalid")
    (repository / ".gitignore").write_bytes(b"ignored/\n")
    (repository / "README.md").write_bytes(b"reviewed source\n")
    executable_directory = repository / "bin"
    executable_directory.mkdir()
    executable = executable_directory / "tool.sh"
    executable.write_bytes(b"#!/usr/bin/env bash\nprintf 'reviewed\\n'\n")
    executable.chmod(0o755)
    _git(repository, "add", "--all")
    _git(repository, "commit", "--quiet", "-m", "reviewed source")
    return repository, _git(repository, "rev-parse", "HEAD")


def _verify(
    repository: Path,
    commit: str,
    *arguments: str,
    env: dict[str, str] | None = None,
) -> Verification:
    completed = subprocess.run(
        [
            str(PYTHON),
            "-I",
            str(VERIFIER),
            str(repository),
            commit,
            *arguments,
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return Verification(
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


def test_exact_tree_emits_one_deterministic_canonical_identity(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)

    first = _verify(repository, commit)
    second = _verify(repository, "HEAD")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
    assert first.stderr == second.stderr == ""
    identity = json.loads(first.stdout)
    assert identity == {
        "commit": commit,
        "source_file_count": 3,
        "source_tree_sha256": identity["source_tree_sha256"],
    }
    assert len(identity["source_tree_sha256"]) == 64
    assert first.stdout == (
        json.dumps(identity, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    )


def test_git_metadata_and_explicit_generated_roots_do_not_change_source_identity(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)
    before = _verify(repository, commit)
    assert before.returncode == 0, before.stderr

    (repository / ".git" / "local-verifier-sentinel").write_bytes(b"metadata\n")
    venv_bin = repository / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python3").symlink_to("/usr/bin/python3")
    deployment = repository / ".hub-deployment"
    deployment.mkdir(mode=0o700)
    (deployment / "validation.log").write_bytes(b"3 passed\n")

    after = _verify(
        repository,
        commit,
        "--allow-generated",
        ".venv",
        "--allow-generated",
        ".hub-deployment",
    )

    assert after.returncode == 0, after.stderr
    assert after.stdout == before.stdout
    assert after.stderr == ""


@pytest.mark.parametrize("generated", (".venv", ".hub-deployment"))
def test_generated_root_requires_its_literal_allowlist_flag(
    tmp_path: Path,
    generated: str,
) -> None:
    repository, commit = _repository(tmp_path)
    (repository / generated).mkdir()

    result = _verify(repository, commit)

    assert result.returncode == 1
    assert "requires an explicit allowlist flag" in result.stderr
    assert generated in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("kind", ("file", "symlink", "writable-directory"))
def test_allowlisted_generated_root_must_still_be_one_safe_real_directory(
    tmp_path: Path,
    kind: str,
) -> None:
    repository, commit = _repository(tmp_path)
    generated = repository / ".venv"
    if kind == "file":
        generated.write_bytes(b"not a directory\n")
    elif kind == "symlink":
        target = tmp_path / "external-venv"
        target.mkdir()
        generated.symlink_to(target, target_is_directory=True)
    else:
        generated.mkdir()
        generated.chmod(0o777)

    result = _verify(
        repository,
        commit,
        "--allow-generated",
        ".venv",
    )

    assert result.returncode == 1
    if kind == "writable-directory":
        assert "group- or world-writable" in result.stderr
    else:
        assert "not one real directory" in result.stderr
    assert result.stdout == ""


def test_allowlist_rejects_unknown_or_duplicate_generated_roots(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)

    unknown = _verify(
        repository,
        commit,
        "--allow-generated",
        "ignored",
    )
    duplicate = _verify(
        repository,
        commit,
        "--allow-generated",
        ".venv",
        "--allow-generated",
        ".venv",
    )

    assert unknown.returncode == 2
    assert "invalid choice" in unknown.stderr
    assert unknown.stdout == ""
    assert duplicate.returncode == 1
    assert "allowlist contains a duplicate" in duplicate.stderr
    assert duplicate.stdout == ""


@pytest.mark.parametrize("index_flag", ("--assume-unchanged", "--skip-worktree"))
def test_index_flags_cannot_hide_modified_tracked_bytes(
    tmp_path: Path,
    index_flag: str,
) -> None:
    repository, commit = _repository(tmp_path)
    _git(repository, "update-index", index_flag, "README.md")
    (repository / "README.md").write_bytes(b"hidden drift\n")

    result = _verify(repository, commit)

    assert result.returncode == 1
    assert "bytes differ from the reviewed commit" in result.stderr
    assert result.stdout == ""


def test_ambient_git_index_config_and_object_paths_are_ignored(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)
    hostile_config = tmp_path / "hostile.gitconfig"
    hostile_config.write_text("[core]\n\tbare = true\n", encoding="ascii")
    hostile_environment = os.environ.copy()
    hostile_environment.update(
        {
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(tmp_path / "alternates"),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_GLOBAL": str(hostile_config),
            "GIT_CONFIG_KEY_0": "core.repositoryformatversion",
            "GIT_CONFIG_SYSTEM": str(hostile_config),
            "GIT_CONFIG_VALUE_0": "999",
            "GIT_DIR": str(tmp_path / "other-git-dir"),
            "GIT_INDEX_FILE": str(tmp_path / "substituted-index"),
            "GIT_OBJECT_DIRECTORY": str(tmp_path / "objects"),
            "GIT_WORK_TREE": str(tmp_path / "other-worktree"),
            "HOME": str(tmp_path),
            "PATH": str(tmp_path),
        }
    )

    result = _verify(repository, commit, env=hostile_environment)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["commit"] == commit
    assert result.stderr == ""


def test_git_replace_cannot_substitute_the_reviewed_commit_tree(
    tmp_path: Path,
) -> None:
    repository, reviewed_commit = _repository(tmp_path)
    (repository / "README.md").write_bytes(b"replacement source\n")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "--quiet", "-m", "replacement source")
    replacement_commit = _git(repository, "rev-parse", "HEAD")
    _git(repository, "replace", reviewed_commit, replacement_commit)

    result = _verify(repository, reviewed_commit)

    assert result.returncode == 1
    assert "bytes differ from the reviewed commit" in result.stderr
    assert result.stdout == ""


def test_loose_blob_bytes_must_cryptographically_match_the_referenced_oid(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)
    blob_id = _git(repository, "rev-parse", f"{commit}:README.md")
    poisoned = b"same worktree bytes supplied by a corrupted loose blob\n"
    (repository / "README.md").write_bytes(poisoned)
    _replace_loose_object(repository, blob_id, "blob", poisoned)

    result = _verify(repository, commit)

    assert result.returncode == 1
    assert "object bytes do not match their cryptographic identity" in result.stderr
    assert result.stdout == ""


def test_loose_tree_bytes_must_cryptographically_match_the_commit_tree_oid(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)
    original_tree = _git(repository, "rev-parse", f"{commit}^{{tree}}")
    poisoned = b"same worktree bytes supplied by a corrupted loose tree\n"
    (repository / "README.md").write_bytes(poisoned)
    _git(repository, "add", "README.md")
    replacement_tree = _git(repository, "write-tree")
    replacement_payload = _git_object_payload(
        repository,
        "tree",
        replacement_tree,
    )
    _replace_loose_object(repository, original_tree, "tree", replacement_payload)

    result = _verify(repository, commit)

    assert result.returncode == 1
    assert "object bytes do not match their cryptographic identity" in result.stderr
    assert result.stdout == ""


def test_loose_commit_bytes_must_cryptographically_match_the_requested_oid(
    tmp_path: Path,
) -> None:
    repository, reviewed_commit = _repository(tmp_path)
    poisoned = b"same worktree bytes supplied by a corrupted loose commit\n"
    (repository / "README.md").write_bytes(poisoned)
    _git(repository, "add", "README.md")
    _git(repository, "commit", "--quiet", "-m", "unreviewed source")
    replacement_commit = _git(repository, "rev-parse", "HEAD")
    replacement_payload = _git_object_payload(
        repository,
        "commit",
        replacement_commit,
    )
    _replace_loose_object(
        repository,
        reviewed_commit,
        "commit",
        replacement_payload,
    )

    result = _verify(repository, reviewed_commit)

    assert result.returncode == 1
    assert "object bytes do not match their cryptographic identity" in result.stderr
    assert result.stdout == ""


def test_ignored_descendant_and_untracked_empty_directory_are_rejected(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)
    ignored = repository / "ignored" / "nested"
    ignored.mkdir(parents=True)
    (ignored / "payload.txt").write_bytes(b"ignored but present\n")

    ignored_result = _verify(repository, commit)
    assert ignored_result.returncode == 1
    assert "unexpected source directory" in ignored_result.stderr
    assert "ignored" in ignored_result.stderr

    for path in sorted((repository / "ignored").rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        else:
            path.rmdir()
    (repository / "ignored").rmdir()
    (repository / "empty-untracked").mkdir()

    empty_result = _verify(repository, commit)
    assert empty_result.returncode == 1
    assert "unexpected source directory" in empty_result.stderr
    assert "empty-untracked" in empty_result.stderr


def test_missing_tracked_file_is_rejected(tmp_path: Path) -> None:
    repository, commit = _repository(tmp_path)
    (repository / "README.md").unlink()

    result = _verify(repository, commit)

    assert result.returncode == 1
    assert "missing source file" in result.stderr
    assert "README.md" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("relative", "permissions"),
    (("README.md", 0o600), ("bin/tool.sh", 0o744)),
)
def test_tracked_file_mode_must_match_the_git_mode_exactly(
    tmp_path: Path,
    relative: str,
    permissions: int,
) -> None:
    repository, commit = _repository(tmp_path)
    (repository / relative).chmod(permissions)

    result = _verify(repository, commit)

    assert result.returncode == 1
    assert "mode differs from Git" in result.stderr
    assert result.stdout == ""


def test_group_or_world_writable_source_file_and_directory_are_rejected(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)
    readme = repository / "README.md"
    readme.chmod(0o666)

    file_result = _verify(repository, commit)
    assert file_result.returncode == 1
    assert "source file 'README.md' is group- or world-writable" in file_result.stderr

    readme.chmod(0o644)
    source_directory = repository / "bin"
    source_directory.chmod(0o777)

    directory_result = _verify(repository, commit)
    assert directory_result.returncode == 1
    assert "source directory 'bin' is group- or world-writable" in (
        directory_result.stderr
    )


def test_hardlink_symlink_and_fifo_cannot_replace_a_tracked_file(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)
    readme = repository / "README.md"
    reviewed_bytes = readme.read_bytes()
    readme.unlink()
    hardlink_source = tmp_path / "hardlink-source"
    hardlink_source.write_bytes(reviewed_bytes)
    os.link(hardlink_source, readme)

    hardlink_result = _verify(repository, commit)
    assert hardlink_result.returncode == 1
    assert "not one single-link file" in hardlink_result.stderr

    readme.unlink()
    hardlink_source.unlink()
    symlink_source = tmp_path / "symlink-source"
    symlink_source.write_bytes(reviewed_bytes)
    readme.symlink_to(symlink_source)

    symlink_result = _verify(repository, commit)
    assert symlink_result.returncode == 1
    assert "unexpected non-regular source entry" in symlink_result.stderr

    readme.unlink()
    os.mkfifo(readme, 0o644)

    fifo_result = _verify(repository, commit)
    assert fifo_result.returncode == 1
    assert "unexpected non-regular source entry" in fifo_result.stderr


def test_commit_cannot_track_a_reserved_generated_root(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    tracked_generated = repository / ".venv"
    tracked_generated.mkdir()
    (tracked_generated / "payload").write_bytes(b"tracked generated path\n")
    _git(repository, "add", ".venv/payload")
    _git(repository, "commit", "--quiet", "-m", "track reserved path")
    commit = _git(repository, "rev-parse", "HEAD")

    result = _verify(
        repository,
        commit,
        "--allow-generated",
        ".venv",
    )

    assert result.returncode == 1
    assert "tracks reserved local path" in result.stderr
    assert ".venv/payload" in result.stderr
    assert result.stdout == ""


def test_commit_with_a_tracked_symlink_is_rejected(tmp_path: Path) -> None:
    repository, _ = _repository(tmp_path)
    (repository / "tracked-link").symlink_to("README.md")
    _git(repository, "add", "tracked-link")
    _git(repository, "commit", "--quiet", "-m", "track symlink")
    commit = _git(repository, "rev-parse", "HEAD")

    result = _verify(repository, commit)

    assert result.returncode == 1
    assert "non-regular source entry" in result.stderr
    assert "tracked-link" in result.stderr
    assert result.stdout == ""


def test_release_root_must_be_a_safe_canonical_physical_directory(
    tmp_path: Path,
) -> None:
    repository, commit = _repository(tmp_path)
    repository.chmod(0o777)

    writable = _verify(repository, commit)

    assert writable.returncode == 1
    assert "release directory is group- or world-writable" in writable.stderr
    assert writable.stdout == ""
