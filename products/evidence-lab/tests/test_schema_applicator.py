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

    def request(self, method, path, *, body=None, headers=None):
        self.calls.append((method, path, body, headers or {}))
        key = (method, path)
        if key not in self.responses:
            return MODULE.Response(404, {}, None)
        response = self.responses[key]
        return response() if callable(response) else response


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
