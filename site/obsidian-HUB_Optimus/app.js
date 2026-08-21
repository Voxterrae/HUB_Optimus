(() => {
  "use strict";

  const {
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
  } = window.HubIntelligence;

  function renderComponents() {
    const fragment = document.createDocumentFragment();
    const components = state.model.components.filter(
      (component) => state.componentFilter === "all" || component.status === state.componentFilter
    );

    components.forEach((component) => {
      const card = htmlElement("article", "component-card");
      const topline = htmlElement("div", "card-topline");
      topline.append(
        htmlElement("span", "card-layer", component.layer),
        statusLabel(component.status)
      );
      const heading = htmlElement("h3", "", component.name);
      const purpose = htmlElement("p", "", component.purpose);
      const links = htmlElement("div", "card-links");

      const graphLink = htmlElement("a", "text-link", "GRAPH");
      graphLink.href = "#architecture";
      graphLink.addEventListener("click", () => {
        if (!state.model.views[state.mode].nodes.includes(component.id)) {
          state.mode = "system";
          updateModeButtons();
        }
        state.selectedNodeId = component.id;
        renderGraph();
      });
      links.append(graphLink);

      if (component.note) {
        links.append(createExternalLink("OBSIDIAN", obsidianUrl(component.note), "text-link"));
      }
      if (component.source.length) {
        links.append(createExternalLink("SOURCE", sourceUrl(component.source[0]), "text-link"));
      }

      card.append(topline, heading, purpose, links);
      fragment.append(card);
    });

    elements.componentGrid.replaceChildren(fragment);
  }

  function renderRuntimeFlows() {
    const fragment = document.createDocumentFragment();
    state.model.runtime_flows.forEach((flow) => {
      const card = htmlElement("article", "flow-card");
      const intro = htmlElement("div");
      intro.append(
        statusLabel(flow.status),
        htmlElement("h3", "", flow.name)
      );
      const steps = htmlElement("div", "flow-steps");
      flow.steps.forEach((step, index) => {
        steps.append(htmlElement("span", "flow-step", step));
        if (index < flow.steps.length - 1) {
          steps.append(htmlElement("span", "flow-arrow", "→"));
        }
      });
      const boundary = htmlElement("p", "flow-boundary", flow.boundary);
      card.append(intro, steps, boundary);
      fragment.append(card);
    });
    elements.runtimeFlowList.replaceChildren(fragment);
  }

  function renderEntities() {
    const fragment = document.createDocumentFragment();
    state.model.entities.forEach((entity) => {
      const row = htmlElement("tr");
      const name = htmlElement("td");
      name.append(htmlElement("strong", "", entity.name));
      const status = htmlElement("td");
      status.append(statusLabel(entity.status));
      const purpose = htmlElement("td", "", entity.purpose);
      const source = htmlElement("td");
      const paths = htmlElement("div", "path-list");
      entity.source.forEach((path) => {
        paths.append(createExternalLink(path, sourceUrl(path), "path-link"));
      });
      source.append(paths);
      row.append(name, status, purpose, source);
      fragment.append(row);
    });
    elements.entityTableBody.replaceChildren(fragment);
  }

  function renderInterfaces() {
    const fragment = document.createDocumentFragment();
    state.model.interfaces.forEach((item) => {
      const card = htmlElement("article", "interface-card");
      const signature = item.kind === "http"
        ? `${item.method} ${item.route}`
        : item.command;
      card.append(
        htmlElement("code", "interface-signature", signature),
        htmlElement("h3", "", item.name),
        htmlElement("p", "", item.purpose)
      );

      const metadata = htmlElement("dl", "interface-meta");
      const addMeta = (term, value) => {
        metadata.append(htmlElement("dt", "", term), htmlElement("dd", "", value));
      };
      addMeta("STATUS", item.status);
      addMeta("EVIDENCE", item.confidence);
      addMeta("INPUT", item.input);
      addMeta("OUTPUT", item.output);
      card.append(metadata);

      const links = htmlElement("div", "card-links");
      if (item.note) links.append(createExternalLink("OBSIDIAN", obsidianUrl(item.note), "text-link"));
      if (item.source.length) links.append(createExternalLink("SOURCE", sourceUrl(item.source[0]), "text-link"));
      card.append(links);
      fragment.append(card);
    });
    elements.interfaceGrid.replaceChildren(fragment);
  }

  function renderDependencies() {
    const fragment = document.createDocumentFragment();
    state.model.dependencies.forEach((dependency) => {
      const card = htmlElement("article", "dependency-card");
      card.append(
        htmlElement("span", "card-layer", dependency.category),
        htmlElement("h3", "", dependency.name),
        htmlElement(
          "p",
          "",
          `Status ${dependency.status}; ${dependency.confidence}. ${dependency.source.join(", ")}`
        )
      );
      fragment.append(card);
    });
    elements.dependencyGrid.replaceChildren(fragment);
  }

  function renderDeployment() {
    const fragment = document.createDocumentFragment();
    state.model.deployment.forEach((target) => {
      const card = htmlElement("article", "deployment-card");
      card.append(
        statusLabel(target.status),
        htmlElement("h3", "", target.name),
        htmlElement("p", "", target.mechanism)
      );
      const metadata = htmlElement("dl", "deployment-meta");
      metadata.append(
        htmlElement("dt", "", "SOURCE"),
        htmlElement("dd", "", target.status),
        htmlElement("dt", "", "RUNTIME"),
        htmlElement("dd", "", target.runtime_state),
        htmlElement("dt", "", "ROUTES"),
        htmlElement("dd", "", target.routes.join(" · ")),
        htmlElement("dt", "", "BOUNDARY"),
        htmlElement("dd", "", target.boundary)
      );
      card.append(metadata);
      const links = htmlElement("div", "card-links");
      target.source.forEach((path) => {
        links.append(createExternalLink(path, sourceUrl(path), "text-link"));
      });
      card.append(links);
      fragment.append(card);
    });
    elements.deploymentGrid.replaceChildren(fragment);
  }

  function renderSourceMap() {
    const query = state.sourceQuery.trim().toLowerCase();
    const fragment = document.createDocumentFragment();
    state.model.components
      .filter((component) => {
        if (!query) return true;
        const haystack = [
          component.name,
          component.layer,
          component.status,
          ...component.source
        ].join(" ").toLowerCase();
        return haystack.includes(query);
      })
      .forEach((component) => {
        const row = htmlElement("tr");
        const concept = htmlElement("td");
        const conceptLink = createExternalLink(component.name, obsidianUrl(component.note));
        conceptLink.className = "text-link";
        concept.append(conceptLink);
        const status = htmlElement("td");
        status.append(statusLabel(component.status));
        const layer = htmlElement("td", "", component.layer);
        const sourceCell = htmlElement("td");
        const paths = htmlElement("div", "path-list");
        component.source.forEach((path) => {
          paths.append(createExternalLink(path, sourceUrl(path), "path-link"));
        });
        sourceCell.append(paths);
        row.append(concept, status, layer, sourceCell);
        fragment.append(row);
      });
    elements.sourceTableBody.replaceChildren(fragment);
  }

  function renderRisks() {
    const fragment = document.createDocumentFragment();
    state.model.risks.forEach((risk) => {
      const item = htmlElement("div", "risk-item");
      item.append(
        htmlElement("span", `risk-severity ${risk.severity}`),
        htmlElement("strong", "", risk.name),
        htmlElement("span", "", `${risk.severity} · ${risk.status}`)
      );
      fragment.append(item);
    });
    elements.riskList.replaceChildren(fragment);
  }

  function updateModeButtons() {
    document.querySelectorAll("[data-mode]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.mode === state.mode));
    });
  }

  function bindControls() {
    document.querySelectorAll("[data-mode]").forEach((button) => {
      button.addEventListener("click", () => {
        state.mode = button.dataset.mode;
        updateModeButtons();
        renderGraph();
      });
    });

    document.querySelectorAll("[data-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        state.componentFilter = button.dataset.filter;
        document.querySelectorAll("[data-filter]").forEach((candidate) => {
          candidate.setAttribute(
            "aria-pressed",
            String(candidate.dataset.filter === state.componentFilter)
          );
        });
        renderComponents();
      });
    });

    elements.sourceSearch.addEventListener("input", () => {
      state.sourceQuery = elements.sourceSearch.value;
      renderSourceMap();
    });

    reducedMotion.addEventListener?.("change", () => renderGraph());
  }

  function validateModel(model) {
    if (!model || typeof model !== "object") throw new Error("Model is not an object");
    const requiredArrays = [
      "components",
      "external_systems",
      "dependencies",
      "relations",
      "interfaces",
      "entities",
      "runtime_flows",
      "deployment",
      "risks"
    ];
    requiredArrays.forEach((key) => {
      if (!Array.isArray(model[key])) throw new Error(`Missing model array: ${key}`);
    });
    if (model.analysis?.commit !== "30e985226347b4bc59b0e187b96633a09647ca42") {
      throw new Error("Model baseline commit does not match the page contract");
    }
    return model;
  }

  function renderAll() {
    renderStats();
    renderGraph();
    renderComponents();
    renderRuntimeFlows();
    renderEntities();
    renderInterfaces();
    renderDependencies();
    renderDeployment();
    renderSourceMap();
    renderRisks();
  }

  async function boot() {
    document.documentElement.classList.remove("no-js");
    bindControls();

    try {
      const response = await fetch(MODEL_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`Model request failed: ${response.status}`);
      const coreModel = await response.json();
      const fragmentUrls = Array.isArray(coreModel.includes) ? coreModel.includes : [];
      const fragments = await Promise.all(fragmentUrls.map(async (url) => {
        const fragmentResponse = await fetch(url, { cache: "no-store" });
        if (!fragmentResponse.ok) {
          throw new Error(`Model fragment request failed: ${fragmentResponse.status}`);
        }
        return fragmentResponse.json();
      }));
      state.model = validateModel(Object.assign({}, coreModel, ...fragments));
      state.selectedNodeId = "operator";
      renderAll();
    } catch (error) {
      console.error("[project-intelligence]", error);
      elements.graphError.hidden = false;
    }
  }

  boot();
})();
