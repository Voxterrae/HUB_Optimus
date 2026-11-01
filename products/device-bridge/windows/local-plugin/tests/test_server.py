"""Contract tests. Never invoke an unmocked Windows collector."""

import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "hub-relay" / "server.py"
spec = importlib.util.spec_from_file_location("relay_candidate", ENTRY)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


def request(method, params=None, ident=1):
    value = {"jsonrpc": "2.0", "id": ident, "method": method}
    if params is not None:
        value["params"] = params
    return value


def initialize(version="2025-06-18"):
    return request("initialize", {
        "protocolVersion": version, "capabilities": {},
        "clientInfo": {"name": "candidate-tests", "version": "1.0.0"},
    })


def ready(server, version="2025-06-18"):
    response = server.handle(initialize(version))
    server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
    return response


def call(arguments=None, ident=3):
    return request("tools/call", {
        "name": relay.TOOL_NAME, "arguments": {} if arguments is None else arguments,
    }, ident)


class FakeBackend:
    def __init__(self, version=(10, 0, 19045), volume=(128000, 32000)):
        self.version, self.volume = version, volume
        self.calls = []

    def get_windows_version(self):
        self.calls.append("windows-version")
        return self.version

    def get_system_volume_usage(self):
        self.calls.append("fixed-system-volume")
        return self.volume


def sample():
    return relay.diagnostics(FakeBackend())


class CollectorContract(unittest.TestCase):
    def test_exact_result_has_no_identity_paths_or_runtime_claims(self):
        backend = FakeBackend()
        value = relay.diagnostics(backend)
        self.assertEqual(value, {
            "schema": "hub-relay.local-windows-diagnostics.v0.1",
            "mode": "local-supervised-pilot", "biometricEnforced": False,
            "nativeProtocol": False, "status": "completed",
            "windows": {"major": 10, "minor": 0, "build": 19045},
            "systemVolume": {"drive": "C:", "totalBytes": 128000, "freeBytes": 32000},
        })
        self.assertEqual(backend.calls, ["windows-version", "fixed-system-volume"])

    def test_backend_is_fixed_to_c_and_only_numeric_os_fields(self):
        version = Mock(major=10, minor=0, build=19045)
        disk = Mock(total=128000, free=32000)
        with patch.object(relay.sys, "platform", "win32"), \
             patch.object(relay.sys, "getwindowsversion", return_value=version, create=True) as os_read, \
             patch.object(relay.shutil, "disk_usage", return_value=disk) as disk_read:
            self.assertEqual(relay.diagnostics(), sample())
        os_read.assert_called_once_with()
        disk_read.assert_called_once_with("C:\\")

    def test_non_windows_is_not_a_fallback(self):
        with patch.object(relay.sys, "platform", "linux"), \
             patch.object(relay.shutil, "disk_usage") as disk_read:
            with self.assertRaises(relay.DiagnosticError) as caught:
                relay.diagnostics()
        self.assertEqual(caught.exception.code, "UNSUPPORTED_PLATFORM")
        disk_read.assert_not_called()

    def test_collection_failure_hides_exception_details(self):
        backend = FakeBackend()
        backend.get_windows_version = Mock(side_effect=OSError("PRIVATE-SECRET-PATH"))
        with self.assertRaises(relay.DiagnosticError) as caught:
            relay.diagnostics(backend)
        self.assertEqual(str(caught.exception), "COLLECTION_FAILED")
        self.assertEqual(backend.calls, [])

    def test_invalid_numeric_data_is_refused(self):
        invalid = [
            ((True, 0, 1), (100, 20)), ((-1, 0, 1), (100, 20)),
            ((10, 0, "19045"), (100, 20)), ((10, 0, 2**31), (100, 20)),
            ((10, 0), (100, 20)), ((10, 0, 1), (0, 0)),
            ((10, 0, 1), (100, 101)), ((10, 0, 1), (100, -1)),
            ((10, 0, 1), (100, True)), ((10, 0, 1), (2**63, 20)),
        ]
        for version, volume in invalid:
            with self.subTest(version=version, volume=volume):
                with self.assertRaises(relay.DiagnosticError):
                    relay.diagnostics(FakeBackend(version, volume))


class LifecycleContract(unittest.TestCase):
    def test_default_rejects_before_collector_even_with_meta_opt_in(self):
        collector = Mock(side_effect=AssertionError("collector must not run"))
        server = relay.Server(collector=collector)
        ready(server)
        message = call()
        message["params"]["_meta"] = {"local_enabled": True, "approval": True}
        response = server.handle(message)
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(response["result"]["content"][0]["text"], "LOCAL_PILOT_DISABLED")
        collector.assert_not_called()

    def test_discovery_is_static_and_only_lists_one_tool(self):
        collector = Mock(side_effect=AssertionError("collector must not run"))
        server = relay.Server(collector=collector)
        ready(server)
        tools = server.handle(request("tools/list"))["result"]["tools"]
        self.assertEqual([item["name"] for item in tools], [relay.TOOL_NAME])
        self.assertFalse(tools[0]["inputSchema"]["additionalProperties"])
        self.assertIn("No biometric", tools[0]["description"])
        collector.assert_not_called()

    def test_synthetic_success_is_bounded_and_truthful(self):
        collector = Mock(side_effect=sample)
        server = relay.Server(collector=collector, local_enabled=True)
        ready(server)
        response = server.handle(call())
        result = response["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(result["structuredContent"], sample())
        self.assertEqual(json.loads(result["content"][0]["text"]), sample())
        self.assertLessEqual(len(json.dumps(response).encode()), 4096)
        collector.assert_called_once_with()

    def test_omitted_arguments_and_optional_meta_are_supported(self):
        server = relay.Server(collector=sample, local_enabled=True)
        ready(server)
        self.assertIn("result", server.handle(request("tools/list", {"_meta": {"test": 1}})))
        response = server.handle(request("tools/call", {
            "name": relay.TOOL_NAME, "_meta": {"progressToken": "test"},
        }))
        self.assertFalse(response["result"]["isError"])

    def test_no_argument_can_expand_scope(self):
        collector = Mock(side_effect=sample)
        server = relay.Server(collector=collector, local_enabled=True)
        ready(server)
        for value in [[], "", True, 1, {"path": "E:\\"}, {"command": "whoami"},
                      {"device": "xiaomi"}, {"approved": True}, {"local_enabled": True},
                      {"drive": "E:"}, {"_meta": {"enabled": True}}]:
            with self.subTest(value=value):
                self.assertEqual(server.handle(call(value))["error"]["code"], -32602)
        collector.assert_not_called()

    def test_early_and_invalid_initialized_notifications_cannot_enable(self):
        collector = Mock(side_effect=sample)
        server = relay.Server(collector=collector, local_enabled=True)
        server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertIn("error", server.handle(call()))
        server.handle(initialize())
        server.handle({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {"x": 1}})
        self.assertIn("error", server.handle(call()))
        collector.assert_not_called()

    def test_bad_initialization_does_not_advance_state(self):
        server = relay.Server(collector=Mock())
        self.assertIn("error", server.handle(request("initialize", {})))
        self.assertIn("result", ready(server))
        self.assertIn("error", server.handle(initialize()))

    def test_versions_and_text_compatibility(self):
        for version in ["2024-11-05", "2025-03-26", "2025-06-18", "2099-01-01"]:
            with self.subTest(version=version):
                server = relay.Server(collector=sample, local_enabled=True)
                response = ready(server, version)
                selected = response["result"]["protocolVersion"]
                self.assertEqual(selected, "2025-06-18")
                result = server.handle(call())["result"]
                self.assertEqual(json.loads(result["content"][0]["text"]), sample())
                self.assertEqual("structuredContent" in result, selected == "2025-06-18")

    def test_invalid_envelope_is_not_a_notification(self):
        server = relay.Server(collector=Mock())
        for value in [{}, {"method": "ping"}, {"jsonrpc": "2.0"},
                      {"jsonrpc": "2.0", "method": 4}]:
            response = server.handle(value)
            self.assertEqual(response["error"]["code"], -32600)
            self.assertIsNone(response["id"])
        self.assertIsNone(server.handle({"jsonrpc": "2.0", "method": "notifications/unknown"}))

    def test_null_arguments_and_bad_metadata_do_not_invoke_collector(self):
        collector = Mock()
        server = relay.Server(collector=collector, local_enabled=True)
        ready(server)
        message = call()
        message["params"]["arguments"] = None
        self.assertIn("error", server.handle(message))
        message = call()
        message["params"]["_meta"] = "enable"
        self.assertIn("error", server.handle(message))
        collector.assert_not_called()

    def test_unknown_methods_and_tools_have_no_capabilities(self):
        collector = Mock()
        server = relay.Server(collector=collector, local_enabled=True)
        ready(server)
        for method in ["shell/exec", "resources/read", "roots/list", "PRIVATE-SECRET-PATH"]:
            response = server.handle(request(method))
            self.assertEqual(response["error"]["code"], -32601)
            self.assertNotIn("PRIVATE", json.dumps(response))
        response = server.handle(request("tools/call", {"name": "shell", "arguments": {}}))
        self.assertIn("error", response)
        collector.assert_not_called()

    def test_collector_failures_never_expose_details_or_partial_data(self):
        for failure in [RuntimeError("PRIVATE-SECRET-PATH"), relay.DiagnosticError("UNSUPPORTED_PLATFORM")]:
            server = relay.Server(collector=Mock(side_effect=failure), local_enabled=True)
            ready(server)
            result = server.handle(call())["result"]
            self.assertTrue(result["isError"])
            self.assertNotIn("PRIVATE", json.dumps(result))
            self.assertNotIn("structuredContent", result)

    def test_collector_cannot_smuggle_extra_fields_or_biometric_claim(self):
        values = []
        for key, value in [("biometricEnforced", True), ("nativeProtocol", True),
                           ("privateData", "SECRET" * 5000), ("status", "authorized")]:
            altered = sample()
            altered[key] = value
            values.append(altered)
        altered = sample()
        altered["systemVolume"]["drive"] = "E:"
        values.append(altered)
        for value in values:
            server = relay.Server(collector=lambda: value, local_enabled=True)
            ready(server)
            result = server.handle(call())["result"]
            self.assertTrue(result["isError"])
            self.assertNotIn("SECRET", json.dumps(result))


class TransportContract(unittest.TestCase):
    def test_ambiguous_invalid_and_unbounded_json_is_rejected(self):
        cases = [b'{"id":1,"id":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
                 b'[]', b'null', b'"text"', b'\xff', b'{', b'[' * 100 + b']' * 100,
                 b' ' * (relay.MAX_INPUT_BYTES + 1)]
        for value in cases:
            with self.subTest(value=value[:50]):
                with self.assertRaises(relay.ProtocolError):
                    relay.parse_message(value)

    def test_invalid_ids_are_rejected_without_reflection(self):
        for value in [None, True, False, 1.0, {}, [], "x" * 257, 2**70, "\ud800"]:
            response = relay.Server().handle(request("ping", ident=value))
            self.assertEqual(response["id"], None)
            self.assertEqual(response["error"]["code"], -32600)

    def test_stream_recovers_from_malformed_line_then_stops_on_eof(self):
        source = io.BytesIO(b'not-json\n' + json.dumps(request("ping")).encode() + b'\n')
        output, errors = io.BytesIO(), io.StringIO()
        self.assertEqual(relay.Server().run(source, output, errors), 0)
        messages = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(messages[0]["error"]["code"], -32700)
        self.assertEqual(messages[1]["result"], {})
        self.assertEqual(errors.getvalue(), "")

    def test_overlong_frame_terminates_without_unbounded_drain(self):
        source = io.BytesIO(b'X' * (relay.MAX_INPUT_BYTES + 5000) + b'\n')
        output, errors = io.BytesIO(), io.StringIO()
        self.assertEqual(relay.Server().run(source, output, errors), 1)
        self.assertLessEqual(source.tell(), relay.MAX_INPUT_BYTES + 1)
        self.assertLessEqual(len(output.getvalue()), 4096)
        self.assertEqual(errors.getvalue(), "HUB_RELAY_INPUT_LIMIT\n")

    def test_incomplete_frame_never_reaches_handler(self):
        server = relay.Server(collector=Mock())
        source = io.BytesIO(json.dumps(initialize()).encode())
        output, errors = io.BytesIO(), io.StringIO()
        server.run(source, output, errors)
        self.assertEqual(server.state, "new")
        self.assertIn("error", json.loads(output.getvalue()))

    def test_real_subprocess_handshake_and_default_denial_no_live_read(self):
        messages = [initialize(), {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    request("tools/list", ident=2), call()]
        wire = b"".join(json.dumps(message).encode() + b"\n" for message in messages)
        completed = subprocess.run([sys.executable, "-I", "-B", str(ENTRY)], input=wire,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b"")
        output = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual([value["id"] for value in output], [1, 2, 3])
        self.assertEqual(output[-1]["result"]["content"][0]["text"], "LOCAL_PILOT_DISABLED")
        self.assertTrue(all(len(json.dumps(value).encode()) <= 4096 for value in output))

    def test_invalid_startup_flag_never_starts_collector(self):
        completed = subprocess.run([sys.executable, "-I", "-B", str(ENTRY), "--approved=true"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, b"")


class PackageContract(unittest.TestCase):
    def test_portable_manifest_preserves_disabled_reading_and_name(self):
        manifest = json.loads((ROOT / "hub-relay" / "plugin.json").read_text(encoding="utf-8"))
        config = json.loads((ROOT / "hub-relay" / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "hub-relay")
        self.assertLessEqual(len(manifest["extensions"]["com.openai"]["interface"]["shortDescription"]), 30)
        server = config["mcpServers"]["hub-relay"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["args"], ["-I", "-B", "${PLUGIN_ROOT}/server.py"])
        self.assertNotIn("env", server)
        self.assertNotIn("url", server)


if __name__ == "__main__":
    unittest.main()
