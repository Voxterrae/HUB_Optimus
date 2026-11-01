"""Strict offline v0.1 diagnostic validator; parsing never grants authority.

The 32 MiB input/depth limits bound wire data, not Python's working set. Build
stamps, paths, token fields and a successful digest comparison are untrusted
diagnostic data. Exact complete capture and exit evidence are checked separately.
No dependency on historical proposal tools is required in the delivered bundle.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

MAX_RECEIPT_BYTES = 32 * 1024 * 1024
MAX_JSON_DEPTH = 8
_U32_MAX = 0xFFFFFFFF
_U64_MAX = 0xFFFFFFFFFFFFFFFF
_TARGET = "x86_64-pc-windows-msvc"
_OBSERVATIONS = ("process", "primary_token", "thread_token", "anchor", "ancestors")
_FIXED = dict(schema="hub_relay.bootstrap_inventory.v0.1", mode="diagnostic_only",
              activation="blocked", loaded_image_provenance="not_established",
              product_collision="not_observed", service_collision="not_observed",
              service_sid_binding="external_evidence_required")
_ROOT_KEYS = frozenset((*_FIXED, *_OBSERVATIONS, "outcome", "collector", "started_utc",
                        "finished_utc", "elapsed_ms", "thread_context", "recheck", "errors", "cleanup"))
_OPERATIONS = frozenset(("DuplicateHandle", "GetHandleInformation", "GetProcessId", "GetProcessTimes",
    "QueryFullProcessImageNameW", "IsWow64Process2", "OpenProcessToken", "OpenThreadToken",
    "GetTokenInformation", "CoInitializeEx", "SHGetKnownFolderPath", "CreateFileW", "NtCreateFile",
    "NtQueryInformationFile", "GetFileInformationByHandleEx", "GetFileType",
    "GetVolumeInformationByHandleW", "GetFinalPathNameByHandleW", "GetVolumeNameForVolumeMountPointW",
    "GetDriveTypeW", "GetSecurityInfo", "LookupPrivilegeNameW", "CompareStringOrdinal",
    "CloseHandle", "LocalFree", "validate", "serialize"))
_REASONS = frozenset(("unsupported", "malformed", "bound", "policy", "impersonation", "app_container",
                      "token_changed", "drift", "budget", "receipt_bound"))
_RECEIPT_ERROR = dict(kind="receipt", phase="serialize", operation="serialize", domain="internal",
                      code=None, reason="receipt_bound", ancestor_index=None, completion=None)
_CLEANUP = frozenset(("CloseHandle", "LocalFree"))
_NT = frozenset(("NtCreateFile", "NtQueryInformationFile"))


class ReceiptError(ValueError):
    """Closed diagnostic; never carries private input in its message/context."""
    def __init__(self):
        super().__init__("Invalid diagnostic receipt")


class _ClosedParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Invalid diagnostic verifier arguments.\n")


def _reject(*_unused):
    raise ReceiptError() from None


def _object(value, keys):
    if type(value) is not dict or value.keys() != frozenset(keys): _reject()
    return value


def _enum(value, choices):
    if type(value) is not str or value not in choices: _reject()


def _integer(value, minimum=0, maximum=_U32_MAX):
    if type(value) is not int or not minimum <= value <= maximum: _reject()
    return value


def _u64s(value):
    if (type(value) is not str or not 1 <= len(value) <= 20
            or any(c not in "0123456789" for c in value)
            or (len(value) > 1 and value[0] == "0") or int(value) > _U64_MAX): _reject()
    return int(value)


def _hex(value, length):
    if (type(value) is not str or len(value) != length * 2
            or any(c not in "0123456789abcdef" for c in value)): _reject()
    return bytes.fromhex(value)


def _text(value, limit, empty=False):
    if type(value) is not str or "\0" in value: _reject()
    count = len(value.encode("utf-16-le", "strict")) // 2
    if count > limit or (not empty and count == 0): _reject()
    return value


def _path(value):
    _object(value, ("text", "utf16_units"))
    text = _text(value["text"], 32767)
    _integer(value["utf16_units"], 1, 32767)
    if len(text.encode("utf-16-le")) // 2 != value["utf16_units"]: _reject()
    return text


def _bytes(value, maximum):
    _object(value, ("hex", "byte_count"))
    count = _integer(value["byte_count"], 0, maximum)
    return _hex(value["hex"], count)


def _sid_raw(data):
    if not 8 <= len(data) <= 68 or data[0] != 1 or data[1] > 15 or len(data) != 8 + 4 * data[1]: _reject()
    return int.from_bytes(data[2:8], "big"), struct.unpack("<" + "I" * data[1], data[8:])


def _sid(value):
    data = _bytes(value, 68)
    _sid_raw(data)
    return data


def _luid(value):
    _object(value, ("low", "high")); _integer(value["low"]); _integer(value["high"], -2147483648, 2147483647)


def _sid_attributes(value):
    _object(value, ("sid", "attributes")); _sid(value["sid"]); _integer(value["attributes"])


def _array(value, maximum, validate):
    if type(value) is not list or len(value) > maximum: _reject()
    for item in value: validate(item)


def _token(value):
    _object(value, ("type", "impersonation_level", "user", "owner", "primary_group", "integrity", "groups",
        "restricted_sids", "capabilities", "privileges", "token_id", "authentication_id", "modified_id",
        "session_id", "elevation_type", "elevation", "has_restrictions", "is_app_container", "mandatory_policy",
        "ui_access", "virtualization_allowed", "virtualization_enabled"))
    _integer(value["type"], 1, 2)
    if value["type"] == 1:
        if value["impersonation_level"] is not None: _reject()
    else: _integer(value["impersonation_level"], 0, 3)
    for key in ("user", "owner", "primary_group"): _sid(value[key])
    _sid_attributes(value["integrity"])
    for key in ("groups", "restricted_sids", "capabilities"): _array(value[key], 2048, _sid_attributes)
    def privilege(item):
        _object(item, ("luid", "name", "attributes")); _luid(item["luid"])
        _text(item["name"], 256); _integer(item["attributes"])
    _array(value["privileges"], 256, privilege)
    for key in ("token_id", "authentication_id", "modified_id"): _luid(value[key])
    for key in ("session_id", "elevation_type", "elevation", "has_restrictions", "is_app_container",
                "mandatory_policy", "ui_access", "virtualization_allowed", "virtualization_enabled"): _integer(value[key])


def _process(value):
    _object(value, ("pid", "creation_utc", "process_machine", "native_machine", "image_win32", "image_native"))
    _integer(value["pid"]); _u64s(value["creation_utc"])
    _integer(value["process_machine"], 0, 65535); _integer(value["native_machine"], 0, 65535)
    _path(value["image_win32"]); _path(value["image_native"])


def _component(component):
    if (not component or component in (".", "..") or component[-1] in " ."
            or any(ord(c) < 32 or c in '\\/:*?"<>|' for c in component)): _reject()


def _drive_route(text):
    if len(text) < 3 or text[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" or text[1:3] != ":\\": _reject()
    suffix = text[3:]
    if suffix:
        for component in suffix.split("\\"): _component(component)
    return suffix


def _anchor(value):
    _object(value, ("known_folder_id", "resolved_path", "volume_guid", "native_root", "volume_serial64",
                    "filesystem_serial32", "filesystem", "drive_type"))
    _enum(value["known_folder_id"], ("905e63b6-c1bf-494e-b29c-65b732d3d21a",))
    _drive_route(_path(value["resolved_path"]))
    guid = _path(value["volume_guid"])
    if not re.fullmatch(r"\\\\\?\\Volume\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}\\", guid, re.ASCII|re.IGNORECASE): _reject()
    native = _path(value["native_root"])
    base=native.rstrip("\\")
    if not _ordinal_equal(base[:8],"\\Device\\") or len(base.split("\\")) != 3 or native.endswith("\\\\"): _reject()
    _component(base.split("\\")[2])
    _u64s(value["volume_serial64"]); _integer(value["filesystem_serial32"])
    _text(value["filesystem"], 31); _integer(value["drive_type"])


def _ordinal_equal(left, right):
    # Deliberate conservative subset shared with the collector: fold ASCII only,
    # require exact non-ASCII code points. This is not Windows Unicode casefold.
    table=str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
    return left.translate(table) == right.translate(table)


_TRUSTED = {(5, (18,)), (5, (32, 544)),
            (5, (80, 956008885, 3418522649, 1831038044, 1853292631, 2271478464))}


def _descriptor(data, policy):
    """Conservative OS ancestor policy; no effective-access computation."""
    if not 20 <= len(data) <= 65536: _reject()
    revision, reserved, control, owner, group, sacl, dacl = struct.unpack_from("<BBHIIII", data)
    if revision != 1 or reserved != 0 or not control & 0x8000 or not control & 4 or sacl != 0 or not owner or not dacl: _reject()
    regions = [(0, 20)]
    def sid_at(offset):
        if offset < 20 or offset % 4 or offset + 8 > len(data): _reject()
        end = offset + 8 + 4 * data[offset + 1]
        if end > len(data): _reject()
        parsed = _sid_raw(data[offset:end]); regions.append((offset, end)); return parsed
    owner_sid = sid_at(owner)
    if group: sid_at(group)
    if dacl < 20 or dacl % 4 or dacl + 8 > len(data): _reject()
    acl_rev, sbz1, size, count, sbz2 = struct.unpack_from("<BBHHH", data, dacl)
    if acl_rev not in (2, 4) or sbz1 or sbz2 or size < 8 or size % 4 or dacl + size > len(data): _reject()
    regions.append((dacl, dacl + size)); cursor=dacl+8
    for _ in range(count):
        if cursor + 8 > dacl + size: _reject()
        kind, flags, ace_size, mask = struct.unpack_from("<BBHI", data, cursor)
        if (kind not in (0, 1) or flags & ~0x1F or ((flags & 0x0C) and not flags & 3)
                or ace_size < 16 or ace_size % 4 or cursor + ace_size > dacl + size): _reject()
        principal = _sid_raw(data[cursor + 8:cursor + ace_size])
        authority, subs = principal
        if principal in ((0, (0,)), (5, (10,))): _reject()
        if authority == 3 and (subs not in ((0,), (1,)) or not flags & 8): _reject()
        expanded = mask & 0x0FFFFFFF
        for generic, mapped in ((0x80000000, 0x120089), (0x40000000, 0x120116),
                                (0x20000000, 0x1200A0), (0x10000000, 0x1F01FF)):
            if mask & generic: expanded |= mapped
        if not expanded or expanded & ~0x1F01FF: _reject()
        if policy and kind == 0 and not flags & 8 and principal not in _TRUSTED and expanded & ~0x1200AD: _reject()
        cursor += ace_size
    if any(data[cursor:dacl+size]): _reject()
    for i, (start, end) in enumerate(regions):
        if any(start < other_end and other_start < end for other_start, other_end in regions[:i]): _reject()
    if policy and owner_sid not in _TRUSTED: _reject()


def _ancestor(value):
    _object(value, ("index", "path", "native_path", "volume_serial64", "file_id", "attributes",
                    "reparse_tag", "delete_pending", "owner_dacl", "policy_result"))
    _integer(value["index"], 0, 127); _path(value["path"]); _path(value["native_path"])
    _u64s(value["volume_serial64"]); _hex(value["file_id"], 16)
    _integer(value["attributes"]); _integer(value["reparse_tag"])
    if type(value["delete_pending"]) is not bool: _reject()
    _enum(value["policy_result"], ("match", "refused"))
    _descriptor(_bytes(value["owner_dacl"], 65536), value["policy_result"] == "match")


def _error(value):
    _object(value, ("kind", "phase", "operation", "domain", "code", "reason", "ancestor_index", "completion"))
    _enum(value["kind"], ("primary", "cleanup", "receipt"))
    _enum(value["phase"], ("initial", "capture", "recheck", "cleanup", "serialize"))
    _enum(value["operation"], _OPERATIONS); _enum(value["domain"], ("win32", "hresult", "ntstatus", "internal"))
    if value["ancestor_index"] is not None: _integer(value["ancestor_index"], 0, 127)
    if value["domain"] == "internal":
        if value["code"] is not None: _reject()
        _enum(value["reason"], _REASONS)
    else:
        _integer(value["code"])
        if value["reason"] is not None: _reject()
    completion=value["completion"]
    if completion is not None:
        _object(completion, ("call", "io_status", "information"))
        call=_integer(completion["call"]); io=_integer(completion["io_status"]); info=_u64s(completion["information"])
        if (value["operation"] not in _NT or call == 0x103 or io == 0x103
                or (call < 0x80000000 and io == 0xC0000001 and info == _U64_MAX)): _reject()
        if value["domain"] == "ntstatus":
            # The collector requires exact STATUS_SUCCESS, not NT_SUCCESS.
            # Other terminal statuses retain their original native domain.
            if value["code"] != call or (call == 0 and io == 0): _reject()
        elif value["domain"] != "internal" or value["reason"] != "malformed" or call != 0 or io != 0: _reject()
    elif value["domain"] == "ntstatus": _reject()
    if value["kind"] == "receipt":
        if value != _RECEIPT_ERROR: _reject()
    elif value["kind"] == "cleanup":
        if value["phase"] != "cleanup" or value["operation"] not in _CLEANUP: _reject()
    elif (value["phase"] == "serialize" or value["operation"] == "serialize"
          or ((value["phase"] == "cleanup") != (value["operation"] in _CLEANUP))): _reject()


def _validated(value):
    _object(value, _ROOT_KEYS)
    for key, expected in _FIXED.items(): _enum(value[key], (expected,))
    _enum(value["outcome"], ("observed", "refused"))
    collector = _object(value["collector"], ("source_commit", "policy_sha256", "target"))
    _hex(collector["source_commit"], 20); _hex(collector["policy_sha256"], 32)
    target=collector["target"]
    if type(target) is not str or len(target) > 128 or not target.isascii() or "\0" in target: _reject()
    for key in ("started_utc", "finished_utc", "elapsed_ms"): _u64s(value[key])
    _enum(value["thread_context"], ("no_token", "present", "unknown"))
    _enum(value["recheck"], ("equal", "changed", "not_completed")); _enum(value["cleanup"], ("complete", "failed"))
    for key, validate in (("process", _process), ("primary_token", _token), ("thread_token", _token), ("anchor", _anchor)):
        if value[key] is not None: validate(value[key])
    if value["thread_context"] == "no_token" and value["thread_token"] is not None: _reject()
    if value["thread_token"] is not None and (value["thread_context"] != "present" or value["thread_token"]["type"] != 2): _reject()
    ancestors=value["ancestors"]
    if ancestors is not None:
        _array(ancestors, 128, _ancestor)
        if not ancestors: _reject()
        for index, ancestor in enumerate(ancestors):
            if ancestor["index"] != index: _reject()
        identities=[(a["volume_serial64"], a["file_id"]) for a in ancestors]
        if value["outcome"] == "observed" and len(set(identities)) != len(identities): _reject()
        anchor=value["anchor"]
        if anchor is not None:
            suffix = _drive_route(anchor["resolved_path"]["text"])
            route = [""] if not suffix else ["", *["\\".join(suffix.split("\\")[:n]) for n in range(1, len(suffix.split("\\"))+1)]]
            if len(ancestors) != len(route): _reject()
            for a, suffix in zip(ancestors, route):
                native_expected=anchor["native_root"]["text"]
                if suffix: native_expected=native_expected.rstrip("\\")+"\\"+suffix
                if (a["volume_serial64"] != anchor["volume_serial64"]
                        or not _ordinal_equal(a["path"]["text"], anchor["volume_guid"]["text"] + suffix)
                        or not _ordinal_equal(a["native_path"]["text"], native_expected)): _reject()
    errors=value["errors"]
    _array(errors, 256, _error)
    primary=receipt=cleanup_failed=False
    for index, error in enumerate(errors):
        kind=error["kind"]
        if kind == "primary":
            if primary or index != 0: _reject()
            primary=True; cleanup_failed=error["operation"] in _CLEANUP
        elif kind == "cleanup":
            if receipt: _reject()
            cleanup_failed=True
        else:
            if receipt or index != len(errors)-1 or any(value[key] is not None for key in _OBSERVATIONS): _reject()
            receipt=True
    if (len(errors) == 256 and not receipt) or (value["cleanup"] == "failed") != cleanup_failed: _reject()
    if value["outcome"] == "refused":
        if not errors: _reject()
    else:
        if (any(value[key] is None for key in ("process", "primary_token", "anchor", "ancestors"))
                or value["thread_context"] != "no_token" or value["thread_token"] is not None
                or value["recheck"] != "equal" or errors or value["cleanup"] != "complete"
                or int(value["elapsed_ms"]) > 10000 or collector["target"] != _TARGET): _reject()
        process, token, anchor=value["process"], value["primary_token"], value["anchor"]
        if (process["pid"] == 0 or process["process_machine"] != 0 or process["native_machine"] != 0x8664
                or token["type"] != 1 or token["is_app_container"] != 0 or anchor["filesystem"] != "NTFS" or anchor["drive_type"] != 3
                or len(ancestors) != len(route)): _reject()
        for ancestor in ancestors:
            if (ancestor["policy_result"] != "match" or ancestor["reparse_tag"] != 0
                    or ancestor["attributes"] & 0x400 or not ancestor["attributes"] & 0x10
                    or ancestor["delete_pending"]): _reject()
    return value


def _check_depth(raw):
    depth=0; string=escaped=False
    for byte in raw:
        if string:
            if escaped: escaped=False
            elif byte == 92: escaped=True
            elif byte == 34: string=False
        elif byte == 34: string=True
        elif byte in (91, 123):
            depth += 1
            if depth > MAX_JSON_DEPTH: _reject()
        elif byte in (93, 125):
            depth -= 1
            if depth < 0: _reject()
    if depth != 0 or string: _reject()


def _unique(pairs):
    result={}
    for key, value in pairs:
        if key in result: _reject()
        result[key]=value
    return result


def _json_integer(text):
    if len(text) > 11: _reject()
    return int(text)


def parse_receipt(raw: bytes) -> dict:
    """Return strict diagnostic data, never a capability or approval object."""
    try:
        if type(raw) is not bytes or len(raw) > MAX_RECEIPT_BYTES or raw.startswith(b"\xef\xbb\xbf"): _reject()
        _check_depth(raw)
        value=json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_unique, parse_int=_json_integer,
                         parse_float=_reject, parse_constant=_reject)
        return _validated(value)
    except Exception:
        pass
    raise ReceiptError() from None


def verify_capture(raw: bytes, exit_code: int, capture_complete: bool,
                   expected_length: int, expected_sha256: str) -> dict:
    """Bind exact retained private bytes to an independently retained record.

    Equality to this caller-supplied record establishes no authenticated origin,
    approved host profile, running image, freshness or creation authority.
    """
    try:
        if type(exit_code) is not int or exit_code != 0 or capture_complete is not True: _reject()
        _integer(expected_length, 1, MAX_RECEIPT_BYTES); _hex(expected_sha256, 32)
        if type(raw) is not bytes or len(raw) != expected_length or hashlib.sha256(raw).hexdigest() != expected_sha256: _reject()
        return parse_receipt(raw)
    except Exception:
        pass
    raise ReceiptError() from None


def main(argv=None):
    parser=_ClosedParser(description="Offline diagnostic validation; activation remains blocked.")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--capture-record")
    args=parser.parse_args(argv)
    try:
        with Path(args.receipt).open("rb") as stream: raw=stream.read(MAX_RECEIPT_BYTES+1)
        if args.capture_record:
            with Path(args.capture_record).open("rb") as stream: record_raw=stream.read(4097)
            if len(record_raw) > 4096: _reject()
            record=json.loads(record_raw.decode("utf-8", "strict"), object_pairs_hook=_unique)
            _object(record, ("schema", "exit_code", "capture_complete", "byte_length", "sha256", "authority"))
            if record["schema"] != "hub_relay.capture.v0.1" or record["authority"] != "none": _reject()
            verify_capture(raw, record["exit_code"], record["capture_complete"], record["byte_length"], record["sha256"])
            print("Complete capture validated; diagnostic data only; activation blocked.")
        else:
            parse_receipt(raw)
            print("Receipt syntax validated; complete transfer not established; activation blocked.")
        return 0
    except Exception:
        print("Diagnostic validation failed; no authority established.", file=sys.stderr)
        return 1


if __name__ == "__main__": sys.exit(main())
