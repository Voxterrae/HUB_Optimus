/* Text-only offline demonstration. No actual approval, collection or session. */
(function (root) {
  "use strict";
  const contract = root.HUB_DEVICE_BRIDGE_CONTRACT;
  const deny = code => ({simulated: true, state: "denied", code});
  const clone = value => JSON.parse(JSON.stringify(value));
  // Optional cards project validated fixture data; older documents keep working.
  function renderHealth(document, result, pending = false) {
    const fields = {windows: "Windows", powershell7: "PowerShell 7", node: "Node"};
    const labels = {available: "Disponible", missing: "Ausente", unverified: "Sin verificar"};
    const completed = result && result.state === "completed";
    const review = [];
    for (const [field, name] of Object.entries(fields)) {
      const entry = completed ? result.data[field] : null;
      const state = document.getElementById("fixture-health-" + field + "-state");
      const version = document.getElementById("fixture-health-" + field + "-version");
      if (state) {
        state.textContent = entry ? labels[entry.state] : pending ? "Pendiente" : "No comprobado";
        state.setAttribute("data-state", entry ? entry.state : pending ? "pending" : "unchecked");
      }
      if (version) version.textContent = entry && entry.state === "available" ? entry.version : "";
      if (entry && entry.state !== "available") review.push(name);
    }
    const summary = document.getElementById("fixture-health-summary");
    if (summary) {
      summary.textContent = completed ? (review.length ?
        "Diagnóstico de la simulación: revisa " + review.join(", ") + "." :
        "Diagnóstico de la simulación: los tres componentes están disponibles.") : pending ?
        "Comprobación de la simulación pendiente." : result ?
        "Diagnóstico no disponible: la simulación fue denegada." :
        "Sin resultados. Inicia y completa una simulación.";
    }
  }
  function createFixtureRun(request, scenarioId, context) {
    const checked = contract.validateRequest(request);
    const snapshot = checked.ok ? checked.request : null;
    const state = {...context};
    let terminal = null;
    return Object.freeze({
      cancel() {
        if (terminal === null) terminal = deny("CANCELLED");
        return clone(terminal);
      },
      complete() {
        if (terminal === null) {
          terminal = checked.ok ? contract.evaluateFixture(snapshot, scenarioId, state) :
            deny(checked.code);
        }
        return clone(terminal);
      }
    });
  }
  function renderFixtureResult(document, input) {
    const checked = contract.validateResult(input);
    const result = checked.ok ? checked.result : deny(checked.code);
    document.getElementById("fixture-result").textContent = JSON.stringify(result, null, 2);
    document.getElementById("fixture-status").textContent =
      result.state === "completed" ? "Simulación completada" : "Simulación denegada: " + result.code;
    document.getElementById("fixture-export").disabled = result.state !== "completed";
    renderHealth(document, result);
    return result;
  }
  function mountFixtureUI(document, suppliedContract, fixtures) {
    const ids = ["fixture-scenario", "fixture-run", "fixture-complete", "fixture-cancel",
      "fixture-export", "fixture-status", "fixture-result", "fixture-request"];
    const controls = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
    let pending = null;
    let shown = null;
    function clear() {
      if (pending) pending.cancel();
      pending = null;
      shown = null;
      controls["fixture-result"].textContent = "";
      controls["fixture-export"].disabled = true;
      controls["fixture-complete"].disabled = true;
      controls["fixture-cancel"].disabled = true;
      renderHealth(document, null);
    }
    function select() {
      clear();
      const fixture = fixtures.getFixture(controls["fixture-scenario"].value);
      controls["fixture-run"].disabled = fixture.ok === false;
      controls["fixture-request"].textContent = fixture.ok === false ? "" :
        JSON.stringify(fixture.request, null, 2);
      controls["fixture-status"].textContent = fixture.ok === false ?
        "Escenario desconocido" : "Preparada la simulación";
    }
    function show(result) {
      shown = renderFixtureResult(document, result);
      controls["fixture-complete"].disabled = true;
      controls["fixture-cancel"].disabled = true;
      pending = null;
    }
    controls["fixture-scenario"].addEventListener("change", select);
    controls["fixture-run"].addEventListener("click", () => {
      clear();
      const id = controls["fixture-scenario"].value;
      const fixture = fixtures.getFixture(id);
      if (fixture.ok === false) {
        show(deny("UNKNOWN_SCENARIO"));
        return;
      }
      pending = createFixtureRun(fixture.request, id,
        {nowMs: 1000, startedAtMs: 1000, cancelled: false, usedApprovalIds: new Set()});
      controls["fixture-status"].textContent = "Pendiente: completa o cancela la simulación";
      renderHealth(document, null, true);
      controls["fixture-complete"].disabled = false;
      controls["fixture-cancel"].disabled = false;
    });
    controls["fixture-complete"].addEventListener("click", () => {
      if (pending) show(pending.complete());
    });
    controls["fixture-cancel"].addEventListener("click", () => {
      if (pending) show(pending.cancel());
    });
    controls["fixture-export"].addEventListener("click", () => {
      const checked = suppliedContract.validateResult(shown);
      if (!checked.ok || checked.result.state !== "completed") return;
      // Export the exact displayed serialization, bounded including whitespace.
      const text = controls["fixture-result"].textContent;
      try {
        const parsed = JSON.parse(text);
        if (text !== JSON.stringify(checked.result, null, 2) ||
            new TextEncoder().encode(text).length > 4096 ||
            !suppliedContract.validateResult(parsed).ok) return;
        const blob = new root.Blob([text], {type: "application/json;charset=utf-8"});
        const url = root.URL.createObjectURL(blob);
        const link = document.createElement("a");
        try {
          link.href = url;
          link.download = "hub-optimus-device-bridge-fixture.json";
          document.body.appendChild(link);
          link.click();
        } finally {
          link.remove();
          root.URL.revokeObjectURL(url);
        }
      } catch (_) {
        controls["fixture-status"].textContent = "Exportación no disponible";
      }
    });
    select();
    return Object.freeze({});
  }
  root.HUB_DEVICE_BRIDGE_UI = Object.freeze({
    mountFixtureUI, renderFixtureResult, createFixtureRun
  });
  if (root.document) mountFixtureUI(root.document, contract, root.HUB_DEVICE_BRIDGE_FIXTURES);
})(globalThis);
