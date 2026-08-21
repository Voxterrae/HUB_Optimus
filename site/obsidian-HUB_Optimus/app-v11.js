(() => {
  "use strict";

  const ADDON_MODEL_URL = "./system.learning.json";
  const BASE_VIEW_BOX = Object.freeze({ x: 0, y: 0, width: 940, height: 600 });
  const MIN_VIEW_WIDTH = 360;
  const MAX_VIEW_WIDTH = 1500;
  const POLL_LIMIT = 240;
  const hub = window.HubIntelligence;

  if (!hub?.state || !hub?.elements?.graph) return;

  const addonState = {
    initialized: false,
    pollCount: 0,
    scope: "direct",
    query: "",
    viewport: { ...BASE_VIEW_BOX },
    dragging: false,
    pointerId: null,
    dragStart: null,
    learning: null,
    observer: null
  };

  function element(tag, className = "", text = undefined) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function allNodes() {
    const model = hub.state.model;
    if (!model) return [];
    return [
      ...(model.components || []),
      ...(model.external_systems || []),
      ...(model.dependencies || [])
    ];
  }

  function nodesById() {
    return new Map(allNodes().map((node) => [node.id, node]));
  }

  function nodeSearchText(node) {
    return [
      node.id,
      node.name,
      node.purpose,
      node.layer,
      node.category,
      node.kind,
      ...(Array.isArray(node.source) ? node.source : [])
    ].filter(Boolean).join(" ").toLowerCase();
  }

  function findModeForNode(nodeId) {
    const views = hub.state.model?.views || {};
    const match = Object.entries(views).find(
      ([, view]) => Array.isArray(view.nodes) && view.nodes.includes(nodeId)
    );
    return match?.[0] || null;
  }

  function bestSearchMatch(query) {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return null;
    const ranked = allNodes()
      .map((node) => {
        const id = String(node.id || "").toLowerCase();
        const name = String(node.name || "").toLowerCase();
        const haystack = nodeSearchText(node);
        let score = Number.POSITIVE_INFINITY;
        if (id === normalized || name === normalized) score = 0;
        else if (name.startsWith(normalized) || id.startsWith(normalized)) score = 1;
        else if (haystack.includes(normalized)) score = 2;
        return { node, score };
      })
      .filter((item) => Number.isFinite(item.score))
      .sort((left, right) => left.score - right.score
        || left.node.name.localeCompare(right.node.name));
    return ranked[0]?.node || null;
  }

  function selectSearchMatch() {
    const input = document.getElementById("graph-node-search");
    const status = document.getElementById("graph-search-status");
    const match = bestSearchMatch(input?.value || "");
    if (!match) {
      if (status) status.textContent = "Sin coincidencia en el modelo actual.";
      return;
    }
    const targetMode = findModeForNode(match.id);
    if (!targetMode) {
      if (status) status.textContent = `${match.name} no pertenece a una vista publicada.`;
      return;
    }
    hub.state.mode = targetMode;
    document.querySelectorAll("[data-mode]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.mode === targetMode));
    });
    hub.selectNode(match.id);
    if (status) status.textContent = `${match.name} seleccionado en ${targetMode.toUpperCase()}.`;
    queueMicrotask(applyGraphFocus);
  }

  function adjacency(direction) {
    const map = new Map();
    for (const node of allNodes()) map.set(node.id, new Set());
    for (const relation of hub.state.model?.relations || []) {
      const from = direction === "reverse" ? relation.to : relation.from;
      const to = direction === "reverse" ? relation.from : relation.to;
      if (!map.has(from)) map.set(from, new Set());
      map.get(from).add(to);
    }
    return map;
  }

  function reachable(startId, direction) {
    const graph = adjacency(direction);
    const visited = new Set([startId]);
    const queue = [startId];
    while (queue.length) {
      const current = queue.shift();
      for (const next of graph.get(current) || []) {
        if (visited.has(next)) continue;
        visited.add(next);
        queue.push(next);
      }
    }
    return visited;
  }

  function directNeighbours(nodeId) {
    const neighbours = new Set([nodeId]);
    for (const relation of hub.state.model?.relations || []) {
      if (relation.from === nodeId) neighbours.add(relation.to);
      if (relation.to === nodeId) neighbours.add(relation.from);
    }
    return neighbours;
  }

  function focusSet() {
    const selected = hub.state.selectedNodeId;
    if (!selected || addonState.scope === "all") return null;
    if (addonState.scope === "direct") return directNeighbours(selected);
    if (addonState.scope === "upstream") return reachable(selected, "reverse");
    if (addonState.scope === "downstream") return reachable(selected, "forward");
    return null;
  }

  function relationIsFocused(relation, focusedNodes) {
    if (!focusedNodes) return true;
    if (addonState.scope === "direct") {
      return relation.from === hub.state.selectedNodeId
        || relation.to === hub.state.selectedNodeId;
    }
    return focusedNodes.has(relation.from) && focusedNodes.has(relation.to);
  }

  function relationDirectionClass(relation) {
    const selected = hub.state.selectedNodeId;
    if (!selected) return "";
    if (relation.to === selected) return "v11-upstream";
    if (relation.from === selected) return "v11-downstream";
    return "";
  }

  function applyGraphFocus() {
    if (!addonState.initialized || !hub.state.model) return;
    const selected = hub.state.selectedNodeId;
    const focusedNodes = focusSet();
    const modelNodes = nodesById();
    const graph = hub.elements.graph;

    graph.querySelectorAll(".graph-node[data-node-id]").forEach((nodeElement) => {
      const nodeId = nodeElement.getAttribute("data-node-id");
      const isSelected = nodeId === selected;
      const isFocused = !focusedNodes || focusedNodes.has(nodeId);
      nodeElement.classList.toggle("v11-selected", isSelected);
      nodeElement.classList.toggle("v11-related", isFocused && !isSelected);
      nodeElement.classList.toggle("v11-dimmed", !isFocused);
    });

    const focusedRelations = [];
    for (const relation of hub.state.model.relations || []) {
      const edge = document.getElementById(`edge-${relation.id}`);
      if (!edge) continue;
      const isFocused = relationIsFocused(relation, focusedNodes);
      edge.classList.toggle("v11-edge-focus", isFocused);
      edge.classList.toggle("v11-edge-dimmed", !isFocused);
      edge.classList.remove("v11-upstream", "v11-downstream");
      const directionClass = relationDirectionClass(relation);
      if (isFocused && directionClass) edge.classList.add(directionClass);
      edge.dataset.relationId = relation.id;
      edge.dataset.relationType = relation.type;
      edge.dataset.relationConfidence = relation.confidence;
      if (isFocused) focusedRelations.push(relation);
    }

    const summary = document.getElementById("graph-focus-summary");
    const selectedNode = modelNodes.get(selected);
    if (summary) {
      const nodeCount = focusedNodes ? focusedNodes.size : allNodes().length;
      summary.textContent = selectedNode
        ? `${selectedNode.name} · ${addonState.scope} · ${nodeCount} nodos · ${focusedRelations.length} relaciones visibles`
        : "Selecciona un nodo para analizar su impacto.";
    }

    renderRelationInspector(focusedRelations, modelNodes);
  }

  function renderRelationInspector(relations, modelNodes) {
    const inspector = document.getElementById("graph-relation-inspector");
    if (!inspector) return;
    const fragment = document.createDocumentFragment();
    const heading = element("strong", "", "RELATION EVIDENCE");
    fragment.append(heading);
    if (!relations.length) {
      fragment.append(element("span", "", "Sin relaciones en el foco actual."));
    } else {
      relations.slice(0, 6).forEach((relation) => {
        const item = element("span", "graph-relation-chip");
        const from = modelNodes.get(relation.from)?.name || relation.from;
        const to = modelNodes.get(relation.to)?.name || relation.to;
        item.textContent = `${from} → ${to} · ${relation.label} · ${relation.confidence}`;
        item.title = `${relation.type} · ${relation.status}`;
        fragment.append(item);
      });
      if (relations.length > 6) {
        fragment.append(element("span", "", `+${relations.length - 6} relaciones`));
      }
    }
    inspector.replaceChildren(fragment);
  }

  function setViewBox(viewport) {
    const graph = hub.elements.graph;
    addonState.viewport = viewport;
    graph.setAttribute(
      "viewBox",
      `${viewport.x} ${viewport.y} ${viewport.width} ${viewport.height}`
    );
    const zoomStatus = document.getElementById("graph-zoom-status");
    if (zoomStatus) {
      const scale = Math.round((BASE_VIEW_BOX.width / viewport.width) * 100);
      zoomStatus.textContent = `${scale}%`;
    }
  }

  function resetViewBox() {
    setViewBox({ ...BASE_VIEW_BOX });
  }

  function zoomGraph(factor, anchor = null) {
    const current = addonState.viewport;
    const nextWidth = Math.min(
      MAX_VIEW_WIDTH,
      Math.max(MIN_VIEW_WIDTH, current.width * factor)
    );
    const ratio = nextWidth / current.width;
    const nextHeight = current.height * ratio;
    const anchorX = anchor?.x ?? current.x + current.width / 2;
    const anchorY = anchor?.y ?? current.y + current.height / 2;
    setViewBox({
      x: anchorX - ((anchorX - current.x) * ratio),
      y: anchorY - ((anchorY - current.y) * ratio),
      width: nextWidth,
      height: nextHeight
    });
  }

  function svgPointFromEvent(event) {
    const graph = hub.elements.graph;
    const rect = graph.getBoundingClientRect();
    const viewport = addonState.viewport;
    return {
      x: viewport.x + ((event.clientX - rect.left) / rect.width) * viewport.width,
      y: viewport.y + ((event.clientY - rect.top) / rect.height) * viewport.height
    };
  }

  function bindViewportControls() {
    const graph = hub.elements.graph;
    graph.setAttribute("tabindex", "0");
    graph.setAttribute(
      "aria-label",
      "Grafo interactivo. Usa los controles de zoom, arrastra el fondo para mover y selecciona nodos para explorar relaciones."
    );

    document.getElementById("graph-zoom-in")?.addEventListener("click", () => zoomGraph(0.82));
    document.getElementById("graph-zoom-out")?.addEventListener("click", () => zoomGraph(1.22));
    document.getElementById("graph-zoom-fit")?.addEventListener("click", resetViewBox);

    graph.addEventListener("wheel", (event) => {
      event.preventDefault();
      zoomGraph(event.deltaY < 0 ? 0.88 : 1.14, svgPointFromEvent(event));
    }, { passive: false });

    graph.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || event.target.closest?.(".graph-node")) return;
      addonState.dragging = true;
      addonState.pointerId = event.pointerId;
      addonState.dragStart = {
        clientX: event.clientX,
        clientY: event.clientY,
        viewport: { ...addonState.viewport }
      };
      graph.classList.add("v11-panning");
      graph.setPointerCapture?.(event.pointerId);
    });

    graph.addEventListener("pointermove", (event) => {
      if (!addonState.dragging || event.pointerId !== addonState.pointerId) return;
      const rect = graph.getBoundingClientRect();
      const start = addonState.dragStart;
      const dx = ((event.clientX - start.clientX) / rect.width) * start.viewport.width;
      const dy = ((event.clientY - start.clientY) / rect.height) * start.viewport.height;
      setViewBox({
        ...start.viewport,
        x: start.viewport.x - dx,
        y: start.viewport.y - dy
      });
    });

    const finishPan = (event) => {
      if (!addonState.dragging || event.pointerId !== addonState.pointerId) return;
      addonState.dragging = false;
      addonState.pointerId = null;
      addonState.dragStart = null;
      graph.classList.remove("v11-panning");
      graph.releasePointerCapture?.(event.pointerId);
    };
    graph.addEventListener("pointerup", finishPan);
    graph.addEventListener("pointercancel", finishPan);

    graph.addEventListener("keydown", (event) => {
      if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        zoomGraph(0.82);
      } else if (event.key === "-") {
        event.preventDefault();
        zoomGraph(1.22);
      } else if (event.key === "0") {
        event.preventDefault();
        resetViewBox();
      }
    });
  }

  function injectGraphToolbar() {
    if (document.getElementById("graph-intelligence-toolbar")) return;
    const toolbar = element("div", "graph-intelligence-toolbar");
    toolbar.id = "graph-intelligence-toolbar";
    toolbar.setAttribute("aria-label", "Controles de inteligencia del grafo");

    const searchGroup = element("div", "graph-control-group graph-search-group");
    const searchLabel = element("label", "", "Find node");
    searchLabel.htmlFor = "graph-node-search";
    const searchInput = element("input");
    searchInput.id = "graph-node-search";
    searchInput.type = "search";
    searchInput.placeholder = "operator, governance, tests…";
    searchInput.autocomplete = "off";
    searchInput.setAttribute("data-v11-search", "true");
    const searchButton = element("button", "", "SELECT");
    searchButton.type = "button";
    searchButton.addEventListener("click", selectSearchMatch);
    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        selectSearchMatch();
      }
    });
    searchGroup.append(searchLabel, searchInput, searchButton);

    const scopeGroup = element("div", "graph-control-group");
    const scopeLabel = element("label", "", "Impact");
    scopeLabel.htmlFor = "graph-impact-scope";
    const scope = element("select");
    scope.id = "graph-impact-scope";
    scope.setAttribute("data-v11-scope", "true");
    [
      ["all", "All context"],
      ["direct", "Direct neighbours"],
      ["upstream", "Upstream"],
      ["downstream", "Downstream"]
    ].forEach(([value, label]) => {
      const option = element("option", "", label);
      option.value = value;
      option.selected = value === addonState.scope;
      scope.append(option);
    });
    scope.addEventListener("change", () => {
      addonState.scope = scope.value;
      applyGraphFocus();
    });
    scopeGroup.append(scopeLabel, scope);

    const zoomGroup = element("div", "graph-control-group graph-zoom-group");
    const zoomOut = element("button", "", "−");
    zoomOut.id = "graph-zoom-out";
    zoomOut.type = "button";
    zoomOut.setAttribute("aria-label", "Alejar grafo");
    const zoomStatus = element("output", "graph-zoom-status", "100%");
    zoomStatus.id = "graph-zoom-status";
    const zoomIn = element("button", "", "+");
    zoomIn.id = "graph-zoom-in";
    zoomIn.type = "button";
    zoomIn.setAttribute("aria-label", "Acercar grafo");
    const fit = element("button", "", "FIT");
    fit.id = "graph-zoom-fit";
    fit.type = "button";
    zoomGroup.append(zoomOut, zoomStatus, zoomIn, fit);

    toolbar.append(searchGroup, scopeGroup, zoomGroup);

    const modeToolbar = document.querySelector(".mode-toolbar");
    modeToolbar?.insertAdjacentElement("afterend", toolbar);

    const status = element("div", "graph-focus-status");
    const summary = element("p", "", "Selecciona un nodo para analizar su impacto.");
    summary.id = "graph-focus-summary";
    summary.setAttribute("aria-live", "polite");
    const searchStatus = element("span", "graph-search-status");
    searchStatus.id = "graph-search-status";
    searchStatus.setAttribute("aria-live", "polite");
    const inspector = element("div", "graph-relation-inspector");
    inspector.id = "graph-relation-inspector";
    status.append(summary, searchStatus, inspector);
    toolbar.insertAdjacentElement("afterend", status);
  }

  function renderLearningPanel(learning) {
    if (!learning || document.getElementById("whole-system-learning")) return;
    const section = element("section", "section section-muted intelligence-learning");
    section.id = "whole-system-learning";
    section.setAttribute("aria-labelledby", "learning-title");

    const heading = element("div", "section-heading");
    const headingCopy = element("div");
    headingCopy.append(
      element("p", "eyebrow", "V1.1 · WHOLE-SYSTEM LEARNING"),
      element("h2", "", "Aprender el sistema sin perder la procedencia.")
    );
    headingCopy.querySelector("h2").id = "learning-title";
    heading.append(
      headingCopy,
      element("p", "", learning.release?.boundary || "Learning remains evidence-bound and reviewable.")
    );

    const metrics = element("div", "learning-metric-grid");
    const snapshot = learning.coverage?.model_snapshot || {};
    [
      ["Components", snapshot.components],
      ["Interfaces", snapshot.interfaces],
      ["Entities", snapshot.entities],
      ["Relations", snapshot.relations],
      ["Risks", snapshot.risks]
    ].forEach(([label, value]) => {
      const card = element("article", "learning-metric");
      card.append(element("strong", "", String(value ?? "—")), element("span", "", label));
      metrics.append(card);
    });

    const capabilityGrid = element("div", "learning-capability-grid");
    for (const capability of learning.capabilities || []) {
      const card = element("article", "learning-capability");
      card.append(
        element("span", `badge badge-${capability.status}`, capability.status),
        element("h3", "", capability.name),
        element("p", "", capability.purpose),
        element("small", "", `${capability.confidence} · ${capability.evidence}`)
      );
      capabilityGrid.append(card);
    }

    const boundary = element("div", "learning-boundary");
    boundary.append(
      element("strong", "", "LEARNING CONTRACT"),
      element("p", "", learning.evidence_contract?.summary || "No claim becomes system knowledge without evidence and review."),
      element("code", "", (learning.evidence_contract?.confidence_vocabulary || []).join(" · "))
    );

    section.append(heading, metrics, capabilityGrid, boundary);
    document.getElementById("architecture")?.insertAdjacentElement("afterend", section);
  }

  async function loadLearningModel() {
    try {
      const response = await fetch(ADDON_MODEL_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`Learning model request failed: ${response.status}`);
      const learning = await response.json();
      if (learning.fragment_version !== "hub-optimus-project-intelligence.learning.v1.1") {
        throw new Error("Unexpected learning model version");
      }
      addonState.learning = learning;
      renderLearningPanel(learning);
    } catch (error) {
      console.error("[project-intelligence-v1.1]", error);
    }
  }

  function observeGraphRenders() {
    const graph = hub.elements.graph;
    addonState.observer = new MutationObserver(() => queueMicrotask(applyGraphFocus));
    addonState.observer.observe(graph, { childList: true, subtree: true });
    document.querySelector(".mode-toolbar")?.addEventListener("click", () => {
      resetViewBox();
      queueMicrotask(applyGraphFocus);
    });
    hub.elements.mobileGraphList?.addEventListener("click", () => queueMicrotask(applyGraphFocus));
    graph.addEventListener("click", () => queueMicrotask(applyGraphFocus));
  }

  function initialize() {
    if (addonState.initialized || !hub.state.model) return;
    addonState.initialized = true;
    document.documentElement.classList.add("project-intelligence-v11");
    injectGraphToolbar();
    bindViewportControls();
    observeGraphRenders();
    resetViewBox();
    applyGraphFocus();
    loadLearningModel();
  }

  function waitForModel() {
    if (hub.state.model && hub.elements.graph.querySelector(".graph-node")) {
      initialize();
      return;
    }
    addonState.pollCount += 1;
    if (addonState.pollCount >= POLL_LIMIT) return;
    window.setTimeout(waitForModel, 50);
  }

  waitForModel();
})();
