from __future__ import annotations

import json
from pathlib import Path

from tools.institutional_qualification import evaluate

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads(
    (ROOT / "config" / "launch" / "qualification_policy.v0.1.json").read_text(
        encoding="utf-8"
    )
)


def paid_intake() -> dict:
    return {
        "request_id": "test-1",
        "organization_name": "Example",
        "organization_type": "enterprise",
        "requested_track": "paid",
        "decision_authority_confirmed": True,
        "procurement_owner_confirmed": True,
        "budget_band": "250k_750k",
        "accepts_paid_diagnostic": True,
        "accepts_paid_pov": True,
        "requests_free_bespoke_work": False,
        "requires_core_source_transfer": False,
        "requires_ownership_or_control": False,
        "requests_white_label_oem_resale_or_exclusivity": False,
        "hidden_reseller_or_commercial_beneficiary": False,
        "intended_commercial_use": True,
        "verified_nonprofit": False,
        "direct_human_or_animal_benefit": False,
    }


def test_qualified_paid_request_passes() -> None:
    decision = evaluate(paid_intake(), POLICY)
    assert decision.classification == "QUALIFIED_PAID"
    assert decision.owner_review_required is False


def test_free_bespoke_work_is_declined() -> None:
    intake = paid_intake()
    intake["requests_free_bespoke_work"] = True
    assert evaluate(intake, POLICY).classification == "DECLINE_FREE_BESPOKE_WORK"


def test_enterprise_below_minimum_is_held() -> None:
    intake = paid_intake()
    intake["budget_band"] = "15k_50k"
    assert evaluate(intake, POLICY).classification == "HOLD_UNQUALIFIED"


def test_missing_authority_is_held() -> None:
    intake = paid_intake()
    intake["decision_authority_confirmed"] = False
    decision = evaluate(intake, POLICY)
    assert decision.classification == "HOLD_UNQUALIFIED"
    assert "Decision authority" in decision.reasons[0]


def test_source_transfer_requires_owner_review() -> None:
    intake = paid_intake()
    intake["requires_core_source_transfer"] = True
    decision = evaluate(intake, POLICY)
    assert decision.classification == "HOLD_OWNER_RIGHTS_REVIEW"
    assert decision.owner_review_required is True


def test_white_label_or_oem_requires_strategic_review() -> None:
    intake = paid_intake()
    intake["requests_white_label_oem_resale_or_exclusivity"] = True
    decision = evaluate(intake, POLICY)
    assert decision.classification == "HOLD_STRATEGIC_RIGHTS_REVIEW"
    assert decision.owner_review_required is True


def test_common_good_candidate_routes_to_review() -> None:
    intake = paid_intake()
    intake.update(
        {
            "organization_type": "nonprofit",
            "requested_track": "common_good",
            "budget_band": "under_15k",
            "intended_commercial_use": False,
            "verified_nonprofit": True,
            "direct_human_or_animal_benefit": True,
        }
    )
    decision = evaluate(intake, POLICY)
    assert decision.classification == "COMMON_GOOD_REVIEW"
    assert decision.owner_review_required is True


def test_hidden_commercial_beneficiary_blocks_common_good() -> None:
    intake = paid_intake()
    intake.update(
        {
            "organization_type": "nonprofit",
            "requested_track": "common_good",
            "intended_commercial_use": False,
            "verified_nonprofit": True,
            "direct_human_or_animal_benefit": True,
            "hidden_reseller_or_commercial_beneficiary": True,
        }
    )
    assert evaluate(intake, POLICY).classification == "DECLINE_COMMON_GOOD_INELIGIBLE"
