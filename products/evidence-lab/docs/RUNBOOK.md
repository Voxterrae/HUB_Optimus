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
