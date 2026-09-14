from __future__ import annotations

import importlib.metadata
import json
import os
import re
import runpy
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "ops" / "ec2" / "verify-installed-dependencies.py"
LOCK_TOOL = ROOT / "ops" / "ec2" / "dependency-lock-digest.sh"
RUNTIME_LOCK = (ROOT / "ops" / "ec2" / "requirements-runtime.lock").read_text(
    encoding="ascii"
)
VALIDATION_LOCK = (
    ROOT / "ops" / "ec2" / "requirements-validation.lock"
).read_text(encoding="ascii")


@dataclass(frozen=True)
class VerifierResult:
    returncode: int
    stdout: str
    stderr: str


def _release(
    tmp_path: Path,
    *,
    runtime_lock: str = RUNTIME_LOCK,
    validation_lock: str = VALIDATION_LOCK,
) -> Path:
    release = tmp_path / "release"
    lock_dir = release / "ops" / "ec2"
    lock_dir.mkdir(parents=True)
    (lock_dir / "requirements-runtime.lock").write_text(
        runtime_lock,
        encoding="ascii",
    )
    (lock_dir / "requirements-validation.lock").write_text(
        validation_lock,
        encoding="ascii",
    )
    return release


def _distribution(name: str, version: str) -> SimpleNamespace:
    return SimpleNamespace(metadata={"Name": name}, version=version)


def _expected_inventory() -> list[tuple[str, str]]:
    inventory: dict[str, str] = {}
    for text in (RUNTIME_LOCK, VALIDATION_LOCK):
        for match in re.finditer(
            r"(?m)^([A-Za-z0-9][A-Za-z0-9._-]*)==([^ \\\n]+)",
            text,
        ):
            name = re.sub(r"[-_.]+", "-", match.group(1)).lower()
            inventory[name] = match.group(2)
    return sorted(inventory.items())


def _run_verifier(
    release: Path,
    installed: list[tuple[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    wrong_executable: bool = False,
    wrong_base_interpreter: bool = False,
    expected_digest: str | None = None,
    expected_token: str | None = None,
) -> VerifierResult:
    expected_python = release / ".venv" / "bin" / "python"
    expected_python.parent.mkdir(parents=True, exist_ok=True)
    expected_python.touch()
    system_python = release.parent / "reviewed-system-python"
    system_python.touch()

    executable = expected_python
    if wrong_executable:
        executable = release.parent / "different-venv-python"
        executable.touch()
    base_executable = system_python
    if wrong_base_interpreter:
        base_executable = release.parent / "different-system-python"
        base_executable.touch()

    if expected_digest is None:
        expected_digest = subprocess.run(
            ["bash", str(LOCK_TOOL), str(release)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    if expected_token is None and expected_digest != "0" * 64:
        expected_token = subprocess.run(
            [
                "/usr/bin/python3",
                "-I",
                str(VERIFIER),
                "capture",
                str(release),
                expected_digest,
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    if expected_token is None:
        expected_token = "0" * 64
    installed_distributions = tuple(
        _distribution(name, version) for name, version in installed
    )
    monkeypatch.setattr(
        importlib.metadata,
        "distributions",
        lambda: installed_distributions,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(VERIFIER),
            "verify",
            str(release),
            str(system_python),
            expected_digest,
            expected_token,
        ],
    )
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "_base_executable", str(base_executable))

    capsys.readouterr()
    returncode = 0
    try:
        runpy.run_path(str(VERIFIER), run_name="__main__")
    except SystemExit as exc:
        returncode = int(exc.code)
    captured = capsys.readouterr()
    return VerifierResult(returncode, captured.out, captured.err)


def test_exact_installed_inventory_is_accepted_and_normalized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    release = _release(tmp_path)
    expected = _expected_inventory()

    result = _run_verifier(
        release,
        list(reversed(expected)),
        monkeypatch,
        capsys,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        {"name": name, "version": version} for name, version in expected
    ]
    assert result.stderr == ""


def test_unexpected_installed_distribution_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    release = _release(tmp_path)

    result = _run_verifier(
        release,
        _expected_inventory() + [("surprise", "9.9")],
        monkeypatch,
        capsys,
    )

    assert result.returncode == 1
    assert "unexpected=surprise" in result.stderr
    assert "missing=none" in result.stderr
    assert result.stdout == ""


def test_wrong_installed_version_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    release = _release(tmp_path)
    installed = dict(_expected_inventory())
    installed["attrs"] = "0.0"

    result = _run_verifier(
        release,
        sorted(installed.items()),
        monkeypatch,
        capsys,
    )

    assert result.returncode == 1
    assert "wrong_version=attrs" in result.stderr
    assert "unexpected=none" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("wrong_executable", "wrong_base_interpreter", "expected_error"),
    (
        (True, False, "not running from the candidate virtual environment"),
        (False, True, "was not created by the reviewed system Python"),
    ),
)
def test_wrong_python_identity_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    wrong_executable: bool,
    wrong_base_interpreter: bool,
    expected_error: str,
) -> None:
    release = _release(tmp_path)

    result = _run_verifier(
        release,
        _expected_inventory(),
        monkeypatch,
        capsys,
        wrong_executable=wrong_executable,
        wrong_base_interpreter=wrong_base_interpreter,
    )

    assert result.returncode == 1
    assert expected_error in result.stderr
    assert result.stdout == ""


def test_non_exact_lock_entry_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    release = _release(
        tmp_path,
        runtime_lock=RUNTIME_LOCK.replace("attrs==26.1.0", "attrs>=26.1.0"),
    )

    result = _run_verifier(
        release,
        _expected_inventory(),
        monkeypatch,
        capsys,
        expected_digest="0" * 64,
    )

    assert result.returncode == 1
    assert "dependency is not one exact version pin" in result.stderr
    assert result.stdout == ""


def test_repeated_exact_lock_pin_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    release = _release(
        tmp_path,
        runtime_lock=(
            RUNTIME_LOCK
            + "attrs==26.1.0 \\\n"
            + "    --hash=sha256:"
            + "a" * 64
            + "\n"
        ),
    )

    result = _run_verifier(
        release,
        _expected_inventory(),
        monkeypatch,
        capsys,
        expected_digest="0" * 64,
    )

    assert result.returncode == 1
    assert "lock contains a" in result.stderr
    assert "dependency: attrs" in result.stderr
    assert result.stdout == ""


def test_restored_lock_bytes_do_not_hide_an_atomic_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    release = _release(tmp_path)
    digest = subprocess.run(
        ["bash", str(LOCK_TOOL), str(release)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    token = subprocess.run(
        [
            "/usr/bin/python3",
            "-I",
            str(VERIFIER),
            "capture",
            str(release),
            digest,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    lock = release / "ops" / "ec2" / "requirements-validation.lock"
    replacement = lock.with_name("replacement.lock")
    replacement.write_bytes(lock.read_bytes())
    replacement.chmod(0o644)
    os.replace(replacement, lock)

    result = _run_verifier(
        release,
        _expected_inventory(),
        monkeypatch,
        capsys,
        expected_digest=digest,
        expected_token=token,
    )

    assert result.returncode == 1
    assert "paths changed since the sealed install snapshot" in result.stderr
    assert result.stdout == ""
