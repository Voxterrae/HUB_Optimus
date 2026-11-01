"""Offline minimum-refusal codec tests; no host or Windows observations."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "products/device-bridge/windows/native-pilot/tools/bootstrap_refusal_receipt.py"
WIRE_LIMIT = 128 * 1024
U64_MAX = "18446744073709551615"


def error(**changes):
    value = {
        "kind": "primary", "phase": "initial", "operation": "validate",
        "domain": "internal", "code": None, "reason": "unsupported",
        "ancestor_index": None, "completion": None,
    }
    value.update(changes)
    return value


def receipt():
    return {
        "schema": "hub_relay.bootstrap_inventory.v0.1",
        "mode": "diagnostic_only", "outcome": "refused", "activation": "blocked",
        "loaded_image_provenance": "not_established",
        "collector": {"source_commit": "a" * 40, "policy_sha256": "b" * 64,
                      "target": "x86_64-pc-windows-msvc"},
        "started_utc": "20", "finished_utc": "10", "elapsed_ms": "10001",
        "process": None, "primary_token": None, "thread_token": None,
        "thread_context": "unknown", "anchor": None, "ancestors": None,
        "recheck": "not_completed", "product_collision": "not_observed",
        "service_collision": "not_observed",
        "service_sid_binding": "external_evidence_required",
        "errors": [error()], "cleanup": "complete",
    }


def raw(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")


class RefusalReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODULE.is_file():
            raise AssertionError("offline refusal-receipt codec module is missing")
        spec = importlib.util.spec_from_file_location("bootstrap_refusal_receipt", MODULE)
        cls.codec = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.codec)

    def reject(self, value):
        for call, argument in ((self.codec.serialize_refusal, value),
                               (self.codec.parse_refusal, raw(value))):
            with self.subTest(api=call.__name__):
                with self.assertRaises(self.codec.ReceiptError) as caught:
                    call(argument)
                self.assertEqual(str(caught.exception), "Invalid minimum refusal receipt")

    def test_roundtrip_preserves_all_metadata_and_wall_clock_reversal(self):
        value = receipt()
        self.assertEqual(self.codec.parse_refusal(self.codec.serialize_refusal(value)), value)
        self.assertEqual(self.codec.parse_refusal(raw(value)), value)

    def test_reject_observed_and_every_nonnull_observation(self):
        value = receipt()
        value["outcome"] = "observed"
        self.reject(value)
        for field in ("process", "primary_token", "thread_token", "anchor", "ancestors"):
            for observation in ({}, []):
                value = receipt()
                value[field] = observation
                with self.subTest(field=field, observation=observation):
                    self.reject(value)

    def test_every_top_level_key_is_required_and_unknown_keys_are_rejected(self):
        for field in receipt():
            value = receipt()
            del value[field]
            with self.subTest(field=field):
                self.reject(value)
        value = receipt()
        value["approved"] = True
        self.reject(value)

    def test_every_nested_key_is_required_and_unknown_keys_are_rejected(self):
        examples = (("collector", receipt()["collector"]),
                    ("errors", error()),
                    ("completion", {"call": 0, "io_status": 0xC0000022, "information": "0"}))
        for location, record in examples:
            for field in (*record, "extra"):
                value = receipt()
                if location == "collector":
                    nested = value["collector"]
                elif location == "errors":
                    nested = value["errors"][0]
                else:
                    value["errors"] = [error(operation="NtCreateFile", domain="ntstatus",
                                             code=0, reason=None, completion=copy.deepcopy(record))]
                    nested = value["errors"][0]["completion"]
                if field == "extra":
                    nested[field] = None
                else:
                    del nested[field]
                with self.subTest(location=location, field=field):
                    self.reject(value)

    def test_fixed_metadata_and_closed_context_enums(self):
        for field in ("schema", "mode", "outcome", "activation", "loaded_image_provenance",
                      "product_collision", "service_collision", "service_sid_binding",
                      "thread_context", "recheck", "cleanup"):
            for invalid in (None, 0, True, "unknown-value"):
                value = receipt()
                value[field] = invalid
                with self.subTest(field=field, invalid=invalid):
                    self.reject(value)
        for context in ("no_token", "present", "unknown"):
            for recheck in ("equal", "changed", "not_completed"):
                value = receipt()
                value.update(thread_context=context, recheck=recheck)
                self.assertEqual(self.codec.parse_refusal(raw(value)), value)

    def test_collector_hash_extents_and_ascii_target_limit(self):
        for field, valid_length in (("source_commit", 40), ("policy_sha256", 64)):
            for invalid in ("a" * (valid_length - 1), "a" * (valid_length + 1),
                            "A" * valid_length, "g" * valid_length, None, 3):
                value = receipt()
                value["collector"][field] = invalid
                with self.subTest(field=field, invalid=invalid):
                    self.reject(value)
        for target in ("", "x" * 128, "\x00" * 128):
            value = receipt()
            value["collector"]["target"] = target
            self.assertEqual(self.codec.parse_refusal(self.codec.serialize_refusal(value)), value)
        for target in ("x" * 129, "é", "😀", None, True):
            value = receipt()
            value["collector"]["target"] = target
            self.reject(value)

    def test_timing_is_canonical_u64_text_with_exact_maximum(self):
        for field in ("started_utc", "finished_utc", "elapsed_ms"):
            for valid in ("0", U64_MAX):
                value = receipt()
                value[field] = valid
                self.assertEqual(self.codec.parse_refusal(raw(value)), value)
            for invalid in ("18446744073709551616", "9" * 21, "", "00", "01", "+1", "-1",
                            " 1", "1 ", "1.0", "١", 0, True, None):
                value = receipt()
                value[field] = invalid
                with self.subTest(field=field, invalid=invalid):
                    self.reject(value)

    def test_u32_status_bits_and_ancestor_index_limits(self):
        for code in (0, 0x80000000, 0xFFFFFFFF):
            value = receipt()
            value["errors"] = [error(operation="GetHandleInformation", domain="win32", code=code, reason=None)]
            self.assertEqual(self.codec.parse_refusal(raw(value)), value)
        for field, valid_values, invalid_values in (
            ("code", (0, 0xFFFFFFFF), (-1, 0x100000000, True, 1.0, "1", None)),
            ("ancestor_index", (None, 0, 127), (-1, 128, True, 1.0, "1")),
        ):
            for invalid in invalid_values:
                value = receipt()
                value["errors"] = [error(domain="win32", code=5, reason=None)]
                value["errors"][0][field] = invalid
                with self.subTest(field=field, invalid=invalid):
                    self.reject(value)
            for valid in valid_values:
                value = receipt()
                value["errors"] = [error(domain="win32", code=5, reason=None)]
                value["errors"][0][field] = valid
                self.assertEqual(self.codec.parse_refusal(raw(value)), value)

    def test_domains_require_native_codes_or_closed_internal_reasons(self):
        for domain in ("win32", "hresult"):
            value = receipt()
            value["errors"] = [error(domain=domain, code=0x80070005, reason=None)]
            self.assertEqual(self.codec.parse_refusal(raw(value)), value)
            value["errors"][0]["reason"] = "policy"
            self.reject(value)
        for reason in ("unsupported", "malformed", "bound", "policy", "impersonation",
                       "app_container", "token_changed", "drift", "budget", "receipt_bound"):
            value = receipt()
            value["errors"][0]["reason"] = reason
            self.assertEqual(self.codec.parse_refusal(raw(value)), value)
        for changes in ({"domain": "other"}, {"reason": "raw host path"}, {"reason": None},
                        {"code": 0}, {"kind": "other"}, {"phase": "other"}, {"operation": "OpenProcess"}):
            value = receipt()
            value["errors"][0].update(changes)
            self.reject(value)

    def test_all_declared_operations_and_noncleanup_primary_phases(self):
        operations = (
            "DuplicateHandle", "GetHandleInformation", "GetProcessId", "GetProcessTimes",
            "QueryFullProcessImageNameW", "IsWow64Process2", "OpenProcessToken", "OpenThreadToken",
            "GetTokenInformation", "CoInitializeEx", "SHGetKnownFolderPath", "CreateFileW",
            "NtCreateFile", "NtQueryInformationFile", "GetFileInformationByHandleEx", "GetFileType",
            "GetVolumeInformationByHandleW", "GetFinalPathNameByHandleW", "GetVolumeNameForVolumeMountPointW",
            "GetDriveTypeW", "GetSecurityInfo", "LookupPrivilegeNameW", "CompareStringOrdinal",
            "validate",
        )
        for phase in ("initial", "capture", "recheck"):
            for operation in operations:
                value = receipt()
                value["errors"] = [error(phase=phase, operation=operation)]
                self.assertEqual(self.codec.parse_refusal(raw(value)), value)
        value = receipt()
        value["errors"][0]["phase"] = "serialize"
        self.reject(value)

    def test_nt_completion_roundtrip_keeps_independent_statuses_information_and_order(self):
        first = error(operation="NtCreateFile", domain="ntstatus", code=0, reason=None,
                      completion={"call": 0, "io_status": 0xC0000022, "information": "7"})
        cleanup = error(kind="cleanup", phase="cleanup", operation="CloseHandle", domain="win32",
                        code=6, reason=None)
        value = receipt()
        value.update(errors=[first, cleanup, copy.deepcopy(cleanup)], cleanup="failed")
        encoded = self.codec.serialize_refusal(value)
        self.assertEqual(self.codec.parse_refusal(encoded), value)
        for operation in ("NtCreateFile", "NtQueryInformationFile"):
            for information in ("0", "1", U64_MAX):
                value = receipt()
                value["errors"] = [error(operation=operation, domain="ntstatus", code=0xC0000001, reason=None,
                                         completion={"call": 0xC0000001, "io_status": 0,
                                                     "information": information})]
                self.assertEqual(self.codec.parse_refusal(self.codec.serialize_refusal(value)), value)
            value = receipt()
            value["errors"] = [error(operation=operation, reason="malformed",
                                     completion={"call": 0, "io_status": 0, "information": "17"})]
            self.assertEqual(self.codec.parse_refusal(self.codec.serialize_refusal(value)), value)

    def test_nt_completion_rejects_mismatched_domains_codes_statuses_and_bounds(self):
        good = error(operation="NtCreateFile", domain="ntstatus", code=0, reason=None,
                     completion={"call": 0, "io_status": 0xC0000022, "information": "1"})
        for changes in ({"completion": None}, {"operation": "CreateFileW"}, {"code": 5},
                        {"domain": "win32"}, {"domain": "hresult"},
                        {"domain": "internal", "code": None, "reason": "malformed"}):
            value = receipt()
            value["errors"] = [dict(good, **changes)]
            self.reject(value)
        for field, invalids in (("call", (-1, 0x100000000, True, 1.0)),
                                ("io_status", (-1, 0x100000000, True, 1.0)),
                                ("information", (0, True, "01", "9" * 21, "18446744073709551616"))):
            for invalid in invalids:
                value = receipt()
                value["errors"] = [copy.deepcopy(good)]
                value["errors"][0]["completion"][field] = invalid
                self.reject(value)
        for changes in ({"domain": "ntstatus", "code": 0, "reason": None}, {"reason": "bound"},
                        {"operation": "validate"}):
            value = receipt()
            value["errors"] = [error(operation="NtCreateFile", reason="malformed",
                                     completion={"call": 0, "io_status": 0, "information": "1"})]
            value["errors"][0].update(changes)
            self.reject(value)

    def test_fatal_pending_source_classification_never_becomes_a_receipt(self):
        for call, io_status, information in ((0x103, 0, "0"), (0xC0000001, 0x103, "0"),
                                             (0, 0xC0000001, U64_MAX),
                                             (0x7FFFFFFF, 0xC0000001, U64_MAX)):
            value = receipt()
            value["errors"] = [error(operation="NtQueryInformationFile", domain="ntstatus", code=call,
                                     reason=None, completion={"call": call, "io_status": io_status,
                                                              "information": information})]
            self.reject(value)

    def test_cleanup_order_multiplicity_and_primary_cleanup_failure(self):
        for operation in ("CloseHandle", "LocalFree"):
            for phase in ("initial", "capture", "recheck", "cleanup"):
                value = receipt()
                value.update(errors=[error(operation=operation, phase=phase, domain="win32", code=6,
                                           reason=None)], cleanup="failed")
                if phase == "cleanup":
                    self.assertEqual(self.codec.parse_refusal(raw(value)), value)
                else:
                    self.reject(value)
                value["cleanup"] = "complete"
                self.reject(value)
        value = receipt()
        value["errors"][0]["phase"] = "cleanup"
        self.reject(value)
        cleanup = error(kind="cleanup", phase="cleanup", operation="LocalFree", domain="win32", code=8,
                        reason=None)
        value = receipt()
        value.update(errors=[cleanup, copy.deepcopy(cleanup)], cleanup="failed")
        self.assertEqual(self.codec.parse_refusal(self.codec.serialize_refusal(value)), value)
        for invalid in (dict(cleanup, phase="capture"), dict(cleanup, operation="validate")):
            value["errors"] = [invalid]
            self.reject(value)
        value = receipt()
        value["cleanup"] = "failed"
        self.reject(value)
        value.update(errors=[cleanup], cleanup="complete")
        self.reject(value)

    def test_error_counts_reserve_final_slot_and_receipt_error_is_exact(self):
        final = error(kind="receipt", phase="serialize", operation="serialize", reason="receipt_bound")
        cleanup = error(kind="cleanup", phase="cleanup", operation="CloseHandle", domain="win32", code=6,
                        reason=None)
        for errors in ([final], [cleanup] * 255, [cleanup] * 255 + [final],
                       [error()] + [cleanup] * 254 + [final]):
            value = receipt()
            value.update(errors=copy.deepcopy(errors), cleanup="failed" if cleanup in errors else "complete")
            self.assertEqual(self.codec.parse_refusal(self.codec.serialize_refusal(value)), value)
        for errors in ([], [error(), error()], [cleanup, error()], [cleanup] * 256,
                       [cleanup] * 256 + [final], [final, cleanup], [final, final]):
            value = receipt()
            value.update(errors=copy.deepcopy(errors), cleanup="failed" if cleanup in errors else "complete")
            self.reject(value)
        for field, invalid in (("phase", "capture"), ("operation", "validate"), ("domain", "win32"),
                               ("code", 0), ("reason", "bound"), ("ancestor_index", 0),
                               ("completion", {"call": 0, "io_status": 0, "information": "0"})):
            value = receipt()
            value["errors"] = [dict(final, **{field: invalid})]
            self.reject(value)

    def test_wrong_container_types_and_surrogates_reject_in_both_apis(self):
        for field, invalid in (("collector", []), ("errors", {}), ("errors", [None]),
                               ("started_utc", "\ud800")):
            value = receipt()
            value[field] = invalid
            self.reject(value)
        value = receipt()
        value["collector"]["target"] = "\udfff"
        self.reject(value)
        for invalid in ([], None, "{}", 4, True):
            self.reject(invalid)

    def test_duplicate_keys_at_each_record_level_reject(self):
        encoded = raw(receipt())
        for old, new in ((b'"schema":', b'"schema":"other","schema":'),
                         (b'"target":', b'"target":"first","target":'),
                         (b'"kind":', b'"kind":"primary","kind":')):
            with self.assertRaises(self.codec.ReceiptError):
                self.codec.parse_refusal(encoded.replace(old, new, 1))
        value = receipt()
        value["errors"] = [error(operation="NtCreateFile", domain="ntstatus", code=0, reason=None,
                                 completion={"call": 0, "io_status": 0xC0000022, "information": "1"})]
        with self.assertRaises(self.codec.ReceiptError):
            self.codec.parse_refusal(raw(value).replace(b'"call":0', b'"call":1,"call":0'))

    def test_malformed_utf8_bom_truncation_trailing_floats_and_nonfinite_reject_safely(self):
        encoded = raw(receipt())
        invalids = (b"", b"\xef\xbb\xbf" + encoded, b"\xff", encoded[:-1], encoded + b"{}",
                    encoded + b" trailing secret", encoded.replace(b'"code":null', b'"code":1.0'),
                    encoded.replace(b'"code":null', b'"code":1e0'),
                    encoded.replace(b'"code":null', b'"code":NaN'),
                    encoded.replace(b'"code":null', b'"code":Infinity'),
                    encoded.replace(b'"code":null', b'"code":-Infinity'),
                    encoded.replace(b'"code":null', b'"code":' + b"9" * 5000),
                    encoded.replace(b"unsupported", b"\xc0\xaf"))
        for invalid in invalids:
            with self.subTest(prefix=invalid[:20]), self.assertRaises(self.codec.ReceiptError) as caught:
                self.codec.parse_refusal(invalid)
            self.assertEqual(str(caught.exception), "Invalid minimum refusal receipt")
        for invalid in ("{}", bytearray(encoded), memoryview(encoded), None, 2):
            with self.assertRaises(self.codec.ReceiptError):
                self.codec.parse_refusal(invalid)
        for invalid in (float("nan"), float("inf"), 1.0, True):
            value = receipt()
            value["errors"][0]["code"] = invalid
            with self.assertRaises(self.codec.ReceiptError):
                self.codec.serialize_refusal(value)

    def test_input_exact_wire_limit_and_plus_one_before_json_decode(self):
        encoded = raw(receipt())
        exact = encoded + b" " * (WIRE_LIMIT - len(encoded))
        self.assertEqual(self.codec.parse_refusal(exact), receipt())
        with patch.object(self.codec.json, "loads", wraps=json.loads) as loads:
            with self.assertRaises(self.codec.ReceiptError):
                self.codec.parse_refusal(exact + b" ")
            loads.assert_not_called()

    def test_output_limit_counts_json_escaping_and_revalidates_dict(self):
        value = receipt()
        value["collector"]["target"] = "\x00" * 128
        encoded = self.codec.serialize_refusal(value)
        # This subset cannot fill 128 KiB; lower only the cap to exercise the
        # exact encoded-byte boundary through the same public serializer.
        with patch.object(self.codec, "_MAX_RECEIPT_BYTES", len(encoded)):
            self.assertEqual(self.codec.serialize_refusal(value), encoded)
        with patch.object(self.codec, "_MAX_RECEIPT_BYTES", len(encoded) - 1):
            with self.assertRaises(self.codec.ReceiptError):
                self.codec.serialize_refusal(value)
        value["activation"] = "allowed"
        with self.assertRaises(self.codec.ReceiptError):
            self.codec.serialize_refusal(value)

    def test_depth_eight_reaches_json_parser_nine_is_rejected_before_it(self):
        for depth, should_decode in ((8, True), (9, False), (10000, False)):
            encoded = b"[" * depth + b"0" + b"]" * depth
            with patch.object(self.codec.json, "loads", wraps=json.loads) as loads:
                with self.assertRaises(self.codec.ReceiptError):
                    self.codec.parse_refusal(encoded)
                self.assertEqual(loads.called, should_decode)
        value = receipt()
        value["collector"]["target"] = '[{"quote":"\\"}]' * 5
        self.assertEqual(self.codec.parse_refusal(self.codec.serialize_refusal(value)), value)

    def test_no_stdout_or_receipt_output_on_failure(self):
        from contextlib import redirect_stdout
        from io import StringIO

        output = StringIO()
        with redirect_stdout(output):
            self.codec.parse_refusal(raw(receipt()))
            self.codec.serialize_refusal(receipt())
            with self.assertRaises(self.codec.ReceiptError):
                self.codec.parse_refusal(b"private raw diagnostic")
        self.assertEqual(output.getvalue(), "")

    def test_rejections_do_not_retain_private_parser_exception_context(self):
        for invalid in (b'{"private":"SYNTHETIC-PRIVATE" invalid}', b"\xffPRIVATE"):
            with self.subTest(invalid=invalid), self.assertRaises(self.codec.ReceiptError) as caught:
                self.codec.parse_refusal(invalid)
            self.assertIsNone(caught.exception.__context__)
            self.assertIsNone(caught.exception.__cause__)
        for function, argument in ((self.codec.parse_refusal, raw(receipt())),
                                   (self.codec.serialize_refusal, receipt())):
            with patch.object(self.codec, "_validated", side_effect=MemoryError("SYNTHETIC-PRIVATE")):
                with self.assertRaises(self.codec.ReceiptError) as caught:
                    function(argument)
                self.assertIsNone(caught.exception.__context__)
                self.assertIsNone(caught.exception.__cause__)

    def test_serialized_bytes_do_not_depend_on_object_key_order(self):
        value = receipt()
        value["errors"] = [error(operation="NtCreateFile", domain="ntstatus", code=0,
                                 reason=None, completion={"call": 0, "io_status": 0xC0000022,
                                                          "information": "2"})]

        def reverse_objects(item):
            if type(item) is dict:
                return {key: reverse_objects(child) for key, child in reversed(tuple(item.items()))}
            if type(item) is list:
                return [reverse_objects(child) for child in item]
            return item

        self.assertEqual(self.codec.serialize_refusal(value),
                         self.codec.serialize_refusal(reverse_objects(value)))


if __name__ == "__main__":
    unittest.main()
