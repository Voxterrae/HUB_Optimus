"""
hub_optimus_control.py
-----------------------

This module provides a minimal, self‑contained draft implementation of a
"control plane" inspired by the HUB_Optimus architecture discussed in the
previous conversation. The goal of this implementation is to demonstrate
how a central gateway might mediate access to external tools while
enforcing simple policies and maintaining an audit trail. It does not
attempt to integrate with external systems such as OpenTelemetry, SPIFFE,
or Open Policy Agent; instead, it uses in‑memory data structures and
Python exceptions to illustrate the core ideas without external
dependencies.

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

This code is intended for educational purposes and serves as a starting
point for more sophisticated prototypes. In a production system you
would likely replace the ``PolicyEngine`` with a call to OPA, replace
the internal log with structured telemetry (for example, via OpenTelemetry),
and secure identities using SPIFFE/SPIRE. Nevertheless, this simple
implementation shows how the core control loop might be structured.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Mapping, MutableMapping, Optional


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

    All completed and attempted calls (including denied ones) are
    recorded in ``self._log`` for inspection.
    """

    def __init__(self, policies: Mapping[str, List[str]]) -> None:
        self.policy_engine = PolicyEngine(policies)
        # Internal log of call metadata and results. Each entry is a dict.
        self._log: List[MutableMapping[str, Any]] = []

    def process_tool_call(self, actor: str, tool_name: str, args: Mapping[str, Any]) -> Any:
        """Handle a tool invocation request.

        Parameters
        ----------
        actor : str
            The identity requesting execution of the tool. No special
            parsing is applied; identities should be consistent with the
            policy definitions.
        tool_name : str
            The canonical name of the tool to invoke (e.g. ``"sum"``).
        args : Mapping[str, Any]
            Arguments for the tool call. The structure depends on
            individual tool semantics (see ``execute_tool`` for details).

        Returns
        -------
        Any
            The return value of the tool call if allowed and the tool
            exists. The type depends on the tool implementation. If the
            call is forbidden, a ``PermissionError`` is raised. If the
            tool name is unrecognized, a ``ValueError`` is raised.
        """
        # Unique identifier and timestamp for this call
        call_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        # Check the policy
        decision = self.policy_engine.evaluate(actor, tool_name, args)
        allowed = decision["allowed"]

        # Build log entry; result will be inserted after execution if allowed
        entry: MutableMapping[str, Any] = {
            "call_id": call_id,
            "timestamp": timestamp,
            "actor": actor,
            "tool_name": tool_name,
            "args": dict(args),
            "allowed": allowed,
        }

        # Perform action based on policy
        if allowed:
            # Attempt to execute the tool.  Use try/except/else so we can
            # append to the log in both success and failure cases.
            try:
                result = self.execute_tool(tool_name, args)
                entry["result"] = result
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
            A list of dictionaries representing each call attempt in
            chronological order. The list is a shallow copy to prevent
            external modification of internal state.
        """
        return list(self._log)
