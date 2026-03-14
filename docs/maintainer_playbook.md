# Maintainer Playbook

Quick-reference guide for repository maintainers. For full governance details see [docs/governance/](governance/).

---

## Repository Monitoring

### Active Workflows

| Workflow | File | Purpose |
|---|---|---|
| CI | `ci.yml` | Core test suite, linting, policy checks |
| Link Check | `link-check.yml` | Validates all Markdown links (Lychee) |
| Kernel Guard | `kernel-guard.yml` | Blocks unauthorized changes to Layer 0 Kernel files |
| PR Safety Check | `pr-safety-check.yml` | Risk classification of incoming PRs |
| PR Quarantine | `pr-quarantine.yml` | Gates first-time contributor PRs for manual review |
| Repo Health Summary | `repo-health-summary.yml` | Weekly health snapshot with anomaly detection |
| Maintenance Bot | `repo_maintenance_bot.yml` | Automated maintenance tasks |

### Health Ledger

Issue **#93** stores weekly repository health snapshots posted by the `repo-health-summary` workflow every Monday at 08:00 UTC.

### Manual Health Check

```powershell
powershell -File scripts/repo_health.ps1
```

---

## Contributor Flow

```
Contributor opens PR
       ↓
PR Quarantine Gate (first-time contributors held for review)
       ↓
PR Risk Classification (safety-check labels the PR)
       ↓
CI Workflows (tests, links, kernel guard)
       ↓
Maintainer review & merge
       ↓
Weekly Repo Health Summary → Ledger (#93)
```

---

## Active Capabilities

- CI validation (tests + policy)
- PR quarantine for new contributors
- Risk classification on every PR
- Anomaly detection (bot loops, branch floods, PR storms)
- Bot-loop detection (chore/maintenance-* branch monitoring)
- Repository telemetry (weekly snapshots)
- Governance enforcement (kernel guard)

---

## Key Issue Tracker

| Issue | Purpose |
|---|---|
| #93 | Repository health ledger |
| #94 | Contributor task tracking |
| #118 | Feature request: scenario aggregation |

---

## Common Maintenance Tasks

### Review a quarantined PR
1. Check the `needs-maintainer-review` label
2. Review the diff for kernel-adjacent or governance changes
3. Approve or request changes; CI runs after approval

### Investigate a health alert
1. Open Issue #93, read the latest snapshot
2. Check the anomaly warnings section
3. Follow up on flagged metrics (high PRs, CI failures, branch floods)

### Add a new scenario
See the [scenario template](../v1_core/workflow/04_scenario_template.md) and the contribution guidelines in [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## Infrastructure Baseline

The governance infrastructure was stabilized at tag `infra-stable-v1`. This baseline includes:

- Complete governance workflow suite
- Automated monitoring and anomaly detection
- Repository health ledger
- Hardened CI pipeline
- Protection against loops and malicious PRs

Any infrastructure changes beyond this baseline should be justified against Layer 0 principles and evaluated for long-term stability impact.
