"""Private offline reference codec for the minimum refused-envelope subset.

The proposal and full observation validator remain pending. This codec accepts
only refused receipts with all five observation records null. It performs no
collection, Windows calls, host file reads, output, configuration or activation.
Build metadata is an unverified claim; parsing grants no authority or provenance.

Input and encoded output are capped at 128 KiB, narrower than the proposal's
32 MiB full-receipt wire limit. JSON containers are limited to depth eight.
These are input/output caps, NOT an aggregate Python heap or working-set bound:
decoding, JSON objects, a validated snapshot and encoding have their own copies.
The serializer counts a first iterencode pass before retaining output, then
checks a second pass. This is not a fallible-reservation or heap-bound promise.
No mocked or offline result is Windows evidence or complete-transfer evidence.
"""

import json


_MAX_RECEIPT_BYTES = 128 * 1024
_MAX_JSON_DEPTH = 8
_U32_MAX = 0xFFFFFFFF
_U64_MAX = 18446744073709551615
_MESSAGE = "Invalid minimum refusal receipt"
_OBSERVATIONS = ("process", "primary_token", "thread_token", "anchor", "ancestors")
_FIXED = {
    "schema": "hub_relay.bootstrap_inventory.v0.1",
    "mode": "diagnostic_only", "outcome": "refused", "activation": "blocked",
    "loaded_image_provenance": "not_established",
    "product_collision": "not_observed", "service_collision": "not_observed",
    "service_sid_binding": "external_evidence_required",
}
_ROOT_KEYS = frozenset((*_FIXED, *_OBSERVATIONS, "collector", "started_utc", "finished_utc",
                        "elapsed_ms", "thread_context", "recheck", "errors", "cleanup"))
_COLLECTOR_KEYS = frozenset(("source_commit", "policy_sha256", "target"))
_ERROR_KEYS = frozenset(("kind", "phase", "operation", "domain", "code", "reason",
                         "ancestor_index", "completion"))
_COMPLETION_KEYS = frozenset(("call", "io_status", "information"))
_OPERATIONS = frozenset((
    "DuplicateHandle", "GetHandleInformation", "GetProcessId", "GetProcessTimes",
    "QueryFullProcessImageNameW", "IsWow64Process2", "OpenProcessToken", "OpenThreadToken",
    "GetTokenInformation", "CoInitializeEx", "SHGetKnownFolderPath", "CreateFileW",
    "NtCreateFile", "NtQueryInformationFile", "GetFileInformationByHandleEx", "GetFileType",
    "GetVolumeInformationByHandleW", "GetFinalPathNameByHandleW", "GetVolumeNameForVolumeMountPointW",
    "GetDriveTypeW", "GetSecurityInfo", "LookupPrivilegeNameW", "CompareStringOrdinal",
    "CloseHandle", "LocalFree", "validate", "serialize",
))
_NT_OPERATIONS = frozenset(("NtCreateFile", "NtQueryInformationFile"))
_CLEANUP_OPERATIONS = frozenset(("CloseHandle", "LocalFree"))
_REASONS = frozenset(("unsupported", "malformed", "bound", "policy", "impersonation",
                      "app_container", "token_changed", "drift", "budget", "receipt_bound"))
_RECEIPT_ERROR = {
    "kind": "receipt", "phase": "serialize", "operation": "serialize", "domain": "internal",
    "code": None, "reason": "receipt_bound", "ancestor_index": None, "completion": None,
}


class ReceiptError(ValueError):
    """Invalid/unsupported receipt; the message never includes input or host data."""

    def __init__(self):
        super().__init__(_MESSAGE)


def _reject(*_unused):
    raise ReceiptError() from None


def _object(value, keys):
    if type(value) is not dict or len(value) != len(keys):
        _reject()
    if any(type(key) is not str for key in value) or value.keys() != keys:
        _reject()
    # Copy only bounded, closed records; callers validate the copied values.
    return dict(value)


def _enum(value, choices):
    if type(value) is not str or value not in choices:
        _reject()


def _u32(value):
    if type(value) is not int or not 0 <= value <= _U32_MAX:
        _reject()


def _u64s(value):
    if type(value) is not str or not 1 <= len(value) <= 20:
        _reject()
    if any(char < "0" or char > "9" for char in value):
        _reject()
    if (len(value) > 1 and value[0] == "0") or int(value) > _U64_MAX:
        _reject()


def _hex(value, length):
    if type(value) is not str or len(value) != length:
        _reject()
    if any(char not in "0123456789abcdef" for char in value):
        _reject()


def _error(value):
    value = _object(value, _ERROR_KEYS)
    _enum(value["kind"], ("primary", "cleanup", "receipt"))
    _enum(value["phase"], ("initial", "capture", "recheck", "cleanup", "serialize"))
    _enum(value["operation"], _OPERATIONS)
    _enum(value["domain"], ("win32", "hresult", "ntstatus", "internal"))
    index = value["ancestor_index"]
    if index is not None:
        _u32(index)
        if index > 127:
            _reject()
    if value["domain"] == "internal":
        if value["code"] is not None:
            _reject()
        _enum(value["reason"], _REASONS)
    else:
        _u32(value["code"])
        if value["reason"] is not None:
            _reject()

    completion = value["completion"]
    if completion is not None:
        completion = _object(completion, _COMPLETION_KEYS)
        _u32(completion["call"])
        _u32(completion["io_status"])
        _u64s(completion["information"])
        call, io_status = completion["call"], completion["io_status"]
        # Match relative_ntfs::classify, interpreting call's u32 bits as i32.
        # An unwritten IOSB following a nonnegative call is still live/pending.
        if (call == 0x103 or io_status == 0x103
                or (call < 0x80000000 and io_status == 0xC0000001
                    and completion["information"] == str(_U64_MAX))):
            _reject()
        if value["operation"] not in _NT_OPERATIONS:
            _reject()
        if value["domain"] == "ntstatus":
            if value["code"] != call or (call == 0 and io_status == 0):
                _reject()
        elif (value["domain"] != "internal" or value["reason"] != "malformed"
              or call != 0 or io_status != 0):
            _reject()
        value["completion"] = completion
    elif value["domain"] == "ntstatus":
        _reject()

    if value["kind"] == "receipt":
        if value != _RECEIPT_ERROR:
            _reject()
    elif value["kind"] == "cleanup":
        if value["phase"] != "cleanup" or value["operation"] not in _CLEANUP_OPERATIONS:
            _reject()
    elif (value["phase"] == "serialize" or value["operation"] == "serialize"
          or ((value["phase"] == "cleanup") != (value["operation"] in _CLEANUP_OPERATIONS))):
        _reject()
    return value


def _validated(value):
    value = _object(value, _ROOT_KEYS)
    for key, expected in _FIXED.items():
        _enum(value[key], (expected,))
    if any(value[key] is not None for key in _OBSERVATIONS):
        _reject()
    collector = _object(value["collector"], _COLLECTOR_KEYS)
    _hex(collector["source_commit"], 40)
    _hex(collector["policy_sha256"], 64)
    target = collector["target"]
    if type(target) is not str or len(target) > 128 or not target.isascii():
        _reject()
    value["collector"] = collector
    for key in ("started_utc", "finished_utc", "elapsed_ms"):
        _u64s(value[key])
    # Wall-clock reversal and elapsed > budget are representable refusals.
    _enum(value["thread_context"], ("no_token", "present", "unknown"))
    _enum(value["recheck"], ("equal", "changed", "not_completed"))
    _enum(value["cleanup"], ("complete", "failed"))
    errors = value["errors"]
    if type(errors) is not list or not 1 <= len(errors) <= 256:
        _reject()
    errors = [_error(item) for item in errors]
    # The acquisition ledger can occupy 255 entries; reserve the final slot for
    # receipt_bound. Preserve occurrence order and duplicate cleanup failures.
    primary_seen = receipt_seen = cleanup_failed = False
    for index, item in enumerate(errors):
        kind = item["kind"]
        if kind == "primary":
            if primary_seen or index != 0:
                _reject()
            primary_seen = True
            cleanup_failed = item["operation"] in _CLEANUP_OPERATIONS
        elif kind == "cleanup":
            if receipt_seen:
                _reject()
            cleanup_failed = True
        else:
            if receipt_seen or index != len(errors) - 1:
                _reject()
            receipt_seen = True
    if (len(errors) == 256 and not receipt_seen) or (value["cleanup"] == "failed") != cleanup_failed:
        _reject()
    value["errors"] = errors
    return value


def _check_json_depth(raw):
    depth = 0
    in_string = escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 92:  # backslash
                escaped = True
            elif byte == 34:  # quote
                in_string = False
        elif byte == 34:
            in_string = True
        elif byte in (91, 123):  # [, {
            depth += 1
            if depth > _MAX_JSON_DEPTH:
                _reject()
        elif byte in (93, 125):  # ], }
            depth -= 1
            if depth < 0:
                _reject()
    if depth != 0 or in_string:
        _reject()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _reject()
        result[key] = value
    return result


def _json_integer(text):
    # The subset's JSON integer fields are u32; bound conversion independently
    # of Python's configurable maximum integer-string conversion length.
    if len(text) > 10 or text.startswith("-"):
        _reject()
    return int(text)


def parse_refusal(raw: bytes) -> dict:
    """Parse one strict minimum refused-envelope document, or raise ReceiptError."""
    try:
        if type(raw) is not bytes or len(raw) > _MAX_RECEIPT_BYTES or raw.startswith(b"\xef\xbb\xbf"):
            _reject()
        _check_json_depth(raw)
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_unique_object, parse_int=_json_integer,
                           parse_float=_reject, parse_constant=_reject)
        return _validated(value)
    except Exception:
        pass
    # Raise outside the handler so JSONDecodeError.doc / UnicodeDecodeError.object
    # are not attached through __context__, even with a suppressed traceback.
    raise ReceiptError() from None


def serialize_refusal(receipt: dict) -> bytes:
    """Revalidate a minimum refusal, then encode within the private wire cap."""
    try:
        value = _validated(receipt)
        encoder = json.JSONEncoder(ensure_ascii=True, allow_nan=False, sort_keys=True,
                                   separators=(",", ":"))
        size = 0
        for chunk in encoder.iterencode(value):
            size += len(chunk)  # ensure_ascii makes every code point one byte.
            if size > _MAX_RECEIPT_BYTES:
                _reject()
        output = bytearray()
        for chunk in encoder.iterencode(value):
            encoded = chunk.encode("ascii")
            if len(output) + len(encoded) > _MAX_RECEIPT_BYTES:
                _reject()
            output.extend(encoded)
        if len(output) != size:
            _reject()
        return bytes(output)
    except Exception:
        pass
    raise ReceiptError() from None
