"""Regression tests for authoritative scenario selection in the mutator."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "tools" / "scenario_mutator.py"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("scenario_mutator", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_scenario() -> dict[str, object]:
    return {
        "title": "Mutation fixture",
        "description": "A valid base for controlled mutations.",
        "roles": [{"name": "Alpha", "role": "negotiator"}],
        "success_criteria": {"offer": 5},
        "max_rounds": 2,
    }


def _run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _source_with_constant(constant: str) -> bytes:
    source = json.dumps(_valid_scenario()).replace(
        '"offer": 5',
        f'"offer": {constant}',
    )
    return source.encode("utf-8")


def _duplicate_actor_source() -> bytes:
    payload = _valid_scenario()
    payload["roles"] = [
        {"name": "Alpha", "role": "negotiator"},
        {"name": "Alpha", "role": "mediator"},
    ]
    return json.dumps(payload).encode("utf-8")


@pytest.mark.parametrize(
    ("source", "error_code"),
    [
        pytest.param(_source_with_constant("NaN"), "invalid_json", id="nan"),
        pytest.param(
            _source_with_constant("Infinity"),
            "invalid_json",
            id="positive-infinity",
        ),
        pytest.param(
            _source_with_constant("-Infinity"),
            "invalid_json",
            id="negative-infinity",
        ),
        pytest.param(
            _duplicate_actor_source(),
            "schema_invalid",
            id="duplicate-actors",
        ),
        pytest.param(b"\xff\xfe", "invalid_utf8", id="invalid-utf8"),
        pytest.param(
            b'{"title": "Incomplete"}',
            "schema_invalid",
            id="missing-fields",
        ),
        pytest.param(b"[]", "json_root_not_object", id="non-object-root"),
    ],
)
def test_invalid_base_fails_closed_before_output_creation(
    tmp_path: Path,
    source: bytes,
    error_code: str,
) -> None:
    base_path = tmp_path / "invalid.json"
    output_dir = tmp_path / "mutations"
    base_path.write_bytes(source)

    result = _run_tool(
        "--base",
        str(base_path),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 2
    assert error_code in result.stderr
    assert "Traceback" not in result.stderr
    assert not output_dir.exists()


def test_generated_mutations_reuse_semantic_actor_validation(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mutator = _load_tool()
    base = _valid_scenario()
    base["roles"] = [{"name": "Faction_E", "role": "negotiator"}]

    mutations = mutator.generate_mutations(
        [("existing-extra-name", base)],
        ["actors"],
    )

    assert [stem for stem, _axis, _scenario in mutations] == [
        "existing-extra-name_actors_1"
    ]
    captured = capsys.readouterr()
    assert "duplicate actor name 'Faction_E'" in captured.err
