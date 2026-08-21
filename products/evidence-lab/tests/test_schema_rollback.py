from __future__ import annotations

import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "apply-dataverse-schema.py"
SPEC = importlib.util.spec_from_file_location("evidence_rollback", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RollbackTransport:
    def __init__(self, *, rows=False, absent_parent=False):
        self.rows = rows
        self.absent_parent = absent_parent
        self.deletes = []
        self.publications = 0

    def request(self, method, path, *, body=None, headers=None):
        if method == "GET" and path.startswith("EntityDefinitions(LogicalName="):
            if self.absent_parent and "opt_observation" in path:
                return MODULE.Response(404, {}, None)
            if "/" not in path.split("?")[0]:
                return MODULE.Response(200, {}, {"EntitySetName": "opt_rows"})
        if method == "GET" and path.startswith("opt_rows?"):
            return MODULE.Response(200, {}, {"value": [{"id": "x"}] if self.rows else []})
        if method == "DELETE":
            self.deletes.append(path)
            return MODULE.Response(204, {}, None)
        if method == "POST" and path == "PublishAllXml":
            self.publications += 1
            return MODULE.Response(204, {}, None)
        return MODULE.Response(404, {}, None)


class RollbackTests(unittest.TestCase):
    def make_journal(self, directory: Path):
        journal = {
            "schemaVersion": "1.0",
            "contractSha256": MODULE.AUTHORIZED_CONTRACT_SHA256,
            "planSha256": MODULE.AUTHORIZED_PLAN_SHA256,
            "created": [
                {
                    "kind": "GlobalChoice",
                    "name": "opt_testchoice",
                    "deletePath": "GlobalOptionSetDefinitions(00000000-0000-4000-8000-000000000001)",
                    "parentTables": [],
                },
                {
                    "kind": "Table",
                    "name": "opt_observation",
                    "deletePath": "EntityDefinitions(00000000-0000-4000-8000-000000000002)",
                    "parentTables": ["opt_observation"],
                },
                {
                    "kind": "Column",
                    "name": "opt_observation.opt_test",
                    "deletePath": "EntityDefinitions(LogicalName='opt_observation')/Attributes(00000000-0000-4000-8000-000000000003)",
                    "parentTables": ["opt_observation"],
                },
            ],
        }
        path = directory / "journal.json"
        path.write_text(json.dumps(journal), encoding="utf-8")
        return path

    def test_reverse_journal_order_and_single_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            journal = self.make_journal(directory)
            transport = RollbackTransport()
            result = MODULE.rollback_from_journal(transport, journal, directory / "out")
            self.assertEqual(
                transport.deletes,
                [
                    "EntityDefinitions(LogicalName='opt_observation')/Attributes(00000000-0000-4000-8000-000000000003)",
                    "EntityDefinitions(00000000-0000-4000-8000-000000000002)",
                    "GlobalOptionSetDefinitions(00000000-0000-4000-8000-000000000001)",
                ],
            )
            self.assertEqual(transport.publications, 1)
            self.assertEqual(result["rowsDeleted"], 0)

    def test_rows_block_rollback_before_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            journal = self.make_journal(directory)
            transport = RollbackTransport(rows=True)
            with self.assertRaises(MODULE.ApplicatorError):
                MODULE.rollback_from_journal(transport, journal, directory / "out")
            self.assertEqual(transport.deletes, [])

    def test_unsafe_journal_kind_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            journal = self.make_journal(directory)
            value = json.loads(journal.read_text())
            value["created"][-1]["kind"] = "ArbitraryDelete"
            journal.write_text(json.dumps(value))
            with self.assertRaises(MODULE.ApplicatorError):
                MODULE.rollback_from_journal(RollbackTransport(), journal, directory / "out")


if __name__ == "__main__":
    unittest.main()
