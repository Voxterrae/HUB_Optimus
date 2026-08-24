from __future__ import annotations

import json
from pathlib import Path

MODEL_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "business"
    / "revenue_ambition.v0.1.json"
)


def load_model() -> dict:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def test_operating_target_components_reconcile() -> None:
    target = load_model()["scenarios"]["operating_target"]
    components = target["components"]

    assert sum(components.values()) == target["gross_contracted_value"]
    assert target["one_time_value"] + target["exit_arr"] == target[
        "gross_contracted_value"
    ]


def test_channel_mix_and_fee_reconcile() -> None:
    target = load_model()["scenarios"]["operating_target"]
    mix = target["illustrative_channel_mix"]

    assert sum(item["share_percent"] for item in mix.values()) == 100

    weighted = 0.0
    for item in mix.values():
        fee = item.get("fee_percent", item.get("fee_percent_internal_assumption"))
        weighted += item["share_percent"] * fee / 100

    assert round(weighted, 6) == target["weighted_channel_fee_percent"]
    assert round(
        target["gross_contracted_value"] * weighted / 100, 3
    ) == round(target["channel_fees"], 3)
    assert round(
        target["gross_contracted_value"] - target["channel_fees"], 3
    ) == round(target["cash_after_channel_fees_before_tax_and_operating_cost"], 3)


def test_three_year_cumulative_value_reconciles() -> None:
    model = load_model()

    assert sum(
        year["gross_contracted_value"] for year in model["three_year_ambition"]
    ) == model["three_year_cumulative_gross_contracted_value"]


def test_arr_and_gross_increase_without_personal_net_claim() -> None:
    model = load_model()
    years = model["three_year_ambition"]

    assert all(
        later["gross_contracted_value"] > earlier["gross_contracted_value"]
        for earlier, later in zip(years, years[1:])
    )
    assert all(
        later["exit_arr"] > earlier["exit_arr"]
        for earlier, later in zip(years, years[1:])
    )
    assert model["personal_take_home_modelled"] is False
    assert model["requires_professional_legal_tax_accounting_design"] is True
