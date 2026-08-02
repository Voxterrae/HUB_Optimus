(() => {
  "use strict";

  const EVIDENCE_SHA = "8426b08e5f88b650c4d79e41d3ce3afd7d42746b";
  const repository = "https://github.com/Voxterrae/HUB_Optimus";
  const blob = (path) => `${repository}/blob/${EVIDENCE_SHA}/${path}`;
  const tree = (path) => `${repository}/tree/${EVIDENCE_SHA}/${path}`;

  const routes = Object.freeze({
    "core.canonical": {
      href: tree("v1_core/languages/es"),
      language: "es",
      maturity: "canonical"
    },
    "core.meta-learning": {
      href: blob("v1_core/workflow/05_meta_learning.md"),
      language: "es"
    },
    "status.policy": {
      href: blob("docs/context/STATUS.md"),
      language: "en"
    },
    "simulator.guide": {
      href: blob("SIMULATION_README.md"),
      language: "es"
    },
    "runtime.contract": {
      href: blob("docs/architecture/runtime_contract.md"),
      language: "en"
    },
    "semantic.cli": {
      href: blob("docs/architecture/semantic_engine_cli.md"),
      language: "en"
    },
    "lab.state": {
      href: blob("docs/lab_state.md"),
      language: "en"
    },
    "governance.protocol": {
      href: blob("docs/governance/GOVERNANCE_INTELLIGENCE.md"),
      language: "en",
      maturity: "canonical",
      variants: Object.freeze({
        de: Object.freeze({
          href: blob("docs/de/governance/GOVERNANCE_INTELLIGENCE.md"),
          language: "de",
          maturity: "review-needed"
        })
      })
    },
    "governance.protection": {
      href: blob("docs/governance/SYSTEM_PROTECTION_MATRIX.md"),
      language: "en",
      maturity: "canonical"
    },
    "operator.intake.rfc": {
      href: blob("docs/rfc/operator_controlled_url_intake.md"),
      language: "en"
    },
    "platform.policy": {
      href: blob("docs/architecture/platform_compatibility.md"),
      language: "en"
    },
    "future.hermes": {
      href: blob("docs/rfc/hermes_pwa_interface_boundary.md"),
      language: "en"
    },
    "future.enterprise": {
      href: blob("docs/rfc/enterprise_boundary.md"),
      language: "en"
    },
    "future.postquantum": {
      href: blob("docs/rfc/post_quantum_control_plane.md"),
      language: "en"
    },
    "capability.status": {
      href: blob("docs/architecture/capability_status.md"),
      language: "en"
    },
    "legal.ip": {
      href: blob("IP_NOTICE.md"),
      language: "en"
    },
    "security.policy": {
      href: blob("SECURITY.md"),
      language: "en"
    },
    "translation.status": {
      href: "./i18n/README.md",
      language: "en"
    },
    "geo.data": {
      href: "./assets/geo/README.md",
      language: "en"
    },
    "translation.termbase": {
      href: "./i18n/termbase.v1.json",
      language: "data"
    }
  });

  function resolve(routeId, locale) {
    const route = routes[routeId];
    if (!route) return null;

    const selected = route.variants?.[locale] || route;
    const relation = selected.language === "data"
      ? "data"
      : (selected.language === locale ? "source" : "fallback");

    return Object.freeze({
      href: selected.href,
      language: selected.language,
      relation,
      maturity: selected.maturity || null
    });
  }

  globalThis.HUB_OPTIMUS_DOCUMENT_ROUTES = Object.freeze({
    evidenceSha: EVIDENCE_SHA,
    routeIds: Object.freeze(Object.keys(routes)),
    resolve
  });
})();
