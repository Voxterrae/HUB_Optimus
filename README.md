# HUB_Optimus

[![CI](https://github.com/Voxterrae/HUB_Optimus/actions/workflows/ci.yml/badge.svg)](https://github.com/Voxterrae/HUB_Optimus/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Voxterrae/HUB_Optimus)](https://github.com/Voxterrae/HUB_Optimus/releases/latest)
[![License](https://img.shields.io/badge/license-see%20IP__NOTICE-blue)](IP_NOTICE.md)

**Integrity-first diplomatic simulation workflow for evaluation, preventive mediation, and systemic learning.**

**Languages / Idiomas:**

> **Primary onboarding:** [EN](docs/00_start_here.md) · [ES](docs/es/00_start_here.md) · [DE](docs/de/00_start_here.md)
>
> **Translation status:** CA / FR / RU = progressive translation (not language-faithful onboarding yet) · HE = stub / full translation pending · ZH = governance stub only
>
> Source of truth: [docs/context/STATUS.md](docs/context/STATUS.md)

**Quick paths:**
- 90 seconds: [EN](docs/00_start_here.md) · [ES](docs/es/00_start_here.md) · [DE](docs/de/00_start_here.md)
- 20 minutes (canonical v1 ES): [v1_core/languages/es](v1_core/languages/es)
- Hands-on: [Scenario Template](v1_core/workflow/04_scenario_template.md)




---

## What it is
**HUB_Optimus** is developed in a publicly visible repository with restricted rights;
contribution and use are governed by [IP_NOTICE.md](IP_NOTICE.md). It is designed to improve diplomatic outcomes through:
- structured evaluation (incentives, verification, sequencing),
- preventive, non-coercive mediation options,
- iterative meta-learning from both failures and successes.

It helps humans and institutions:
- avoid repeating known historical failure patterns,
- detect “false successes” before they escalate,
- align incentives with medium/long-term stability,
- operate rationally under time pressure and political noise.

## What it is not
- Not an authority.
- Not a prediction engine.
- Not a replacement for diplomacy.

It is a tool for **better judgment**.

---

## Start in 60 seconds
**New here?**
- Start (EN): [docs/00_start_here.md](docs/00_start_here.md)
- Empezar (ES): [docs/es/00_start_here.md](docs/es/00_start_here.md)
- Start (DE): [docs/de/00_start_here.md](docs/de/00_start_here.md)

**See it in practice (guided walkthrough):**
- 🇬🇧 Try a scenario: [docs/03_try_a_scenario.md](docs/03_try_a_scenario.md)
- 🇪🇸 Probar un escenario: [docs/es/03_try_a_scenario.md](docs/es/03_try_a_scenario.md)

**Go deeper (workflow / simulator):**
- 🇬🇧 Workflow: [v1_core/workflow/README.md](v1_core/workflow/README.md)
- 🇪🇸 Workflow (ES): [v1_core/workflow/es/README.md](v1_core/workflow/es/README.md)

---

## Why this project exists
Modern diplomatic and institutional systems often fail not because of lack of intelligence, but because of:
- misaligned incentives,
- short-term optics overriding long-term stability,
- absence of early correction mechanisms,
- ignored historical recurrence.

HUB_Optimus exists to **break that cycle** by evaluating scenarios **before** decisions become irreversible.

---

## Core principles (high-level)
- **Stability over optics**  
  Medium/long-term systemic stability is the supreme criterion.

- **Integrity first**  
  Influence over the core is earned through ethical coherence, not position or credentials.

- **Evaluation over narrative**  
  Outcomes are assessed structurally (incentives, verification, sequencing), not rhetorically.

- **Prevention over reaction**  
  Early, discreet mediation is preferred to public escalation.

- **No scapegoating**  
  Errors are treated as systemic, not personal.

---

## Repository map
- `docs/` → onboarding and reading paths (recommended entry point)
- `v1_core/` → active kernel: architecture, operational flow, workflow, templates, scenarios, meta-learning
- `docs/architecture/runtime_contract.md` → full technical contract (schema, runtime, CI, encoding)
- `legacy/` → historical/exploratory materials (v0), preserved for transparency

> Source-of-truth policy is defined in `docs/context/STATUS.md`: `v1_core/languages/es/` is canonical and `v1_core/languages/en/` is parity reference.

---

## The simulator

**Current prototype** (`hub_optimus_simulator.py` + `run_scenario.py`):
- loads and validates scenario files against a JSON schema,
- runs round-based negotiation with configurable actors and policies,
- checks simple offer-based success criteria,
- produces a deterministic JSON report (`status`, `rounds`, `history`, `detail`).

**Framework design objectives** (not yet implemented in the runtime):
- evaluate incentive alignment and sequencing,
- classify long-term stability risk,
- detect false successes (agreements that appear to succeed but carry systemic instability),
- propose non-coercive corrective options,
- support iterative meta-learning from historical scenario outcomes.

It **does not predict outcomes**. The current runtime evaluates whether a simple configurable condition is met. The broader **structural evaluation** capabilities are part of the project vision described in the governance and methodology documents.

Start here:
- [v1_core/workflow/README.md](v1_core/workflow/README.md)

---

## Contributing
See: [CONTRIBUTING.md](CONTRIBUTING.md)  
Link-checking is enforced via GitHub Actions (Lychee).

---

## Contact / Collaboration
If you want to collaborate (scenarios, methodology, review), open an issue or pull request including:
- intended use-case (training / policy review / research),
- target domain,
- constraints (time, verification, actors),
- desired outcome type (stabilizing / risk-reducing / de-escalatory).
