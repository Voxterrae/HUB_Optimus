from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


PACKAGE_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = PACKAGE_ROOT / "dataverse" / "schema" / "optimus-admin-gateway.dataverse.json"
META_SCHEMA_PATH = PACKAGE_ROOT / "dataverse" / "schema" / "optimus-admin-gateway.dataverse.schema.json"
PLAN_PATH = PACKAGE_ROOT / "dataverse" / "plans" / "optimus-admin-gateway.schema-plan.json"
BUILDER_PATH = PACKAGE_ROOT / "scripts" / "build-dataverse-schema-plan.py"
FLOW_PATH = PACKAGE_ROOT / "power-platform" / "flows" / "approval-flow.blueprint.yaml"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_contract_validates_and_uses_the_verified_solution_identity() -> None:
    contract = _load_contract()
    meta_schema = json.loads(META_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(meta_schema).validate(contract)

    assert contract["solution"] == {
        "uniqueName": "OptimusAdminGateway",
        "displayName": "Optimus Admin Gateway",
        "publisher": "HUB_Optimus",
        "prefix": "opt",
        "choiceValuePrefix": 88483,
        "version": "0.1.0.0",
        "packageType": "Unmanaged",
        "baseLanguageCode": 1033,
    }
    assert contract["deployment"]["applyDefault"] is False


def test_choices_have_explicit_non_overlapping_publisher_scoped_values() -> None:
    contract = _load_contract()
    choices = contract["globalChoices"]
    assert [choice["logicalName"] for choice in choices] == [
        "opt_adminrisk",
        "opt_adminrequeststate",
        "opt_adminapprovaldecision",
        "opt_adminjobstate",
    ]

    values = [
        option["value"]
        for choice in choices
        for option in choice["options"]
    ]
    assert len(values) == len(set(values))
    assert all(str(value).startswith("88483") for value in values)
    assert min(values) == 884830000
    assert max(values) == 884833004


def test_table_names_columns_keys_and_payload_limits_are_fail_closed() -> None:
    contract = _load_contract()
    table_names = {table["logicalName"] for table in contract["tables"]}
    assert table_names == {
        "opt_adminrequest",
        "opt_adminapproval",
        "opt_adminjob",
        "opt_adminevent",
    }

    choice_names = {choice["logicalName"] for choice in contract["globalChoices"]}
    sensitive = set(contract["privacy"]["sensitiveColumns"])
    key_pattern = contract["conventions"]["alternateKeyPattern"]
    forbidden_key_characters = set("/#<>*%&:\\?+")

    all_logical_names: set[tuple[str, str]] = set()
    for table in contract["tables"]:
        assert table["auditEnabled"] is True
        assert table["changeTrackingEnabled"] is True
        assert table["hasActivities"] is False
        assert table["hasNotes"] is False
        assert table["primaryName"]["logicalName"] == "opt_name"

        columns = {column["logicalName"]: column for column in table["columns"]}
        assert len(columns) == len(table["columns"])
        for logical_name, column in columns.items():
            assert (table["logicalName"], logical_name) not in all_logical_names
            all_logical_names.add((table["logicalName"], logical_name))
            assert not logical_name.lower().endswith("id")
            if column["type"] == "Choice":
                assert column["globalChoice"] in choice_names
            if column["type"] == "DateTime":
                assert column["behavior"] == "UserLocal"
                assert column["format"] == "DateAndTime"
            if column["type"] == "Memo":
                assert column["auditEnabled"] is False
                assert column["containsSensitiveData"] is True
                assert column["maxLength"] <= 131072
                assert logical_name in sensitive

        for key in table["alternateKeys"]:
            for column_name in key["columns"]:
                column = columns[column_name]
                assert column["type"] == "String"
                assert column["maxLength"] <= 128
                assert column["pattern"] == key_pattern
                assert not forbidden_key_characters.intersection(column_name)

    assert sensitive == {
        "opt_parametersjson",
        "opt_requesterdisplayname",
        "opt_targetsummary",
        "opt_reason",
        "opt_decidedbydisplayname",
        "opt_receiptjson",
        "opt_outputsummaryjson",
        "opt_payloadjson",
    }


def test_relationships_are_explicit_restrictive_and_reference_declared_tables() -> None:
    contract = _load_contract()
    table_names = {table["logicalName"] for table in contract["tables"]}
    relationships = contract["relationships"]
    assert len(relationships) == 4

    for relationship in relationships:
        assert relationship["referencedTable"] in table_names
        assert relationship["referencingTable"] in table_names
        assert not relationship["lookup"]["logicalName"].lower().endswith("id")
        assert relationship["cascade"] == {
            "assign": "NoCascade",
            "delete": "Restrict",
            "merge": "NoCascade",
            "reparent": "NoCascade",
            "share": "NoCascade",
            "unshare": "NoCascade",
        }


def test_deterministic_plan_is_current_non_applying_and_hash_bound() -> None:
    subprocess.run([sys.executable, str(BUILDER_PATH)], cwd=PACKAGE_ROOT, check=True)
    contract = _load_contract()
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))

    assert plan["mode"] == "DRY_RUN"
    assert plan["apply"] is False
    assert plan["safety"] == {
        "containsExecutableMutationCommands": False,
        "environmentBinding": "private-runtime-only",
        "requiresExplicitApplyAuthorization": True,
        "tablesCreatedByThisPlan": 0,
        "rowsCreatedByThisPlan": 0,
        "merge": False,
        "deployment": False,
    }
    assert plan["counts"] == {
        "globalChoices": 4,
        "choiceOptions": 21,
        "tables": 4,
        "primaryColumns": 4,
        "scalarColumns": 41,
        "lookupColumns": 4,
        "alternateKeys": 4,
        "relationships": 4,
        "plannedActions": 60,
    }
    assert plan["contractSha256"] == hashlib.sha256(_canonical_bytes(contract)).hexdigest()

    unsigned = dict(plan)
    plan_hash = unsigned.pop("planHash")
    assert plan_hash == hashlib.sha256(_canonical_bytes(unsigned)).hexdigest()
    assert not any("environmentUrl" in action for action in plan["actions"])


def test_approval_flow_uses_numeric_choice_values_and_exact_plan_digest() -> None:
    flow = yaml.safe_load(FLOW_PATH.read_text(encoding="utf-8"))
    assert flow["trigger"]["table"] == "opt_adminrequest"
    assert flow["trigger"]["filter"] == (
        "opt_mutation eq true and opt_dryrun eq false and "
        "opt_requeststate eq 884831003"
    )
    assert flow["controls"] == {
        "mutation_only": True,
        "dry_run_must_be_false": True,
        "disallow_self_approval": True,
        "preserve_original_plan_digest": True,
        "numeric_choice_values_only": True,
        "receipt_plan_hash_source": "opt_plandigest",
        "approved_at_source": "utc_approval_decision",
        "signature_profile": "hmac-sha256-lp-v1",
        "signature_algorithm": "hmac-sha256",
        "signature_encoding": "lowercase-hex-64",
        "signature_material": {
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
        },
        "signed_receipt_fields": [
            "signature_profile",
            "approval_id",
            "plan_hash",
            "approved_by",
            "approved_at",
        ],
        "automatic_send_email": False,
    }
    approval_steps = flow["steps"][4]["on_approve"]
    assert approval_steps[0] == "capture_approved_at_from_utc_approval_decision"
    assert approval_steps[1] == "sign_v1_length_prefixed_receipt_using_tenant_service"
    persisted = approval_steps[2]["persist_complete_signed_approval_receipt"]
    assert persisted == {
        "table": "opt_adminapproval",
        "decision": 884832000,
        "bind_request_lookup": True,
    }
    assert approval_steps[3] == {"update_request_state": 884831004}
    assert approval_steps[4] == "call_gateway_execute_with_original_parameters"
    assert flow["steps"][5]["on_reject"][0]["create_opt_adminapproval"]["decision"] == 884832001


def test_api_and_connector_expose_the_alternate_key_safe_identifier_pattern() -> None:
    safe_pattern = r"^[A-Za-z0-9._-]{8,128}$"
    connector = json.loads(
        (PACKAGE_ROOT / "power-platform" / "custom-connector" / "apiDefinition.swagger.json").read_text(
            encoding="utf-8"
        )
    )
    openapi = yaml.safe_load(
        (PACKAGE_ROOT / "openapi" / "optimus-admin-gateway.openapi.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert connector["definitions"]["OperationRequest"]["properties"]["idempotency_key"]["pattern"] == safe_pattern
    assert connector["definitions"]["ApprovalReceipt"]["properties"]["approval_id"]["pattern"] == safe_pattern
    assert openapi["components"]["schemas"]["OperationRequest"]["properties"]["idempotency_key"]["pattern"] == safe_pattern
    assert openapi["components"]["schemas"]["ApprovalReceipt"]["properties"]["approval_id"]["pattern"] == safe_pattern
