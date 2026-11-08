---
applyTo: "products/evidence-lab/**,.github/workflows/optimus-evidence-lab.yml"
---

# Evidence Lab

Read `products/evidence-lab/README.md`, its `docs/MODEL.md`, `docs/APPLICATOR.md`
and `docs/RUNBOOK.md` for the affected change. This is the separate
`OptimusEvidenceLab` solution, not Admin Gateway. Preserve the tenant-neutral
public contract, sanitized baseline B0, aggregate-only seed and source/plan
hash bindings.

## Deterministic offline validation

Match `.github/workflows/optimus-evidence-lab.yml`: Python 3.12, standard-library
builder and unittest, with commands run from the repository root:

```bash
python products/evidence-lab/scripts/build_artifacts.py
git diff --exit-code -- \
  products/evidence-lab/plans/optimus-evidence-lab.schema-plan.json \
  products/evidence-lab/plans/hiv-global-2026.seed-plan.json \
  products/evidence-lab/plans/optimus-evidence-lab.dry-run.json
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover \
  -s products/evidence-lab/tests -v
```

The builder rewrites those three local artifacts; it does not connect to
Dataverse. Inspect existing plan changes first; do not overwrite unrelated local
edits. For an instruction-only or non-contract change, regeneration must
leave them unchanged. For an intentional reviewed contract/seed change, inspect
the exact deterministic delta and package-manifest implications; do not erase a
diff or edit hashes just to make validation green. Avoid creating environments,
caches or unrelated files inside the package because its manifest test checks
the package inventory. `PYTHONDONTWRITEBYTECODE=1` prevents new bytecode files.

Optional default-mode review is also offline, from the repository root:

```bash
python products/evidence-lab/scripts/apply-dataverse-schema.py
```

Tests exercise fake transport, checkout binding, idempotency, membership and
rollback behavior. A green result and planned write counts prove neither live
target inspection nor executed metadata/row writes. Report exact tests and
artifact diff results, not historical validation totals as current evidence.

## Separate live gates

- The private live collision inspection is read-only but still requires a
  separately scoped tenant operation. Offline review does not perform it.
- Metadata apply, journal-bound rollback and the 17-row seed each require their
  own explicit authorization. Applying schema must not seed rows; source
  publication, regeneration and merge authorize none of these operations.
- Keep exact applicator commit, protected checkout ancestry/content, contract,
  plan, B0, environment, expiry and component-count checks intact. Never relax
  pins or checkout checks to reuse an authorization after a source change.
- Preserve check-first discovery, exact solution membership (direct or included
  through an exact `RootComponentBehavior=0` table root), propagation waits and
  fail-closed handling of orphan/conflicting metadata.
- Rollback is separately authorized, reverse-journal ordered, exact-ID-bound,
  zero-row-gated and has no automatic rollback/retry. Business rows block
  metadata deletion. A failed/incomplete journal needs private reconciliation.

Keep private authorizations, tokens, tenant/environment identifiers, exports and
evidence outside the public repository. Preserve uncertainty bounds and
published display text in the aggregate seed; introduce no patient/person-level
data or claim that prepared plans certify a live tenant.
