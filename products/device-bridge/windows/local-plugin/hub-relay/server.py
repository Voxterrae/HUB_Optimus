"""Bounded MCP stdio candidate; disabled unless explicitly enabled at startup.

The opt-in flag is a local operating profile, not authentication. This candidate
does not enforce biometrics or implement the HUB_Relay native protocol.
"""

import json
import math
import shutil
import sys


MAX_INPUT_BYTES = 16384
MAX_OUTPUT_BYTES = 4096
MAX_NESTING = 16
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOLS = (PROTOCOL_VERSION,)
TOOL_NAME = "hub_relay_windows_diagnostics"
SCHEMA = "hub-relay.local-windows-diagnostics.v0.1"
DIAGNOSTIC_CODES = frozenset({
    "UNSUPPORTED_PLATFORM", "COLLECTION_FAILED", "INVALID_DIAGNOSTIC_DATA",
})


class ProtocolError(ValueError):
    """A protocol error whose message is fixed and safe to send to the client."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class DiagnosticError(ValueError):
    def __init__(self, code):
        self.code = code if code in DIAGNOSTIC_CODES else "COLLECTION_FAILED"
        super().__init__(self.code)


def _reject_constant(_value):
    raise ValueError("Invalid JSON constant")


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Invalid JSON number")
    return result


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def parse_message(raw):
    """Parse one bounded UTF-8 JSON line, rejecting ambiguous JSON and batches."""
    if type(raw) is not bytes or len(raw) > MAX_INPUT_BYTES:
        raise ProtocolError(-32700, "Parse error")
    try:
        source = raw.decode("utf-8", errors="strict")
        depth, quoted, escaped = 0, False, False
        for char in source:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                if depth > MAX_NESTING:
                    raise ValueError("Excessive nesting")
            elif char in "]}":
                depth -= 1
        message = json.loads(source, object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant, parse_float=_finite_float)
    except (UnicodeError, ValueError, RecursionError):
        raise ProtocolError(-32700, "Parse error") from None
    if type(message) is not dict:
        raise ProtocolError(-32600, "Invalid Request")
    return message


def _integer(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def _payload(version, volume):
    if (type(version) not in (tuple, list) or len(version) != 3
            or not all(_integer(value, 2**31 - 1) for value in version)
            or type(volume) not in (tuple, list) or len(volume) != 2
            or not all(_integer(value, 2**63 - 1) for value in volume)
            or volume[0] == 0 or volume[1] > volume[0]):
        raise DiagnosticError("INVALID_DIAGNOSTIC_DATA")
    return {
        "schema": SCHEMA,
        "mode": "local-supervised-pilot",
        "biometricEnforced": False,
        "nativeProtocol": False,
        "status": "completed",
        "windows": dict(zip(("major", "minor", "build"), version)),
        "systemVolume": {"drive": "C:", "totalBytes": volume[0],
                         "freeBytes": volume[1]},
    }


class WindowsBackend:
    """The only live collector: numeric OS version and fixed C: capacity."""

    def get_windows_version(self):
        if sys.platform != "win32":
            raise DiagnosticError("UNSUPPORTED_PLATFORM")
        version = sys.getwindowsversion()
        return (version.major, version.minor, version.build)

    def get_system_volume_usage(self):
        if sys.platform != "win32":
            raise DiagnosticError("UNSUPPORTED_PLATFORM")
        volume = shutil.disk_usage("C:\\")
        return (volume.total, volume.free)


def diagnostics(backend=None):
    """Collect through an injected backend, emitting only fixed validated fields."""
    backend = WindowsBackend() if backend is None else backend
    try:
        return _payload(backend.get_windows_version(),
                        backend.get_system_volume_usage())
    except DiagnosticError:
        raise
    except Exception:
        raise DiagnosticError("COLLECTION_FAILED") from None


def _validate_collector_result(value):
    """Enforce the same boundary for injected collectors and production output."""
    expected = {"schema", "mode", "biometricEnforced", "nativeProtocol",
                "status", "windows", "systemVolume"}
    if type(value) is not dict or set(value) != expected:
        raise DiagnosticError("INVALID_DIAGNOSTIC_DATA")
    windows, volume = value["windows"], value["systemVolume"]
    if (type(windows) is not dict or set(windows) != {"major", "minor", "build"}
            or type(volume) is not dict
            or set(volume) != {"drive", "totalBytes", "freeBytes"}):
        raise DiagnosticError("INVALID_DIAGNOSTIC_DATA")
    canonical = _payload(tuple(windows[key] for key in ("major", "minor", "build")),
                         (volume["totalBytes"], volume["freeBytes"]))
    if (value != canonical or value["biometricEnforced"] is not False
            or value["nativeProtocol"] is not False):
        raise DiagnosticError("INVALID_DIAGNOSTIC_DATA")
    return canonical


def _valid_id(value):
    if type(value) is int:
        return -(2**63) <= value < 2**63
    if type(value) is str:
        try:
            return len(value.encode("utf-8")) <= 256
        except UnicodeError:
            return False
    return False


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": code, "message": message}}


def _tool_error(code):
    return {"isError": True, "content": [{"type": "text", "text": code}]}


def _empty_params(params):
    if type(params) is not dict or params:
        raise ProtocolError(-32602, "Invalid params")


class Server:
    def __init__(self, collector=diagnostics, local_enabled=False):
        self.collector = collector
        self.local_enabled = local_enabled is True
        self.state = "new"
        self.protocol_version = None

    def handle(self, message):
        """Handle a decoded message; notifications never produce responses."""
        request_id = None
        notification = False
        try:
            if type(message) is not dict:
                raise ProtocolError(-32600, "Invalid Request")
            if "id" in message:
                if not _valid_id(message["id"]):
                    raise ProtocolError(-32600, "Invalid Request")
                request_id = message["id"]
            if (message.get("jsonrpc") != "2.0"
                    or type(message.get("method")) is not str
                    or not message["method"] or len(message["method"]) > 128
                    or set(message) - {"jsonrpc", "id", "method", "params"}):
                raise ProtocolError(-32600, "Invalid Request")
            notification = "id" not in message
            params = message.get("params", {})
            if type(params) is not dict:
                raise ProtocolError(-32602, "Invalid params")
            if "_meta" in params:
                if type(params["_meta"]) is not dict:
                    raise ProtocolError(-32602, "Invalid params")
                params = {key: value for key, value in params.items() if key != "_meta"}
            method = message["method"]
            if notification:
                if method == "notifications/initialized":
                    _empty_params(params)
                    if self.state == "initializing":
                        self.state = "ready"
                return None
            result = self._request(method, params)
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except ProtocolError as error:
            return None if notification else _error(request_id, error.code, error.message)
        except Exception:
            return None if notification else _error(request_id, -32603, "Internal error")

    def _request(self, method, params):
        if method == "ping":
            _empty_params(params)
            return {}
        if method == "initialize":
            if self.state != "new":
                raise ProtocolError(-32600, "Already initialized")
            client = params.get("clientInfo")
            if (set(params) != {"protocolVersion", "capabilities", "clientInfo"}
                    or type(params.get("protocolVersion")) is not str
                    or not 1 <= len(params["protocolVersion"]) <= 64
                    or type(params.get("capabilities")) is not dict
                    or type(client) is not dict
                    or any(type(client.get(key)) is not str
                           or not 1 <= len(client[key]) <= 128
                           for key in ("name", "version"))):
                raise ProtocolError(-32602, "Invalid params")
            self.protocol_version = PROTOCOL_VERSION
            self.state = "initializing"
            return {"protocolVersion": self.protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "hub-relay-local-diagnostics",
                                   "version": "0.1.0"}}
        if method not in ("tools/list", "tools/call"):
            raise ProtocolError(-32601, "Method not found")
        if self.state != "ready":
            raise ProtocolError(-32002, "Server not initialized")
        if method == "tools/list":
            _empty_params(params)
            tool = {
                "name": TOOL_NAME,
                "description": "Local supervised Windows version and C: capacity. "
                               "Disabled by default. No biometric authentication; "
                               "not the native HUB_Relay protocol.",
                "inputSchema": {"type": "object", "properties": {},
                                "additionalProperties": False},
                "annotations": {
                    "readOnlyHint": True, "destructiveHint": False,
                    "idempotentHint": True, "openWorldHint": False,
                },
            }
            return {"tools": [tool]}
        if (set(params) not in ({"name"}, {"name", "arguments"})
                or params.get("name") != TOOL_NAME):
            raise ProtocolError(-32602, "Invalid params")
        _empty_params(params.get("arguments", {}))
        if not self.local_enabled:
            return _tool_error("LOCAL_PILOT_DISABLED")
        try:
            result = _validate_collector_result(self.collector())
        except DiagnosticError as error:
            return _tool_error(error.code)
        except Exception:
            return _tool_error("COLLECTION_FAILED")
        return {"isError": False, "content": [{"type": "text", "text":
                json.dumps(result, separators=(",", ":"), allow_nan=False)}],
                "structuredContent": result}

    def run(self, input_stream, output_stream, error_stream):
        """Read newline-delimited binary stdio; terminate an oversized frame."""
        try:
            while True:
                raw = input_stream.readline(MAX_INPUT_BYTES + 1)
                if not raw:
                    return 0
                oversized = len(raw) > MAX_INPUT_BYTES
                incomplete = not raw.endswith(b"\n")
                try:
                    if incomplete:
                        raise ProtocolError(-32700, "Parse error")
                    response = self.handle(parse_message(raw))
                except ProtocolError as error:
                    response = _error(None, error.code, error.message)
                if response is not None:
                    encoded = (json.dumps(response, separators=(",", ":"),
                                          ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
                    if len(encoded) > MAX_OUTPUT_BYTES:
                        encoded = b'{"jsonrpc":"2.0","id":null,"error":{"code":-32603,"message":"Internal error"}}\n'
                    output_stream.write(encoded)
                    output_stream.flush()
                if oversized:
                    error_stream.write("HUB_RELAY_INPUT_LIMIT\n")
                    return 1
                if incomplete:
                    error_stream.write("HUB_RELAY_FRAMING_ERROR\n")
                    return 1
        except (OSError, ValueError, TypeError):
            error_stream.write("HUB_RELAY_TRANSPORT_ERROR\n")
            return 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv not in ([], ["--local-supervised-diagnostics"]):
        sys.stderr.write("Usage: server.py [--local-supervised-diagnostics]\n")
        return 2
    return Server(local_enabled=bool(argv)).run(sys.stdin.buffer, sys.stdout.buffer,
                                                sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
