from __future__ import annotations

import importlib.util
import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "apply-dataverse-schema.py"
SPEC = importlib.util.spec_from_file_location("evidence_membership", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeTransport:
    def __init__(self, records):
        self.records = records

    def request(self, method, path, *, body=None, headers=None):
        if method == "GET" and path.startswith("solutioncomponents?"):
            for metadata_id, records in self.records.items():
                if f"objectid eq {metadata_id}" in path:
                    return MODULE.Response(200, {}, {"value": records})
            return MODULE.Response(200, {}, {"value": []})
        return MODULE.Response(404, {}, None)


class MembershipTests(unittest.TestCase):
    def make(self, records):
        contract, plan = MODULE.load_public_artifacts()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        journal = MODULE.EvidenceJournal(Path(temp.name), mode="TEST", target={})
        app = MODULE.SchemaApplicator(contract, plan, FakeTransport(records), journal, apply=False)
        app.solution_id = "00000000-0000-4000-8000-000000000100"
        app.table_ids["opt_observation"] = "00000000-0000-4000-8000-000000000200"
        return app

    def test_direct_membership_is_accepted(self):
        component = "00000000-0000-4000-8000-000000000300"
        app = self.make({component: [{"rootcomponentbehavior": None}]})
        result = app.require_effective_membership(component, "Column", "direct")
        self.assertEqual(result["mode"], "DIRECT_SOLUTION_COMPONENT")

    def test_table_root_behavior_zero_includes_subcomponent(self):
        root = "00000000-0000-4000-8000-000000000200"
        child = "00000000-0000-4000-8000-000000000301"
        app = self.make({root: [{"rootcomponentbehavior": 0}], child: []})
        result = app.require_effective_membership(
            child, "Column", "included", parent_tables=("opt_observation",)
        )
        self.assertEqual(result["mode"], "INCLUDED_VIA_TABLE_ROOT")
        self.assertEqual(result["rootComponentBehavior"], 0)

    def test_nonzero_root_behavior_does_not_include_subcomponent(self):
        root = "00000000-0000-4000-8000-000000000200"
        child = "00000000-0000-4000-8000-000000000302"
        app = self.make({root: [{"rootcomponentbehavior": 1}], child: []})
        with self.assertRaises(MODULE.ApplicatorError):
            app.require_effective_membership(
                child, "Column", "orphan", parent_tables=("opt_observation",)
            )

    def test_missing_root_rejects_real_orphan(self):
        child = "00000000-0000-4000-8000-000000000303"
        app = self.make({child: []})
        with self.assertRaises(MODULE.ApplicatorError):
            app.require_effective_membership(
                child, "AlternateKey", "orphan", parent_tables=("opt_observation",)
            )


if __name__ == "__main__":
    unittest.main()
