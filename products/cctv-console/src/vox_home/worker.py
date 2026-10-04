"""Bounded anonymous-pipe worker for explicitly registered trusted adapters.

This is fault containment, not an OS/network sandbox. No incoming request can
select a module, target, context, or credential reference. The core sends one
private bootstrap on inherited stdin before RPC begins. Adapter stdout/stderr
are discarded; the protocol owns a separate duplicate of inherited stdout.
"""
from dataclasses import fields
import importlib
import json
import math
import os
import threading

from .contracts import (ActionProposal, Capability, DeviceRecord, EventRecord,
                        EvidenceRef, OperationResult, Target, validate_manifest)
from .secrets import SecretMaterial

MAX_MESSAGE_BYTES = 64 * 1024
_RECORDS = {kind.__name__: kind for kind in (
    Target, Capability, DeviceRecord, EventRecord, EvidenceRef, ActionProposal, OperationResult)}
_TUPLES = {"DeviceRecord": ("capabilities",), "ActionProposal": ("required_operations",)}
_output = None
_output_lock = threading.Lock()


class ProtocolError(ValueError):
    """Safe boundary failure; never include a worker's private input."""


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ProtocolError("invalid_message")
        result[key] = value
    return result


def packet_bytes(packet):
    try:
        data = json.dumps(packet, ensure_ascii=True, allow_nan=False,
                          separators=(",", ":")).encode("utf-8") + b"\n"
    except (TypeError, ValueError, RecursionError):
        raise ProtocolError("invalid_message") from None
    if len(data) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message_too_large")
    return data


def read_packet(stream):
    data = stream.readline(MAX_MESSAGE_BYTES + 1)
    if not data:
        raise EOFError
    if len(data) > MAX_MESSAGE_BYTES or not data.endswith(b"\n"):
        raise ProtocolError("invalid_message")
    try:
        packet = json.loads(data, object_pairs_hook=_pairs,
                            parse_constant=lambda value: (_ for _ in ()).throw(ProtocolError("invalid_message")))
    except (UnicodeError, ValueError, RecursionError):
        raise ProtocolError("invalid_message") from None
    if type(packet) is not dict:
        raise ProtocolError("invalid_message")
    return packet


def encode_value(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value).__name__ in _RECORDS and type(value) is _RECORDS[type(value).__name__]:
        return {"type": "record", "name": type(value).__name__,
                "fields": {field.name: encode_value(getattr(value, field.name)) for field in fields(value)}}
    if type(value) is dict and all(type(key) is str for key in value):
        return {"type": "mapping", "items": {key: encode_value(item) for key, item in value.items()}}
    if type(value) in (tuple, list):
        return {"type": "sequence", "items": [encode_value(item) for item in value]}
    raise ProtocolError("invalid_result")


def decode_value(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is not dict:
        raise ProtocolError("invalid_result")
    kind = value.get("type")
    if kind == "mapping" and set(value) == {"type", "items"} and type(value["items"]) is dict:
        return {key: decode_value(item) for key, item in value["items"].items()}
    if kind == "sequence" and set(value) == {"type", "items"} and type(value["items"]) is list:
        return [decode_value(item) for item in value["items"]]
    if kind == "record" and set(value) == {"type", "name", "fields"}:
        record = _RECORDS.get(value["name"]) if type(value["name"]) is str else None
        if record is None or type(value["fields"]) is not dict:
            raise ProtocolError("invalid_result")
        if set(value["fields"]) != {field.name for field in fields(record)}:
            raise ProtocolError("invalid_result")
        decoded = {key: decode_value(item) for key, item in value["fields"].items()}
        for name in _TUPLES.get(value["name"], ()):
            if type(decoded[name]) is not list:
                raise ProtocolError("invalid_result")
            decoded[name] = tuple(decoded[name])
        try:
            return record(**decoded)
        except (TypeError, ValueError):
            raise ProtocolError("invalid_result") from None
    raise ProtocolError("invalid_result")


def send(packet):
    data = packet_bytes(packet)
    with _output_lock:
        pending = memoryview(data)
        while pending:
            written = _output.write(pending)
            if not written:
                raise OSError("pipe_closed")
            pending = pending[written:]
        _output.flush()


def _fatal():
    # Immediate process exit also stops an idle adapter event generator.
    os._exit(2)


def _events(adapter):
    try:
        for event in adapter.subscribe_events():
            if type(event) is not EventRecord:
                raise ProtocolError("invalid_event")
            send({"kind": "event", "value": encode_value(event)})
        packet = {"kind": "event_end"}
        # Only the shipped native adapter has a cached, query-free stop cause.
        # Ordinary extensions retain generic end/error behavior. Never export
        # its result value/reason, raw transport exception or credential material.
        from .adapters.native import NativeAdapter
        if isinstance(adapter, NativeAdapter):
            status = adapter._subscription_terminal_status()
            if type(status) is str and status in (
                    "identity_mismatch", "authentication_failed", "unavailable"):
                packet["status"] = status
        send(packet)
    except Exception:
        try:
            send({"kind": "event_error"})
        finally:
            _fatal()


_PARAMETERS = {"probe": (), "health": (), "events": (), "snapshot": ("channel",),
               "recordings": ("query",), "playback": ("reference",),
               "prepare_action": ("action", "parameters"), "execute_action": ("proposal_id",)}


def _invoke(adapter, target, operation, parameters):
    if operation not in _PARAMETERS:
        return OperationResult("unsupported", None, "operation_unavailable")
    if type(parameters) is not dict or set(parameters) != set(_PARAMETERS[operation]):
        return OperationResult("invalid_request", None, "invalid_parameters")
    if operation == "probe":
        return adapter.probe(target)
    if operation == "health":
        return adapter.health()
    if operation == "snapshot":
        if type(parameters["channel"]) is not int or parameters["channel"] < 1:
            return OperationResult("invalid_request", None, "invalid_channel")
        return adapter.snapshot(parameters["channel"])
    if operation == "recordings":
        if type(parameters["query"]) is not dict:
            return OperationResult("invalid_request", None, "invalid_query")
        return adapter.list_recordings(parameters["query"])
    if operation == "playback":
        if type(parameters["reference"]) is not str:
            return OperationResult("invalid_request", None, "invalid_reference")
        return adapter.playback(parameters["reference"])
    if operation == "prepare_action":
        if type(parameters["action"]) is not str or type(parameters["parameters"]) is not dict:
            return OperationResult("invalid_request", None, "invalid_action")
        return adapter.prepare_action(parameters["action"], parameters["parameters"])
    if operation == "execute_action":
        if type(parameters["proposal_id"]) is not str:
            return OperationResult("invalid_request", None, "invalid_proposal")
        return adapter.execute_action(parameters["proposal_id"])


def main():
    global _output
    # Keep the private protocol descriptor; discard adapter/library prints even
    # at OS-descriptor level, so they cannot become IPC or credential logs.
    _output = os.fdopen(os.dup(1), "wb", buffering=0)
    input_pipe = os.fdopen(os.dup(0), "rb", buffering=0)
    with open(os.devnull, "wb") as discard:
        os.dup2(discard.fileno(), 1)
        os.dup2(discard.fileno(), 2)
    try:
        bootstrap = read_packet(input_pipe)
        if set(bootstrap) != {"kind", "manifest", "target", "material"} or bootstrap["kind"] != "bootstrap":
            raise ProtocolError("invalid_bootstrap")
        manifest = validate_manifest(bootstrap["manifest"])
        target = Target(**bootstrap["target"])
        if target not in manifest.allowed_targets:
            raise ProtocolError("invalid_bootstrap")
        private = bootstrap["material"]
        if private is None:
            material = None
        elif (type(private) is dict and set(private) == {"kind", "value"}
              and "credential_use" in manifest.permissions):
            material = SecretMaterial(private["kind"], private["value"])
        else:
            raise ProtocolError("invalid_bootstrap")
        module, name = manifest.entrypoint.split(":")
        adapter = getattr(importlib.import_module(module), name)(target, material)
        del private, material, bootstrap
        send({"kind": "ready"})
        subscribed = False
        while True:
            request = read_packet(input_pipe)
            if (set(request) != {"kind", "id", "operation", "parameters"}
                    or request["kind"] != "request" or type(request["id"]) is not int
                    or type(request["operation"]) is not str or type(request["parameters"]) is not dict):
                raise ProtocolError("invalid_request")
            operation, parameters = request["operation"], request["parameters"]
            start_events = False
            if operation not in manifest.permissions:
                result = OperationResult("unsupported", None, "operation_not_approved")
            elif operation == "events" and parameters == {}:
                result = OperationResult("ok", None, None)
                start_events = not subscribed
                subscribed = True
            else:
                try:
                    result = _invoke(adapter, target, operation, parameters)
                except Exception:
                    result = OperationResult("adapter_error", None, "operation_failed")
            if type(result) not in (OperationResult, ActionProposal, DeviceRecord):
                raise ProtocolError("invalid_result")
            send({"kind": "response", "id": request["id"], "value": encode_value(result)})
            if start_events:
                threading.Thread(target=_events, args=(adapter,), daemon=True).start()
    except EOFError:
        return
    except Exception:
        # Errors are deliberately not printed; even exception text may be secret.
        _fatal()


if __name__ == "__main__":
    main()
