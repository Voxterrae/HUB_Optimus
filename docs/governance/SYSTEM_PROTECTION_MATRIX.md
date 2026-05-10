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
| IP and usage rights | Public visibility may be mistaken for unrestricted license, commercial permission, or permission to create competing derivative systems. | `IP_NOTICE.md` and `docs/governance/IP_NOTICE.md` define restricted rights, kernel protection, operational method restrictions, scenario/documentation use limits, trademark notice, and enforcement language. | HUB_Optimus Governance / `@Voxterrae` | active | Keep wording aligned between root and governance IP notices. Legal enforceability and external misuse handling remain outside repo automation. |
| Kernel and governance docs | Governance drift, translation drift, or unauthorized changes could weaken the constitutional core. | `docs/governance/` is covered by `.github/CODEOWNERS`; translation drift is addressed by `docs/governance/TRANSLATION_POLICY.md`; source-of-truth conflicts defer to `docs/context/STATUS.md`. | `@Voxterrae` | active | CODEOWNERS review depends on GitHub branch/ruleset enforcement. Translation parity checks are policy-based unless a separate issue adds automation. |
| Canonical v1 language content | Canonical content could diverge from parity translations or be edited without appropriate scrutiny. | `.github/CODEOWNERS` assigns `v1_core/languages/`, `v1_core/languages/es/`, and `v1_core/languages/en/` to `@Voxterrae`; `docs/context/STATUS.md` states ES is canonical for v1 and EN is the parity target. | `@Voxterrae` | active | Automated parity verification is not established here. Future canonical-language changes require separate governed scope. |
| CODEOWNERS review map | Protected files could change without the expected maintainer review if CODEOWNERS is incomplete or not enforced. | `.github/CODEOWNERS` maps kernel language content, governance docs, `.github/`, root configs, simulator files, `hub_optimus/`, and benchmarks to `@Voxterrae`. | `@Voxterrae` | active | GitHub must enforce CODEOWNERS through branch protection or rulesets; that Settings state is pending verification in #1590. |
| CI baseline | Regressions, encoding problems, or test failures could enter `main`. | `.github/workflows/ci.yml` runs the mojibake guard, narrative consistency check, `pytest`, and non-blocking benchmarks on pull requests and pushes to `main`. | `@Voxterrae` | active | CI only protects merges if required checks are configured in GitHub Settings. Required-check status is pending verification in #1590. |
| Kernel guard | Protected kernel/governance changes could be merged without explicit acknowledgement. | `.github/workflows/kernel-guard.yml` runs `tools/kernel_guard.py` on pull requests and requires the `allow-kernel-change` label to permit kernel changes. | `@Voxterrae` | active | Guard strength depends on the maintained protected-path list and required-check enforcement. Required status is pending verification in #1590. |
| PR risk classification | High-risk changes could be reviewed as ordinary documentation or tooling edits. | `.github/workflows/pr-safety-check.yml` classifies protected-path changes, including `docs/governance/`, `.github/workflows/`, `.github/CODEOWNERS`, runtime files, schema, expected benchmarks, and v1 language content. | `@Voxterrae` | active | The workflow warns and summarizes risk; it does not itself block merge unless configured as a required check. |
| External contributor quarantine | First-time fork PRs could run untrusted code or bypass maintainer attention. | `.github/workflows/pr-quarantine.yml` is metadata-only, avoids checkout/execution, labels first-time external fork PRs, and comments that maintainer review is required. | `@Voxterrae` | active | Applies only to first-time external fork PRs. Label existence and required-review policy still depend on GitHub configuration. |
| Branch protection and rulesets | Direct pushes, force pushes, missing required checks, or missing review requirements could bypass repo policy. | Expected protection belongs in GitHub Settings, not in repository files. Local repo evidence cannot fully verify rulesets or branch protection. | `@Voxterrae` | pending | Verify branch protection, required checks, CODEOWNERS enforcement, no force pushes, and deletion restrictions in #1590. Until then, treat Settings state as pending/unknown. |
| AI handoff and chat decisions | Unsynced chat decisions could be treated as governance, roadmap, or implementation authority. | `docs/context/AI_HANDOFF.md` states GitHub is the source of truth and chat context only matters when reflected in issues, PRs, or repo docs. | `@Voxterrae` | active | Detailed AI access levels are not defined here; that belongs to #1584 and #1585. |

## Current Gaps To Track
- Verify GitHub branch protection and rulesets in #1590.
- Verify required checks for CI, kernel guard, and risk classification in #1590.
- Confirm CODEOWNERS enforcement through GitHub Settings in #1590.
- Keep external AI roles out of scope for this matrix; define them separately in #1584 and #1585.
- Keep architecture terminology and capability status out of scope for this matrix; define them separately in #1586, #1587, and #1589.
