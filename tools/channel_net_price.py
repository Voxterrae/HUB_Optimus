#!/usr/bin/env python3
"""Calculate a gross customer price that preserves an approved target net.

This is a commercial planning calculator. It does not determine VAT, withholding,
corporate tax, transfer pricing, or legal tax treatment.
"""

from __future__ import annotations

import argparse
import json
import sys


def calculate(target_net: float, deductions_percent: list[float]) -> dict[str, object]:
    if target_net <= 0:
        raise ValueError("target_net must be greater than zero")
    if any(value < 0 for value in deductions_percent):
        raise ValueError("deduction percentages cannot be negative")
    total_percent = sum(deductions_percent)
    if total_percent >= 100:
        raise ValueError("total deductions must be below 100 percent")

    gross = target_net / (1 - total_percent / 100)
    deductions = [gross * value / 100 for value in deductions_percent]
    return {
        "target_net": round(target_net, 2),
        "gross_customer_price": round(gross, 2),
        "total_deductions_percent": round(total_percent, 6),
        "deductions": [round(value, 2) for value in deductions],
        "net_after_deductions": round(gross - sum(deductions), 2),
        "tax_note": "VAT, withholding and legal tax treatment are excluded and require professional review."
    }


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
