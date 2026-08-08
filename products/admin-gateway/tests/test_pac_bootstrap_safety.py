from pathlib import Path


def test_pac_bootstrap_is_dry_run_first_and_has_no_dynamic_script_execution() -> None:
    content = (
        Path(__file__).parents[1] / "dataverse" / "pac" / "bootstrap-solution.ps1"
    ).read_text(encoding="utf-8")
    lowered = content.lower()

    assert "[switch]$apply" in lowered
    assert "if (-not $apply)" in lowered
    assert "scriptblock]::create" not in lowered
    assert "invoke-expression" not in lowered
    assert "& pac @arguments" in lowered
    assert "unexpected executable in reviewed plan" in lowered


def test_approval_blueprint_targets_the_declared_dataverse_table() -> None:
    content = (
        Path(__file__).parents[1]
        / "power-platform"
        / "flows"
        / "approval-flow.blueprint.yaml"
    ).read_text(encoding="utf-8")

    assert "table: opt_adminrequest" in content
    assert "filter: opt_state eq 'APPROVAL_REQUIRED'" in content
    assert "opt_adminrequests" not in content
