---
type: "dependencies"
status: "active"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "dependencies"
  - "runtime"
  - "supply-chain"
---

# Dependencies

## Runtime Dependencies

- **Python 3.11+** — `active`; evidence: `README.md`, `.github/workflows/ci.yml`.
- **jsonschema 4.x** — `active`; evidence: `requirements.txt`.
- **Browser APIs** — `active`; evidence: `site/`, `site/operator/`.

## Development Dependencies

- **pytest 9.x** — `active`; evidence: `requirements-dev.txt`.
- **PyYAML 6.x** — `active`; evidence: `requirements-dev.txt`.
- **PowerShell 7** — `active`; evidence: `.github/workflows/ci.yml`.

## Infrastructure Dependencies

- **GitHub Actions / Pages** — `active`; evidence: `.github/workflows/`.
- **Linux, git, systemd and shell tooling** — `partial`; evidence: `ops/ec2/README.md`.

## Internal Modules

- [[Scenario Contract and Loader]] → [[Round-based Simulator]]
- [[EC2 Core Runner and Run Registry]] → [[Semantic Engine Contracts and CLI]]
- [[Local HTTP API]] → [[Controlled URL Intake]] + hub-core
- [[Operator PWA]] → [[Operator Learning Store]]
- [[GitHub Pages Pipeline]] → `site/`
- [[Scenario Laboratory and Datasets]] → canonical scenario loader

## External Services

- GitHub repository, Actions and Pages.
- Remote HTTP sources for controlled intake.
- Managed Linux/EC2 host and Nginx when installed.
- DNS/TLS/network infrastructure outside repository proof.

## Critical Dependencies

| Dependency | Why critical | Failure effect |
| --- | --- | --- |
| Python + jsonschema | Contract validation/runtime | Scenario/Semantic commands fail |
| GitHub | source, review, CI, Pages | Change/deployment path unavailable |
| Browser APIs | public site/Operator | Frontend functionality degrades |
| Linux/git/systemd | managed host operations | host runtime unavailable |
| Human owner review | protected authorization | no project-valid merge |

## Dependency Policy

Version ranges are bounded by major version. GitHub Actions are pinned. The new explorer adds no external frontend package.

## Related

- [[Dependency Graph]]
- [[Testing Strategy]]
- [[Security Boundaries]]
