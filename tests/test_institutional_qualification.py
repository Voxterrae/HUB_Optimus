from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import validate

from tools.institutional_qualification import QualificationError, evaluate, main

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


@pytest.mark.parametrize("accepts_pov", [True, False])
def test_paid_hidden_beneficiary_is_held(accepts_pov: bool) -> None:
    intake = paid_intake()
    intake["hidden_reseller_or_commercial_beneficiary"] = True
    intake["accepts_paid_pov"] = accepts_pov
    decision = evaluate(intake, POLICY)
    assert decision.classification == "HOLD_UNQUALIFIED"
    assert any("hidden" in reason.lower() for reason in decision.reasons)
    assert decision.owner_review_required is False


def test_paid_missing_hidden_beneficiary_answer_is_rejected() -> None:
    intake = paid_intake()
    del intake["hidden_reseller_or_commercial_beneficiary"]
    with pytest.raises(QualificationError, match="hidden_reseller_or_commercial_beneficiary"):
        evaluate(intake, POLICY)


@pytest.mark.parametrize("value", [None, 0, 1, "false", "", [], {}])
def test_paid_invalid_hidden_beneficiary_answer_is_rejected(value: object) -> None:
    intake = paid_intake()
    intake["hidden_reseller_or_commercial_beneficiary"] = value
    with pytest.raises(QualificationError, match="hidden_reseller_or_commercial_beneficiary"):
        evaluate(intake, POLICY)


def test_disclosed_paid_diagnostic_request_passes() -> None:
    intake = paid_intake()
    intake["accepts_paid_pov"] = False
    decision = evaluate(intake, POLICY)
    assert decision.classification == "QUALIFIED_DIAGNOSTIC_ONLY"
    assert decision.owner_review_required is False


@pytest.mark.parametrize(
    "key,classification,owner_review",
    [
        ("requires_ownership_or_control", "DECLINE_PROTECTED_RIGHTS", True),
        ("requests_free_bespoke_work", "DECLINE_FREE_BESPOKE_WORK", False),
        ("requires_core_source_transfer", "HOLD_OWNER_RIGHTS_REVIEW", True),
        ("requests_white_label_oem_resale_or_exclusivity", "HOLD_STRATEGIC_RIGHTS_REVIEW", True),
    ],
)
def test_paid_hidden_beneficiary_preserves_prior_rights_gates(
    key: str, classification: str, owner_review: bool
) -> None:
    intake = paid_intake()
    intake["hidden_reseller_or_commercial_beneficiary"] = True
    intake[key] = True
    decision = evaluate(intake, POLICY)
    assert decision.classification == classification
    assert decision.owner_review_required is owner_review


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


GOVERNED_POLICY_FLAGS = [
    (None, "free_bespoke_work_allowed"),
    (None, "core_source_transfer_allowed_by_standard_qualification"),
    (None, "ownership_or_control_allowed"),
    (None, "white_label_oem_resale_requires_owner_review"),
    (None, "paid_diagnostic_required"),
    ("common_good", "requires_nonprofit"),
    ("common_good", "requires_direct_human_or_animal_benefit"),
    ("common_good", "requires_noncommercial_use"),
    ("common_good", "hidden_commercial_beneficiary_allowed"),
    ("common_good", "core_source_transfer_allowed"),
    ("common_good", "ownership_or_control_allowed"),
]

PAID_PATHS = [
    pytest.param({}, id="qualified-paid"),
    pytest.param({"requires_ownership_or_control": True}, id="protected-rights"),
    pytest.param({"requests_free_bespoke_work": True}, id="free-work"),
    pytest.param({"requires_core_source_transfer": True}, id="core-transfer"),
    pytest.param(
        {"requests_white_label_oem_resale_or_exclusivity": True},
        id="strategic-rights",
    ),
    pytest.param({"decision_authority_confirmed": False}, id="unqualified"),
    pytest.param({"accepts_paid_pov": False}, id="diagnostic-only"),
]

QUALIFICATION_PATHS = PAID_PATHS + [
    pytest.param(
        {
            "requested_track": "common_good",
            "organization_type": "nonprofit",
            "verified_nonprofit": True,
            "direct_human_or_animal_benefit": True,
            "intended_commercial_use": False,
        },
        id="common-good-review",
    ),
    pytest.param({"requested_track": "common_good"}, id="common-good-ineligible"),
]


def test_schema_valid_missing_strategic_rights_answer_is_held() -> None:
    intake = paid_intake()
    del intake["requests_white_label_oem_resale_or_exclusivity"]
    schema = json.loads(
        (ROOT / "config/launch/institutional_qualification.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(intake, schema)
    decision = evaluate(intake, POLICY)
    assert decision.classification == "HOLD_STRATEGIC_RIGHTS_REVIEW"
    assert decision.owner_review_required is True
    assert any("missing" in reason.lower() for reason in decision.reasons)


@pytest.mark.parametrize("overrides", PAID_PATHS)
@pytest.mark.parametrize("value", [None, 0, 1, "false", "", [], {}])
def test_paid_invalid_strategic_rights_answer_is_rejected(
    overrides: dict, value: object
) -> None:
    intake = paid_intake()
    intake.update(overrides)
    intake["requests_white_label_oem_resale_or_exclusivity"] = value
    with pytest.raises(
        QualificationError, match="requests_white_label_oem_resale_or_exclusivity"
    ):
        evaluate(intake, POLICY)


@pytest.mark.parametrize("overrides", QUALIFICATION_PATHS)
@pytest.mark.parametrize("section,key", GOVERNED_POLICY_FLAGS)
@pytest.mark.parametrize("mutation", ["missing", "opposite", None, 0, 1, "false", [], {}])
def test_governed_policy_flags_fail_closed_on_every_path(
    overrides: dict, section: str | None, key: str, mutation: object
) -> None:
    policy = deepcopy(POLICY)
    flags = policy if section is None else policy[section]
    if mutation == "missing":
        del flags[key]
    elif mutation == "opposite":
        flags[key] = not flags[key]
    else:
        flags[key] = mutation
    intake = paid_intake()
    intake.update(overrides)
    with pytest.raises(QualificationError, match=key):
        evaluate(intake, policy)


@pytest.mark.parametrize("overrides", QUALIFICATION_PATHS)
@pytest.mark.parametrize("value", [None, [], "invalid"])
def test_malformed_common_good_policy_is_rejected_on_every_path(
    overrides: dict, value: object
) -> None:
    policy = deepcopy(POLICY)
    policy["common_good"] = value
    intake = paid_intake()
    intake.update(overrides)
    with pytest.raises(QualificationError, match="common_good"):
        evaluate(intake, policy)


def test_cli_missing_strategic_rights_answer_returns_hold(tmp_path, capsys) -> None:
    intake = paid_intake()
    del intake["requests_white_label_oem_resale_or_exclusivity"]
    intake_path = tmp_path / "intake.json"
    intake_path.write_text(json.dumps(intake), encoding="utf-8")
    policy_path = ROOT / "config/launch/qualification_policy.v0.1.json"
    assert main([str(intake_path), "--policy", str(policy_path)]) == 0
    captured = capsys.readouterr()
    decision = json.loads(captured.out)
    assert decision["classification"] == "HOLD_STRATEGIC_RIGHTS_REVIEW"
    assert decision["owner_review_required"] is True
    assert captured.err == ""


@pytest.mark.parametrize("malformed", ["intake", "policy"])
def test_cli_malformed_input_returns_error(malformed, tmp_path, capsys) -> None:
    intake = paid_intake()
    policy = deepcopy(POLICY)
    if malformed == "intake":
        intake["requests_white_label_oem_resale_or_exclusivity"] = "false"
    else:
        policy["paid_diagnostic_required"] = False
    intake_path = tmp_path / "intake.json"
    intake_path.write_text(json.dumps(intake), encoding="utf-8")
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    assert main([str(intake_path), "--policy", str(policy_path)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "QUALIFICATION: ERROR:" in captured.err
