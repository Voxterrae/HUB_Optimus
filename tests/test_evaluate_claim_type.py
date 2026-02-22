from pathlib import Path

from hub_optimus.evaluate import evaluate_scenario


def test_evaluate_payload_includes_claim_type(tmp_path: Path):
    scenario = tmp_path / "mini.md"
    scenario.write_text(
        "\n".join(
            [
                "# Mini scenario",
                "## Context",
                "x",
                "## Incentives",
                "x",
                "## Systemic impact",
                "x",
                "## Classification",
                "x",
                "## Verification",
                "- Independent third-party audit with on-site inspections and public reports.",
            ]
        ),
        encoding="utf-8",
    )

    report_md, payload = evaluate_scenario(scenario)
    assert "Trust Layer" in report_md
    assert payload["claims"]
    assert "claim_type" in payload["claims"][0]
    assert payload["claims"][0]["claim_type"] == "third_party_audit"
