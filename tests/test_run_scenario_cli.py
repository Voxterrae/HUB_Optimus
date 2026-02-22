import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_SCENARIO = REPO_ROOT / "run_scenario.py"
EXAMPLE = REPO_ROOT / "example_scenario.json"


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


def test_example_scenario_smoke_cli():
    assert EXAMPLE.exists()

    proc = _run_cli("--scenario", str(EXAMPLE), "--seed", "42")

    assert proc.returncode == 0

    payload = json.loads(proc.stdout)
    assert payload["status"] in {"success", "failure"}
    assert isinstance(payload["rounds"], int)
    assert payload["rounds"] >= 1
    assert payload["rounds"] <= 5
    assert isinstance(payload["history"], list)
    assert isinstance(payload["detail"], str)


def test_run_scenario_fails_fast_on_schema_error(tmp_path: Path):
    invalid = tmp_path / "invalid_scenario.json"
    invalid.write_text(
        json.dumps(
            {
                "title": "bad scenario",
                "description": "missing required fields",
                "roles": [],
                "success_criteria": {},
                "max_rounds": 0,
            }
        ),
        encoding="utf-8",
    )

    proc = _run_cli("--scenario", str(invalid))

    assert proc.returncode == 2
    assert "schema-error" in proc.stderr
    assert "roles must be a non-empty list" in proc.stderr
    assert "success_criteria must be a non-empty object" in proc.stderr
    assert "max_rounds must be an integer >= 1" in proc.stderr
