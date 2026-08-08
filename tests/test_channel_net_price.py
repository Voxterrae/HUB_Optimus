from __future__ import annotations

import pytest

from tools.channel_net_price import calculate


def test_microsoft_marketplace_gross_up_preserves_net() -> None:
    result = calculate(1_000_000, [3])
    assert result["gross_customer_price"] == 1_030_927.84
    assert result["net_after_deductions"] == 1_000_000.00


def test_combined_channel_deductions_preserve_net() -> None:
    result = calculate(500_000, [3, 20, 0.5])
    assert result["total_deductions_percent"] == 23.5
    assert result["net_after_deductions"] == 500_000.00


def test_invalid_total_deductions_fail() -> None:
    with pytest.raises(ValueError, match="below 100"):
        calculate(1000, [60, 40])


def test_negative_values_fail() -> None:
    with pytest.raises(ValueError):
        calculate(-1, [3])
    with pytest.raises(ValueError):
        calculate(1000, [-1])
