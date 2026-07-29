"""
hub_optimus_control.py
-----------------------

Status: local educational prototype.

This module demonstrates how an in-memory gateway can apply a simple
actor-to-tool allowlist and retain an inspection log. It is not imported by
the supported scenario runtime, Semantic Engine, Operator, or deployment
scripts. It provides no authentication, production authorization, durable
audit, distributed identity, policy service, or telemetry integration.

Key components:
  * ``PolicyEngine`` – Evaluates whether a given actor is allowed to
    invoke a specific tool with the provided arguments. Policies are
    expressed as a mapping of actors to allowed tool names.
  * ``ControlPlane`` – Orchestrates tool invocations. Before executing a
    tool, it consults the policy engine and records every attempted call
    in an internal log. Successful calls return a result produced by a
    small set of stubbed tool implementations. Unauthorized calls raise
    ``PermissionError``, while calls to unknown tools raise
    ``ValueError``.

The names Open Policy Agent (OPA), OpenTelemetry, SPIFFE, and SPIRE describe
capabilities that this module explicitly does not implement. The actor string
is only an in-memory lookup key, not an authenticated identity. The log is
process-local inspection data, not a security or compliance audit record.
Accepted call arguments are restricted to plain, string-keyed built-in
containers and scalar values so snapshots never invoke user-defined copy hooks.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, MutableMapping


SNAPSHOT_VALUE_ERROR = (
    "Arguments must contain only snapshot-safe built-in values: "
    "None, bool, int, float, str, list, tuple, and string-keyed dict."
)


def _snapshot_value(value: Any) -> Any:
    """Copy the prototype's restricted value domain without user hooks."""
    value_type = type(value)
    if value is None or value_type in {bool, int, float, str}:
        return value
    if value_type is list:
        return [_snapshot_value(item) for item in value]
    if value_type is tuple:
        return tuple(_snapshot_value(item) for item in value)
    if value_type is dict:
        snapshot: Dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(SNAPSHOT_VALUE_ERROR)
            snapshot[key] = _snapshot_value(item)
        return snapshot
    raise TypeError(SNAPSHOT_VALUE_ERROR)


def _snapshot_arguments(args: Dict[str, Any]) -> Dict[str, Any]:
    """Copy one plain dictionary without invoking mapping hooks."""
    if type(args) is not dict:
        raise TypeError(SNAPSHOT_VALUE_ERROR)
    snapshot = _snapshot_value(args)
    return snapshot


class PolicyEngine:
    """A trivial in‑memory policy engine.

    Policies are provided as a mapping from actor identifiers to a list
    of tool names that the actor is permitted to invoke. The
    ``evaluate`` method checks whether the requested tool is allowed
    under the current policies.

    Attributes
    ----------
    policies : Mapping[str, List[str]]
        A mapping from actor identifiers to allowed tool names.
    """

    def __init__(self, policies: Mapping[str, List[str]]) -> None:
        # Store policies internally as a dict of sets for efficient lookup
        self._policies: Dict[str, set[str]] = {
            actor: set(tools) for actor, tools in policies.items()
        }

    def evaluate(self, actor: str, tool_name: str, args: Mapping[str, Any]) -> Dict[str, bool]:
        """Determine whether an actor may invoke a tool.

        Parameters
        ----------
        actor : str
            Identifier of the requester (e.g., user or service name).
        tool_name : str
            Name of the tool the actor wishes to invoke.
        args : Mapping[str, Any]
            Arguments provided for the tool call. The policy engine in
            this draft implementation does not inspect arguments but
            accepts them for completeness.

        Returns
        -------
        Dict[str, bool]
            A dictionary containing a single key ``"allowed"`` set to
            True if the call is permitted and False otherwise.
        """
        allowed_tools = self._policies.get(actor, set())
        return {"allowed": tool_name in allowed_tools}


class ControlPlane:
    """A simple control plane for mediating tool invocations.

    The control plane couples a ``PolicyEngine`` with rudimentary tool
    implementations. Each time ``process_tool_call`` is invoked, the
    control plane:

      1. Generates a unique identifier and timestamp for the call.
      2. Evaluates the call against the policy engine.
      3. Records the attempted call in an internal log.
      4. If the call is authorized, executes the corresponding tool
         implementation.
      5. Returns the result of the tool or raises an exception if
         unauthorized or unknown.

    All completed and attempted calls (including denied ones) are recorded in
    ``self._log`` for inspection. Records follow process-local append order;
    this prototype makes no concurrency or durable-ordering guarantee.
    """

    def __init__(self, policies: Mapping[str, List[str]]) -> None:
        self.policy_engine = PolicyEngine(policies)
        # Internal log of call metadata and results. Each entry is a dict.
        self._log: List[MutableMapping[str, Any]] = []

    def process_tool_call(self, actor: str, tool_name: str, args: Dict[str, Any]) -> Any:
        """Handle a tool invocation request.

        Parameters
        ----------
        actor : str
            The identity requesting execution of the tool. No special
            parsing is applied; identities should be consistent with the
            policy definitions.
        tool_name : str
            The canonical name of the tool to invoke (e.g. ``"sum"``).
        args : Dict[str, Any]
            Arguments for the tool call. Snapshot-safe arguments use plain
            string-keyed dictionaries containing only ``None``, booleans,
            numbers, strings, lists, tuples, and dictionaries. The structure
            otherwise depends on individual tool semantics (see
            ``execute_tool`` for details).

        Returns
        -------
        Any
            The return value of the tool call if allowed and the tool
            exists. The type depends on the tool implementation. If the
            call is forbidden, a ``PermissionError`` is raised. If the
            tool name is unrecognized, a ``ValueError`` is raised. A
            ``TypeError`` is raised for non-plain actor/tool identifiers.
            Arguments outside the snapshot-safe built-in value domain raise
            ``TypeError`` only for an otherwise allowed call; denied calls
            retain ``PermissionError`` precedence.
        """
        # Unique identifier and timestamp for this call
        call_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        if type(actor) is not str or type(tool_name) is not str:
            self._log.append(
                {
                    "call_id": call_id,
                    "timestamp": timestamp,
                    "actor": actor if type(actor) is str else "<invalid>",
                    "tool_name": (
                        tool_name if type(tool_name) is str else "<invalid>"
                    ),
                    "args": {},
                    "args_snapshot_status": "not-attempted",
                    "allowed": False,
                    "status": "error",
                    "error": "Actor and tool_name must be plain strings.",
                }
            )
            raise TypeError("Actor and tool_name must be plain strings.")

        # Check the policy
        decision = self.policy_engine.evaluate(actor, tool_name, args)
        allowed = decision["allowed"]

        # Build the base entry before copying arguments so an unsupported value
        # cannot suppress the attempt record.
        entry: MutableMapping[str, Any] = {
            "call_id": call_id,
            "timestamp": timestamp,
            "actor": actor,
            "tool_name": tool_name,
            "allowed": allowed,
        }

        try:
            execution_args = _snapshot_arguments(args)
            entry["args"] = _snapshot_value(execution_args)
            entry["args_snapshot_status"] = "complete"
        except Exception as error:
            entry["args"] = {}
            entry["args_snapshot_status"] = "rejected"
            if allowed:
                entry["status"] = "error"
                entry["error"] = SNAPSHOT_VALUE_ERROR
                self._log.append(entry)
                raise TypeError(SNAPSHOT_VALUE_ERROR) from error

            entry["status"] = "denied"
            self._log.append(entry)
            raise PermissionError(
                f"Actor '{actor}' is not permitted to invoke tool '{tool_name}'"
            ) from None

        # Perform action based on policy
        if allowed:
            # Attempt to execute the tool.  Use try/except/else so we can
            # append to the log in both success and failure cases.
            try:
                result = self.execute_tool(tool_name, execution_args)
                entry["result"] = _snapshot_value(result)
                entry["status"] = "success"
            except Exception as e:
                # Capture any error raised by the tool and propagate it
                entry["status"] = "error"
                entry["error"] = str(e)
                self._log.append(entry)
                # Re‑raise the exception to the caller
                raise
            else:
                # Only appended in successful execution
                self._log.append(entry)
                return result
        else:
            # Denied call; log and raise a permission error
            entry["status"] = "denied"
            self._log.append(entry)
            raise PermissionError(f"Actor '{actor}' is not permitted to invoke tool '{tool_name}'")

    def execute_tool(self, tool_name: str, args: Mapping[str, Any]) -> Any:
        """Execute a stubbed tool implementation.

        Supported tools:
          * ``"sum"`` – expects integer or float arguments ``"a"`` and
            ``"b"`` and returns their sum. Missing arguments default to
            zero.
          * ``"echo"`` – returns the ``args`` mapping itself as a
            dictionary.

        Parameters
        ----------
        tool_name : str
            Name of the tool to invoke.
        args : Mapping[str, Any]
            Arguments for the tool.

        Returns
        -------
        Any
            The result of the tool call.

        Raises
        ------
        ValueError
            If the tool is not recognized.
        """
        if tool_name == "sum":
            # Note: we deliberately coerce non‑numeric values to float
            a = float(args.get("a", 0))
            b = float(args.get("b", 0))
            return a + b
        elif tool_name == "echo":
            return dict(args)
        else:
            raise ValueError(f"Unknown tool '{tool_name}'")

    def get_log(self) -> List[Mapping[str, Any]]:
        """Return a copy of the internal log.

        Returns
        -------
        List[Mapping[str, Any]]
            A snapshot of each call attempt in process-local append order.
            Mutating the returned list or any nested value cannot alter the
            internal log. No cross-thread chronological ordering is promised.
        """
        return _snapshot_value(self._log)
