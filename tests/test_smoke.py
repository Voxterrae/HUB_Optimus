import json
import os
import subprocess
import sys
from pathlib import Path

from hub_optimus.evaluate import evaluate_scenario


SCN001 = Path("v1_core/workflow/scenario_001_partial_ceasefire.md")
SCN002 = Path("v1_core/workflow/scenario_002_verified_ceasefire.md")


def _run_cli(*extra_args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [
        sys.executable,
        "-m",
        "hub_optimus",
        "evaluate",
        str(SCN001),
        *extra_args,
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def test_scn001_has_claim_and_critical_flag():
    assert SCN001.exists()

    rep, payload = evaluate_scenario(SCN001)

    assert "Scenario Evaluation Report" in rep
    assert payload["trust_layer"]["counts"]["C"] >= 1
    assert any("CRITICAL missing section" in f for f in payload["flags"])


def test_scn002_has_verification_claims():
    assert SCN002.exists()

    _, payload = evaluate_scenario(SCN002)

    claims = payload["claims"]
    assert claims
    assert any(
        item["claim_type"] in {"verification_mechanism", "third_party_audit"}
        for item in claims
    )
    assert any(item["level"] == "A" for item in claims)


def test_cli_fail_on_critical_returns_nonzero():
    proc = _run_cli("--fail-on-critical")

    assert proc.returncode == 2
    assert "critical" in proc.stderr.lower()


def test_cli_format_json_writes_only_json(tmp_path: Path):
    proc = _run_cli("--write", "--out", str(tmp_path), "--format", "json")

    assert proc.returncode == 0

    json_file = tmp_path / "scenario_001_partial_ceasefire_report.json"
    md_file = tmp_path / "scenario_001_partial_ceasefire_report.md"

    assert json_file.exists()
    assert not md_file.exists()

    payload = json.loads(json_file.read_text(encoding="utf-8"))
    assert payload["trust_layer"]["counts"]["C"] >= 1
    assert payload["schema"]["critical_missing"] == ["verification"]


def test_cli_format_both_prints_markdown_and_json():
    proc = _run_cli("--format", "both")

    assert proc.returncode == 0
    assert "# Scenario Evaluation Report:" in proc.stdout
    assert "--- JSON ---" in proc.stdout
    assert '"trust_layer"' in proc.stdout
