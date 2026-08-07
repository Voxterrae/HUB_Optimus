from __future__ import annotations

import json
from pathlib import Path

POLICY_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "business"
    / "commercial_policy.v0.1.json"
)


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_paid_client_classes_fail_closed() -> None:
    policy = load_policy()
    classes = policy["customer_classes"]

    assert classes["commercial_company"]["paid_by_default"] is True
    assert classes["enterprise"]["paid_by_default"] is True
    assert classes["public_institution"]["paid_by_default"] is True
    assert classes["commercial_company"]["free_custom_poc_allowed"] is False
    assert classes["enterprise"]["free_custom_poc_allowed"] is False
    assert classes["public_institution"]["free_custom_poc_allowed"] is False


def test_free_qualification_contains_no_bespoke_delivery() -> None:
    qualification = load_policy()["qualification"]

    assert qualification["free_once"] is True
    assert qualification["maximum_minutes"] == 30
    assert qualification["bespoke_deliverables_allowed"] is False
    assert qualification["custom_architecture_allowed"] is False
    assert qualification["custom_code_allowed"] is False
    assert qualification["custom_report_allowed"] is False


def test_common_good_is_free_without_transferring_core() -> None:
    policy = load_policy()
    public_benefit = policy["customer_classes"]["qualifying_public_benefit"]
    common_good = policy["common_good"]

    assert public_benefit["professional_fee_eur"] == 0
    assert public_benefit["direct_third_party_costs"] == "AT_COST_NO_MARGIN"
    assert public_benefit["noncommercial_use_only"] is True
    assert public_benefit["core_ip_transferred"] is False
    assert public_benefit["unlimited_support_included"] is False
    assert common_good["percentage_of_donations_allowed"] is False
    assert common_good["profit_based_on_suffering_allowed"] is False
    assert common_good["beneficiary_data_sale_allowed"] is False
    assert common_good["hidden_commercial_beneficiary_allowed"] is False
    assert common_good["public_institutions_eligible_by_default"] is False


def test_price_ranges_are_positive_and_ordered() -> None:
    price_book = load_policy()["price_book"]

    for name, value in price_book.items():
        if isinstance(value, dict) and "minimum" in value and "maximum" in value:
            assert value["minimum"] > 0, name
            assert value["maximum"] >= value["minimum"], name

    assert price_book["founder_architecture_day_rate"] == 2500
    assert price_book["engineering_integration_day_rate"] == 1500
    assert price_book["urgent_multiplier"] == 1.5


def test_payment_percentages_balance() -> None:
    payment = load_policy()["payment_terms"]

    assert sum(payment["larger_diagnostic"]) == 100
    assert sum(payment["pilot"]) == 100
    assert sum(payment["implementation_above_45000"]) == 100


def test_discount_and_exception_authority() -> None:
    policy = load_policy()

    assert policy["discount_policy"][
        "maximum_without_explicit_owner_decision_percent"
    ] == 15
    assert policy["discount_policy"]["exposure_is_consideration"] is False
    assert policy["exceptions"]["owner_only"] is True
    assert policy["exceptions"]["must_be_written"] is True
    assert policy["exceptions"]["creates_precedent_by_default"] is False


def test_common_good_reserve_is_present() -> None:
    common_good = load_policy()["common_good"]

    assert (
        common_good[
            "initial_reserve_percent_of_collected_net_commercial_service_revenue"
        ]
        == 5
    )
    assert common_good["owner_may_increase_commitment"] is True


def test_joint_venture_does_not_imply_core_transfer() -> None:
    joint_venture = load_policy()["joint_venture"]

    assert joint_venture["requires_written_owner_approved_agreement"] is True
    assert joint_venture["funded_current_delivery_by_default"] is True
    assert joint_venture["pure_equity_replaces_cash_by_default"] is False
    assert joint_venture["core_ownership_transferred_by_default"] is False
