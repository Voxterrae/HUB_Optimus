---
type: "frontend-architecture"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "frontend"
  - "architecture"
  - "pages"
---

# Frontend Architecture

## Surfaces

### Public Static Site

`site/index.html`, shared CSS/JS, WebGL globe and accessible fallback. Served without a frontend build step.

### Operator PWA

Self-contained browser workflow with locale support, service worker, source-bound drafts, review UI and local learning modules.

### Project Intelligence Explorer

`site/obsidian-HUB_Optimus/` reads `system.json` and renders the same component/relation model documented by this vault.

## Design System

Observed design DNA:

- graphite backgrounds;
- Mediterranean blue and copper/amber accents;
- Inter/system sans + monospace technical labels;
- subtle grid/radial backgrounds;
- cards with thin borders and generous spacing;
- keyboard focus and reduced-motion support;
- responsive simplification rather than uncontrolled horizontal overflow.

## Runtime

No React/Vue/Svelte or bundler is present. HTML, CSS, JavaScript, SVG, Canvas/WebGL and browser storage are used directly.

## State

- Public portfolio: browser DOM and local language preference.
- Operator: local form/review state plus IndexedDB store.
- Project Intelligence: read-only `system.json` snapshot and selected graph node.

## Accessibility

- Semantic landmarks and skip links.
- `focus-visible`.
- keyboard-operable graph controls.
- `prefers-reduced-motion`.
- static/no-JavaScript fallback.

## Related

- [[Public Static Site]]
- [[Operator PWA]]
- [[Operator Learning Store]]
- [[GitHub Pages Pipeline]]
