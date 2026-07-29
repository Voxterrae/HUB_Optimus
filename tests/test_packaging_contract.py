"""Tests for the documented Python and dependency installation contract."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap.py"
RUNTIME_REQUIREMENTS = REPO_ROOT / "requirements.txt"
DEVELOPMENT_REQUIREMENTS = REPO_ROOT / "requirements-dev.txt"


def _load_bootstrap() -> ModuleType:
    spec = importlib.util.spec_from_file_location("hub_bootstrap", BOOTSTRAP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _requirement_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_runtime_and_development_dependencies_are_separate() -> None:
    runtime = _requirement_lines(RUNTIME_REQUIREMENTS)
    development = _requirement_lines(DEVELOPMENT_REQUIREMENTS)

    assert runtime == ["jsonschema>=4.26.0,<5"]
    assert development == ["-r requirements.txt", "pytest>=9.1.1,<10"]
    assert all("pytest" not in requirement.lower() for requirement in runtime)


def test_bootstrap_uses_python_311_and_explicit_dependency_tiers() -> None:
    bootstrap = _load_bootstrap()

    assert bootstrap.MIN_PYTHON == (3, 11)
    assert bootstrap.RUNTIME_REQUIREMENTS == RUNTIME_REQUIREMENTS
    assert bootstrap.DEVELOPMENT_REQUIREMENTS == DEVELOPMENT_REQUIREMENTS


def test_runtime_only_check_does_not_require_pytest() -> None:
    proc = subprocess.run(
        [sys.executable, str(BOOTSTRAP), "--runtime-only", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "Mode: runtime (requirements.txt)" in proc.stdout
    assert "[OK]   jsonschema" in proc.stdout
    assert "pytest" not in proc.stdout.lower()


def test_package_check_rejects_an_installed_version_outside_the_contract(
    monkeypatch: Any,
) -> None:
    bootstrap = _load_bootstrap()
    monkeypatch.setattr(bootstrap.metadata, "version", lambda _name: "3.2.0")

    assert not bootstrap.check_package("jsonschema")


def test_missing_tool_is_reported_without_a_traceback(monkeypatch: Any) -> None:
    bootstrap = _load_bootstrap()

    def missing_tool(*_args: Any, **_kwargs: Any) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(bootstrap.subprocess, "run", missing_tool)

    assert not bootstrap.check_tool("git")


def test_runtime_tier_does_not_probe_for_git(monkeypatch: Any) -> None:
    bootstrap = _load_bootstrap()
    monkeypatch.setattr(bootstrap, "check_python", lambda: True)
    monkeypatch.setattr(bootstrap, "check_package", lambda _name: True)

    def unexpected_tool_probe(_name: str) -> bool:
        raise AssertionError("runtime-only mode must not require Git")

    monkeypatch.setattr(bootstrap, "check_tool", unexpected_tool_probe)

    assert bootstrap.main(["--runtime-only", "--check"]) == 0


def test_runtime_smoke_uses_only_the_supported_cli_contract() -> None:
    bootstrap = _load_bootstrap()

    assert bootstrap.run_runtime_smoke()


def test_runtime_smoke_writes_only_to_a_temporary_path(monkeypatch: Any) -> None:
    bootstrap = _load_bootstrap()
    observed: dict[str, Path] = {}

    def fake_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        output_index = command.index("--output") + 1
        observed["output"] = Path(command[output_index])
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"status":"success","rounds":1,"history":[]}',
            stderr="",
        )

    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)

    assert bootstrap.run_runtime_smoke()
    assert not observed["output"].is_relative_to(REPO_ROOT)


def test_readmes_document_the_same_minimum_and_install_paths() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    simulation_readme = (REPO_ROOT / "SIMULATION_README.md").read_text(
        encoding="utf-8"
    )

    assert "Python 3.11" in readme
    assert "Python 3.11" in simulation_readme
    assert "pip install -r requirements.txt" in readme
    assert "pip install -r requirements.txt" in simulation_readme
    assert "pip install -r requirements-dev.txt" in simulation_readme
