# Execution gates

## Gate 0 — completed

- Contract prepared.
- Deterministic schema and seed plans prepared.
- Offline dry-run and tests pass.
- Zero Dataverse writes.

## Gate 1 — read-only live dry-run

Run the separately supplied private PowerShell inspector against LCDH-OS DEV.
Required result:

```text
Environment type:          Sandbox
Target table collisions:   0
Target choice collisions:  0
Metadata writes:           0
Rows written:              0
```

## Gate 2 — metadata apply, separately authorized

A future authorization must bind the exact contract and schema plan hashes,
require a pre-apply export, component journal, one publication, exact
verification and a post-apply export. It must not seed rows.

## Gate 3 — 17-row seed, separately authorized

Only after exact schema verification. Upsert by alternate key and confirm that
a second seed run leaves exactly 17 rows.


## Gate 2 implementation prepared

The applicator and rollback templates are now present, but no APPLY_METADATA has
been authorized or executed. Before a future apply:

1. bind a private authorization to the exact verified PR head;
2. revalidate B0, component count 0, zero rows and zero collisions;
3. export pre-apply;
4. journal every created component;
5. publish exactly once;
6. wait until all five alternate keys are Active;
7. verify 11 direct components and effective subcomponent membership;
8. export post-apply.

Rollback is a separate authorization bound to the exact journal and post-apply
export. It is blocked if any target table contains business rows.
