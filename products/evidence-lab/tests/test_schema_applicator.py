from __future__ import annotations

import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "apply-dataverse-schema.py"
SPEC = importlib.util.spec_from_file_location("evidence_applicator", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.responses = {}

    def add(self, method, path, response):
        self.responses[(method, path)] = response

    def add_sequence(self, method, path, *responses):
        self.responses[(method, path)] = list(responses)

    def request(self, method, path, *, body=None, headers=None):
        self.calls.append((method, path, body, headers or {}))
        key = (method, path)
        if key not in self.responses:
            return MODULE.Response(404, {}, None)
        response = self.responses[key]
        if isinstance(response, list):
            if not response:
                raise AssertionError(f"No fake response remains for {method} {path}")
            response = response.pop(0)
        return response() if callable(response) else response


class MembershipFreeApplicator(MODULE.SchemaApplicator):
    def require_effective_membership(
        self,
        metadata_id,
        kind,
        description,
        *,
        parent_tables=(),
    ):
        return {
            "metadataId": metadata_id,
            "kind": kind,
            "description": description,
            "mode": "DIRECT_SOLUTION_COMPONENT",
        }


class ApplicatorTests(unittest.TestCase):
    def test_offline_review_is_bound_and_zero_write(self):
        contract, plan = MODULE.load_public_artifacts()
        result = MODULE.offline_review(contract, plan)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["counts"]["expectedFinalDirectComponents"], 11)
        self.assertEqual(result["metadataWritesExecuted"], 0)
        self.assertEqual(result["rowsWritten"], 0)

    def test_odata_encoding_preserves_odata_and_encodes_spaces(self):
        path = (
            "solutions?$select=solutionid&$filter=uniquename eq "
            "'Optimus Evidence Lab'"
        )
        encoded = MODULE.encode_odata_relative_path(path)
        self.assertNotIn(" ", encoded)
        self.assertIn("$filter=uniquename%20eq%20'Optimus%20Evidence%20Lab'", encoded)

    def test_odata_rejects_absolute_urls_control_chars_and_traversal(self):
        for value in (
            "https://example.crm4.dynamics.com/api/data/v9.2/solutions",
            "solutions?x=bad\nvalue",
            "../solutions",
            "solutions\\bad",
        ):
            with self.assertRaises(MODULE.ApplicatorError):
                MODULE.encode_odata_relative_path(value)


    def test_global_choice_lookup_uses_alternate_key_and_escapes_literal(self):
        with tempfile.TemporaryDirectory() as temp:
            transport = FakeTransport()
            journal = MODULE.EvidenceJournal(Path(temp), mode="TEST", target={})
            applicator = MODULE.SchemaApplicator({}, {}, transport, journal, apply=False)
            path = applicator.choice_query("opt_o'brien")
            self.assertEqual(
                path,
                "GlobalOptionSetDefinitions(Name='opt_o''brien')"
                "?$select=MetadataId,Name,IsGlobal,OptionSetType",
            )
            self.assertNotIn("$filter", path)

    def test_optional_global_choice_lookup_treats_404_as_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            transport = FakeTransport()
            journal = MODULE.EvidenceJournal(Path(temp), mode="TEST", target={})
            applicator = MODULE.SchemaApplicator({}, {}, transport, journal, apply=False)
            path = applicator.choice_query("opt_missing")
            self.assertIsNone(applicator.query_single(path, optional=True))

    def test_global_choice_lookup_fails_closed_on_405(self):
        with tempfile.TemporaryDirectory() as temp:
            transport = FakeTransport()
            journal = MODULE.EvidenceJournal(Path(temp), mode="TEST", target={})
            applicator = MODULE.SchemaApplicator({}, {}, transport, journal, apply=False)
            path = applicator.choice_query("opt_bad")
            transport.add(
                "GET",
                path,
                MODULE.Response(405, {}, {"error": {"message": "$filter is not supported"}}),
            )
            with self.assertRaises(MODULE.ApplicatorError):
                applicator.query_single(path, optional=True)

    def test_wait_for_global_choice_retries_404_until_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            transport = FakeTransport()
            journal = MODULE.EvidenceJournal(Path(temp), mode="TEST", target={})
            applicator = MODULE.SchemaApplicator({}, {}, transport, journal, apply=False)
            path = applicator.choice_query("opt_eventual")
            transport.add_sequence(
                "GET",
                path,
                MODULE.Response(404, {}, None),
                MODULE.Response(404, {}, None),
                MODULE.Response(200, {}, {
                    "MetadataId": "00000000-0000-4000-8000-000000000001",
                    "Name": "opt_eventual",
                }),
            )
            result = applicator.wait_for_single(
                path,
                description="global choice opt_eventual",
                timeout_seconds=1,
                interval_seconds=0,
            )
            self.assertEqual(result["Name"], "opt_eventual")
            self.assertEqual(
                len([call for call in transport.calls if call[:2] == ("GET", path)]),
                3,
            )

    def test_global_choice_apply_is_idempotent_after_propagation(self):
        with tempfile.TemporaryDirectory() as temp:
            metadata_id = "00000000-0000-4000-8000-000000000001"
            choice = {
                "logicalName": "opt_testchoice",
                "displayName": "Test Choice",
                "description": "Test Choice",
                "options": [{"value": 884830000, "label": "One"}],
            }
            contract = {"globalChoices": [choice]}
            transport = FakeTransport()
            journal = MODULE.EvidenceJournal(Path(temp), mode="TEST", target={})
            applicator = MembershipFreeApplicator(contract, {}, transport, journal, apply=True)
            path = applicator.choice_query("opt_testchoice")
            existing = {
                "MetadataId": metadata_id,
                "Name": "opt_testchoice",
                "IsGlobal": True,
                "OptionSetType": "Picklist",
            }
            transport.add_sequence(
                "GET", path,
                MODULE.Response(404, {}, None),
                MODULE.Response(200, {}, existing),
                MODULE.Response(200, {}, existing),
            )
            transport.add(
                "POST",
                "GlobalOptionSetDefinitions",
                MODULE.Response(204, {
                    "OData-EntityId": (
                        "https://example.crm4.dynamics.com/api/data/v9.2/"
                        f"GlobalOptionSetDefinitions({metadata_id})"
                    )
                }, None),
            )
            applicator.ensure_choices()
            applicator.ensure_choices()
            posts = [call for call in transport.calls if call[0] == "POST" and call[1] == "GlobalOptionSetDefinitions"]
            self.assertEqual(len(posts), 1)
            self.assertEqual(len(journal.data["created"]), 1)
            self.assertEqual(len(journal.data["reused"]), 1)
            self.assertEqual(applicator.choice_ids["opt_testchoice"], metadata_id)

    def test_payload_counts_and_types(self):
        contract, _ = MODULE.load_public_artifacts()
        self.assertEqual(len(contract["globalChoices"]), 6)
        self.assertEqual(len(contract["tables"]), 5)
        self.assertEqual(sum(len(t["columns"]) for t in contract["tables"]), 50)
        for choice in contract["globalChoices"]:
            payload = MODULE.global_choice_payload(choice)
            self.assertEqual(payload["@odata.type"], "Microsoft.Dynamics.CRM.OptionSetMetadata")
            self.assertTrue(payload["IsGlobal"])
        for table in contract["tables"]:
            payload = MODULE.table_payload(table)
            self.assertEqual(payload["@odata.type"], "Microsoft.Dynamics.CRM.EntityMetadata")
            self.assertIn("PrimaryAttribute", payload)

    def test_column_payloads_bind_global_choices(self):
        contract, _ = MODULE.load_public_artifacts()
        choice_ids = {
            item["logicalName"]: "00000000-0000-4000-8000-000000000001"
            for item in contract["globalChoices"]
        }
        seen = set()
        for table in contract["tables"]:
            for column in table["columns"]:
                payload = MODULE.column_payload(column, choice_ids)
                seen.add(column["type"])
                if column["type"] == "Choice":
                    self.assertIn("GlobalOptionSet@odata.bind", payload)
        self.assertEqual(seen, {"String", "Memo", "Boolean", "DateTime", "Integer", "Decimal", "Choice"})

    def test_relationship_delete_is_restrictive(self):
        contract, _ = MODULE.load_public_artifacts()
        for relationship in contract["relationships"]:
            payload = MODULE.relationship_payload(relationship)
            self.assertEqual(payload["CascadeConfiguration"]["Delete"], "Restrict")


if __name__ == "__main__":
    unittest.main()
