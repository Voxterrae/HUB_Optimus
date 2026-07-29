from __future__ import annotations

import threading
from collections.abc import Mapping
from datetime import datetime, timedelta

import pytest

from hub_optimus.hub_optimus_control import ControlPlane


class SelfCopyingMutable:
    def __init__(self) -> None:
        self.items = [1]

    def __deepcopy__(self, _memo):
        return self


class MutableStr(str):
    def __new__(cls, value):
        instance = super().__new__(cls, value)
        instance.items = [1]
        return instance


class HookedMapping(Mapping):
    def __init__(self) -> None:
        self.iterations = 0

    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        self.iterations += 1
        raise SystemExit("mapping hook must not run")

    def __len__(self):
        return 0


class MutatingControlPlane(ControlPlane):
    def execute_tool(self, tool_name, args):
        args["payload"]["items"].append(2)
        return args


def test_echo_log_is_isolated_from_inputs_results_and_returned_snapshots() -> None:
    plane = ControlPlane({"analyst": ["echo"]})
    args = {"payload": {"items": [1]}}

    result = plane.process_tool_call("analyst", "echo", args)
    args["payload"]["items"].append(2)
    result["payload"]["items"].append(3)

    first_snapshot = plane.get_log()
    assert first_snapshot[0]["args"] == {"payload": {"items": [1]}}
    assert first_snapshot[0]["result"] == {"payload": {"items": [1]}}

    first_snapshot[0]["args"]["payload"]["items"].append(4)
    first_snapshot[0]["result"]["payload"]["items"].append(5)
    second_snapshot = plane.get_log()
    assert second_snapshot[0]["args"] == {"payload": {"items": [1]}}
    assert second_snapshot[0]["result"] == {"payload": {"items": [1]}}


def test_log_timestamps_are_timezone_aware_utc() -> None:
    plane = ControlPlane({"analyst": ["sum"]})

    assert plane.process_tool_call("analyst", "sum", {"a": 2, "b": 3}) == 5

    timestamp = datetime.fromisoformat(plane.get_log()[0]["timestamp"])
    assert timestamp.utcoffset() == timedelta(0)


def test_denied_and_unknown_calls_remain_visible_without_becoming_authority() -> None:
    plane = ControlPlane({"analyst": ["not-a-tool"]})

    with pytest.raises(PermissionError, match="not permitted"):
        plane.process_tool_call("guest", "echo", {"text": "hello"})
    with pytest.raises(ValueError, match="Unknown tool"):
        plane.process_tool_call("analyst", "not-a-tool", {})

    log = plane.get_log()
    assert [entry["status"] for entry in log] == ["denied", "error"]
    assert [entry["allowed"] for entry in log] == [False, True]


def test_object_copy_hooks_cannot_create_a_shared_log_reference() -> None:
    plane = ControlPlane({"analyst": ["echo"]})
    adversarial = SelfCopyingMutable()

    with pytest.raises(TypeError, match="snapshot-safe built-in values"):
        plane.process_tool_call("analyst", "echo", {"payload": adversarial})

    adversarial.items.append(2)
    log = plane.get_log()
    assert log[0]["args"] == {}
    assert log[0]["args_snapshot_status"] == "rejected"
    assert log[0]["status"] == "error"
    assert "result" not in log[0]


def test_uncopyable_denied_arguments_cannot_suppress_the_denial_record() -> None:
    plane = ControlPlane({})

    with pytest.raises(PermissionError, match="not permitted"):
        plane.process_tool_call("guest", "echo", {"lock": threading.Lock()})

    log = plane.get_log()
    assert log[0]["args"] == {}
    assert log[0]["args_snapshot_status"] == "rejected"
    assert log[0]["status"] == "denied"
    assert log[0]["allowed"] is False


def test_mutable_string_subclasses_are_not_retained_as_actor_identifiers() -> None:
    plane = ControlPlane({})
    actor = MutableStr("guest")

    with pytest.raises(TypeError, match="plain strings"):
        plane.process_tool_call(actor, "echo", {})

    actor.items.append(2)
    log = plane.get_log()
    assert log[0]["actor"] == "<invalid>"
    assert log[0]["tool_name"] == "echo"
    assert log[0]["args_snapshot_status"] == "not-attempted"
    assert log[0]["status"] == "error"


def test_mapping_hooks_cannot_suppress_a_denied_attempt_record() -> None:
    plane = ControlPlane({})
    args = HookedMapping()

    with pytest.raises(PermissionError, match="not permitted"):
        plane.process_tool_call("guest", "echo", args)

    assert args.iterations == 0
    log = plane.get_log()
    assert log[0]["args_snapshot_status"] == "rejected"
    assert log[0]["status"] == "denied"


def test_execution_uses_an_isolated_validated_argument_snapshot() -> None:
    plane = MutatingControlPlane({"analyst": ["mutate"]})
    original = {"payload": {"items": [1]}}

    result = plane.process_tool_call("analyst", "mutate", original)

    assert original == {"payload": {"items": [1]}}
    assert result == {"payload": {"items": [1, 2]}}
    log = plane.get_log()
    assert log[0]["args"] == {"payload": {"items": [1]}}
    assert log[0]["result"] == {"payload": {"items": [1, 2]}}
