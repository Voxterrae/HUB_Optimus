from pathlib import Path


def test_exchange_runbook_is_allowlisted_and_dry_run_by_default() -> None:
    content = (Path(__file__).parents[1] / "runbooks" / "Invoke-OptimusExchangeOperation.ps1").read_text(encoding="utf-8")
    lowered = content.lower()
    assert "invoke-expression" not in lowered
    assert "iex " not in lowered
    assert "downloadstring" not in lowered
    assert "[validateset(" in lowered
    assert "[bool]$dryrun = $true" in lowered
    assert "mutation requires approvalid, planhash, reason and changeticket" in lowered
