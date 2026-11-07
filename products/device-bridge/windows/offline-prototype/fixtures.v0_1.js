/* Synthetic data only. No operating system or authorization capability. */
(function (root) {
  "use strict";
  const scenarioIds = Object.freeze([
    "approved", "missing_approval", "expired", "invalid_signature",
    "changed_request", "changed_target", "replayed", "cancelled",
    "timeout", "missing_runtime", "unverified_runtime"
  ]);
  const request = {
    schemaVersion: "fixture.v0.1",
    operationId: "windows.runtime_inventory.v0_1",
    requestId: "fixture-request-01",
    targetRef: "fixture-windows-01",
    profileRef: "fixture-profile-01",
    nonce: "fixture-nonce-01",
    fields: ["windows", "powershell7", "node"]
  };
  const data = {
    windows: {state: "available", version: "fixture-windows-10.0"},
    powershell7: {state: "available", version: "fixture-powershell-7.0"},
    node: {state: "available", version: "fixture-node-24.0"}
  };
  function getFixture(scenarioId) {
    if (!scenarioIds.includes(scenarioId)) return {ok: false, code: "UNKNOWN_SCENARIO"};
    const fixture = {
      request: request,
      scenario: {id: scenarioId, approvalId: "fixture-approval-" + scenarioId,
        issuedAtMs: 0, expiresAtMs: 60000},
      data: data
    };
    const copy = JSON.parse(JSON.stringify(fixture));
    if (scenarioId === "missing_runtime") copy.data.node = {state: "missing"};
    if (scenarioId === "unverified_runtime") copy.data.node = {state: "unverified"};
    return copy;
  }
  root.HUB_DEVICE_BRIDGE_FIXTURES = Object.freeze({scenarioIds, getFixture});
})(globalThis);
