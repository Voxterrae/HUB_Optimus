# HUB_Optimus - System Protection Matrix

## Purpose
This matrix records the current protection surface for HUB_Optimus and the
visible gaps that still need verification or follow-up.

It is descriptive only. It does not add enforcement, change GitHub settings, or
redefine repository architecture.

## Status Key
- `active`: protection exists in the repository or documented policy.
- `partial`: protection exists but does not cover the full risk.
- `pending`: expected protection or verification is not complete.
- `unknown`: current state cannot be verified from repository files alone.

## Matrix

| Zone | Risk | Current protection | Owner | Status | Gaps |
| --- | --- | --- | --- | --- | --- |
| IP and usage rights | Public visibility may be mistaken for unrestricted license, commercial permission, or permission to create competing derivative systems. | `IP_NOTICE.md` and `docs/governance/IP_NOTICE.md` define restricted rights, kernel protection, operational method restrictions, scenario/documentation use limits, trademark notice, and enforcement language. | Benjamin Gerrit Hoff / HUB_Optimus Governance via `@Voxterrae` | active | Keep wording aligned between root and governance IP notices. Legal enforceability and external misuse handling remain outside repo automation. |
| Human stewardship and technical review boundaries | Project ownership, repository identity, technical stewardship, path-specific review authority, and AI assistance could be conflated. | `docs/governance/PROJECT_STEWARDSHIP.md` defines Benjamin Gerrit Hoff as creator, project owner, and primary human steward; `@Voxterrae` as repository identity; and Rodrigo / `@itteamrod` as Core Technical Steward with enforceable CODEOWNERS authority only for paths listed in `.github/CODEOWNERS`. | Benjamin Gerrit Hoff; Core Technical Steward Rodrigo / `@itteamrod` | active | CODEOWNERS enforcement still depends on GitHub permissions and rulesets. Technical stewardship does not transfer project ownership or constitutional governance. |
| Kernel and governance docs | Governance drift, translation drift, or unauthorized changes could weaken the constitutional core. | `docs/governance/` is covered by `.github/CODEOWNERS`; translation drift is addressed by `docs/governance/TRANSLATION_POLICY.md`; source-of-truth conflicts defer to `docs/context/STATUS.md`. | Benjamin Gerrit Hoff / `@Voxterrae` | active | CODEOWNERS review depends on GitHub branch/ruleset enforcement. Translation parity checks are policy-based unless a separate issue adds automation. |
| Canonical v1 language content | Canonical content could diverge from parity translations or be edited without appropriate scrutiny. | `.github/CODEOWNERS` assigns `v1_core/languages/`, `v1_core/languages/es/`, and `v1_core/languages/en/` to `@Voxterrae`; `docs/context/STATUS.md` states ES is canonical for v1 and EN is the parity target. | Benjamin Gerrit Hoff / `@Voxterrae` | active | Automated parity verification is not established here. Future canonical-language changes require separate governed scope. |
| CODEOWNERS review map | Protected files could change without the expected human review if CODEOWNERS is incomplete or not enforced. | `.github/CODEOWNERS` maps Kernel, governance, repository infrastructure, root configs, simulator files, and benchmarks to `@Voxterrae`; interface and Semantic Engine paths are jointly mapped to `@Voxterrae` and `@itteamrod`. | `@Voxterrae`; Core Technical Steward `@itteamrod` for assigned paths | partial | `@itteamrod` currently has read-only repository access and cannot function as an effective CODEOWNER until Write access is granted and accepted. Ruleset enforcement is tracked in #1682. |
| CI baseline | Regressions, encoding problems, or test failures could enter `main`. | `.github/workflows/ci.yml` runs the mojibake guard, narrative consistency check, `pytest`, and non-blocking benchmarks on pull requests and pushes to `main`. | `@Voxterrae` | active | CI only protects merges if required checks are configured in GitHub Settings. Required-check enforcement is tracked in #1681. |
| Kernel guard | Protected kernel/governance changes could be merged without explicit acknowledgement. | `.github/workflows/kernel-guard.yml` runs `tools/kernel_guard.py` on pull requests and requires the `allow-kernel-change` label to permit kernel changes. | `@Voxterrae` | active | Guard strength depends on the maintained protected-path list and required-check enforcement. Required status is tracked in #1681. |
| PR risk classification | High-risk changes could be reviewed as ordinary documentation or tooling edits. | `.github/workflows/pr-safety-check.yml` classifies protected-path changes, including `docs/governance/`, `.github/workflows/`, `.github/CODEOWNERS`, runtime files, schema, expected benchmarks, and v1 language content. | `@Voxterrae` | active | The workflow warns and summarizes risk; it does not itself block merge unless configured as a required check. |
| External contributor quarantine | First-time fork PRs could run untrusted code or bypass maintainer attention. | `.github/workflows/pr-quarantine.yml` is metadata-only, avoids checkout/execution, labels first-time external fork PRs, and comments that maintainer review is required. | `@Voxterrae` | active | Applies only to first-time external fork PRs. Label existence and required-review policy still depend on GitHub configuration. |
| Branch protection and rulesets | Direct pushes, force pushes, missing required checks, missing review requirements, or undocumented bypass could bypass repo policy. | Expected protection belongs in GitHub Settings, with observed state recorded in `docs/governance/GITHUB_SETTINGS_PROTECTION_CHECKLIST.md`. | `@Voxterrae` | pending | Ruleset consolidation is tracked in #1680, required checks in #1681, CODEOWNERS enforcement in #1682, and bypass policy in #1683. |
| AI handoff and chat decisions | Unsynced chat decisions could be treated as governance, roadmap, or implementation authority. | `docs/context/AI_HANDOFF.md` states GitHub is the source of truth and chat context only matters when reflected in issues, PRs, or repo docs. `docs/governance/PROJECT_STEWARDSHIP.md` keeps final accountability human and technical stewardship human-led. | Benjamin Gerrit Hoff / `@Voxterrae` | active | Detailed AI access levels remain governed separately; AI roles must not be inferred as ownership or CODEOWNERS authority. |

## Current Gaps To Track
- Consolidate overlapping `main` rulesets in #1680.
- Enforce required checks for CI, Kernel Guard, Link Check, and PR Safety Check in #1681.
- Enforce CODEOWNERS review through GitHub Settings in #1682.
- Define and document repository-role bypass policy in #1683.
- Grant and confirm Write collaborator access for `@itteamrod` before treating assigned CODEOWNERS paths as enforceable.
- Keep technical stewardship synchronized across `.github/CODEOWNERS`, `PROJECT_STEWARDSHIP.md`, `ACKNOWLEDGEMENTS.md`, and `AI_HANDOFF.md`.
- Keep external AI roles out of scope for this matrix; define them separately in #1584 and #1585.
- Keep architecture terminology and capability status out of scope for this matrix; define them separately in #1586, #1587, and #1589.
