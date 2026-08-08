#!/usr/bin/env python3
"""Deterministic first-pass qualification for HUB_Optimus institutional access.

This tool does not approve a customer, contract, Common Good engagement, price,
or rights exception. It applies the repository policy and returns a transparent
classification for owner review.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

DEFAULT_POLICY = pathlib.Path("config/launch/qualification_policy.v0.1.json")


class QualificationError(RuntimeError):
    """Raised when the intake or policy is malformed."""


@dataclass(frozen=True)
class Decision:
    classification: str
    reasons: tuple[str, ...]
    owner_review_required: bool


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise QualificationError(f"{label} must be an object")
    return value


def _bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise QualificationError(f"{key} must be boolean")
    return value


def _string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QualificationError(f"{key} must be a non-empty string")
    return value.strip()


def evaluate(intake: dict[str, Any], policy: dict[str, Any]) -> Decision:
    intake = _mapping(intake, "intake")
    policy = _mapping(policy, "policy")

    track = _string(intake, "requested_track")
    organization_type = _string(intake, "organization_type")
    budget_band = _string(intake, "budget_band")

    if _bool(intake, "requires_ownership_or_control"):
        return Decision(
            "DECLINE_PROTECTED_RIGHTS",
            ("Ownership or control of HUB_Optimus is not an access condition.",),
            True,
        )

    if _bool(intake, "requests_free_bespoke_work"):
        return Decision(
            "DECLINE_FREE_BESPOKE_WORK",
            ("Commercial and public-sector bespoke work is not free.",),
            False,
        )

    if track == "common_good":
        common_good = _mapping(policy.get("common_good"), "common_good policy")
        reasons: list[str] = []
        if organization_type != "nonprofit" or not _bool(intake, "verified_nonprofit"):
            reasons.append("Verified nonprofit status is required.")
        if not _bool(intake, "direct_human_or_animal_benefit"):
            reasons.append("Direct human or animal welfare benefit is required.")
        if _bool(intake, "intended_commercial_use"):
            reasons.append("Common Good access must be noncommercial.")
        if _bool(intake, "hidden_reseller_or_commercial_beneficiary"):
            reasons.append("Hidden commercial or reseller beneficiaries are prohibited.")
        if _bool(intake, "requires_core_source_transfer"):
            reasons.append("Common Good access does not transfer the core source code.")
        if reasons:
            return Decision("DECLINE_COMMON_GOOD_INELIGIBLE", tuple(reasons), True)
        return Decision(
            "COMMON_GOOD_REVIEW",
            ("Eligibility indicators passed; safeguarding and owner review remain required.",),
            True,
        )

    if track != "paid":
        raise QualificationError(f"unsupported requested_track: {track!r}")

    if _bool(intake, "requires_core_source_transfer"):
        return Decision(
            "HOLD_OWNER_RIGHTS_REVIEW",
            ("Core source-code transfer is outside standard qualification.",),
            True,
        )

    if _bool(intake, "requests_white_label_oem_resale_or_exclusivity"):
        return Decision(
            "HOLD_STRATEGIC_RIGHTS_REVIEW",
            ("White-label, OEM, resale, or exclusivity requires a separate owner decision.",),
            True,
        )

    reasons = []
    if not _bool(intake, "decision_authority_confirmed"):
        reasons.append("Decision authority is not confirmed.")
    if not _bool(intake, "procurement_owner_confirmed"):
        reasons.append("Procurement/accounts-payable ownership is not confirmed.")
    if not _bool(intake, "accepts_paid_diagnostic"):
        reasons.append("The applicant does not accept the paid diagnostic boundary.")

    enterprise_types = set(policy.get("enterprise_public_types") or [])
    if organization_type in enterprise_types:
        permitted_bands = set(policy.get("enterprise_public_minimum_budget_bands") or [])
    else:
        permitted_bands = set(policy.get("general_minimum_budget_bands") or [])
    if budget_band not in permitted_bands:
        reasons.append("Budget is below the applicable minimum or is undisclosed.")

    if reasons:
        return Decision("HOLD_UNQUALIFIED", tuple(reasons), False)

    if not _bool(intake, "accepts_paid_pov"):
        return Decision(
            "QUALIFIED_DIAGNOSTIC_ONLY",
            ("Paid diagnostic accepted; Proof of Value requires later confirmation.",),
            False,
        )

    return Decision(
        "QUALIFIED_PAID",
        ("Authority, procurement, budget, and paid-engagement boundaries passed.",),
        False,
    )


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))
    except FileNotFoundError as exc:
        raise QualificationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise QualificationError(f"invalid JSON in {path}: {exc}") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intake", type=pathlib.Path)
    parser.add_argument("--policy", type=pathlib.Path, default=DEFAULT_POLICY)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        decision = evaluate(load_json(args.intake), load_json(args.policy))
    except (OSError, QualificationError) as exc:
        print(f"QUALIFICATION: ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "classification": decision.classification,
                "reasons": list(decision.reasons),
                "owner_review_required": decision.owner_review_required,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
