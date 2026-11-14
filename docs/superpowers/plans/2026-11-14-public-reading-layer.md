# Public reading layer implementation plan

> **For agentic workers:** Use executing-plans to implement these tasks with a
> final independent review. Steps use checkbox syntax for tracking.

**Goal:** Publish a readable, source-bound introduction, catalogue, governance
documents and Operator pilot through the existing public surfaces.

**Architecture:** Keep Markdown as the source and generate a fixed allowlist of
static HTML pages from one explicit Git commit. Preserve the original Markdown
bytes beside each page. The existing portfolio links into this reading layer;
Sites synchronization remains a separate, provenance-recorded publication.

**Tech Stack:** Python 3.10+, markdown-it-py 4.3.0 and mdurl 0.1.2 as authoring
tools; existing buildless HTML/CSS/JavaScript; pytest and existing site checks.

**Spec:** `docs/superpowers/specs/2026-11-14-public-portfolio-expansion-design.md`.
Editorial design and Operator-first pilot approved by the owner on 2026-11-14.

## Global constraints

- Related to #2187; #2185 and #1936 remain open.
- Never alter normative source text, canonicality, ownership or ratification.
- Use a source commit that exists before generation; record path and SHA-256.
- Keep source, generated artifact, integration and deployment receipts separate.
- No runtime dependency, provider, framework, CI-workflow or audience change.
- Tooling dependency is pinned in `requirements-docs.txt`, included by the
  existing development requirements so current CI can run authoring tests.
- No private source, device/customer data, credentials or external transport.
- Translation fallbacks must name the real source language; no stub as a full
  translation. Eight reader UI choices do not imply eight translated documents.
- Keep the existing seven public routes and all their evidence pins intact.

## Review focus

- Preambles and trailing normative content survive, with byte-exact source.
- Malformed/encoded URL schemes and raw HTML never become active content.
- Heading collisions, relative fragments and unavailable translations resolve
  without dead local links or misleading language labels.
- Long tables, narrow screens, keyboard focus and Hebrew UI retain readable
  content whose actual document language is unchanged.
- A successful test or source push never stands in for a deployment receipt or
  acceptance of an external action.

### Task 1: Pin approved source and a useful Operator walkthrough

**Files:** update the editorial status in the design and plain-language guide;
create `docs/project/OPERATOR_FIRST_PILOT.md`; this plan.

**Interfaces:** produces a signed source commit, `SOURCE_REF`, containing the
approved guide and exact Operator steps. Later generation reads only Git blobs
at that commit, never silently substitutes working-tree text.

- [x] Check current Operator controls and existing DOM tests with a synthetic
  two-line fixture; record observed results separately from browser acceptance.
- [x] Document paste, draft, review, Advanced / Build JSON / Copy JSON and clear
  actions using their actual controls. No URL-fetch or generic export claim.
- [x] Publish the scoped source-only commit and verify its file blobs and actor.

### Task 2: Generate safe, reproducible reading pages

**Files:** create `tools/render_public_docs.py`, `requirements-docs.txt`,
`site/data/public-documents.v1.json`, `site/docs/reading.css`,
`site/docs/reading.js`, generated `site/docs/<id>/index.html` and `source.md`,
`site/docs/index.html`, `tests/test_public_reading.py`; update development
requirements only to include the pinned authoring dependencies.

**Interfaces:** `load_sources(root: Path, manifest: dict) -> list[dict]` validates
IDs, paths, immutable source commit and checksums; `render_document(record,
records, root) -> str` generates one complete page;
`generate(root: Path, check: bool = False) -> list[Path]` writes deterministic
artifacts or rejects drift without writing. CLI: `--check` and `--root`.

The manifest records `source_ref`, `documents` with `id`, `path`, `language`,
`title`, `kind`, `sha256`, optional `variants`, and an explicit route inventory.
Initial IDs: `conoce`, `capacidades`, `contribuciones`, `ecosistema`, `catalogo`,
`autoridad`, `charter`, `kernel`, `carta-nucleo`, `simulation-charter`,
`operator-piloto`. Do not infer publication by scanning all repository Markdown.

- [x] Write and run failing tests for byte-exact preamble/body/tail, deterministic
  output/drift, source/path/hash rejection, hostile URLs/HTML, duplicate headings,
  relative-fragment rewrite, source fallback and no-JavaScript readability.
- [x] Implement with MarkdownIt HTML disabled, tables enabled and strict URL
  handling. Non-allowlisted existing paths link to the fixed GitHub source;
  missing destinations remain visibly unavailable rather than dead links.
- [x] Prefix generated heading IDs with `doc-`; preserve source URLs/line anchors
  when no generated destination can represent them faithfully.
- [x] Never auto-load remote images from Markdown. Preserve alt text and a safe
  link to their source; raw source remains available for exact inspection.
- [x] Generate an index and readable pages with original-source download,
  provenance, full document, contents, boundaries and keyboard navigation.
- [x] Add eight language UI choices and explicit fallback; use actual source
  `lang`/`dir` for content and selected UI language/direction only for controls.
- [x] Run authoring tests and `--check`; all generated files must be reproducible.

### Task 3: Connect the portfolio and preserve route contracts

**Files:** `site/index.html`, `site/app.js`, locale metadata/README;
`tests/test_public_site_links_and_contrast.py`, `tests/test_public_portfolio.py`.

**Interfaces:** existing portfolio links to `./docs/index.html?lang=<locale>`;
reader index links to `../operator/?lang=<locale>#product_intake`. Original
route/evidence tests remain applicable to their seven routes; generated routes
are an explicit additional set and the union equals every published HTML file.

- [x] Write failing assertions for reader links, honest public Operator wording,
  language-link propagation and the exact route union.
- [x] Add the reader entry and pilot links; correct the URL-fetch implication in
  the six existing portfolio dictionaries and English static fallback.
- [x] Retain original pinned-source and external-navigation guards. Check the
  reader's source targets/fragments and exact external inventory independently.
- [x] Run portfolio, reading, catalogue, registry, links/contrast and language
  tests; run encoding, JavaScript syntax and diff checks.

### Task 4: Observe acceptance and prepare publication

**Files:** handoff and a dated validation/publication receipt as evidence permits.

**Interfaces:** exact candidate SHA/tree and source receipt; eventual Pages
run/source/artifact/served bytes, then existing Site version/source/access.

- [ ] Use supported CUA preview only for visible desktop/mobile, keyboard,
  no-JavaScript/source fallback and reader language checks. If unavailable,
  record that limit; do not improvise a second browser-control route.
- [ ] Run the synthetic Operator walkthrough in the observed UI where available;
  distinguish harness assertions from real-browser or human acceptance.
- [ ] Obtain one independent whole-change review and correct material findings.
- [ ] Publish the signed candidate and verify files against the tested tree.
- [ ] Confirm all required checks and owner/integration constraints for the exact
  candidate. No automatic bypass, approval substitution or workflow retry.
- [ ] Publish only through the authorized protected path. Verify Pages receipt
  and bytes; synchronize the existing Site separately, preserving audience.
- [ ] Report what is actually live and any specific unresolved gate.
