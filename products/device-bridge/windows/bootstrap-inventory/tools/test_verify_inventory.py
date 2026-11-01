"""Synthetic private receipts: no host observations or authority assertions."""
import copy
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import verify_inventory as verifier


def blob(data):
    return {"hex": data.hex(), "byte_count": len(data)}


def path(text):
    return {"text": text, "utf16_units": len(text.encode("utf-16-le")) // 2}


def sid(authority=5, *subs):
    return bytes((1, len(subs))) + authority.to_bytes(6, "big") + b"".join(struct.pack("<I", n) for n in subs)


def descriptor():
    system = sid(5, 18)
    ace = struct.pack("<BBHI", 0, 0, 8 + len(system), 0x001F01FF) + system
    acl = struct.pack("<BBHHH", 2, 0, 8 + len(ace), 1, 0) + ace
    return struct.pack("<BBHIIII", 1, 0, 0x8004, 20, 0, 0, 20 + len(system)) + system + acl


def receipt(observed=False):
    error = dict(kind="primary", phase="initial", operation="validate", domain="internal",
                 code=None, reason="unsupported", ancestor_index=None, completion=None)
    value = dict(schema="hub_relay.bootstrap_inventory.v0.1", mode="diagnostic_only",
                 outcome="refused", activation="blocked", loaded_image_provenance="not_established",
                 collector=dict(source_commit="a" * 40, policy_sha256="b" * 64,
                                target="x86_64-pc-windows-msvc"),
                 started_utc="1", finished_utc="2", elapsed_ms="1", process=None,
                 primary_token=None, thread_token=None, thread_context="no_token", anchor=None,
                 ancestors=None, recheck="not_completed", product_collision="not_observed",
                 service_collision="not_observed", service_sid_binding="external_evidence_required",
                 errors=[error], cleanup="complete")
    if not observed:
        return value
    system = blob(sid(5, 18))
    luid = dict(low=1, high=-1)
    token = dict(type=1, impersonation_level=None, user=system, owner=system, primary_group=system,
                 integrity=dict(sid=blob(sid(16, 16384)), attributes=32), groups=[],
                 restricted_sids=[], capabilities=[], privileges=[], token_id=luid,
                 authentication_id=luid, modified_id=luid, session_id=0, elevation_type=1,
                 elevation=0, has_restrictions=0, is_app_container=0, mandatory_policy=1,
                 ui_access=0, virtualization_allowed=0, virtualization_enabled=0)
    guid = "\\\\?\\Volume{11111111-2222-3333-4444-555555555555}\\"
    native = "\\Device\\HarddiskVolume7\\"
    value.update(outcome="observed", recheck="equal", errors=[], primary_token=token,
                 process=dict(pid=7, creation_utc="1", process_machine=0, native_machine=0x8664,
                              image_win32=path("C:\\test.exe"), image_native=path(native + "test.exe")),
                 anchor=dict(known_folder_id="905e63b6-c1bf-494e-b29c-65b732d3d21a",
                             resolved_path=path("C:\\Program Files"), volume_guid=path(guid),
                             native_root=path(native), volume_serial64="9", filesystem_serial32=9,
                             filesystem="NTFS", drive_type=3),
                 ancestors=[dict(index=i, path=path(guid + suffix), native_path=path(native + suffix),
                                 volume_serial64="9", file_id=(bytes([i+1]) * 16).hex(),
                                 attributes=16, reparse_tag=0, delete_pending=False,
                                 owner_dacl=blob(descriptor()), policy_result="match")
                            for i, suffix in enumerate(("", "Program Files"))])
    return value


def raw(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii")


class ReceiptTests(unittest.TestCase):
    def reject(self, value):
        with self.assertRaises(verifier.ReceiptError) as caught:
            verifier.parse_receipt(raw(value))
        self.assertEqual(str(caught.exception), "Invalid diagnostic receipt")
        self.assertIsNone(caught.exception.__context__)

    def test_complete_refusal_and_synthetic_observation_are_data(self):
        for value in (receipt(), receipt(True)):
            self.assertEqual(verifier.parse_receipt(raw(value)), value)

    def test_transfer_is_separate_and_exact(self):
        data = raw(receipt())
        result = verifier.verify_capture(data, 0, True, len(data), hashlib.sha256(data).hexdigest())
        self.assertEqual(result, receipt())
        for args in ((1, True, len(data), hashlib.sha256(data).hexdigest()),
                     (0, False, len(data), hashlib.sha256(data).hexdigest()),
                     (0, True, len(data) + 1, hashlib.sha256(data).hexdigest()),
                     (0, True, len(data), "0" * 64),
                     (False, True, len(data), hashlib.sha256(data).hexdigest())):
            with self.assertRaises(verifier.ReceiptError):
                verifier.verify_capture(data, *args)

    def test_unknown_missing_partial_null_and_boolean_integer_rejected(self):
        for key in receipt():
            value = receipt()
            del value[key]
            self.reject(value)
        value = receipt(); value["trusted"] = True; self.reject(value)
        for location, key in (("collector", "source_commit"), ("process", "pid"),
                              ("primary_token", "user"), ("anchor", "filesystem")):
            value = receipt(True); value[location][key] = None; self.reject(value)
        value = receipt(True); value["process"]["pid"] = True; self.reject(value)
        value = receipt(True); value["primary_token"]["token_id"]["high"] = 2147483648; self.reject(value)

    def test_strict_json_bytes_and_depth(self):
        valid = raw(receipt())
        for data in (valid + b"{}", b"\xef\xbb\xbf" + valid, b"\xff", b'{"a":1,"a":2}',
                     b"[" * 9 + b"0" + b"]" * 9, valid.replace(b'"elapsed_ms":"1"', b'"elapsed_ms":1.0'),
                     valid.replace(b'"elapsed_ms":"1"', b'"elapsed_ms":NaN'),
                     b" " * (32 * 1024 * 1024 + 1)):
            with self.assertRaises(verifier.ReceiptError): verifier.parse_receipt(data)

    def test_sid_descriptor_path_and_policy_are_checked(self):
        value = receipt(True); value["primary_token"]["user"] = blob(b"\x01\x0f" + b"\0" * 6); self.reject(value)
        value = receipt(True); value["ancestors"][0]["owner_dacl"] = blob(b"\0" * 20); self.reject(value)
        unsafe = bytearray(descriptor()); unsafe[-4:] = struct.pack("<I", 19)
        value = receipt(True); value["ancestors"][0]["owner_dacl"] = blob(unsafe); self.reject(value)
        value = receipt(True); value["process"]["image_win32"]["utf16_units"] += 1; self.reject(value)
        value = receipt(True); value["process"]["image_win32"] = dict(text="\ud800", utf16_units=1); self.reject(value)
        value = receipt(True); value["ancestors"][1]["native_path"] = path("\\Device\\Other\\Program Files"); self.reject(value)
        value = receipt(True); value["ancestors"][0]["file_id"] = value["ancestors"][1]["file_id"]; self.reject(value)

    def test_observed_invariants_and_array_caps(self):
        for key, replacement in (("thread_context", "present"), ("recheck", "changed"),
                                 ("elapsed_ms", "10001"), ("ancestors", []), ("process", None)):
            value = receipt(True); value[key] = replacement; self.reject(value)
        value = receipt(True); value["process"]["native_machine"] = 0xAA64; self.reject(value)
        value = receipt(True); value["primary_token"]["is_app_container"] = 1; self.reject(value)
        value = receipt(True); value["primary_token"]["groups"] = [dict(sid=blob(sid(5,18)), attributes=0)] * 2049; self.reject(value)
        value = receipt(True); value["ancestors"][1]["index"] = 3; self.reject(value)

    def test_refusal_can_retain_complete_nonmatching_observations(self):
        value = receipt(True); value.update(outcome="refused", errors=receipt()["errors"])
        value["ancestors"][0]["policy_result"] = "refused"
        self.assertEqual(verifier.parse_receipt(raw(value)), value)

    def test_refusal_preserves_complete_failure_facts_without_acquisition_order(self):
        value=receipt(True); value.update(outcome="refused",errors=receipt()["errors"],anchor=None)
        value["process"]["pid"]=0
        value["primary_token"].update(type=2,impersonation_level=0)
        self.assertEqual(verifier.parse_receipt(raw(value)),value)
        value.update(outcome="observed",errors=[])
        self.reject(value)

    def test_partial_ancestor_array_is_not_a_complete_observation(self):
        value=receipt(True); value.update(outcome="refused", errors=receipt()["errors"])
        value["ancestors"].pop()
        self.reject(value)

    def test_exact_numeric_array_and_error_reserve_boundaries(self):
        value=receipt(True); value["primary_token"]["token_id"]={"low":0xFFFFFFFF,"high":-2147483648}
        value["primary_token"]["groups"]=[dict(sid=blob(sid(5,18)),attributes=0xFFFFFFFF)]*2048
        verifier.parse_receipt(raw(value))
        value["primary_token"]["groups"].append(value["primary_token"]["groups"][0]); self.reject(value)
        value=receipt(); cleanup=dict(kind="cleanup",phase="cleanup",operation="LocalFree",domain="win32",
            code=5,reason=None,ancestor_index=None,completion=None)
        reserve=dict(kind="receipt",phase="serialize",operation="serialize",domain="internal",code=None,
                     reason="receipt_bound",ancestor_index=None,completion=None)
        value.update(errors=[value["errors"][0]]+[cleanup]*254+[reserve],cleanup="failed")
        verifier.parse_receipt(raw(value))
        value["errors"].insert(-1,cleanup); self.reject(value)

    def test_path_and_descriptor_exact_and_plus_one_bounds(self):
        value=receipt(); value["process"]=receipt(True)["process"]
        value["process"]["image_win32"]=path("x"*32767)
        verifier.parse_receipt(raw(value))
        value["process"]["image_win32"]=path("x"*32768); self.reject(value)
        value=receipt(True)
        value["ancestors"][0]["owner_dacl"]=blob(descriptor()+bytes(65536-len(descriptor())))
        verifier.parse_receipt(raw(value))
        value["ancestors"][0]["owner_dacl"]=blob(descriptor()+bytes(65537-len(descriptor()))); self.reject(value)

    def test_ascii_casing_does_not_become_unicode_casefold(self):
        value=receipt(True)
        value["ancestors"][1]["path"]=path(value["ancestors"][1]["path"]["text"].lower())
        verifier.parse_receipt(raw(value))
        value["anchor"]["resolved_path"]=path("C:\\Straße")
        guid=value["anchor"]["volume_guid"]["text"]; native=value["anchor"]["native_root"]["text"]
        value["ancestors"][1]["path"]=path(guid+"STRASSE")
        value["ancestors"][1]["native_path"]=path(native+"STRASSE")
        self.reject(value)

    def test_error_order_reserve_and_nt_completion(self):
        value = receipt(); cleanup = copy.deepcopy(value["errors"][0])
        cleanup.update(kind="cleanup", phase="cleanup", operation="CloseHandle", domain="win32", code=6, reason=None)
        value["errors"].append(cleanup); value["cleanup"] = "failed"
        verifier.parse_receipt(raw(value))
        value["errors"].reverse(); self.reject(value)
        value = receipt(); value["errors"] *= 2; self.reject(value)
        value = receipt(); error=value["errors"][0]
        error.update(operation="NtCreateFile", domain="ntstatus", code=0, reason=None,
                     completion=dict(call=0, io_status=0xC0000022, information="0"))
        verifier.parse_receipt(raw(value))
        error["completion"]["io_status"] = 0x103; self.reject(value)
        error["completion"] = None; self.reject(value)
        value = receipt(); value["errors"] = [cleanup] * 256; value["cleanup"]="failed"; self.reject(value)

    def test_nt_informational_success_is_not_a_native_failure(self):
        value=receipt(); error=value["errors"][0]
        error.update(operation="NtCreateFile",domain="internal",reason="malformed",
                     completion=dict(call=0x40000000,io_status=0,information="99"))
        verifier.parse_receipt(raw(value))
        error.update(domain="ntstatus",reason=None,code=0x40000000)
        self.reject(value)

    def test_normalized_native_root_without_terminal_slash(self):
        value=receipt(True)
        root=value["anchor"]["native_root"]["text"].rstrip("\\")
        value["anchor"]["native_root"]=path(root)
        value["ancestors"][0]["native_path"]=path(root)
        verifier.parse_receipt(raw(value))

    def test_cli_never_echoes_private_input_or_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "private.json"; source.write_bytes(b"secret-host-path-and-sid")
            run = subprocess.run([sys.executable, str(Path(verifier.__file__)), "--receipt", str(source)],
                                 capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertNotIn("secret", run.stdout + run.stderr)
        self.assertNotIn(directory, run.stdout + run.stderr)
        unknown=subprocess.run([sys.executable,str(Path(verifier.__file__)),"--receipt","unused","--private-host-path"],capture_output=True,text=True)
        self.assertNotIn("--private-host-path",unknown.stdout+unknown.stderr)

    def test_cli_requires_complete_independent_capture_record(self):
        data=raw(receipt()); digest=hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"private.json"; source.write_bytes(data)
            record=Path(directory)/"capture.json"
            value=dict(schema="hub_relay.capture.v0.1",exit_code=0,capture_complete=True,
                       byte_length=len(data),sha256=digest,authority="none")
            record.write_text(json.dumps(value))
            command=[sys.executable,str(Path(verifier.__file__)),"--receipt",str(source),"--capture-record",str(record)]
            run=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertNotIn(digest,run.stdout+run.stderr)
            self.assertNotIn(directory,run.stdout+run.stderr)
            value["capture_complete"]=False; record.write_text(json.dumps(value))
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
            record.write_bytes(b" "*4097)
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)


if __name__ == "__main__": unittest.main()
