# Optimus Evidence Lab — v0.1.0.0

Status: **PREPARED / OFFLINE DRY-RUN PASS / ZERO WRITES**

## Solution boundary

```text
Display name:       Optimus Evidence Lab
Unique name:        OptimusEvidenceLab
Version:            0.1.0.0
Publisher:          HUB_Optimus
Prefix:             opt
Package type:       Unmanaged
Intended target:    LCDH-OS DEV Sandbox
Admin Gateway:      separate solution
```

## Contract counts

```text
Global choices:      6
Choice options:      33
Tables:              5
Primary columns:     5
Scalar columns:      50
Lookup columns:      4
Alternate keys:      5
Relationships:       4
Logical components:  70
Schema actions:      74
Planned writes:      72
Executed writes:     0
```

Contract SHA-256:

```text
912e762601fb3265627787dd57fb1f248929492a6bca3ba5c3d2cec5afe09e70
```

Schema plan SHA-256:

```text
fd6751ff5fe42b0336bb3bc5b7da1d3854b78ec733afb76fc72a7f842005a981
```

## HIVGlobal2026Seed

Exactly 17 aggregate rows:

```text
Geography:     1
Source:        2
Release:       2
Metric:        6
Observation:   6
Total:        17
```

Seed SHA-256:

```text
005fcdf4b99c0496a934d7fb0c75cde6ddf4d98564125a20570edb1ae089de04
```

Seed plan SHA-256:

```text
800cb8db1fbbd0ee7264893dd1898fe1d95654566c6835e5078c783764da0c8f
```

The seed is derived from `HIV_AIDS_Global_Master_2026.xlsx`, cut
`2026-08-14`, with epidemiological data year `2025`. It preserves published
uncertainty bounds and original display text. It contains no patient or
person-level data.

## Rebuild and test

```bash
python scripts/build_artifacts.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

## Safety boundary

This package has not created a solution, metadata or rows. It has not touched
production, merged a branch or deployed anything. A separate private, read-only
LCDH-OS DEV inspection runner is supplied outside this tenant-neutral package.


## Governed metadata applicator

The draft package now includes an idempotent metadata applicator and an exact
rollback-by-journal plan. The applicator is bound to baseline B0 and remains
non-applying unless a private, time-limited authorization is supplied outside
the repository.

Expected post-apply direct solution components:

```text
Global choices: 6
Table roots:    5 (RootComponentBehavior=0)
Total direct:  11
Rows:           0
```

Columns, lookups, alternate keys, and relationships may be direct components or
effectively included through a table root whose `RootComponentBehavior` is `0`.
Real orphan metadata is rejected.

## Prewrite OData correction

A governed LCDH-OS DEV attempt stopped before any metadata write when
Dataverse rejected `$filter` on the `GlobalOptionSetDefinitions` collection.
The applicator now retrieves global choices by the supported `Name` alternate
key, escapes OData string literals, treats only `404` as absence, fails closed
on `405`, waits for post-create propagation, and keeps rollback deletion bound
to the exact metadata ID in the journal.

Sanitized outcome of run `20260821T113235Z`:

```text
Classification:       FAILED_PREWRITE_UNSUPPORTED_GLOBAL_OPTIONSET_FILTER
Created components:   0
Reused components:    0
Direct components:    0
Rows:                 0
Publications:         0
Rollback required:    no
Authorization reuse: no
```

No new `APPLY_METADATA`, `ROLLBACK_METADATA`, seed, merge, or deployment is
performed by this source correction.
