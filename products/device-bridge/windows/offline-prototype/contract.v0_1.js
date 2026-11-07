/* Offline fixture logic. Fixture binding is NOT a cryptographic signature. */
(function (root) {
  "use strict";
  const fields = ["windows", "powershell7", "node"];
  const requestKeys = ["schemaVersion", "operationId", "requestId", "targetRef",
    "profileRef", "nonce", "fields"];
  const denialCodes = Object.freeze([
    "INVALID_REQUEST", "UNKNOWN_OPERATION", "UNKNOWN_TARGET", "UNKNOWN_FIELD",
    "REQUEST_TOO_LARGE", "INVALID_RESULT", "RESULT_TOO_LARGE", "APPROVAL_MISSING",
    "APPROVAL_EXPIRED", "APPROVAL_INVALID", "REQUEST_CHANGED", "TARGET_CHANGED",
    "APPROVAL_REPLAYED", "CANCELLED", "TIMED_OUT", "UNKNOWN_SCENARIO", "EXECUTOR_DISABLED"
  ]);
  const clone = value => JSON.parse(JSON.stringify(value));
  const record = value => value !== null && typeof value === "object" && !Array.isArray(value);
  const exactKeys = (value, keys) => record(value) &&
    Reflect.ownKeys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
  const identifier = value => typeof value === "string" && value.length >= 1 &&
    value.length <= 64 && !/[^A-Za-z0-9_-]/.test(value);
  function boundedSnapshot(input, category) {
    try {
      const serialized = JSON.stringify(input);
      if (typeof serialized !== "string") return {ok: false, code: "INVALID_" + category};
      if (new TextEncoder().encode(serialized).length > 4096) {
        return {ok: false, code: category + "_TOO_LARGE"};
      }
      return {ok: true, value: JSON.parse(serialized)};
    } catch (_) {
      return {ok: false, code: "INVALID_" + category};
    }
  }
  function validateRequest(input) {
    const snapshot = boundedSnapshot(input, "REQUEST");
    if (!snapshot.ok) return snapshot;
    const value = input;
    if (!exactKeys(value, requestKeys) || value.schemaVersion !== "fixture.v0.1" ||
        !identifier(value.requestId) || !identifier(value.nonce)) {
      return {ok: false, code: "INVALID_REQUEST"};
    }
    if (value.operationId !== "windows.runtime_inventory.v0_1") {
      return {ok: false, code: "UNKNOWN_OPERATION"};
    }
    if (value.targetRef !== "fixture-windows-01" || value.profileRef !== "fixture-profile-01") {
      return {ok: false, code: "UNKNOWN_TARGET"};
    }
    if (!Array.isArray(value.fields) || value.fields.length !== fields.length ||
        Reflect.ownKeys(value.fields).length !== fields.length + 1 ||
        !fields.every((field, index) => value.fields[index] === field)) {
      return {ok: false, code: "UNKNOWN_FIELD"};
    }
    return {ok: true, request: snapshot.value};
  }
  function validField(value) {
    if (!record(value)) return false;
    if (value.state === "available") {
      return exactKeys(value, ["state", "version"]) && typeof value.version === "string" &&
        Array.from(value.version).length <= 128;
    }
    return ["missing", "unverified"].includes(value.state) && exactKeys(value, ["state"]);
  }
  function validateResult(input) {
    const snapshot = boundedSnapshot(input, "RESULT");
    if (!snapshot.ok) return snapshot;
    const value = input;
    const completed = exactKeys(value, ["simulated", "state", "data"]) &&
      value.state === "completed" && exactKeys(value.data, fields) &&
      fields.every(field => validField(value.data[field]));
    const denied = exactKeys(value, ["simulated", "state", "code"]) &&
      value.state === "denied" && denialCodes.includes(value.code);
    if ((!completed && !denied) || value.simulated !== true) {
      return {ok: false, code: "INVALID_RESULT"};
    }
    return {ok: true, result: snapshot.value};
  }
  const deny = code => ({simulated: true, state: "denied", code});
  // A deterministic fixture comparison only; this is not a production digest.
  function nonCryptographicFixtureBinding(request) {
    return JSON.stringify(requestKeys.map(key => request[key]));
  }
  function evaluateFixture(input, scenarioId, context) {
    const fixture = root.HUB_DEVICE_BRIDGE_FIXTURES.getFixture(scenarioId);
    if (fixture.ok === false) return deny("UNKNOWN_SCENARIO");
    const validated = validateRequest(input);
    if (!validated.ok) {
      return deny(validated.code === "UNKNOWN_TARGET" ? "TARGET_CHANGED" : validated.code);
    }
    const request = validated.request;
    if (scenarioId === "changed_target") return deny("TARGET_CHANGED");
    if (scenarioId === "changed_request" ||
        nonCryptographicFixtureBinding(request) !== nonCryptographicFixtureBinding(fixture.request)) {
      return deny("REQUEST_CHANGED");
    }
    if (!record(context) || !Number.isFinite(context.nowMs) ||
        !Number.isFinite(context.startedAtMs) || context.startedAtMs < 0 ||
        context.nowMs < context.startedAtMs || typeof context.cancelled !== "boolean" ||
        !context.usedApprovalIds || typeof context.usedApprovalIds.has !== "function" ||
        typeof context.usedApprovalIds.add !== "function") return deny("APPROVAL_INVALID");
    if (context.cancelled || scenarioId === "cancelled") return deny("CANCELLED");
    if (scenarioId === "timeout" || context.nowMs - context.startedAtMs >= 10000) {
      return deny("TIMED_OUT");
    }
    if (scenarioId === "missing_approval") return deny("APPROVAL_MISSING");
    if (scenarioId === "expired" || context.nowMs >= fixture.scenario.expiresAtMs) {
      return deny("APPROVAL_EXPIRED");
    }
    if (scenarioId === "invalid_signature") return deny("APPROVAL_INVALID");
    if (scenarioId === "replayed" || context.usedApprovalIds.has(fixture.scenario.approvalId)) {
      return deny("APPROVAL_REPLAYED");
    }
    const result = validateResult({simulated: true, state: "completed", data: fixture.data});
    if (!result.ok) return deny(result.code);
    context.usedApprovalIds.add(fixture.scenario.approvalId);
    return result.result;
  }
  function requestRealExecution() {
    return {simulated: true, state: "denied", code: "EXECUTOR_DISABLED"};
  }
  root.HUB_DEVICE_BRIDGE_CONTRACT = Object.freeze({
    validateRequest, validateResult, evaluateFixture, requestRealExecution
  });
})(globalThis);
