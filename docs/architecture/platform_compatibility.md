# Platform Compatibility Policy

HUB_Optimus is platform-neutral by contract.

It must remain accessible from modern desktop and mobile operating systems without requiring users or contributors to change device for reading, review, or participation.

## Compatibility layers

| Layer | Capability | Expected support |
|---|---|---|
| Reading | README, docs, scenarios | Any modern browser |
| Review | Issues, pull requests, diffs, CI results | GitHub web or app |
| Light editing | Documentation edits, comments, small text fixes | GitHub web editor |
| Local execution | Simulator, tests, tools | Python-compatible environment |
| Official validation | Tests, benchmarks, link checks, guardrails | GitHub Actions / CI |

## Runtime guarantee

The runtime guarantee is not tied to a native operating system.

The current runtime contract is based on:

- UTF-8 text files
- JSON scenario input
- JSON Schema validation
- Python CLI execution
- deterministic JSON output
- CI validation

## Mobile platforms

iOS and Android are supported as access and review platforms.

Native mobile execution is not part of the current runtime guarantee. Android-based terminal environments may work when they provide compatible Python and Git tooling, but CI remains the authoritative validation layer.

## Non-goals

This policy does not introduce:

- native iOS app support
- native Android app support
- device-specific forks
- platform-specific runtime behavior
- separate mobile roadmap

## Canonical rule

HUB_Optimus is readable via web, reviewable via GitHub, executable in Python-compatible environments, and validated by CI.

Native mobile execution is not part of the current runtime guarantee.
