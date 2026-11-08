#!/usr/bin/env python3
"""Calculate a gross customer price that preserves an approved target net.

This is a commercial planning calculator. It does not determine VAT, withholding,
corporate tax, transfer pricing, or legal tax treatment.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, DecimalException, ROUND_CEILING, ROUND_HALF_EVEN


def calculate(target_net: float, deductions_percent: list[float]) -> dict[str, object]:
    try:
        target = Decimal(str(target_net))
        percentages = [Decimal(str(value)) for value in deductions_percent]
        if not target.is_finite():
            raise ValueError("target_net must be finite")
        if target <= 0:
            raise ValueError("target_net must be greater than zero")
        if any(not value.is_finite() for value in percentages):
            raise ValueError("deduction percentages must be finite")
        if any(value < 0 for value in percentages):
            raise ValueError("deduction percentages cannot be negative")
        total_percent = sum(percentages, Decimal("0"))
        if total_percent >= 100:
            raise ValueError("total deductions must be below 100 percent")

        cent = Decimal("0.01")
        retained_fraction = 1 - total_percent / 100
        gross = (target / retained_fraction).quantize(cent, rounding=ROUND_CEILING)

        def rounded_deductions(price: Decimal) -> list[Decimal]:
            return [
                (price * value / 100).quantize(cent, rounding=ROUND_HALF_EVEN)
                for value in percentages
            ]

        deductions = rounded_deductions(gross)
        net = gross - sum(deductions, Decimal("0"))
        if net < target:
            gross += (target - net).quantize(cent, rounding=ROUND_CEILING)
            deductions = rounded_deductions(gross)
            net = gross - sum(deductions, Decimal("0"))
        if net < target:
            # Each fee can round upward by at most half a cent.
            rounding_margin = len(percentages) * cent / 2
            gross = ((target + rounding_margin) / retained_fraction).quantize(
                cent, rounding=ROUND_CEILING
            )
            deductions = rounded_deductions(gross)
            net = gross - sum(deductions, Decimal("0"))

        target_amount = target.quantize(cent, rounding=ROUND_HALF_EVEN)
        amounts = [target_amount, gross, *deductions, net]
        if any(Decimal(str(float(amount))) != amount for amount in amounts):
            raise ValueError("monetary amounts cannot be represented as JSON floats in cents")

        return {
            "target_net": float(target_amount),
            "gross_customer_price": float(gross),
            "total_deductions_percent": float(
                total_percent.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)
            ),
            "deductions": [float(value) for value in deductions],
            "net_after_deductions": float(net),
            "tax_note": "VAT, withholding and legal tax treatment are excluded and require professional review."
        }
    except DecimalException as exc:
        raise ValueError("monetary amounts exceed supported decimal precision") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_net", type=float)
    parser.add_argument(
        "deduction_percent",
        type=float,
        nargs="*",
        help="Percentage-of-gross deductions such as marketplace, reseller, bank, or finance-operations fees.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = calculate(args.target_net, args.deduction_percent)
    except ValueError as exc:
        print(f"CHANNEL_NET_PRICE: ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
