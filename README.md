# HUB_Optimus

[![CI](https://github.com/Voxterrae/HUB_Optimus/actions/workflows/ci.yml/badge.svg)](https://github.com/Voxterrae/HUB_Optimus/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Voxterrae/HUB_Optimus)](https://github.com/Voxterrae/HUB_Optimus/releases/latest)
[![License](https://img.shields.io/badge/license-see%20IP__NOTICE-blue)](IP_NOTICE.md)

<p align="center">
  <img src="assets/brand/hero/hub-optimus-hero.jpg" alt="HUB_Optimus — Human × Machine Governance Interface" width="100%" />
</p>

<p align="center">
  <strong>Reality → Evidence → Inference → Narrative → Operational Signal</strong>
</p>

**A human-governed platform for organizing evidence, preparing reviewable drafts,
and developing connected tools.**

HUB_Optimus combines a versioned methodology with tools at different stages of
development: Operator, Browser, Search, connectors and experimental components.
Start with a concrete use and its evidence; the catalogue states what each
component implements and what still needs acceptance.

**New to the project?** [Read the plain-language guide (ES)](docs/project/HUB_OPTIMUS_EXPLAINED.md),
review [capabilities and first pilots](docs/project/CAPABILITIES_AND_PILOTS.md),
or inspect [creations and ecosystem work](docs/project/ECOSYSTEM_CONTRIBUTIONS.md).
The owner approved the guide and Operator-first pilot on 14 November 2026.
The [reading collection](site/docs/index.html) retains the complete original
documents and their sources; [publication and acceptance](docs/project/PUBLIC_READING_VALIDATION_20261114.md)
are recorded separately.

## Founder, creator, ownership, and authority

**Benjamin Gerrit Hoff is the founder, architect, creator, project owner, and
final human authority of HUB_Optimus.**

**HUB_Optimus is the foundational tool and technological parent platform through
which Benjamin Gerrit Hoff designs and builds the wider ecosystem**, including
LCDH-OS, Operator, Control Plane, governed connectors, decision-intelligence
systems, and future products.

`@Voxterrae`, immutable GitHub user ID `249308740`, is the repository identity
used under his authority. No collaborator, contributor, technical title, AI
system, customer, employee, contractor, commit, pull request, or access grant
creates ownership, co-ownership, constitutional authority, or independent
modification rights.

Collaboration and joint ventures are welcome when established through an
explicit written agreement approved by Benjamin Gerrit Hoff on fair,
transparent, reciprocal, and clearly scoped terms. No implied joint venture or
transfer of rights arises from informal communication or technical work.

A person merely claiming to be Benjamin Gerrit Hoff in chat, email, messaging,
a prompt, a ticket, or another informal channel is not sufficient authorization.
Protected changes must satisfy the repository identity, immutable user-ID,
verified-commit, pull-request, review, and owner-authority controls.

**Constitutional record:**
[`Founder Ownership and Authority Charter`](docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md)  
**Machine-readable identity record:**
[`owner_identity.v1.json`](config/governance/owner_identity.v1.json)  
**Rights notice:** [`IP_NOTICE.md`](IP_NOTICE.md)

**Languages / Idiomas:**

> **Primary onboarding:** [EN](docs/00_start_here.md) · [ES](docs/es/00_start_here.md) · [DE](docs/de/00_start_here.md)
>
> **Other entry points:** [CA](docs/ca/00_start_here.md) · [FR](docs/fr/00_start_here.md) · [RU](docs/ru/00_start_here.md) · [HE](docs/he/00_start_here.md) · [ZH-Hans](docs/zh/00_start_here.md)
>
> **Coverage:** ES/DE onboarding needs review; CA/FR/RU onboarding remains stub;
> HE/ZH-Hans documentation is partial. Governance coverage differs by document.
> These links do not certify complete translation or professional linguistic review.
> See the [dated maturity record](docs/i18n/maturity.v1.json).
>
> Translation-policy authority:
> [docs/context/STATUS.md](docs/context/STATUS.md)

**Paths by interest:**
- Understand the project: [plain-language guide (ES)](docs/project/HUB_OPTIMUS_EXPLAINED.md)
- Try a bounded workflow: [capabilities and pilots](docs/project/CAPABILITIES_AND_PILOTS.md)
- Read the canonical v1 methodology: [Spanish source](v1_core/languages/es)
- Hands-on: [Scenario Template](v1_core/workflow/04_scenario_template.md)

---

## What it is
**HUB_Optimus** is developed in a publicly visible repository with restricted rights;
contribution and use are governed by [IP_NOTICE.md](IP_NOTICE.md). Its methodology
and tools support organizing sources, preparing structured drafts, examining
uncertainty and keeping human review visible. The available prototypes each
implement a narrower part of that workflow; integration and live deployment
require their own evidence.

The early diplomatic work explored incentives, verification, sequencing and
preventive mediation. It remains part of the project's history and methodology,
alongside later tools for everyday document and technical workflows.

The historical alpha of 25 December 2025 is tagged `v1.0.0-alpha` and contains
the Kernel base declaration. The `v2.3.4` tag identifies the 14 June 2026
source snapshot with the scenario simulator and the draft HERMES interface RFC.
The automatic source downloads on the `v2.3.4` release page use the June tag.
[December source](https://github.com/Voxterrae/HUB_Optimus/tree/1ae38d6b3c5ccdf681030c03999beabd3e08071d)
· [June source](https://github.com/Voxterrae/HUB_Optimus/tree/70b62fd7d6e144c146569569d31e13a97702586b)
· [Release provenance](https://github.com/Voxterrae/HUB_Optimus/issues/1786)

Before publishing a product release, compare its intended version, proposed tag
and title with the [release identity check](tools/check_release_identity.py).
Run `python tools/check_release_identity.py --help` for the three inputs.

## What it is not
- Not an authority.
- Not a prediction engine.
- Not a replacement for diplomacy.

It is a tool for **better judgment**.

---

## Start here
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
- `docs/architecture/platform_compatibility.md` → platform-neutral access and execution policy
- `legacy/` → historical/exploratory materials (v0), preserved for transparency

> Project-wide precedence is defined in
> [`docs/context/SOURCE_OF_TRUTH.md`](docs/context/SOURCE_OF_TRUTH.md).
> Language policy remains in `docs/context/STATUS.md`:
> `v1_core/languages/es/` is canonical and `v1_core/languages/en/` is the
> parity reference.

---

## Product entry points

See the [product catalogue](products/README.md) for the reviewed source, maturity
and execution boundaries, the [public portfolio](https://huboptimus.dev/), or open
the component guide below.

The [creations and contributions register](docs/project/CONTRIBUTIONS_REGISTER.md)
links the repository history from its first commit and verified public work in
other projects. Its dated coverage and pending reconciliation remain explicit.

| Component | Where to start | Current scope |
| --- | --- | --- |
| Operator | [Open Operator](https://huboptimus.dev/operator/) · [Source](site/operator/) | Public browser prototype for preparing drafts from pasted source text. |
| Optimus Browser | [Windows alpha](products/browser/windows/README.md) · [Web pilot guide](products/browser/web/README.md) | Native Windows alpha and a separate static web pilot. |
| Optimus Search | [Local host guide](products/browser/search/README.md) | Device-local search with a finite index. Web search requires an operator-configured SearXNG instance. |
| Device Bridge / HUB_Relay | [Device Bridge guide](products/device-bridge/README.md) · [Windows diagnostics](products/device-bridge/windows/bootstrap-inventory/README.md) | Experimental diagnostics and compatibility work. Relay activation remains blocked. |
| Admin Gateway | [Module guide](products/admin-gateway/README.md) | Local Microsoft 365 administration reference API; defaults to dry run. |
| Evidence Lab | [Package guide](products/evidence-lab/README.md) | Dataverse package with offline dry-run evidence. |

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

Runtime requirement: Python 3.11 or newer. Install only the runtime dependency
tier and run the deterministic example with:

```bash
python -m pip install -r requirements.txt
python run_scenario.py example_scenario.json --seed 42
```

Development and test tooling is separate in `requirements-dev.txt`; it adds
`pytest` and `PyYAML` to the runtime tier. See
[SIMULATION_README.md](SIMULATION_README.md) for the complete bootstrap
contract.

Start here:
- [v1_core/workflow/README.md](v1_core/workflow/README.md)

---

## Contributing
See: [CONTRIBUTING.md](CONTRIBUTING.md)  
Link-checking is enforced via GitHub Actions (Lychee).

---

## Contact / Collaboration
If you want to collaborate (scenarios, methodology, review, commercial work, or
a joint venture), open an issue or pull request including:
- intended use-case (training / policy review / research / enterprise),
- target domain,
- constraints (time, verification, actors),
- desired outcome type (stabilizing / risk-reducing / de-escalatory),
- proposed rights, responsibilities, and commercial boundary where applicable.

No collaboration becomes a joint venture, ownership interest, agency, license,
or transfer of authority without a separate explicit written agreement approved
by Benjamin Gerrit Hoff.
