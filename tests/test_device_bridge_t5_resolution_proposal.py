"""Closed synthetic corpus checks; no provenance, protected store or authority."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "products/device-bridge/common/enrolled-key/proposal"


class T5ResolutionProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = PROPOSAL / "resolution_policy.v0_1.schema.json"
        corpus = PROPOSAL / "vectors/resolution_policy.v0_1.json"
        if not schema.is_file() or not corpus.is_file():
            raise AssertionError("T5 proposal schema/corpus artifact is missing")
        cls.schema = json.loads(schema.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)
        cls.corpus = json.loads(corpus.read_text(encoding="utf-8"))

    def test_corpus_and_baseline(self):
        self.validator.validate(self.corpus)
        ids = [row["id"] for row in self.corpus["cases"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_closed_objects_and_required_members(self):
        def walk(value, path=()):
            if isinstance(value, dict):
                yield path, value
                for key, child in value.items():
                    yield from walk(child, path + (key,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield from walk(child, path + (index,))
        for path, obj in walk(self.corpus):
            for field in [None, *obj]:
                value = copy.deepcopy(self.corpus)
                target = value
                for member in path:
                    target = target[member]
                if field is None:
                    target["unexpected"] = True
                else:
                    del target[field]
                with self.subTest(path=path, field=field):
                    self.assertFalse(self.validator.is_valid(value))

    def test_authority_injection(self):
        for where in ("presented", "local", "record", "baseline"):
            for name in ("enrolled", "attestationValid", "policyPassed", "namespaceRef",
                         "accountRef", "snapshot", "trustRoot"):
                if where != "presented" and name not in ("enrolled", "attestationValid", "policyPassed"):
                    continue
                value = copy.deepcopy(self.corpus)
                base = value["baseline"]
                target = base["snapshot"]["records"][0] if where == "record" else base if where == "baseline" else base[where]
                target[name] = True
                with self.subTest(where=where, name=name):
                    self.assertFalse(self.validator.is_valid(value))

    def test_type_hex_enum_and_fixed_request_boundaries(self):
        probes = [("local", "nowTick", bad) for bad in (True, -1, 1000001, 1.5, "100")]
        for field, size in (("targetId", 32), ("policyDigest", 64)):
            probes += [("local", field, bad) for bad in ("A" * size, "a" * size + "\n", "g" * size, "a" * (size-1))]
        probes += [("local", "namespaceRef", "fictional:unknown"), ("snapshot", "storeState", "trusted")]
        for group, field, bad in probes:
            value = copy.deepcopy(self.corpus)
            value["baseline"][group][field] = bad
            with self.subTest(group=group, field=field, bad=bad):
                self.assertFalse(self.validator.is_valid(value))
        for role in ("broker", "approver", "transport"):
            for bad in ("04" + "0" * 127, "04" + "0" * 128 + "\n", "03" + "0" * 128, "04" + "A" * 128):
                value = copy.deepcopy(self.corpus)
                value["baseline"]["presented"][role + "Sec1Hex"] = bad
                self.assertFalse(self.validator.is_valid(value))
        for field, bad in (("operation", "other"), ("fields", ["node", "windows", "powershell7"]),
                           ("ttlMs", 60001), ("ttlMs", True)):
            for where in ("pending", "presented"):
                value = copy.deepcopy(self.corpus)
                value["baseline"][where]["request"][field] = bad
                self.assertFalse(self.validator.is_valid(value))

    def test_outputs_never_confer_authority(self):
        for row in self.corpus["cases"]:
            self.assertEqual(row["expected"]["operationalAuthority"], "absent")
        for bad in ({"status": "verified", "code": None, "operationalAuthority": "absent"},
                    {"status": "candidate-consistent", "code": "Revoked", "operationalAuthority": "absent"},
                    {"status": "denied", "code": None, "operationalAuthority": "absent"}):
            value = copy.deepcopy(self.corpus)
            value["cases"][0]["expected"] = bad
            self.assertFalse(self.validator.is_valid(value))

    def test_node_synthetic_conformance(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node unavailable: synthetic T5 conformance unverified")
        result = subprocess.run([node, "--test", str(PROPOSAL / "conformance.cjs")], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
