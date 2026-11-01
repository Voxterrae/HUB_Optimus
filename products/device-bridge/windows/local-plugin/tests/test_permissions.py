"""One-use permission tests use temporary databases and synthetic collectors only."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "hub-relay" / "permissions.py"
spec = importlib.util.spec_from_file_location("relay_permissions_test", ENTRY)
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)
server_spec = importlib.util.spec_from_file_location("relay_server_test", ENTRY.with_name("server.py"))
relay = importlib.util.module_from_spec(server_spec)
server_spec.loader.exec_module(relay)


def initialized_server(store, collector):
    server = relay.Server(permission_store=store, collector=collector)
    server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "synthetic-permission-tests", "version": "1"}}})
    server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
    return server


def call(token):
    return {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": relay.TOOL_NAME, "arguments": {"permission": token}}}


class OneUsePermissionContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hub-relay-permission-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.now = 1000.0
        self.store = self.new_store()

    def new_store(self):
        return permissions.PermissionStore(self.path, clock=lambda: self.now,
                                           directory_guard=lambda path: None)

    def database(self):
        return self.path / permissions.DB_FILENAME

    def alter(self, statement, parameters=()):
        with closing(sqlite3.connect(self.database())) as connection:
            connection.execute(statement, parameters)
            connection.commit()

    def test_issue_stores_only_hash_and_fixed_operation(self):
        token = self.store.issue(ttl_seconds=120)
        self.assertRegex(token, r"^[A-Za-z0-9_-]{43}$")
        with closing(sqlite3.connect(self.database())) as connection:
            row = connection.execute(
                "SELECT token_hash, operation, issued_at, expires_at, consumed FROM grants"
            ).fetchone()
        self.assertEqual(row, (hashlib.sha256(token.encode("ascii")).hexdigest(),
                               relay.TOOL_NAME, 1000.0, 1120.0, 0))
        for path in self.path.iterdir():
            if path.is_file():
                self.assertNotIn(token.encode("ascii"), path.read_bytes())

    def test_permission_can_be_consumed_only_once_across_store_reopen(self):
        token = self.store.issue()
        self.assertTrue(self.new_store().consume(token))
        self.assertFalse(self.store.consume(token))
        self.assertFalse(self.new_store().consume(token))
        with closing(sqlite3.connect(self.database())) as connection:
            self.assertEqual(connection.execute("SELECT consumed FROM grants").fetchone(), (1,))

    def test_invalid_and_unknown_tokens_never_consume_the_valid_grant(self):
        token = self.store.issue()
        for invalid in [None, True, 1, [], {}, "", "A" * 42, "A" * 44,
                        "A" * 42 + "!", "A" * 42 + "\n", "A" * 43]:
            with self.subTest(invalid=invalid):
                self.assertFalse(self.store.consume(invalid))
        self.assertTrue(self.store.consume(token))

    def test_expiry_boundary_is_exclusive_and_clock_rollback_is_denied(self):
        token = self.store.issue(ttl_seconds=10)
        self.now = 1010.0
        self.assertFalse(self.store.consume(token))
        self.now = 999.0
        self.assertFalse(self.store.consume(token))

    def test_valid_before_expiry_and_minimum_ttl(self):
        token = self.store.issue(ttl_seconds=1)
        self.now = 1000.5
        self.assertTrue(self.store.consume(token))

    def test_expiry_during_directory_validation_is_checked_before_consumption(self):
        token = self.store.issue(ttl_seconds=1)

        def delayed_guard(path):
            self.now = 1001.0

        store = permissions.PermissionStore(self.path, clock=lambda: self.now,
                                             directory_guard=delayed_guard)
        collector = Mock()
        server = initialized_server(store, collector)
        self.assertTrue(server.handle(call(token))["result"]["isError"])
        collector.assert_not_called()
        with closing(sqlite3.connect(self.database())) as connection:
            self.assertEqual(connection.execute("SELECT consumed FROM grants").fetchone(), (0,))

    def test_invalid_ttl_and_clock_do_not_issue_permissions(self):
        for ttl in [0, -1, 121, True, 1.5, "120", None, float("nan"), float("inf")]:
            with self.subTest(ttl=ttl):
                with self.assertRaises((ValueError, permissions.PermissionError)):
                    self.store.issue(ttl_seconds=ttl)
        for now in [True, float("nan"), float("inf"), -1.0, "1000"]:
            self.now = now
            with self.subTest(now=now):
                with self.assertRaises((ValueError, permissions.PermissionError)):
                    self.store.issue()

    def test_wrong_operation_or_malformed_database_times_fail_closed(self):
        for column, value in [("operation", "shell"), ("expires_at", 1121.0),
                              ("issued_at", 1001.0), ("expires_at", 999.0),
                              ("consumed", 2)]:
            with self.subTest(column=column):
                token = self.store.issue()
                self.alter("UPDATE grants SET " + column + "=? WHERE token_hash=?",
                           (value, hashlib.sha256(token.encode("ascii")).hexdigest()))
                self.assertFalse(self.store.consume(token))

    def test_consumer_never_creates_missing_database_or_missing_directory(self):
        self.assertFalse(self.database().exists())
        with self.assertRaises(permissions.PermissionError):
            self.store.consume("A" * 43)
        self.assertFalse(self.database().exists())
        missing = self.path / "missing"
        store = permissions.PermissionStore(missing, clock=lambda: self.now,
                                             directory_guard=lambda path: None)
        with self.assertRaises(permissions.PermissionError):
            store.consume("A" * 43)
        self.assertFalse(missing.exists())

    def test_corrupt_store_has_fixed_error_without_private_paths(self):
        self.database().write_bytes(b"PRIVATE-SENTINEL-not-a-database")
        with self.assertRaises(permissions.PermissionError) as caught:
            self.store.consume("A" * 43)
        self.assertEqual(str(caught.exception), "PERMISSION_STORE_UNAVAILABLE")
        self.assertNotIn(str(self.path), str(caught.exception))

    def test_locked_store_denies_without_consuming_then_can_recover(self):
        token = self.store.issue()
        connection = sqlite3.connect(self.database(), timeout=0)
        self.addCleanup(connection.close)
        connection.execute("BEGIN EXCLUSIVE")
        try:
            with self.assertRaises(permissions.PermissionError):
                self.new_store().consume(token)
        finally:
            connection.rollback()
        self.assertTrue(self.store.consume(token))

    def test_store_io_failure_denies_without_token_or_path_leak(self):
        token = self.store.issue()
        with patch.object(permissions.sqlite3, "connect", side_effect=sqlite3.OperationalError(
                "PRIVATE-SECRET-PATH-" + token)):
            with self.assertRaises(permissions.PermissionError) as caught:
                self.store.consume(token)
        self.assertEqual(str(caught.exception), "PERMISSION_STORE_UNAVAILABLE")
        self.assertTrue(self.store.consume(token))

    def test_commit_failure_never_collects_even_if_commit_reached_disk(self):
        original_connect = sqlite3.connect
        for committed in (False, True):
            token = self.store.issue()

            class FailedCommit(sqlite3.Connection):
                def commit(self):
                    if committed:
                        super().commit()
                    raise sqlite3.OperationalError("PRIVATE-COMMIT-" + token)

            def connect(*args, **kwargs):
                return original_connect(*args, factory=FailedCommit, **kwargs)

            collector = Mock()
            server = initialized_server(self.store, collector)
            with patch.object(permissions.sqlite3, "connect", side_effect=connect):
                response = server.handle(call(token))
            self.assertTrue(response["result"]["isError"])
            self.assertNotIn("PRIVATE", json.dumps(response))
            self.assertNotIn(token, json.dumps(response))
            collector.assert_not_called()
            self.assertEqual(self.new_store().consume(token), not committed)

    def test_default_environment_cannot_select_relative_or_caller_database(self):
        for root in [None, "", "relative", "../private"]:
            with self.subTest(root=root), patch.dict(os.environ, {}, clear=True):
                if root is not None:
                    os.environ["PLUGIN_DATA"] = root
                with self.assertRaises(permissions.PermissionError):
                    permissions.from_environment()
        with patch.dict(os.environ, {"PLUGIN_DATA": str(self.path)}, clear=True):
            store = permissions.from_environment()
            self.assertEqual(store.data_dir, self.path / "one-use")
            self.assertEqual(store.db_path, self.path / "one-use" / permissions.DB_FILENAME)

    def test_platform_guard_does_not_silently_weaken_on_non_windows(self):
        with patch.object(permissions.sys, "platform", "linux"):
            with self.assertRaises(permissions.PermissionError):
                permissions.validate_private_directory(self.path)

    def test_directory_guard_failure_prevents_collection(self):
        token = self.store.issue()
        store = permissions.PermissionStore(self.path, clock=lambda: self.now,
                                             directory_guard=Mock(side_effect=OSError("PRIVATE")))
        collector = Mock()
        server = initialized_server(store, collector)
        response = server.handle(call(token))
        self.assertTrue("error" in response or response.get("result", {}).get("isError"))
        self.assertNotIn("PRIVATE", json.dumps(response))
        collector.assert_not_called()

    def test_collector_failure_burns_grant_and_does_not_retry(self):
        token = self.store.issue()
        collector = Mock(side_effect=RuntimeError("PRIVATE"))
        server = initialized_server(self.store, collector)
        response = server.handle(call(token))
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(response["result"]["content"][0]["text"], "COLLECTION_FAILED")
        self.assertFalse(self.new_store().consume(token))
        self.assertTrue(server.handle(call(token))["result"]["isError"])
        collector.assert_called_once_with()

    def test_grant_is_durable_before_collector_begins(self):
        token = self.store.issue()
        observed = []

        def synthetic_collector():
            observed.append(self.new_store().consume(token))
            return relay._payload((10, 0, 1), (100, 20))

        server = initialized_server(self.store, synthetic_collector)
        response = server.handle(call(token))
        self.assertFalse(response["result"]["isError"])
        self.assertEqual(observed, [False])

    def test_two_processes_collect_at_most_once_then_restart_denies(self):
        token = self.store.issue()
        worker = r'''
import importlib.util, json, pathlib, sys
path = pathlib.Path(sys.argv[1])
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
permissions = load("worker_permissions", path)
relay = load("worker_server", path.with_name("server.py"))
store = permissions.PermissionStore(sys.argv[2], clock=lambda:1000.0,
                                     directory_guard=lambda path:None)
calls = []
def collect():
    calls.append(1)
    return relay._payload((10, 0, 1), (100, 20))
server = relay.Server(permission_store=store, collector=collect)
server.handle({"jsonrpc":"2.0", "id":1, "method":"initialize", "params":{
    "protocolVersion":"2025-06-18", "capabilities":{},
    "clientInfo":{"name":"synthetic-worker", "version":"1"}}})
server.handle({"jsonrpc":"2.0", "method":"notifications/initialized"})
token = sys.stdin.readline().strip()
response = server.handle({"jsonrpc":"2.0", "id":2, "method":"tools/call", "params":{
    "name":relay.TOOL_NAME, "arguments":{"permission":token}}})
print(json.dumps({"calls":len(calls), "success":not response.get("result", {}).get("isError", True)}))
'''

        def run_worker():
            completed = subprocess.run([sys.executable, "-I", "-B", "-c", worker,
                                        str(ENTRY), str(self.path)], input=token + "\n",
                                       text=True, capture_output=True, timeout=20)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            self.assertNotIn(token, completed.stdout)
            return json.loads(completed.stdout)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_worker) for _ in range(2)]
            results = [future.result() for future in futures]
        self.assertEqual(sum(result["calls"] for result in results), 1)
        self.assertEqual(sum(result["success"] for result in results), 1)
        self.assertEqual(run_worker(), {"calls": 0, "success": False})


if __name__ == "__main__":
    unittest.main()
