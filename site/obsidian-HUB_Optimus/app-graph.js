window.HubIntelligence = (() => {
  "use strict";

  const MODEL_URL = "./system.json";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const state = {
    model: null,
    mode: "system",
    selectedNodeId: null,
    componentFilter: "all",
    sourceQuery: ""
  };

  const elements = {
    graph: document.getElementById("architecture-graph"),
    graphError: document.getElementById("graph-error"),
    graphModeLabel: document.getElementById("graph-mode-label"),
    viewDescription: document.getElementById("view-description"),
    mobileGraphList: document.getElementById("mobile-graph-list"),
    nodeDetail: document.getElementById("node-detail"),
    componentGrid: document.getElementById("component-grid"),
    runtimeFlowList: document.getElementById("runtime-flow-list"),
    entityTableBody: document.getElementById("entity-table-body"),
    interfaceGrid: document.getElementById("interface-grid"),
    dependencyGrid: document.getElementById("dependency-grid"),
    deploymentGrid: document.getElementById("deployment-grid"),
    sourceTableBody: document.getElementById("source-table-body"),
    sourceSearch: document.getElementById("source-search"),
    riskList: document.getElementById("risk-list")
  };

  function htmlElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(SVG_NS, tag);
    for (const [name, value] of Object.entries(attributes)) {
      element.setAttribute(name, String(value));
    }
    return element;
  }

  function sourceUrl(path) {
    const clean = String(path).replace(/\/+$/, "");
    const route = String(path).endsWith("/") ? "tree" : "blob";
    const repository = state.model.analysis.repository;
    const commit = state.model.analysis.commit;
    return `https://github.com/${repository}/${route}/${commit}/${clean}`;
  }

  function obsidianUrl(notePath) {
    const repository = state.model.analysis.repository;
    return encodeURI(`https://github.com/${repository}/blob/main/obsidian-HUB_Optimus/${notePath}`);
  }

  function createExternalLink(label, href, className = "") {
    const link = htmlElement("a", className, label);
    link.href = href;
    return link;
  }

  function statusDot(status) {
    const dot = htmlElement("i", `status-dot status-${status}`);
    dot.setAttribute("aria-hidden", "true");
    return dot;
  }

  function statusLabel(status) {
    const wrapper = htmlElement("span", "card-status");
    wrapper.append(statusDot(status), document.createTextNode(status));
    return wrapper;
  }

  function allNodes() {
    if (!state.model) return [];
    return [
      ...state.model.components,
      ...state.model.external_systems,
      ...state.model.dependencies
    ];
  }

  function nodeMap() {
    return new Map(allNodes().map((node) => [node.id, node]));
  }

  function nodeKind(node) {
    if (node.note) return node.layer || "component";
    if (node.category) return `dependency · ${node.category}`;
    return node.kind || "external";
  }

  function nodePurpose(node) {
    if (node.purpose) return node.purpose;
    if (node.category) return `Dependencia ${node.category} declarada por el repositorio.`;
    return "Nodo externo o contractual del sistema.";
  }

  function nodeSource(node) {
    return Array.isArray(node.source) ? node.source : [];
  }

  function wrapLabel(value, maxLength = 19) {
    const words = String(value).split(/\s+/).filter(Boolean);
    if (!words.length) return [""];
    const lines = [""];
    for (const word of words) {
      const current = lines[lines.length - 1];
      const candidate = current ? `${current} ${word}` : word;
      if (candidate.length <= maxLength || !current) {
        lines[lines.length - 1] = candidate;
      } else if (lines.length < 2) {
        lines.push(word);
      } else {
        lines[1] = `${lines[1].slice(0, Math.max(1, maxLength - 1))}…`;
        break;
      }
    }
    return lines.slice(0, 2);
  }

  function renderStats() {
    const counts = {
      components: state.model.components.length,
      interfaces: state.model.interfaces.length,
      entities: state.model.entities.length,
      relations: state.model.relations.length,
      risks: state.model.risks.length
    };
    for (const [key, value] of Object.entries(counts)) {
      const target = document.querySelector(`[data-stat="${key}"]`);
      if (target) target.textContent = String(value).padStart(2, "0");
    }
  }

  function relationTitle(relation, nodes) {
    const from = nodes.get(relation.from)?.name || relation.from;
    const to = nodes.get(relation.to)?.name || relation.to;
    return `${from} → ${to}: ${relation.label}`;
  }

  function currentGraphFocus() {
    const active = document.activeElement;
    const nodeId = active?.getAttribute?.("data-node-id");
    if (!nodeId) return null;
    if (elements.mobileGraphList.contains(active)) {
      return { nodeId, target: "mobile" };
    }
    if (elements.graph.contains(active)) {
      return { nodeId, target: "graph" };
    }
    return null;
  }

  function restoreGraphFocus(request) {
    if (!request?.nodeId || !request?.target) return;
    const container = request.target === "mobile"
      ? elements.mobileGraphList
      : elements.graph;
    queueMicrotask(() => {
      const replacement = Array.from(container.querySelectorAll("[data-node-id]"))
        .find((candidate) => candidate.getAttribute("data-node-id") === request.nodeId);
      if (!replacement) return;
      try {
        replacement.focus({ preventScroll: true });
      } catch (_error) {
        replacement.focus();
      }
    });
  }

  function renderGraph(focusRequest = currentGraphFocus()) {
    const model = state.model;
    const view = model.views[state.mode];
    const layout = model.layouts[state.mode];
    const nodes = nodeMap();

    elements.graphModeLabel.textContent = view.label;
    elements.viewDescription.textContent = view.description;

    if (!view.nodes.includes(state.selectedNodeId)) {
      state.selectedNodeId = view.nodes.find((id) => nodes.get(id)?.note) || view.nodes[0];
    }

    const title = svgElement("title", { id: "graph-title" });
    title.textContent = `Arquitectura HUB_Optimus · ${view.label}`;
    const description = svgElement("desc", { id: "graph-description" });
    description.textContent = view.description;

    const defs = svgElement("defs");
    const marker = svgElement("marker", {
      id: "arrow-head",
      markerWidth: 8,
      markerHeight: 8,
      refX: 7,
      refY: 3.5,
      orient: "auto",
      markerUnits: "strokeWidth"
    });
    marker.append(svgElement("path", {
      d: "M0,0 L8,3.5 L0,7 Z",
      fill: "rgba(157,167,179,0.58)"
    }));
    defs.append(marker);

    const edgeLayer = svgElement("g", { "aria-hidden": "true" });
    const nodeLayer = svgElement("g");
    const visibleRelations = model.relations.filter(
      (relation) => view.relations.includes(relation.id)
        && view.nodes.includes(relation.from)
        && view.nodes.includes(relation.to)
        && layout[relation.from]
        && layout[relation.to]
    );

    visibleRelations.forEach((relation, index) => {
      const [sourceX, sourceY] = layout[relation.from];
      const [targetX, targetY] = layout[relation.to];
      const sourceOffset = targetX >= sourceX ? 75 : -75;
      const targetOffset = targetX >= sourceX ? -75 : 75;
      const startX = sourceX + sourceOffset;
      const endX = targetX + targetOffset;
      const middleX = (startX + endX) / 2;
      const pathData = `M ${startX} ${sourceY} C ${middleX} ${sourceY}, ${middleX} ${targetY}, ${endX} ${targetY}`;
      const edgeId = `edge-${relation.id}`;

      const path = svgElement("path", {
        id: edgeId,
        d: pathData,
        class: `graph-edge status-${relation.status}`
      });
      if (["isolated_from", "not_executed_by"].includes(relation.type)) {
        path.classList.add("relation-negative");
      }
      const edgeTitle = svgElement("title");
      edgeTitle.textContent = relationTitle(relation, nodes);
      path.append(edgeTitle);
      edgeLayer.append(path);

      if (!reducedMotion.matches
        && relation.status !== "unknown"
        && !["isolated_from", "not_executed_by"].includes(relation.type)) {
        const pulse = svgElement("circle", { r: 2.6, class: "flow-pulse" });
        const motion = svgElement("animateMotion", {
          dur: `${4.5 + (index % 4)}s`,
          begin: `${(index % 7) * 0.28}s`,
          repeatCount: "indefinite"
        });
        const motionPath = svgElement("mpath", { href: `#${edgeId}` });
        motion.append(motionPath);
        pulse.append(motion);
        edgeLayer.append(pulse);
      }
    });

    view.nodes.forEach((nodeId) => {
      const node = nodes.get(nodeId);
      const position = layout[nodeId];
      if (!node || !position) return;
      const [x, y] = position;
      const group = svgElement("g", {
        class: "graph-node",
        transform: `translate(${x} ${y})`,
        role: "button",
        tabindex: "0",
        "data-node-id": nodeId,
        "aria-label": `${node.name}, ${node.status}, ${nodeKind(node)}`
      });
      if (nodeId === state.selectedNodeId) group.classList.add("is-selected");

      group.append(svgElement("rect", {
        x: -75,
        y: -32,
        width: 150,
        height: 64,
        rx: 14
      }));

      group.append(svgElement("circle", {
        cx: -62,
        cy: -20,
        r: 5,
        class: `node-status status-${node.status}`
      }));

      const labelLines = wrapLabel(node.name);
      labelLines.forEach((line, lineIndex) => {
        const label = svgElement("text", {
          x: 0,
          y: labelLines.length === 1 ? -2 : -7 + (lineIndex * 14)
        });
        label.textContent = line;
        group.append(label);
      });

      const meta = svgElement("text", {
        x: 0,
        y: 22,
        class: "node-meta"
      });
      meta.textContent = `${node.status} · ${nodeKind(node)}`.slice(0, 32);
      group.append(meta);

      const titleNode = svgElement("title");
      titleNode.textContent = `${node.name}: ${nodePurpose(node)}`;
      group.append(titleNode);

      const select = () => selectNode(nodeId, "graph");
      group.addEventListener("click", select);
      group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          select();
        }
      });
      nodeLayer.append(group);
    });

    elements.graph.replaceChildren(title, description, defs, edgeLayer, nodeLayer);
    renderMobileGraphList(view, nodes);
    renderNodeDetail();
    restoreGraphFocus(focusRequest);
  }

  function renderMobileGraphList(view, nodes) {
    const fragment = document.createDocumentFragment();
    view.nodes.forEach((nodeId) => {
      const node = nodes.get(nodeId);
      if (!node) return;
      const button = htmlElement("button", "mobile-node-button");
      button.type = "button";
      button.setAttribute("data-node-id", nodeId);
      button.setAttribute("aria-pressed", String(nodeId === state.selectedNodeId));
      const title = htmlElement("strong", "", node.name);
      const meta = htmlElement("small", "", `${node.status} · ${nodeKind(node)}`);
      button.append(title, meta);
      button.addEventListener("click", () => selectNode(nodeId, "mobile"));
      fragment.append(button);
    });
    elements.mobileGraphList.replaceChildren(fragment);
  }

  function selectNode(nodeId, focusTarget = null) {
    state.selectedNodeId = nodeId;
    const focusRequest = focusTarget ? { nodeId, target: focusTarget } : null;
    renderGraph(focusRequest);
  }

  function renderNodeDetail() {
    const nodes = nodeMap();
    const node = nodes.get(state.selectedNodeId);
    if (!node) return;

    const kicker = htmlElement("p", "panel-kicker", "SELECTED NODE");
    const heading = htmlElement("h3", "", node.name);
    const badges = htmlElement("div", "detail-badges");
    badges.append(
      htmlElement("span", "badge", node.status),
      htmlElement(
        "span",
        `badge badge-${String(node.confidence || "UNKNOWN").toLowerCase()}`,
        node.confidence || "UNKNOWN"
      ),
      htmlElement("span", "badge", nodeKind(node))
    );
    const purpose = htmlElement("p", "", nodePurpose(node));

    const relationSection = htmlElement("section", "detail-section");
    relationSection.append(htmlElement("h4", "", "Relations"));
    const relationList = htmlElement("ul", "detail-list");
    const related = state.model.relations.filter(
      (relation) => relation.from === node.id || relation.to === node.id
    );
    if (!related.length) {
      relationList.append(htmlElement("li", "", "No supported runtime relation in this model."));
    } else {
      related.slice(0, 8).forEach((relation) => {
        const outgoing = relation.from === node.id;
        const peerId = outgoing ? relation.to : relation.from;
        const peer = nodes.get(peerId);
        const arrow = outgoing ? "→" : "←";
        relationList.append(
          htmlElement("li", "", `${arrow} ${peer?.name || peerId}: ${relation.label} [${relation.status}]`)
        );
      });
    }
    relationSection.append(relationList);

    const source = nodeSource(node);
    const sourceSection = htmlElement("section", "detail-section");
    sourceSection.append(htmlElement("h4", "", "Source"));
    const sourceList = htmlElement("ul", "detail-list");
    if (!source.length) {
      sourceList.append(htmlElement("li", "", "External or conceptual node; no repository source path."));
    } else {
      source.forEach((path) => {
        const item = htmlElement("li");
        item.append(createExternalLink(path, sourceUrl(path)));
        sourceList.append(item);
      });
    }
    sourceSection.append(sourceList);

    const linksSection = htmlElement("section", "detail-section");
    linksSection.append(htmlElement("h4", "", "Documentation"));
    const links = htmlElement("ul", "detail-list");
    if (node.note) {
      const noteItem = htmlElement("li");
      noteItem.append(createExternalLink("Open matching Obsidian note", obsidianUrl(node.note)));
      links.append(noteItem);
    }
    const modelItem = htmlElement("li");
    modelItem.append(createExternalLink("Inspect structured model", "./system.json"));
    links.append(modelItem);
    linksSection.append(links);

    elements.nodeDetail.replaceChildren(
      kicker,
      heading,
      badges,
      purpose,
      relationSection,
      sourceSection,
      linksSection
    );
  }

  return {
    MODEL_URL,
    reducedMotion,
    state,
    elements,
    htmlElement,
    statusLabel,
    sourceUrl,
    obsidianUrl,
    createExternalLink,
    renderStats,
    renderGraph,
    selectNode
  };
})();
