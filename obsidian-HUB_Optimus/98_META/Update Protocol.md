---
type: "meta-protocol"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "meta"
  - "maintenance"
  - "delta-update"
---

# Update Protocol

## Trigger

Run this protocol when `main` changes architecture-relevant source, schemas, workflows, tests, public routes or governing truth records.

## Delta Procedure

1. Record new `main` commit and tree.
2. Diff against `30e985226347b4bc59b0e187b96633a09647ca42`.
3. Identify affected components, interfaces, entities, relations, risks and source paths.
4. Inspect current code/config/schema/tests before updating prose.
5. Update `site/obsidian-HUB_Optimus/system.json` and every fragment declared in `includes`.
6. Update only affected notes and dashboard counts.
7. Preserve documentation drift instead of silently deleting history.
8. Run `tests/test_project_intelligence_site.py`, relevant repository tests, mojibake and static JS checks.
9. Review diff for secrets, accidental runtime changes and `/operator/` modification.
10. Open one bounded PR with explicit baseline and rollback.

## Synchronization Invariant

```text
Repository delta
      ↓
system.json delta
      ↓
affected Obsidian notes
      ↓
web explorer
      ↓
focused validation
```

No component may have different names or statuses between the structured model, vault and web UI.

## External Verification

Deployment/runtime state must be inspected separately after merge. Never set it to `active` merely because source was merged.

## Rollback

Revert the bounded project-intelligence commit. Existing runtime, Operator and Pages home must remain unchanged.
