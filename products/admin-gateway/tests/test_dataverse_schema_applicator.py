from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

PACKAGE_ROOT = Path(__file__).parents[1]
MODULE_PATH = PACKAGE_ROOT / "scripts" / "apply-dataverse-schema.py"
SPEC = importlib.util.spec_from_file_location("apply_dataverse_schema", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
app = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = app
SPEC.loader.exec_module(app)

CONTRACT = json.loads(
    (PACKAGE_ROOT / "dataverse" / "schema" / "optimus-admin-gateway.dataverse.json").read_text(
        encoding="utf-8"
    )
)
PLAN = json.loads(
    (PACKAGE_ROOT / "dataverse" / "plans" / "optimus-admin-gateway.schema-plan.json").read_text(
        encoding="utf-8"
    )
)


def guid(index: int) -> str:
    return f"00000000-0000-4000-8000-{index:012d}"


class FakeTransport:
    def __init__(self) -> None:
        self.next_id = 1
        self.writes: list[tuple[str, str, dict[str, Any] | None, dict[str, str]]] = []
        self.choices: dict[str, dict[str, Any]] = {}
        self.tables: dict[str, dict[str, Any]] = {}
        self.columns: dict[tuple[str, str], dict[str, Any]] = {}
        self.keys: dict[str, list[dict[str, Any]]] = {}
        self.relationships: dict[str, dict[str, Any]] = {}
        self.row_counts: dict[str, int] = {table["entitySetName"]: 0 for table in CONTRACT["tables"]}
        self.solution_id = guid(900000)
        self.solution_members: set[tuple[int, str]] = set()
        self.outside_solution_ids: set[str] = set()
        self.missing_entity_sets: set[str] = set()

    def _new_id(self) -> str:
        value = guid(self.next_id)
        self.next_id += 1
        return value

    @staticmethod
    def _entity_headers(metadata_id: str) -> dict[str, str]:
        return {"OData-EntityId": f"https://example.crm4.dynamics.com/api/data/v9.2/metadata({metadata_id})"}

    def _register_component(self, kind: str, metadata_id: str, headers: dict[str, str]) -> None:
        if headers.get(app.SOLUTION_HEADER) == app.AUTHORIZED_SOLUTION:
            self.solution_members.add((app.COMPONENT_TYPES[kind], metadata_id))

    @staticmethod
    def _path_logical_name(path: str, marker: str = "LogicalName='") -> str | None:
        if marker not in path:
            return None
        return path.split(marker, 1)[1].split("'", 1)[0]

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> app.Response:
        method = method.upper()
        headers = dict(headers or {})
        if method != "GET":
            self.writes.append((method, path, body, headers))

        if method == "GET" and path.startswith("solutions?"):
            return app.Response(
                200,
                {},
                {
                    "value": [
                        {
                            "solutionid": self.solution_id,
                            "uniquename": app.AUTHORIZED_SOLUTION,
                            "friendlyname": "Optimus Admin Gateway",
                            "version": app.AUTHORIZED_VERSION,
                            "ismanaged": False,
                            "publisherid": {
                                "uniquename": app.AUTHORIZED_PUBLISHER,
                                "customizationprefix": app.AUTHORIZED_PREFIX,
                                "customizationoptionvalueprefix": 88483,
                            },
                        }
                    ]
                },
            )
        if method == "GET" and path.startswith("solutioncomponents?"):
            if "objectid eq " in path and "componenttype eq " in path:
                metadata_id = path.split("objectid eq ", 1)[1].split(" ", 1)[0]
                component_type = int(path.split("componenttype eq ", 1)[1].split("&", 1)[0])
                values = []
                if (component_type, metadata_id) in self.solution_members and metadata_id not in self.outside_solution_ids:
                    values = [
                        {
                            "solutioncomponentid": guid(990000 + component_type),
                            "objectid": metadata_id,
                            "componenttype": component_type,
                        }
                    ]
                return app.Response(200, {}, {"value": values})
            return app.Response(
                200, {}, {"@odata.count": len(self.solution_members), "value": []}
            )

        if method == "GET" and path.startswith("GlobalOptionSetDefinitions(Name='"):
            name = path.split("Name='", 1)[1].split("'", 1)[0]
            item = self.choices.get(name)
            return app.Response(404, {}, None) if item is None else app.Response(200, {}, item)
        if method == "GET" and path.startswith("GlobalOptionSetDefinitions("):
            metadata_id = path.split("(", 1)[1].split(")", 1)[0]
            item = next(value for value in self.choices.values() if value["MetadataId"] == metadata_id)
            return app.Response(200, {}, item)
        if method == "POST" and path == "GlobalOptionSetDefinitions":
            assert body is not None
            metadata_id = self._new_id()
            name = body["Name"]
            self.choices[name] = {
                "MetadataId": metadata_id,
                "Name": name,
                "IsGlobal": True,
                "Options": [
                    {"Value": option["Value"], "Label": option["Label"]}
                    for option in body["Options"]
                ],
            }
            self._register_component("GlobalChoice", metadata_id, headers)
            return app.Response(204, self._entity_headers(metadata_id), None)

        if path.startswith("EntityDefinitions(LogicalName='") and ")/Attributes" not in path and ")/Keys" not in path:
            table_name = self._path_logical_name(path)
            assert table_name is not None
            if method == "GET":
                item = self.tables.get(table_name)
                return app.Response(404, {}, None) if item is None else app.Response(200, {}, item)
        if method == "POST" and path == "EntityDefinitions":
            assert body is not None
            metadata_id = self._new_id()
            logical_name = body["SchemaName"].lower()
            primary = body["Attributes"][0]
            self.tables[logical_name] = {
                "MetadataId": metadata_id,
                "LogicalName": logical_name,
                "SchemaName": body["SchemaName"],
                "EntitySetName": body["EntitySetName"],
                "OwnershipType": body["OwnershipType"],
                "PrimaryNameAttribute": primary["SchemaName"].lower(),
                "IsAuditEnabled": body["IsAuditEnabled"],
                "ChangeTrackingEnabled": body["ChangeTrackingEnabled"],
                "HasActivities": body["HasActivities"],
                "HasNotes": body["HasNotes"],
                "_PrimaryMetadata": {
                    "MetadataId": self._new_id(),
                    "LogicalName": primary["SchemaName"].lower(),
                    "SchemaName": primary["SchemaName"],
                    "AttributeType": primary.get("AttributeType", "String"),
                    "RequiredLevel": primary["RequiredLevel"],
                    "MaxLength": primary["MaxLength"],
                    "FormatName": primary["FormatName"],
                    "IsAuditEnabled": primary["IsAuditEnabled"],
                    "IsPrimaryName": True,
                },
            }
            self._register_component("Table", metadata_id, headers)
            return app.Response(204, self._entity_headers(metadata_id), None)

        if ")/Attributes(LogicalName='" in path:
            table_name = self._path_logical_name(path)
            column_name = path.split("/Attributes(LogicalName='", 1)[1].split("'", 1)[0]
            table = self.tables.get(table_name)
            if table is not None and column_name == table["PrimaryNameAttribute"]:
                return app.Response(200, {}, table["_PrimaryMetadata"])
            item = self.columns.get((table_name, column_name))
            return app.Response(404, {}, None) if item is None else app.Response(200, {}, item)
        if method == "POST" and ")/Attributes" in path:
            assert body is not None
            table_name = self._path_logical_name(path)
            assert table_name is not None
            column_metadata_id = self._new_id()
            logical_name = body["SchemaName"].lower()
            item = {
                "MetadataId": column_metadata_id,
                "LogicalName": logical_name,
                "SchemaName": body["SchemaName"],
                "AttributeType": body.get("AttributeType"),
                "RequiredLevel": body["RequiredLevel"],
                "IsAuditEnabled": body["IsAuditEnabled"],
            }
            for key in (
                "MaxLength",
                "DefaultValue",
                "DefaultFormValue",
                "DateTimeBehavior",
                "Format",
                "FormatName",
            ):
                if key in body:
                    item[key] = body[key]
            bind_key = "GlobalOptionSet" + "@odata" + ".bind"
            if bind_key in body:
                choice_metadata_id = body[bind_key].split("(", 1)[1].split(")", 1)[0]
                choice_name = next(
                    name for name, value in self.choices.items()
                    if value["MetadataId"] == choice_metadata_id
                )
                item["GlobalOptionSet"] = {"MetadataId": choice_metadata_id, "Name": choice_name}
            self.columns[(table_name, logical_name)] = item
            self._register_component("Column", column_metadata_id, headers)
            return app.Response(204, self._entity_headers(column_metadata_id), None)

        if method == "GET" and ")/Keys?" in path:
            table_name = self._path_logical_name(path)
            assert table_name is not None
            return app.Response(200, {}, {"value": self.keys.get(table_name, [])})
        if method == "POST" and path.endswith(")/Keys"):
            assert body is not None
            table_name = self._path_logical_name(path)
            assert table_name is not None
            metadata_id = self._new_id()
            item = {
                "MetadataId": metadata_id,
                "SchemaName": body["SchemaName"],
                "KeyAttributes": body["KeyAttributes"],
                "EntityKeyIndexStatus": "Active",
            }
            self.keys.setdefault(table_name, []).append(item)
            self._register_component("AlternateKey", metadata_id, headers)
            return app.Response(204, self._entity_headers(metadata_id), None)

        if method == "GET" and path.startswith("RelationshipDefinitions?"):
            name = path.split("SchemaName eq '", 1)[1].split("'", 1)[0]
            item = self.relationships.get(name)
            return app.Response(
                200,
                {},
                {"value": [] if item is None else [{"MetadataId": item["MetadataId"], "SchemaName": name}]},
            )
        if method == "GET" and path.startswith("RelationshipDefinitions("):
            metadata_id = path.split("(", 1)[1].split(")", 1)[0]
            item = next(value for value in self.relationships.values() if value["MetadataId"] == metadata_id)
            return app.Response(200, {}, item)
        if method == "POST" and path == "RelationshipDefinitions":
            assert body is not None
            metadata_id = self._new_id()
            self.relationships[body["SchemaName"]] = {
                "MetadataId": metadata_id,
                "SchemaName": body["SchemaName"],
                "ReferencedEntity": body["ReferencedEntity"],
                "ReferencingEntity": body["ReferencingEntity"],
                "ReferencedAttribute": body["ReferencedAttribute"],
                "Lookup": {
                    "SchemaName": body["Lookup"]["SchemaName"],
                    "LogicalName": body["Lookup"]["SchemaName"].lower(),
                    "RequiredLevel": body["Lookup"]["RequiredLevel"],
                },
                "CascadeConfiguration": {key.lower(): value for key, value in body["CascadeConfiguration"].items()},
            }
            self._register_component("Relationship", metadata_id, headers)
            return app.Response(204, self._entity_headers(metadata_id), None)

        if method == "POST" and path == "PublishAllXml":
            return app.Response(204, {}, None)

        if method == "GET" and "?$select=" in path and "&$top=1" in path:
            entity_set = path.split("?", 1)[0]
            if entity_set in self.missing_entity_sets:
                return app.Response(404, {}, None)
            rows = [] if self.row_counts.get(entity_set, 0) == 0 else [{"id": guid(800000)}]
            return app.Response(200, {}, {"value": rows})

        if method == "DELETE":
            return app.Response(204, {}, None)

        raise AssertionError(f"Unexpected fake request: {method} {path}")


def make_journal(tmp_path: Path, mode: str = "TEST") -> app.EvidenceJournal:
    return app.EvidenceJournal(
        tmp_path,
        mode=mode,
        target={
            "environmentUrl": "https://example.crm4.dynamics.com/",
            "environmentId": guid(700000),
            "solution": app.AUTHORIZED_SOLUTION,
        },
    )


def rollback_authorization(journal_path: Path) -> dict[str, Any]:
    return {
        "mode": "ROLLBACK_METADATA",
        "environmentUrl": "https://example.crm4.dynamics.com/",
        "environmentId": guid(700000),
        "applicatorCommit": app.AUTHORIZED_BASE_COMMIT,
        "journalSha256": app.hashlib.sha256(journal_path.read_bytes()).hexdigest(),
        "rollbackDecision": (
            "DELETE_ONLY_CREATED_COMPONENTS_IN_REVERSE_ORDER_IF_ALL_TARGET_TABLES_HAVE_ZERO_ROWS"
        ),
    }


def test_offline_review_is_hash_bound_and_non_applying() -> None:
    result = app.offline_plan(CONTRACT, PLAN)
    assert result["authorizedBaseCommit"] == app.AUTHORIZED_BASE_COMMIT
    assert result["contractSha256"] == app.AUTHORIZED_CONTRACT_SHA256
    assert result["planSha256"] == app.AUTHORIZED_PLAN_SHA256
    assert result["apply"] is False
    assert result["tablesCreated"] == result["rowsCreated"] == 0


def test_inspect_only_reports_missing_metadata_without_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    journal = make_journal(tmp_path)
    monkeypatch.setattr(app.time, "sleep", lambda _seconds: None)
    result = app.SchemaApplicator(CONTRACT, PLAN, transport, journal, apply=False).run()
    assert result["mode"] == "INSPECT_ONLY"
    assert result["createdCount"] == 0
    assert result["tablesCreated"] == result["rowsCreated"] == 0
    assert transport.writes == []
    assert any(check["result"] == "WOULD_CREATE" for check in journal.data["checks"])


def test_apply_is_check_first_solution_scoped_and_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(app.time, "sleep", lambda _seconds: None)
    first_journal = make_journal(tmp_path / "first", "APPLY")
    first = app.SchemaApplicator(CONTRACT, PLAN, transport, first_journal, apply=True).run()

    assert first == {
        "mode": "APPLY",
        "createdCount": 57,
        "reusedCount": 0,
        "tablesCreated": 4,
        "rowsCreated": 0,
        "merge": False,
        "deployment": False,
    }
    metadata_creates = [item for item in transport.writes if item[0] == "POST" and item[1] != "PublishAllXml"]
    assert len(metadata_creates) == 57
    assert all(headers.get(app.SOLUTION_HEADER) == app.AUTHORIZED_SOLUTION for _, _, _, headers in metadata_creates)
    assert sum(1 for method, path, _, _ in transport.writes if method == "POST" and path == "PublishAllXml") == 1
    barrier_checks = {check["name"]: check["result"] for check in first_journal.data["checks"]}
    assert barrier_checks["Table metadata propagation barrier"] == "WAIT_15_SECONDS"
    assert barrier_checks["Column metadata propagation barrier"] == "WAIT_15_SECONDS"
    assert barrier_checks["Alternate-key metadata propagation barrier"] == "WAIT_15_SECONDS"

    writes_before = len(transport.writes)
    actual_component_count = len(transport.solution_members)
    second_journal = make_journal(tmp_path / "second", "APPLY")
    second = app.SchemaApplicator(
        CONTRACT,
        PLAN,
        transport,
        second_journal,
        apply=True,
        expected_component_count=actual_component_count,
    ).run()
    new_writes = transport.writes[writes_before:]
    assert second["createdCount"] == 0
    assert second["reusedCount"] == 57
    assert new_writes == []



def test_existing_column_with_wrong_type_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(app.time, "sleep", lambda _seconds: None)
    applicator = app.SchemaApplicator(CONTRACT, PLAN, transport, make_journal(tmp_path), apply=True)
    applicator.verify_target()
    table = CONTRACT["tables"][0]
    applicator.ensure_table(table)
    column = next(item for item in table["columns"] if item["type"] == "String")
    transport.columns[(table["logicalName"], column["logicalName"])] = {
        "MetadataId": guid(444),
        "LogicalName": column["logicalName"],
        "SchemaName": column["schemaName"],
        "AttributeType": "Memo",
        "RequiredLevel": {"Value": column["requiredLevel"]},
        "IsAuditEnabled": {"Value": column["auditEnabled"]},
        "MaxLength": column["maxLength"],
        "Format": "TextArea",
    }
    with pytest.raises(app.ApplicatorError, match="Column type drift"):
        applicator.ensure_column(table, column)


def test_existing_drift_fails_before_creating_more_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(app.time, "sleep", lambda _seconds: None)
    journal = make_journal(tmp_path, "APPLY")
    applicator = app.SchemaApplicator(CONTRACT, PLAN, transport, journal, apply=True)
    applicator.verify_target()
    choice = CONTRACT["globalChoices"][0]
    transport.choices[choice["logicalName"]] = {
        "MetadataId": guid(99),
        "Name": choice["logicalName"],
        "IsGlobal": True,
        "Options": [{"Value": 999, "Label": {}}],
    }
    with pytest.raises(app.ApplicatorError, match="option drift"):
        applicator.ensure_global_choice(choice)
    assert transport.writes == []


def test_rollback_refuses_when_any_business_row_exists(tmp_path: Path) -> None:
    transport = FakeTransport()
    transport.row_counts[CONTRACT["tables"][0]["entitySetName"]] = 1
    journal_path = tmp_path / "journal.json"
    journal_path.write_text(
        json.dumps(
            {
                "mode": "APPLY",
                "contractSha256": app.AUTHORIZED_CONTRACT_SHA256,
                "planSha256": app.AUTHORIZED_PLAN_SHA256,
                "target": {
                    "environmentUrl": "https://example.crm4.dynamics.com/",
                    "environmentId": guid(700000),
                    "solution": app.AUTHORIZED_SOLUTION,
                    "applicatorCommit": app.AUTHORIZED_BASE_COMMIT,
                },
                "created": [
                    {
                        "kind": "Table",
                        "name": CONTRACT["tables"][0]["logicalName"],
                        "metadataId": guid(501),
                        "rollbackPath": f"EntityDefinitions({guid(501)})",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    authorization = rollback_authorization(journal_path)
    with pytest.raises(app.ApplicatorError, match="business rows exist"):
        app.rollback_from_journal(transport, journal_path, authorization, CONTRACT, tmp_path / "out")
    assert [request for request in transport.writes if request[0] == "DELETE"] == []


def test_authorization_templates_are_separate_and_contain_no_private_binding() -> None:
    apply_template = json.loads(
        (PACKAGE_ROOT / "dataverse" / "apply" / "authorization.template.json").read_text(encoding="utf-8")
    )
    rollback_template = json.loads(
        (PACKAGE_ROOT / "dataverse" / "apply" / "rollback-authorization.template.json").read_text(encoding="utf-8")
    )
    for template in (apply_template, rollback_template):
        assert template["authorizedBaseCommit"] == app.AUTHORIZED_BASE_COMMIT
        assert template["contractSha256"] == app.AUTHORIZED_CONTRACT_SHA256
        assert template["planSha256"] == app.AUTHORIZED_PLAN_SHA256
        assert template["expectedCurrentComponentCount"] == 0
        assert template["environmentUrl"] == template["environmentId"] == "REPLACE_IN_PRIVATE_FILE"
        assert template["authorizationId"] == "REPLACE_WITH_PRIVATE_GUID"
    assert apply_template["mode"] == "APPLY_METADATA"
    assert "journalSha256" not in apply_template
    assert rollback_template["mode"] == "ROLLBACK_METADATA"
    assert rollback_template["journalSha256"] == "REPLACE_WITH_EXACT_APPLY_JOURNAL_SHA256"




def _write_private_authorization(
    path: Path, *, mode: str, journal_path: Path | None = None, validity_hours: int = 1
) -> None:
    approved_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload: dict[str, Any] = {
        "schemaVersion": "1.0",
        "mode": mode,
        "authorizationId": guid(990001),
        "authorizedBaseCommit": app.AUTHORIZED_BASE_COMMIT,
        "applicatorCommit": app.AUTHORIZED_BASE_COMMIT,
        "contractSha256": app.AUTHORIZED_CONTRACT_SHA256,
        "planSha256": app.AUTHORIZED_PLAN_SHA256,
        "solutionUniqueName": app.AUTHORIZED_SOLUTION,
        "environmentUrl": "https://example.crm4.dynamics.com/",
        "environmentId": guid(700000),
        "expectedCurrentComponentCount": 0,
        "rollbackDecision": (
            "DELETE_ONLY_CREATED_COMPONENTS_IN_REVERSE_ORDER_IF_ALL_TARGET_TABLES_HAVE_ZERO_ROWS"
        ),
        "afterBusinessRows": "NO_AUTOMATIC_METADATA_DELETION",
        "approvedBy": "owner",
        "approvedAtUtc": approved_at.isoformat(),
        "expiresAtUtc": (approved_at + timedelta(hours=validity_hours)).isoformat(),
    }
    if journal_path is not None:
        payload["journalSha256"] = app.hashlib.sha256(journal_path.read_bytes()).hexdigest()
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_authorization_modes_expiry_and_exact_journal_binding(tmp_path: Path) -> None:
    apply_path = tmp_path / "apply-authorization.json"
    _write_private_authorization(apply_path, mode="APPLY_METADATA")
    loaded = app.load_authorization(
        apply_path,
        "https://example.crm4.dynamics.com/",
        guid(700000),
        0,
        app.AUTHORIZED_BASE_COMMIT,
        expected_mode="APPLY_METADATA",
    )
    assert loaded["mode"] == "APPLY_METADATA"

    too_long = tmp_path / "too-long.json"
    _write_private_authorization(too_long, mode="APPLY_METADATA", validity_hours=5)
    with pytest.raises(app.ApplicatorError, match="no longer than four hours"):
        app.load_authorization(
            too_long,
            "https://example.crm4.dynamics.com/",
            guid(700000),
            0,
            app.AUTHORIZED_BASE_COMMIT,
            expected_mode="APPLY_METADATA",
        )

    journal_path = tmp_path / "apply-journal.json"
    journal_path.write_text("{}", encoding="utf-8")
    rollback_path = tmp_path / "rollback-authorization.json"
    _write_private_authorization(
        rollback_path, mode="ROLLBACK_METADATA", journal_path=journal_path
    )
    rollback = app.load_authorization(
        rollback_path,
        "https://example.crm4.dynamics.com/",
        guid(700000),
        0,
        app.AUTHORIZED_BASE_COMMIT,
        expected_mode="ROLLBACK_METADATA",
        rollback_journal=journal_path,
    )
    assert rollback["journalSha256"] == app.hashlib.sha256(journal_path.read_bytes()).hexdigest()
    journal_path.write_text('{"tampered":true}', encoding="utf-8")
    with pytest.raises(app.ApplicatorError, match="journal SHA-256 mismatch"):
        app.load_authorization(
            rollback_path,
            "https://example.crm4.dynamics.com/",
            guid(700000),
            0,
            app.AUTHORIZED_BASE_COMMIT,
            expected_mode="ROLLBACK_METADATA",
            rollback_journal=journal_path,
        )



def test_environment_url_is_bare_https_dataverse_origin() -> None:
    assert app.normalize_environment_url("https://example.crm4.dynamics.com") == (
        "https://example.crm4.dynamics.com/"
    )
    invalid_host_url = "https:" + "//example.invalid"
    credentialed_origin = "https:" + "//" + "user" + "@example.crm4.dynamics.com"
    for unsafe in (
        "http://example.crm4.dynamics.com",
        "https://example.crm4.dynamics.com/path",
        invalid_host_url,
        credentialed_origin,
    ):
        with pytest.raises(app.ApplicatorError, match="bare HTTPS"):
            app.normalize_environment_url(unsafe)

    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "urllib.parse.urlunsplit" in source

def test_wrapper_defaults_offline_and_apply_is_explicit() -> None:
    wrapper = (
        PACKAGE_ROOT / "dataverse" / "pac" / "Invoke-OptimusDataverseSchemaApply.ps1"
    ).read_text(encoding="utf-8")
    lowered = wrapper.lower()
    assert "defaultparametersetname = 'offline'" in lowered
    assert "[switch]$apply" in lowered
    assert "[switch]$rollback" in lowered
    assert "authorizationfile" in lowered
    assert "access-token file" in lowered
    assert "optimusadmingateway.pre-apply.unmanaged.zip" in lowered
    assert "optimusadmingateway.post-apply.unmanaged.zip" in lowered
    assert "optimusadmingateway.pre-rollback.unmanaged.zip" in lowered
    assert "optimusadmingateway.post-rollback.unmanaged.zip" in lowered
    assert "invoke-expression" not in lowered
    assert "scriptblock]::create" not in lowered


def test_applicator_source_never_logs_token_and_scopes_metadata_creates() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    lowered = source.lower()
    assert 'solution_header = "mscrm.solutionuniquename"' in lowered
    assert "shell=true" not in lowered
    assert "print(self.access_token" not in lowered
    assert '"containssecrets": false' in lowered
    assert "authorized_contract_sha256" in lowered
    assert "authorized_plan_sha256" in lowered
    assert "globaloptionsetdefinitions?$select" not in lowered
    assert "globaloptionsetdefinitions(name='" in lowered



def test_metadata_payloads_use_documented_type_discriminators(tmp_path: Path) -> None:
    choice = CONTRACT["globalChoices"][0]
    choice_payload = app.SchemaApplicator._choice_payload(choice)
    assert choice_payload["@odata.type"] == "Microsoft.Dynamics.CRM.OptionSetMetadata"
    assert choice_payload["OptionSetType"] == "Picklist"
    assert "IsGlobal" not in choice_payload

    for table in CONTRACT["tables"]:
        table_payload = app.SchemaApplicator._table_payload(table)
        primary = table_payload["Attributes"][0]
        assert primary["AttributeType"] == "String"
        assert primary["AttributeTypeName"] == {"Value": "StringType"}
        assert "ChangeTrackingEnabled" in table_payload
        assert "IsChangeTrackingEnabled" not in table_payload

    applicator = app.SchemaApplicator(
        CONTRACT, PLAN, FakeTransport(), make_journal(tmp_path / "payload-contract"), apply=False
    )
    applicator.choice_metadata_ids[choice["logicalName"]] = guid(123)
    samples = {
        "String": next(c for t in CONTRACT["tables"] for c in t["columns"] if c["type"] == "String"),
        "Memo": next(c for t in CONTRACT["tables"] for c in t["columns"] if c["type"] == "Memo"),
        "Boolean": next(c for t in CONTRACT["tables"] for c in t["columns"] if c["type"] == "Boolean"),
        "DateTime": next(c for t in CONTRACT["tables"] for c in t["columns"] if c["type"] == "DateTime"),
        "Choice": next(
            c
            for t in CONTRACT["tables"]
            for c in t["columns"]
            if c["type"] == "Choice" and c["globalChoice"] == choice["logicalName"]
        ),
    }
    expected_names = {
        "String": "StringType",
        "Memo": "MemoType",
        "Boolean": "BooleanType",
        "DateTime": "DateTimeType",
        "Choice": "PicklistType",
    }
    for kind, column in samples.items():
        payload = applicator._column_payload(column)
        assert payload["AttributeTypeName"] == {"Value": expected_names[kind]}
        if kind == "Boolean":
            assert "@odata.type" not in payload["OptionSet"]
            assert payload["OptionSet"]["OptionSetType"] == "Boolean"
    assert applicator._global_choice_path(choice["logicalName"]) == (
        f"GlobalOptionSetDefinitions(Name='{choice['logicalName']}')"
    )

def test_zero_row_rollback_deletes_only_journaled_paths_in_reverse_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(app.time, "sleep", lambda _seconds: None)
    journal_path = tmp_path / "journal.json"
    journal_path.write_text(
        json.dumps(
            {
                "mode": "APPLY",
                "contractSha256": app.AUTHORIZED_CONTRACT_SHA256,
                "planSha256": app.AUTHORIZED_PLAN_SHA256,
                "target": {
                    "environmentUrl": "https://example.crm4.dynamics.com/",
                    "environmentId": guid(700000),
                    "solution": app.AUTHORIZED_SOLUTION,
                    "applicatorCommit": app.AUTHORIZED_BASE_COMMIT,
                },
                "created": [
                    {
                        "kind": "GlobalChoice",
                        "name": CONTRACT["globalChoices"][0]["logicalName"],
                        "metadataId": guid(601),
                        "rollbackPath": f"GlobalOptionSetDefinitions({guid(601)})",
                    },
                    {
                        "kind": "Table",
                        "name": CONTRACT["tables"][0]["logicalName"],
                        "metadataId": guid(602),
                        "rollbackPath": f"EntityDefinitions({guid(602)})",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    authorization = rollback_authorization(journal_path)
    result = app.rollback_from_journal(
        transport, journal_path, authorization, CONTRACT, tmp_path / "rollback"
    )
    deletes = [path for method, path, _body, _headers in transport.writes if method == "DELETE"]
    assert deletes == [
        f"EntityDefinitions({guid(602)})",
        f"GlobalOptionSetDefinitions({guid(601)})",
    ]
    assert result["zeroRowsVerified"] is True
    assert result["customizationsPublished"] is True
    assert result["rowsDeleted"] == 0


def test_exact_existing_component_outside_solution_fails_before_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(app.time, "sleep", lambda _seconds: None)
    choice = CONTRACT["globalChoices"][0]
    metadata_id = guid(777)
    transport.choices[choice["logicalName"]] = {
        "MetadataId": metadata_id,
        "Name": choice["logicalName"],
        "IsGlobal": True,
        "Options": [
            {"Value": option["value"], "Label": app.label(option["label"])}
            for option in choice["options"]
        ],
    }
    with pytest.raises(app.ApplicatorError, match="not a component of solution"):
        app.SchemaApplicator(
            CONTRACT, PLAN, transport, make_journal(tmp_path), apply=True
        ).run()
    assert transport.writes == []




def test_relationship_lookup_collision_fails_during_full_preflight_before_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = FakeTransport()
    monkeypatch.setattr(app.time, "sleep", lambda _seconds: None)

    seed = app.SchemaApplicator(
        CONTRACT, PLAN, transport, make_journal(tmp_path / "seed", "APPLY"), apply=True
    )
    seed.run()

    relationship = CONTRACT["relationships"][0]
    relationship_metadata = transport.relationships.pop(relationship["schemaName"])
    transport.solution_members.discard(
        (app.COMPONENT_TYPES["Relationship"], relationship_metadata["MetadataId"])
    )
    collision_id = guid(880000)
    transport.columns[(
        relationship["referencingTable"], relationship["lookup"]["logicalName"]
    )] = {
        "MetadataId": collision_id,
        "LogicalName": relationship["lookup"]["logicalName"],
        "SchemaName": relationship["lookup"]["schemaName"],
        "AttributeType": "String",
    }
    transport.solution_members.add((app.COMPONENT_TYPES["Column"], collision_id))
    transport.writes.clear()

    with pytest.raises(app.ApplicatorError, match="lookup name collision"):
        app.SchemaApplicator(
            CONTRACT,
            PLAN,
            transport,
            make_journal(tmp_path / "collision", "APPLY"),
            apply=True,
            expected_component_count=len(transport.solution_members),
        ).run()
    assert transport.writes == []

def test_numeric_key_status_uses_documented_active_value_two() -> None:
    assert app.normalize_key_index_status(0) == "Pending"
    assert app.normalize_key_index_status(1) == "InProgress"
    assert app.normalize_key_index_status(2) == "Active"
    assert app.normalize_key_index_status(3) == "Failed"


def test_rollback_rejects_tampered_or_cross_environment_journal(tmp_path: Path) -> None:
    transport = FakeTransport()
    metadata_id = guid(701)
    journal_path = tmp_path / "tampered.json"
    journal_path.write_text(
        json.dumps(
            {
                "mode": "APPLY",
                "contractSha256": app.AUTHORIZED_CONTRACT_SHA256,
                "planSha256": app.AUTHORIZED_PLAN_SHA256,
                "target": {
                    "environmentUrl": "https:" + "//other.crm4.dynamics.com/",
                    "environmentId": guid(799999),
                    "solution": app.AUTHORIZED_SOLUTION,
                    "applicatorCommit": app.AUTHORIZED_BASE_COMMIT,
                },
                "created": [
                    {
                        "kind": "Table",
                        "name": CONTRACT["tables"][0]["logicalName"],
                        "metadataId": metadata_id,
                        "rollbackPath": "EntityDefinitions(main)",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(app.ApplicatorError, match="environment URL mismatch"):
        app.rollback_from_journal(
            transport, journal_path, rollback_authorization(journal_path), CONTRACT, tmp_path / "out"
        )
    assert [item for item in transport.writes if item[0] == "DELETE"] == []




def test_rollback_rejects_allowlist_path_tampering(tmp_path: Path) -> None:
    transport = FakeTransport()
    metadata_id = guid(703)
    journal_path = tmp_path / "tampered-path.json"
    journal_path.write_text(
        json.dumps(
            {
                "mode": "APPLY",
                "contractSha256": app.AUTHORIZED_CONTRACT_SHA256,
                "planSha256": app.AUTHORIZED_PLAN_SHA256,
                "target": {
                    "environmentUrl": "https://example.crm4.dynamics.com/",
                    "environmentId": guid(700000),
                    "solution": app.AUTHORIZED_SOLUTION,
                    "applicatorCommit": app.AUTHORIZED_BASE_COMMIT,
                },
                "created": [
                    {
                        "kind": "Table",
                        "name": CONTRACT["tables"][0]["logicalName"],
                        "metadataId": metadata_id,
                        "rollbackPath": "EntityDefinitions(main)",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(app.ApplicatorError, match="path is not allowlisted"):
        app.rollback_from_journal(
            transport, journal_path, rollback_authorization(journal_path), CONTRACT, tmp_path / "out"
        )
    assert [item for item in transport.writes if item[0] == "DELETE"] == []


def test_rollback_requires_exact_solution_and_applicator_commit(tmp_path: Path) -> None:
    transport = FakeTransport()
    journal_path = tmp_path / "wrong-target.json"
    journal_path.write_text(
        json.dumps(
            {
                "mode": "APPLY",
                "contractSha256": app.AUTHORIZED_CONTRACT_SHA256,
                "planSha256": app.AUTHORIZED_PLAN_SHA256,
                "target": {
                    "environmentUrl": "https://example.crm4.dynamics.com/",
                    "environmentId": guid(700000),
                    "solution": "OtherSolution",
                    "applicatorCommit": app.AUTHORIZED_BASE_COMMIT,
                },
                "created": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(app.ApplicatorError, match="solution mismatch"):
        app.rollback_from_journal(
            transport, journal_path, rollback_authorization(journal_path), CONTRACT, tmp_path / "out"
        )

def test_rollback_tolerates_target_tables_that_are_already_absent(tmp_path: Path) -> None:
    transport = FakeTransport()
    transport.missing_entity_sets = {table["entitySetName"] for table in CONTRACT["tables"]}
    metadata_id = guid(702)
    journal_path = tmp_path / "partial.json"
    journal_path.write_text(
        json.dumps(
            {
                "mode": "APPLY",
                "contractSha256": app.AUTHORIZED_CONTRACT_SHA256,
                "planSha256": app.AUTHORIZED_PLAN_SHA256,
                "target": {
                    "environmentUrl": "https://example.crm4.dynamics.com/",
                    "environmentId": guid(700000),
                    "solution": app.AUTHORIZED_SOLUTION,
                    "applicatorCommit": app.AUTHORIZED_BASE_COMMIT,
                },
                "created": [
                    {
                        "kind": "GlobalChoice",
                        "name": CONTRACT["globalChoices"][0]["logicalName"],
                        "metadataId": metadata_id,
                        "rollbackPath": f"GlobalOptionSetDefinitions({metadata_id})",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = app.rollback_from_journal(
        transport, journal_path, rollback_authorization(journal_path), CONTRACT, tmp_path / "rollback-absent"
    )
    assert result["zeroRowsVerified"] is True
    assert result["deleted"][0]["status"] == "DELETED"
