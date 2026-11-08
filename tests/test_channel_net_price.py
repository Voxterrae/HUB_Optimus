from __future__ import annotations

from decimal import Decimal

import pytest

from tools.channel_net_price import calculate, main


def test_microsoft_marketplace_gross_up_preserves_net() -> None:
    result = calculate(1_000_000, [3])
    assert result["gross_customer_price"] == 1_030_927.84
    assert result["net_after_deductions"] == 1_000_000.00


def test_combined_channel_deductions_preserve_net() -> None:
    result = calculate(500_000, [3, 20, 0.5])
    assert result["total_deductions_percent"] == 23.5
    assert result["net_after_deductions"] == 500_000.01


def test_invalid_total_deductions_fail() -> None:
    with pytest.raises(ValueError, match="below 100"):
        calculate(1000, [60, 40])


def test_negative_values_fail() -> None:
    with pytest.raises(ValueError):
        calculate(-1, [3])
    with pytest.raises(ValueError):
        calculate(1000, [-1])


@pytest.mark.parametrize("target, percentages", [
    (1_000_000, [3]),
    (500_000, [3, 20, 0.5]),
    (1_000_000, [3, 20, 0.5]),
    (1, [0.5, 0.5, 0.5]),
    (1000, []),
    (0.001, []),
    (1.005, []),
    (0.01, [49.9999, 49.9999]),
    (1, [0.5] * 30),
])
def test_displayed_amounts_preserve_reported_net_and_target(target, percentages):
    result = calculate(target, percentages)
    displayed_net = Decimal(str(result["gross_customer_price"])) - sum(
        (Decimal(str(value)) for value in result["deductions"]), Decimal("0")
    )
    assert Decimal(str(result["net_after_deductions"])) == displayed_net
    assert displayed_net >= Decimal(str(target))


@pytest.mark.parametrize("target", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_targets_fail(target):
    with pytest.raises(ValueError):
        calculate(target, [3])


@pytest.mark.parametrize("percentage", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_deductions_fail(percentage):
    with pytest.raises(ValueError):
        calculate(1000, [percentage])


def test_cent_shortfall_does_not_double_gross_near_total_deductions():
    result = calculate(0.01, [49.9999, 49.9999])
    assert result["gross_customer_price"] == 5000.01
    assert result["net_after_deductions"] == 0.01


@pytest.mark.parametrize("target, percentages", [
    (1, [99.99999999999999]),
    (1e14, [3, 20, 0.5]),
    (1e30, [3]),
    (1e308, [3]),
])
def test_unrepresentable_cent_amounts_fail_closed(target, percentages):
    with pytest.raises(ValueError):
        calculate(target, percentages)


@pytest.mark.parametrize("arguments", [
    ["1", "99.99999999999999"],
    ["1e14", "3", "20", "0.5"],
    ["1e30", "3"],
    ["1e308", "3"],
    ["nan", "3"],
    ["1000", "nan"],
])
def test_cli_rejects_unsupported_amounts_without_json_or_traceback(arguments, capsys):
    assert main(arguments) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "CHANNEL_NET_PRICE: ERROR:" in output.err
    assert "Traceback" not in output.err
