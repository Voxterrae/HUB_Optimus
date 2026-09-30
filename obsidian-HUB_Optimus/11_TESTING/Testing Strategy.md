---
type: "testing"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "testing"
  - "ci"
  - "quality"
---

# Testing Strategy

## Blocking Python Job

The CI source uses Python 3.12 and:

```bash
python -m pip install -r requirements-dev.txt
python tools/check_mojibake.py .
python benchmarks/check_narrative_consistency.py
python -m pytest -q
```

## PowerShell Job

PowerShell 7 behavior tests run separately on Ubuntu.

## Benchmarks

Scenario and narrative benchmarks are useful evidence but their CI job is non-blocking. A passing benchmark does not establish real-world accuracy.

## Test Domains

- Scenario schema/CLI/simulator determinism.
- Semantic contracts/CLI.
- Operator PWA, i18n, record integrity, learning model/store.
- URL intake and API proxy boundaries.
- EC2 provenance/deploy/rollback.
- Public site, responsive/reduced-motion/static behavior.
- Governance guards, source of truth and workflow pins.
- Datasets and narrative consistency.

## Project Intelligence Tests

`tests/test_project_intelligence_site.py` validates:

- model vocabulary and graph integrity;
- required components, interfaces and baseline commit/tree;
- Obsidian Home/current-state/map files;
- resolvable Wikilinks;
- web local assets, IDs, accessibility primitives and pinned source links;
- reduced-motion and no unsafe `innerHTML`.

## Interpretation

Tests reduce known uncertainty; they do not prove legal, scientific, security, translation or deployment state outside their assertions.

## Related

- [[Tests and Quality Gates]]
- [[Evidence Index]]
- [[Update Protocol]]
