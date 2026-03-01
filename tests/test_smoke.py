from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_SCENARIO = ROOT / "run_scenario.py"
EXAMPLE_SCENARIO = ROOT / "example_scenario.json"


def test_example_scenario_json_smoke(tmp_path: Path) -> None:
    output_path = tmp_path / "scenario_output.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(RUN_SCENARIO),
            str(EXAMPLE_SCENARIO),
            "--output",
            str(output_path),
            "--seed",
            "42",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr

    assert output_path.is_file()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] in {"success", "failure"}
    assert isinstance(payload.get("rounds"), int)
    assert isinstance(payload.get("history"), list)
    assert len(payload["history"]) == payload["rounds"]
