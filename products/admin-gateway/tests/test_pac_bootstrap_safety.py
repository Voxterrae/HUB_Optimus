from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).parents[1]


def test_pac_bootstrap_is_dry_run_first_and_has_no_dynamic_script_execution() -> None:
    content = (
        PACKAGE_ROOT / "dataverse" / "pac" / "bootstrap-solution.ps1"
    ).read_text(encoding="utf-8")
    lowered = content.lower()

    assert "[switch]$apply" in lowered
    assert "if (-not $apply)" in lowered
    assert "scriptblock]::create" not in lowered
    assert "invoke-expression" not in lowered
    assert "& pac @arguments" in lowered
    assert "unexpected executable in reviewed plan" in lowered
    assert "[string]$publishername = 'hub_optimus'" in lowered
    assert "[string]$publisherprefix = 'opt'" in lowered


def test_schema_dry_run_preflight_is_read_only_and_has_no_apply_surface() -> None:
    content = (
        PACKAGE_ROOT
        / "dataverse"
        / "pac"
        / "Test-OptimusDataverseSchemaPlan.ps1"
    ).read_text(encoding="utf-8")
    lowered = content.lower()

    assert "[switch]$apply" not in lowered
    assert "invoke-restmethod" not in lowered
    assert "invoke-webrequest" not in lowered
    assert "add-solution-component" not in lowered
    assert "\'solution\', \'import\'" not in lowered
    assert "\'solution\', \'export\'" not in lowered
    assert "\'solution\', \'add-solution-component\'" not in lowered
    assert "\'env\', \'create\'" not in lowered
    assert "'env', 'who'" in lowered
    assert "'env', 'fetch'" in lowered
    assert "'--xmlfile'" in lowered
    assert "'--xml'," not in lowered
    assert "set-content -literalpath $solutionfetchpath -encoding utf8nobom" in lowered
    assert "set-content -literalpath $componentfetchpath -encoding utf8nobom" in lowered
    assert "tables created:          0" in lowered
    assert "rows created:            0" in lowered


def test_approval_blueprint_targets_numeric_schema_contract_values() -> None:
    blueprint_path = (
        PACKAGE_ROOT
        / "power-platform"
        / "flows"
        / "approval-flow.blueprint.yaml"
    )
    content = blueprint_path.read_text(encoding="utf-8")
    blueprint = yaml.safe_load(content)

    assert "table: opt_adminrequest" in content
    assert (
        "filter: opt_mutation eq true and opt_dryrun eq false and "
        "opt_requeststate eq 884831003"
    ) in content
    assert "decision: 884832000" in content
    assert "decision: 884832001" in content
    assert "preserve_original_plan_digest: true" in content
    assert "opt_state eq 'APPROVAL_REQUIRED'" not in content
    assert "opt_adminrequests" not in content
    assert "approved_at_source: utc_approval_decision" in content
    assert "capture_approved_at_from_utc_approval_decision" in content
    assert content.index("capture_approved_at_from_utc_approval_decision") < content.index(
        "persist_complete_signed_approval_receipt"
    )
    assert content.index("persist_complete_signed_approval_receipt") < content.index(
        "call_gateway_execute_with_original_parameters"
    )
    assert "sign_v1_length_prefixed_receipt_using_tenant_service" in content
    controls = blueprint["controls"]
    assert controls["signature_profile"] == "hmac-sha256-lp-v1"
    assert controls["signature_algorithm"] == "hmac-sha256"
    assert controls["signature_encoding"] == "lowercase-hex-64"
    assert controls["signature_material"] == {
        "domain_ascii": "HUB_OPTIMUS_APPROVAL_RECEIPT",
        "domain_suffix_hex": "00",
        "ordered_field_count": 5,
        "field_count_prefix": "none",
        "field_encoding": "utf-8-strict",
        "length_prefix": "uint32-big-endian",
        "bom": "forbidden",
        "separator": "none",
        "trailing_bytes": "forbidden",
        "unicode_normalization": "none",
        "timestamp_encoding": "utc-plus-00:00-seconds-with-optional-six-digit-fraction",
        "secret_encoding": "utf-8-exact-no-trim-or-base64",
        "secret_minimum_bytes": 32,
        "secret_scope": "dedicated-per-tenant-environment-purpose",
        "binary_framing_owner": "tenant_signer_service",
        "legacy_fallback": False,
    }
    assert controls["signed_receipt_fields"] == [
        "signature_profile",
        "approval_id",
        "plan_hash",
        "approved_by",
        "approved_at",
    ]
