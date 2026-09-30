from __future__ import annotations

import json
from pathlib import Path

POLICY_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "business"
    / "commercial_policy.v0.2.json"
)


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def assert_ordered_range(value: dict, label: str) -> None:
    assert value["minimum"] > 0, label
    assert value["maximum"] >= value["minimum"], label


def test_v02_supersedes_v01_and_is_selective_inbound() -> None:
    policy = load_policy()
    posture = policy["commercial_posture"]

    assert policy["schema_version"] == "0.2"
    assert policy["supersedes"].endswith("commercial_policy.v0.1.json")
    assert posture["selective_inbound_first"] is True
    assert posture["chase_clients_with_free_bespoke_work"] is False
    assert posture["free_qualification_maximum_minutes"] == 30
    assert posture["free_bespoke_deliverables"] is False
    assert posture["paid_commercial_and_public_sector_poc"] is True


def test_platform_canon_and_minimum_engagements_are_material() -> None:
    policy = load_policy()
    services = policy["professional_services"]
    canon = policy["platform_canon_annual_eur"]

    assert services["minimum_engagement_eur"]["general_commercial"] == 15000
    assert services["minimum_engagement_eur"]["enterprise_public"] == 50000
    assert canon["core_business"] == 60000
    assert canon["enterprise"] == 180000
    assert canon["strategic_regulated_public"] == 360000
    assert canon["sovereign_oem_mission_critical_minimum"] == 750000
    assert canon["prepaid"] is True
    assert canon["does_not_transfer_core_ip"] is True


def test_professional_service_ranges_are_ordered() -> None:
    services = load_policy()["professional_services"]

    for section in (
        "diagnostic_architecture_eur",
        "audit_eur",
        "proof_of_value_eur",
        "implementation_eur",
    ):
        for segment, value in services[section].items():
            if isinstance(value, dict) and "minimum" in value:
                assert_ordered_range(value, f"{section}.{segment}")

    assert_ordered_range(
        services["strategic_transformation_eur"], "strategic_transformation_eur"
    )
    assert_ordered_range(
        services["bespoke_rfp_tender_eur"], "bespoke_rfp_tender_eur"
    )
    assert services["day_rates_eur"]["founder_chief_architect"] == 4000
    assert services["day_rates_eur"]["senior_engineering_integration"] == 1800


def test_apps_connectors_and_api_are_separately_monetized() -> None:
    policy = load_policy()
    applications = policy["applications"]
    connectors = policy["connectors"]
    api = policy["api_and_usage"]

    assert applications["platform_canon_still_required"] is True
    assert applications["standard_module_annual_eur"]["minimum"] == 18000
    assert applications["custom_application_build_eur"]["minimum"] == 100000

    assert connectors["connector_is_separate_licensed_product_boundary"] is True
    assert connectors["standard"]["activation_eur"] == 7500
    assert connectors["standard"]["annual_license_eur"] == 12000
    assert connectors["custom"]["annual_maintenance_minimum_eur"] == 24000

    assert api["standard_api_packages"]["base"]["annual_eur"] == 30000
    assert api["standard_api_packages"]["enterprise"]["included_requests"] == 10000000
    assert api["uncommitted_overage_premium_percent"] == 25
    assert api["byok_removes_platform_charges"] is False


def test_embedded_white_label_and_oem_are_distribution_rights() -> None:
    distribution = load_policy()["embedded_iframe_sdk_oem"]
    oem = distribution["oem_resale"]

    assert distribution["embedded_activation_eur"] == 40000
    assert distribution["embedded_per_brand_legal_tenant_annual_eur"] == 60000
    assert distribution["white_label_activation_eur"] == 150000
    assert distribution["white_label_recurring_uplift_percent"] == 50
    assert oem["annual_minimum_guarantee_eur"] == 300000
    assert oem["revenue_share_percent_of_net_downstream_software"] == 15
    assert oem["commercial_rule"] == "GREATER_OF_MINIMUM_GUARANTEE_OR_REVENUE_SHARE"
    assert distribution["ownership_transfered_by_embedding"] is False
    assert distribution["source_code_included_by_default"] is False


def test_environment_and_support_floor_are_explicit() -> None:
    policy = load_policy()
    environments = policy["environments"]
    support = policy["support"]

    assert environments["additional_nonproduction_annual_eur"] == 12000
    assert environments["additional_production_annual_eur"] == 36000
    assert environments["dedicated_isolated_eu_tenant_annual_eur"] == 90000
    assert environments["cloud_and_third_party_costs_separate"] is True

    assert support["premium"]["minimum_annual_eur"] == 36000
    assert support["mission_critical"]["minimum_annual_eur"] == 150000
    assert support["mission_critical"]["service_window"] == "24x7"
    assert support["response_target_is_resolution_guarantee"] is False


def test_channel_pricing_preserves_target_net_value() -> None:
    channel = load_policy()["channel_and_distribution"]

    assert channel["direct_enterprise_preferred"] is True
    assert channel["microsoft_marketplace_minimum_gross_up_percent"] >= 3
    assert channel["merchant_of_record_minimum_gross_up_percent"] >= 5
    assert channel["reseller_margin_percent"]["minimum"] == 20
    assert channel["reseller_margin_requires_defined_funded_duties"] is True
    assert channel["double_discount_allowed_by_default"] is False


def test_no_work_before_clean_commercial_readiness() -> None:
    policy = load_policy()
    procurement = policy["procurement_and_payment"]
    clean_money = policy["clean_money"]

    assert procurement["vendor_activation_retainer_eur"] == 10000
    assert procurement["additional_procurement_support_eur_per_hour"] == 500
    assert procurement["additional_procurement_support_minimum_eur"] == 5000
    assert set(procurement["work_start_conditions"]) == {
        "SIGNED_CONTRACT_OR_BINDING_ORDER",
        "COMPLETE_PROCUREMENT_AND_BILLING_PACK",
        "CLEARED_INITIAL_PAYMENT",
    }
    assert procurement["customer_internal_bureaucracy_included_for_free"] is False

    assert "VERIFIED_BANK_TRANSFER" in clean_money["approved_channels"]
    assert "APPROVED_MERCHANT_OF_RECORD" in clean_money["approved_channels"]
    assert "CASH" in clean_money["prohibited_channels"]
    assert "ANONYMOUS_CRYPTOCURRENCY" in clean_money["prohibited_channels"]
    assert clean_money["customer_bears_bank_fx_intermediary_fees"] is True
    assert clean_money["hub_optimus_retains_own_nontransferable_legal_tax_duties"] is True


def test_common_good_boundary_remains_non_extractive() -> None:
    common_good = load_policy()["common_good"]

    assert common_good["professional_fee_to_approved_beneficiary_eur"] == 0
    assert common_good["direct_third_party_costs"] == "AT_COST_NO_MARGIN"
    assert common_good["profit_from_suffering_allowed"] is False
    assert common_good["percentage_of_donations_allowed"] is False
    assert common_good["beneficiary_data_exploitation_allowed"] is False
    assert common_good["hidden_commercial_beneficiary_allowed"] is False
    assert common_good["public_institution_free_by_default"] is False
    assert common_good["core_ip_transferred"] is False
    assert common_good["unlimited_support_included"] is False


def test_exceptions_remain_owner_controlled() -> None:
    exceptions = load_policy()["exceptions"]

    assert exceptions["owner_only"] is True
    assert exceptions["must_be_written"] is True
    assert exceptions["must_define_scope_duration_consideration_risk_and_precedent"] is True
    assert exceptions["creates_precedent_by_default"] is False
