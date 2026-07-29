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

## PowerShell maintenance utilities

The mutation-capable scripts below have **provisional manual support**:

- `tools/resolve_conflict_markers.ps1`
- `tools/fix_mojibake.ps1`
- `tools/fix_encoding_docs.ps1`

They require PowerShell 7 and Git. They are intended to behave consistently on
Windows, macOS, and Linux when those dependencies are present. This branch adds
a dedicated `PowerShell tooling` job on GitHub's Ubuntu runner. The job fails
immediately when `pwsh` 7 is unavailable and then executes the
temporary-repository behavior tests.

The pytest suite still reports those behavior tests as skipped in local or
generic CI environments without `pwsh`. A skip is not certification. Support
MUST remain described as provisional/manual until the dedicated job passes on
the reviewed PR. A green job certifies the covered behavior on that Ubuntu
runner; it does not independently certify Windows or macOS behavior.

All three scripts:

- preview changes by default;
- require `-Apply` before rewriting content;
- reject paths outside the detected repository and paths under `.git`;
- reject symbolic links/reparse points as rewrite targets;
- operate only on Git-tracked source files;
- keep optional backups in the source file's directory and refuse to overwrite
  an existing backup.

Examples:

```powershell
# Preview only
pwsh -File tools/fix_mojibake.ps1 -Path docs
pwsh -File tools/resolve_conflict_markers.ps1 -Path docs -Keep ours

# Explicit mutation after reviewing the preview
pwsh -File tools/fix_mojibake.ps1 -Path docs -Apply -Backup
pwsh -File tools/resolve_conflict_markers.ps1 -Path docs -Keep ours -Apply
```

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
