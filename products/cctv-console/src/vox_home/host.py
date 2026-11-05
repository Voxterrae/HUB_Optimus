"""Core-bound, bounded process host for approved trusted Home adapter modules.

Anonymous inherited pipes only; no listeners, remote module paths or eval.
Independent workers contain hangs/crashes. They are not a security sandbox:
trusted code still needs OS ACL/network/credential isolation before arbitrary
third-party adapters can be accepted. Sessions own their subprocess lifecycle.
"""
from collections import deque
from dataclasses import asdict
from pathlib import Path
import os
import subprocess
import sys
import threading
import time
import uuid

from .access import AccessContext, AccessDenied, AccessService
from .contracts import (ActionProposal, AdapterManifest, DeviceRecord, EventRecord,
                        OperationResult, Target, PERMISSION_OPERATIONS)
from .secrets import SecretBroker
from .worker import ProtocolError, decode_value, packet_bytes, read_packet

RPC_TIMEOUT = 3.0
EVENT_CAPACITY = 128
RECHECK_SECONDS = .1
STOP_TIMEOUT = .25


class AdapterHost:
    def __init__(self, access: AccessService, broker: SecretBroker,
                 approved_manifests: dict[str, AdapterManifest]):
        if type(access) is not AccessService or type(broker) is not SecretBroker or type(approved_manifests) is not dict:
            raise AccessDenied("invalid_host_configuration")
        if any(type(manifest) is not AdapterManifest or key != manifest.adapter_id
               for key, manifest in approved_manifests.items()):
            raise AccessDenied("invalid_manifest_configuration")
        self._access, self._broker = access, broker
        self._approved = dict(approved_manifests)

    def start(self, manifest: AdapterManifest, target: Target, context: AccessContext):
        if (type(manifest) is not AdapterManifest or self._approved.get(manifest.adapter_id) != manifest
                or type(target) is not Target or target not in manifest.allowed_targets
                or type(context) is not AccessContext or context.site_id != target.site_id):
            raise AccessDenied("unapproved_adapter_binding")
        now = time.time()
        permitted = []
        for operation in manifest.permissions:
            try:
                self._access.require(context, target.device_id, operation, now)
                permitted.append(operation)
            except AccessDenied:
                pass
        if not permitted:
            raise AccessDenied()
        material = None
        if "credential_use" in manifest.permissions:
            self._access.require(context, target.device_id, "credential_use", now)
            self._access.require(context, target.device_id, "credential_use", time.time())
            material = self._broker.resolve_for_worker(context, manifest.adapter_id, target.device_id, now)
        bootstrap = {"kind": "bootstrap", "manifest": asdict(manifest), "target": asdict(target),
                     "material": None if material is None else {"kind": material.kind, "value": material.value}}
        # Private material travels solely through the child's anonymous stdin.
        # Packet sizing happens before spawn; no provider keys are serialized.
        payload = packet_bytes(bootstrap)
        del bootstrap, material
        session = AdapterSession(self._access, manifest, target, context, tuple(permitted))
        try:
            session._boot(payload)
        finally:
            del payload
        return session


class AdapterSession:
    def __init__(self, access, manifest, target, context, permitted):
        self._access, self._manifest, self._target, self._context = access, manifest, target, context
        self._permitted = permitted
        self._condition = threading.Condition()
        self._rpc_lock = threading.Lock()
        self._stop_lock = threading.Lock()
        self._events = deque()
        self._response = None
        self._pending = None
        self._ready = False
        self._closed = False
        self._failure = "worker_closed"
        self._subscribed = False
        self._event_end = False
        self._event_error = False
        self._event_terminal_status = None
        self._counter = 0
        self.process = subprocess.Popen([sys.executable, "-m", "vox_home.worker"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            bufsize=0, close_fds=True,
            cwd=str(Path(__file__).resolve().parent.parent),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._monitor = threading.Thread(target=self._watch, daemon=True)
        self._reader.start()
        self._monitor.start()

    def _require(self, operation, now):
        try:
            # Caller time is additional input, never a way to extend a grant.
            self._access.require(self._context, self._target.device_id, operation, now)
            self._access.require(self._context, self._target.device_id, operation, time.time())
        except AccessDenied:
            self._shutdown("access_denied", clear_events=True)
            raise

    def _watch(self):
        while True:
            with self._condition:
                if self._closed:
                    return
            try:
                for operation in self._permitted:
                    self._access.require(self._context, self._target.device_id, operation, time.time())
            except AccessDenied:
                self._shutdown("access_denied", clear_events=True)
                return
            with self._condition:
                self._condition.wait(RECHECK_SECONDS)

    def _send(self, payload):
        try:
            # The sender can block on a full pipe; RPC timeout kills the child
            # and closes the pipe. Callers never perform a blocking pipe write.
            pending = memoryview(payload)
            while pending:
                written = self.process.stdin.write(pending)
                if not written:
                    raise OSError("pipe_closed")
                pending = pending[written:]
            self.process.stdin.flush()
        except (OSError, ValueError):
            self._shutdown("worker_closed")

    def _boot(self, payload):
        deadline = time.monotonic() + RPC_TIMEOUT
        threading.Thread(target=self._send, args=(payload,), daemon=True).start()
        with self._condition:
            while not self._ready and not self._closed:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
            ready = self._ready and not self._closed
        if not ready:
            self._shutdown("timeout")
            raise RuntimeError("worker_start_failed")

    def _bound(self, value):
        if type(value) is Target:
            return value == self._target
        if type(value) in (DeviceRecord, EventRecord):
            if (value.site_id, value.device_id) != (self._target.site_id, self._target.device_id):
                return False
            if type(value) is DeviceRecord and value.adapter_id != self._manifest.adapter_id:
                return False
        if type(value) is ActionProposal:
            return value.target == self._target
        if type(value) is OperationResult:
            return self._bound(value.value)
        if type(value) is dict:
            return all(self._bound(item) for item in value.values())
        if type(value) in (tuple, list):
            return all(self._bound(item) for item in value)
        return True

    def _read(self):
        failure = "protocol_error"
        try:
            while True:
                packet = read_packet(self.process.stdout)
                kind = packet.get("kind")
                if kind == "ready" and set(packet) == {"kind"}:
                    with self._condition:
                        if self._ready:
                            raise ProtocolError("duplicate_ready")
                        self._ready = True
                        self._condition.notify_all()
                elif kind == "response" and set(packet) == {"kind", "id", "value"}:
                    result = decode_value(packet["value"])
                    if type(result) not in (OperationResult, DeviceRecord, ActionProposal):
                        raise ProtocolError("invalid_response")
                    if not self._bound(result):
                        failure = "identity_mismatch"
                        break
                    with self._condition:
                        if type(packet["id"]) is not int or packet["id"] != self._pending or self._response is not None:
                            raise ProtocolError("unexpected_response")
                        self._response = result
                        self._condition.notify_all()
                elif kind == "event" and set(packet) == {"kind", "value"}:
                    self._require("events", time.time())
                    event = decode_value(packet["value"])
                    if type(event) is not EventRecord:
                        raise ProtocolError("invalid_event")
                    if not self._bound(event):
                        failure = "identity_mismatch"
                        break
                    with self._condition:
                        if not self._subscribed:
                            raise ProtocolError("unexpected_event")
                        if len(self._events) >= EVENT_CAPACITY:
                            # The final slot becomes an explicit loss marker.
                            self._events.pop()
                            self._events.append(EventRecord("overflow-" + uuid.uuid4().hex,
                                self._target.site_id, self._target.device_id, None,
                                "event_overflow", "None", None, time.time()))
                            failure = "event_overflow"
                            break
                        self._events.append(event)
                elif kind in ("event_end", "event_error"):
                    if set(packet) not in ({"kind"}, {"kind", "status"}):
                        raise ProtocolError("invalid_event_end")
                    status = packet.get("status")
                    if "status" in packet and (type(status) is not str or status not in (
                            "identity_mismatch", "authentication_failed", "unavailable")):
                        raise ProtocolError("invalid_event_status")
                    self._require("events", time.time())
                    with self._condition:
                        if not self._subscribed:
                            raise ProtocolError("unexpected_event_end")
                        # Publish the validated stop policy with the end flag;
                        # health must not depend on later process teardown.
                        self._event_terminal_status = status
                        self._event_end = True
                        self._event_error = kind == "event_error"
                    if status is not None or kind == "event_error":
                        failure = status or "event_source_failed"
                        break
                else:
                    raise ProtocolError("invalid_envelope")
        except EOFError:
            # A worker that exits mid-frame/result is a failed protocol boundary.
            pass
        except AccessDenied:
            failure = "access_denied"
        except (ProtocolError, OSError, ValueError, TypeError, RecursionError):
            pass
        finally:
            self._shutdown(failure, clear_events=failure == "access_denied")

    def call(self, operation: str, parameters: dict, now: float):
        if type(operation) is not str or operation not in PERMISSION_OPERATIONS:
            return OperationResult("invalid_request", None, "unknown_operation")
        self._require(operation, now)
        if operation not in self._manifest.permissions:
            return OperationResult("unsupported", None, "operation_not_approved")
        if operation in ("credential_use", "metadata_read", "evidence_read"):
            return OperationResult("unsupported", None, "core_only_operation")
        if type(parameters) is not dict:
            return OperationResult("invalid_request", None, "invalid_parameters")
        deadline = time.monotonic() + RPC_TIMEOUT
        if not self._rpc_lock.acquire(timeout=RPC_TIMEOUT):
            self._require(operation, now)
            return OperationResult("timeout", None, "request_in_progress")
        try:
            return self._call_locked(operation, parameters, now, deadline)
        finally:
            self._rpc_lock.release()

    def _call_locked(self, operation, parameters, now, deadline):
        self._require(operation, now)
        with self._condition:
            if operation == "health" and self._event_terminal_status is not None:
                return OperationResult(self._event_terminal_status, None, "subscription_stopped")
            if self._closed:
                return OperationResult(self._failure, None, "worker_stopped")
            if operation == "health" and self._subscribed and self._event_end:
                return OperationResult("event_source_failed" if self._event_error else "event_source_ended", None, "subscription_stopped")
            self._counter += 1
            request_id = self._counter
            self._pending = request_id
            self._response = None
            if operation == "events" and parameters == {}:
                self._subscribed = True
        try:
            payload = packet_bytes({"kind": "request", "id": request_id,
                                    "operation": operation, "parameters": parameters})
        except ProtocolError as error:
            if str(error) == "message_too_large":
                self._shutdown("message_too_large")
                return OperationResult("message_too_large", None, "message_limit")
            with self._condition:
                self._pending = None
            return OperationResult("invalid_request", None, "invalid_parameters")
        threading.Thread(target=self._send, args=(payload,), daemon=True).start()
        with self._condition:
            while self._response is None and not self._closed:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(remaining)
            result, closed = self._response, self._closed
            self._pending = None
            self._response = None
        self._require(operation, now)
        if result is None:
            if not closed:
                self._shutdown("timeout")
            return OperationResult(self._failure, None, "worker_stopped")
        if type(result) is DeviceRecord:
            return OperationResult("ok", result, None)
        return result

    def poll_events(self) -> list[EventRecord]:
        self._require("events", time.time())
        with self._condition:
            events = list(self._events)
            self._events.clear()
        self._require("events", time.time())
        return events

    def _shutdown(self, failure, *, clear_events=False):
        with self._condition:
            if clear_events:
                self._events.clear()
            if not self._closed:
                self._closed = True
                self._failure = failure
            self._condition.notify_all()
        with self._stop_lock:
            if self.process.poll() is None:
                try:
                    self.process.terminate()
                    self.process.wait(STOP_TIMEOUT)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    try:
                        self.process.wait(STOP_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        pass
                except OSError:
                    pass
            for pipe in (self.process.stdin, self.process.stdout):
                try:
                    pipe.close()
                except (OSError, ValueError):
                    pass

    def close(self):
        self._shutdown("worker_closed", clear_events=True)
