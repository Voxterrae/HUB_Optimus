"""Candidate shape checks only: no native parser, trust admission or execution."""
import copy
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "products/device-bridge/common/native-result/proposal"
FIELDS = ("windows", "powershell7", "node")
CODES = {
    "denied": ("NOT_AUTHORIZED", "EXPIRED", "REVOKED", "REPLAY", "BINDING_MISMATCH"),
    "failed": ("COLLECTOR_FAILED", "TIMEOUT", "OVERFLOW", "INTERRUPTED"),
    "cancelled": ("CANCELLED",),
}


def envelope():
    return {"payload": {
        "version": "relay.native-result.v0.1", "requestDigest": "a" * 64,
        "targetId": "b" * 32, "profileId": "c" * 32,
        "state": "completed", "errorCode": None,
        "inventory": {name: {"state": "available", "version": "1"} for name in FIELDS},
    }, "signatureDerHex": "30"}


class NativeResultProposalSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = PROPOSAL / "native_result.v0_1.schema.json"
        # An actual missing-artifact assertion is the first RED checkpoint.
        if not path.is_file():
            raise AssertionError("candidate schema artifact is missing")
        cls.schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def assert_shape(self, value, valid):
        self.assertEqual(self.validator.is_valid(value), valid)

    def test_all_field_state_permutations(self):
        for states in itertools.product(("available", "missing", "unverified"), repeat=3):
            value = envelope()
            for name, state in zip(FIELDS, states):
                value["payload"]["inventory"][name] = {
                    "state": state, "version": "1" if state == "available" else None}
            with self.subTest(states=states):
                self.assert_shape(value, True)

    def test_all_error_codes_and_cross_state_rejection(self):
        for state, codes in CODES.items():
            for code in codes:
                for candidate_state in ("completed", *CODES):
                    value = envelope()
                    value["payload"].update(state=candidate_state, errorCode=code, inventory=None)
                    with self.subTest(code=code, state=candidate_state):
                        self.assert_shape(value, candidate_state == state)
                value = envelope()
                value["payload"].update(state=state, errorCode=code)
                self.assert_shape(value, False)  # no data on denial/failure/cancellation
                value["payload"]["inventory"] = None
                value["payload"]["errorCode"] = None
                self.assert_shape(value, False)

    def test_closed_required_objects_and_boundary_types(self):
        paths = ((), ("payload",), ("payload", "inventory"),
                 *(("payload", "inventory", name) for name in FIELDS))
        for path in paths:
            original = envelope()
            obj = original
            for key in path:
                obj = obj[key]
            for key in obj:
                changed = copy.deepcopy(original)
                parent = changed
                for part in path:
                    parent = parent[part]
                del parent[key]
                with self.subTest(path=path, missing=key):
                    self.assert_shape(changed, False)
            changed = copy.deepcopy(original)
            parent = changed
            for part in path:
                parent = parent[part]
            parent["message"] = "not permitted"
            self.assert_shape(changed, False)
            for substitute in (None, [], "x", 1, True):
                changed = copy.deepcopy(original)
                if not path:
                    changed = substitute
                else:
                    parent = changed
                    for part in path[:-1]:
                        parent = parent[part]
                    parent[path[-1]] = substitute
                self.assert_shape(changed, False)

    def test_wrong_scalar_types_and_required_nulls(self):
        for key in ("version", "requestDigest", "targetId", "profileId", "state"):
            for bad in (None, True, 7, [], {}):
                value = envelope()
                value["payload"][key] = bad
                self.assert_shape(value, False)
        for bad in (None, True, 7, [], {}):
            value = envelope()
            value["signatureDerHex"] = bad
            self.assert_shape(value, False)
        for state in ("available", "missing", "unverified", "unknown"):
            for version in (None, "", "1", True, 7, [], {}):
                value = envelope()
                value["payload"]["inventory"]["node"] = {"state": state, "version": version}
                valid = (state == "available" and version == "1") or (
                    state in ("missing", "unverified") and version is None)
                self.assert_shape(value, valid)
        for bad in ("ERROR", True, 1, [], {}):
            value = envelope()
            value["payload"]["errorCode"] = bad
            self.assert_shape(value, False)
        value = envelope()
        value["payload"]["inventory"] = None
        self.assert_shape(value, False)

    def test_version_scalar_lengths_and_unicode(self):
        cases = (("", False), ("x", True), ("x" * 128, True), ("x" * 129, False),
                 ("\U0001f680" * 128, True), ("\U0001f680" * 129, False),
                 ("e\u0301" * 64, True), ("e\u0301" * 64 + "e", False),
                 ("\u0000\n\ufffe", True), ("\ud800", False), ("\udfff", False),
                 ("a\ud800b", False), ("\ud800\udc00", False))
        for version, valid in cases:
            value = envelope()
            value["payload"]["inventory"]["node"]["version"] = version
            with self.subTest(version=ascii(version)):
                self.assert_shape(value, valid)

    def test_hex_entire_string_and_transport_bounds(self):
        for key, length in (("requestDigest", 64), ("targetId", 32), ("profileId", 32)):
            for bad in ("a" * (length-1), "a" * (length+1), "A" * length,
                        "a" * length + "\n", " a" * length, "g" * length):
                value = envelope()
                value["payload"][key] = bad
                self.assert_shape(value, False)
        for signature, valid in (("", False), ("a", False), ("aa", True),
                                 ("aa" * 72, True), ("aa" * 73, False),
                                 ("AA", False), ("aa\n", False), ("0g", False)):
            value = envelope()
            value["signatureDerHex"] = signature
            self.assert_shape(value, valid)
        # "aa" is intentionally schema-valid: JSON Schema does not verify DER.

    def test_fixture_and_native_shapes_remain_separate(self):
        fixture_schema = json.loads((ROOT / "products/device-bridge/windows/offline-prototype/"
                                    "runtime_inventory.v0_1.schema.json").read_text(encoding="utf-8"))
        fixture = Draft202012Validator(fixture_schema)
        self.assertFalse(fixture.is_valid(envelope()))
        self.assertFalse(fixture.is_valid(envelope()["payload"]))
        disabled = {"simulated": True, "state": "denied", "code": "EXECUTOR_DISABLED"}
        self.assertTrue(fixture.is_valid(disabled))
        self.assert_shape(disabled, False)

    def test_frozen_vectors_project_to_candidate_schema(self):
        vectors = json.loads((PROPOSAL / "vectors/native_result_signature.v0_1.json").read_text(encoding="utf-8"))
        for vector in vectors["results"]:
            for key in ("signatureLowSDerHex", "signatureHighSDerHex"):
                self.assert_shape({"payload": vector["payload"], "signatureDerHex": vector[key]}, True)

    def test_node_synthetic_conformance(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node unavailable: synthetic math checks unverified")
        result = subprocess.run([node, "--test", str(PROPOSAL / "conformance.cjs")],
                                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
