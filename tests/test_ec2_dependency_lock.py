from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
LOCK_TOOL = ROOT / "ops" / "ec2" / "dependency-lock-digest.sh"
RUNTIME_LOCK = ROOT / "ops" / "ec2" / "requirements-runtime.lock"
VALIDATION_LOCK = ROOT / "ops" / "ec2" / "requirements-validation.lock"
DEPLOY = ROOT / "ops" / "ec2" / "deploy-current.sh"
ENVIRONMENT_TOOL = ROOT / "ops" / "ec2" / "verify-installed-dependencies.py"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _release(tmp_path: Path) -> Path:
    release = tmp_path / "release"
    lock_dir = release / "ops" / "ec2"
    lock_dir.mkdir(parents=True)
    for source in (RUNTIME_LOCK, VALIDATION_LOCK):
        target = lock_dir / source.name
        shutil.copyfile(source, target)
        target.chmod(0o644)
    return release


def _digest(release: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(LOCK_TOOL), str(release)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_reviewed_dependency_locks_have_one_stable_digest(tmp_path: Path) -> None:
    release = _release(tmp_path)

    first = _digest(release)
    second = _digest(release)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
    assert len(first.stdout.strip()) == 64
    assert set(first.stdout.strip()) <= set("0123456789abcdef")


@pytest.mark.parametrize(
    ("corruption", "expected"),
    (
        ("missing-hash", "only reviewed SHA-256 hashes"),
        ("unexpected-transitive", "dependency set differs"),
        ("mutable-version", "not one exact version pin"),
        ("index-override", "unsupported option"),
        ("duplicate", "duplicate dependency"),
        ("symlink", "without following links"),
        ("hardlink", "single-link"),
        ("mode", "unexpected mode"),
    ),
)
def test_lock_boundary_rejects_unreviewed_inputs(
    tmp_path: Path,
    corruption: str,
    expected: str,
) -> None:
    release = _release(tmp_path)
    runtime = release / "ops" / "ec2" / RUNTIME_LOCK.name
    validation = release / "ops" / "ec2" / VALIDATION_LOCK.name
    if corruption == "missing-hash":
        runtime.write_text(
            runtime.read_text(encoding="ascii").replace(
                "    --hash=sha256:c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309\n",
                "",
                1,
            ),
            encoding="ascii",
        )
    elif corruption == "unexpected-transitive":
        validation.write_text(
            validation.read_text(encoding="ascii")
            + "surprise==1.0 --hash=sha256:" + "a" * 64 + "\n",
            encoding="ascii",
        )
    elif corruption == "mutable-version":
        runtime.write_text(
            runtime.read_text(encoding="ascii").replace(
                "attrs==26.1.0", "attrs>=26.1.0", 1
            ),
            encoding="ascii",
        )
    elif corruption == "index-override":
        validation.write_text(
            "--index-url https://example.invalid/simple\n"
            + validation.read_text(encoding="ascii"),
            encoding="ascii",
        )
    elif corruption == "duplicate":
        validation.write_text(
            validation.read_text(encoding="ascii")
            + "pytest==9.1.1 --hash=sha256:" + "b" * 64 + "\n",
            encoding="ascii",
        )
    elif corruption == "symlink":
        sentinel = tmp_path / "sentinel"
        sentinel.write_bytes(runtime.read_bytes())
        runtime.unlink()
        runtime.symlink_to(sentinel)
    elif corruption == "hardlink":
        os.link(runtime, tmp_path / "second-link")
    else:
        validation.chmod(0o600)

    result = _digest(release)

    assert result.returncode == 1
    assert expected in result.stderr


def test_deploy_uses_only_hash_locked_allowlisted_dependencies() -> None:
    source = DEPLOY.read_text(encoding="utf-8")
    tool = ENVIRONMENT_TOOL.read_text(encoding="utf-8")

    assert "pip install --upgrade pip" not in source
    assert "requirements-dev.txt" not in source
    assert 'INDEX_URL = "https://pypi.org/simple"' in tool
    assert "--require-hashes" in tool
    assert "--only-binary=:all:" in tool
    assert "--no-deps" in tool
    assert '"PIP_CONFIG_FILE": "/dev/null"' in tool
    assert '"PIP_NO_INPUT": "1"' in tool
    assert "reject_ambient_pip_environment" in source
    assert '"-I", "-m", "pip", "check"' in tool
    assert "sealed_requirements(snapshot.combined_requirements)" in tool
    assert "F_SEAL_WRITE" in tool
    assert "require_unchanged_paths(snapshot)" in tool


def test_dependency_lock_files_are_public_read_only_inputs() -> None:
    for path in (RUNTIME_LOCK, VALIDATION_LOCK):
        assert stat.S_IMODE(path.stat().st_mode) == 0o644
        assert not path.is_symlink()


def test_locked_ci_certifies_two_reproducible_offline_environments() -> None:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["ec2-locked-environment"]["steps"]
    script = next(
        step["run"]
        for step in steps
        if step.get("name") == "Certify reproducible offline dependency installs"
    )

    assert script.count("-I -m pip download") == 1
    assert '"$python_bin" -I -m venv "$release/.venv"' in script
    assert 'create_release "$release_a"' in script
    assert 'create_release "$release_b"' in script
    assert 'sealed_offline_install "$release_a" "$wheelhouse"' in script
    assert 'sealed_offline_install "$release_b" "$wheelhouse"' in script
    assert "--index-url https://pypi.org/simple" in script
    assert '"--no-index", "--find-links"' in ENVIRONMENT_TOOL.read_text(
        encoding="utf-8"
    )
    assert "--require-hashes" in script
    assert "--no-deps" in script
    assert "--only-binary=:all:" in script
    assert "intentional-hash-corruption" in script
    assert "THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE" in script
    assert script.count("install-offline") == 1
    assert script.count("sealed_offline_install") == 4
    assert script.count("verify-installed-dependencies.py") == 3
    assert 'cmp -s -- "$inventory_a" "$inventory_b"' in script
    assert 'node_bin="$(command -v node)"' in script
    assert 'node_dir="$(dirname -- "$node_bin")"' in script
    assert 'PATH="$node_dir:/usr/bin:/bin"' in script
    assert '"$release_a/.venv/bin/python" -m pytest -q' in script
