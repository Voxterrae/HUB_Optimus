"""Regression tests for the authoritative scenario-loading boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

import run_scenario
from hub_optimus_simulator import Scenario


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SCENARIO = REPO_ROOT / "run_scenario.py"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, str(RUN_SCENARIO), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def _valid_payload() -> dict:
    return {
        "title": "Strict scenario",
        "description": "Synthetic validation fixture.",
        "roles": [
            {"name": "Actor A", "role": "negotiator"},
            {"name": "Actor B", "role": "mediator"},
        ],
        "success_criteria": {"offer": 5},
        "max_rounds": 3,
    }


def _write_non_standard_constant(path: Path, constant: str) -> None:
    payload = _valid_payload()
    payload["success_criteria"]["offer"] = "__NON_STANDARD_CONSTANT__"
    source = json.dumps(payload).replace(
        '"__NON_STANDARD_CONSTANT__"',
        constant,
    )
    path.write_text(source, encoding="utf-8")


def _authoritative_loader(path: Path) -> Scenario:
    return run_scenario.load_validated_scenario(path)


def _compatibility_loader(path: Path) -> Scenario:
    return Scenario.from_json(str(path))


LOADERS: tuple[Callable[[Path], Scenario], ...] = (
    _authoritative_loader,
    _compatibility_loader,
)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_cli_rejects_non_standard_json_constants(
    tmp_path: Path,
    constant: str,
) -> None:
    scenario_path = tmp_path / "non_standard.json"
    output_path = tmp_path / "result.json"
    _write_non_standard_constant(scenario_path, constant)

    proc = _run_cli(
        "--scenario",
        str(scenario_path),
        "--output",
        str(output_path),
    )

    assert proc.returncode == run_scenario.INPUT_ERROR_EXIT_CODE
    assert proc.stdout == ""
    assert proc.stderr.startswith("[schema-error] Invalid JSON:")
    assert f"non-standard JSON constant {constant!r} is not permitted" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert not output_path.exists()


def test_cli_rejects_duplicate_actor_names_before_execution(tmp_path: Path) -> None:
    scenario_path = tmp_path / "duplicate_actors.json"
    output_path = tmp_path / "result.json"
    payload = _valid_payload()
    payload["roles"][1]["name"] = payload["roles"][0]["name"]
    scenario_path.write_text(json.dumps(payload), encoding="utf-8")

    proc = _run_cli(
        "--scenario",
        str(scenario_path),
        "--output",
        str(output_path),
    )

    assert proc.returncode == run_scenario.INPUT_ERROR_EXIT_CODE
    assert proc.stdout == ""
    assert proc.stderr.startswith("[schema-error]")
    assert (
        "roles.1.name: duplicate actor name 'Actor A'; "
        "first declared at roles.0.name"
    ) in proc.stderr
    assert "Traceback" not in proc.stderr
    assert not output_path.exists()


@pytest.mark.parametrize("loader", LOADERS, ids=["authoritative", "compatibility"])
@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_programmatic_loaders_reject_non_standard_json_constants(
    tmp_path: Path,
    loader: Callable[[Path], Scenario],
    constant: str,
) -> None:
    scenario_path = tmp_path / "non_standard.json"
    _write_non_standard_constant(scenario_path, constant)

    with pytest.raises(
        ValueError,
        match=rf"non-standard JSON constant {constant!r} is not permitted",
    ):
        loader(scenario_path)


@pytest.mark.parametrize("loader", LOADERS, ids=["authoritative", "compatibility"])
def test_programmatic_loaders_reject_duplicate_actor_names(
    tmp_path: Path,
    loader: Callable[[Path], Scenario],
) -> None:
    scenario_path = tmp_path / "duplicate_actors.json"
    payload = _valid_payload()
    payload["roles"][1]["name"] = payload["roles"][0]["name"]
    scenario_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate actor name 'Actor A'"):
        loader(scenario_path)


@pytest.mark.parametrize("loader", LOADERS, ids=["authoritative", "compatibility"])
def test_programmatic_loaders_share_required_field_validation(
    tmp_path: Path,
    loader: Callable[[Path], Scenario],
) -> None:
    scenario_path = tmp_path / "missing_fields.json"
    scenario_path.write_text('{"title": "No permissive defaults"}', encoding="utf-8")

    with pytest.raises(ValueError, match="'description' is a required property"):
        loader(scenario_path)


def test_scenario_from_json_delegates_to_authoritative_loader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_path = tmp_path / "delegated.json"
    sentinel = Scenario(
        title="Validated",
        description="Returned by authoritative loader.",
        roles=[{"name": "Actor", "role": "negotiator"}],
        success_criteria={"offer": 5},
        max_rounds=1,
    )
    received: list[Path] = []

    def fake_loader(path: Path) -> Scenario:
        received.append(path)
        return sentinel

    monkeypatch.setattr(run_scenario, "load_validated_scenario", fake_loader)

    assert Scenario.from_json(str(scenario_path)) is sentinel
    assert received == [scenario_path]


def test_valid_loaders_return_equivalent_canonical_scenarios() -> None:
    scenario_path = REPO_ROOT / "example_scenario.json"

    authoritative = run_scenario.load_validated_scenario(scenario_path)
    compatibility = Scenario.from_json(str(scenario_path))

    assert vars(compatibility) == vars(authoritative)
