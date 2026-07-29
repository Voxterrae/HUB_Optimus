# Evidence-backed capability status

This ledger describes repository evidence at commit
`3ef199305c2d2d114f88aceb97b65a08b9f91b4a`, verified on 2026-07-28.
It is not a roadmap, deployment attestation, legal conclusion, scientific
validation, or approval of any draft PR.

Pending PRs are named only as review context. Their changes are not part of
this baseline until humans review and merge them.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| Active document | Versioned project/governance text exists; this is not runtime behavior. |
| Implemented | Code and tests for the stated narrow behavior exist on the baseline. |
| Prototype | Executable code exists, but the surface is local, limited, or not release-attested. |
| Experimental | Research tooling exists; outputs are synthetic observations and known defects may remain. |
| Partial | Some required pieces exist, but the stated surface is incomplete or unverified. |
| Draft / RFC | Proposal text exists and authorizes nothing by itself. |
| Not implemented | No baseline implementation evidence was found. |
| External state | The fact depends on a repository, deployment, or setting outside this commit. |

## Ledger

| Capability or surface | Status | Baseline evidence | Verified boundary or open gap |
| --- | --- | --- | --- |
| Normative governance documents | Active document | `docs/governance/KERNEL.md`; `CHARTER.md`; `CONSENSUS_PROCESS.md`; `TRUST_LAYER.md` | These are human project rules, not executable code or legal authority. Current amendment language is not fully mechanical; issue #1751 and draft PR #1773 propose clarification but are not active governance. |
| Canonical v1 methodology | Active document | `docs/context/STATUS.md`; `v1_core/languages/es/`; `v1_core/languages/en/` | Spanish v1 wins on conflict; English is the parity target. Methodology claims are broader than the current simulator. |
| Scenario JSON validation and CLI error contract | Implemented | `scenario.schema.json`; `run_scenario.py`; `tests/test_run_scenario_cli.py`; `tests/test_regression_runner.py` | Validates a narrow scenario contract and returns deterministic JSON. It does not assess real-world truth or policy quality. |
| Round-based scenario simulator | Prototype | `hub_optimus_simulator.py`; `run_scenario.py`; `benchmarks/scenarios/` | Implements actors, simple policies, exact offer-threshold success, rounds, and history. Repeat-run/global-RNG isolation defect is tracked in #1755; draft #1770 is not in the baseline. |
| Frozen runtime benchmarks | Implemented | `benchmarks/run_benchmarks.py`; `benchmarks/expected/`; `.github/workflows/ci.yml` | Byte-level and structural drift checks exist. The CI benchmark step is advisory (`continue-on-error`) on this baseline. |
| Scenario generator, mutator, telemetry, boundary and frontier tools | Experimental | `tools/scenario_generator/`; `tools/scenario_mutator.py`; `tools/scenario_telemetry.py`; `tools/scenario_boundary_search.py`; `tools/scenario_frontier.py` | Synthetic laboratory tools, not real-world predictors. Known corrections are separately proposed in #1771, #1774, and stacked #1779; evidence regeneration is tracked in #1775. |
| Semantic Engine contracts and CLI | Prototype | `semantic_engine/contracts/`; `semantic_engine/cli/`; `tests/semantic_engine/` | Minimal deterministic record assembly exists. It is not a claim evaluator, scorer, model judge, autonomous analyst, or public service. Strict shared input validation is proposed in draft #1778. |
| Operator browser/PWA | Prototype | `site/operator/`; `tests/test_operator_pwa_product_actions.py`; `tests/test_operator_pwa_record_integrity.py` | Local/browser intake and draft preparation exist. Browser output is not Semantic Engine output. The repository-truth redesign remains draft #1737. |
| Controlled single-URL intake | Partial | `ops/ec2/hub-api.sh`; `site/operator/index.html`; `tests/test_hub_api_controlled_url_intake.py`; PRs #1717 and #1720 | A local/private endpoint and browser fallback exist. No crawling, truth verification, or public deployment is established. Invalid-port and DNS connection-boundary work remains issue #1761. |
| Raw mobile intake CLI | Prototype | `tools/mobile_ingest.py` | Captures local text; the baseline default can expose raw intake to accidental version control. Private-by-default storage is proposed in draft #1777. |
| Narrative-risk datasets and consistency checks | Implemented | `datasets/ai_risk_narratives/`; `datasets/geopolitical_claim_packs/`; `tools/check_narrative_consistency.py`; related tests | Deterministic schema/taxonomy consistency only. Passing checks do not verify claims, sources, motives, legality, or truth. |
| Multilingual documentation structure | Partial | `docs/context/STATUS.md`; locale directories under `docs/` | File presence is not linguistic quality. RU is progressive; HE and current Chinese (`docs/zh`, intended as `zh-Hans`) are stubs/progressive copies. No professional parity is certified; draft #1772 proposes a versioned maturity audit. |
| Static public site and PWA shell | Prototype | `site/`; `.github/workflows/pages.yml`; site tests | Static assets and a Pages workflow exist. The current production-domain content and private GitHub Pages settings are external state; the replacement portfolio is draft #1737. |
| Local EC2 operational scripts | Prototype | `ops/ec2/`; `scripts/infra/bootstrap_aws_dev_runtime.sh`; ops tests | Provider-specific scripts exist. Their presence does not prove a live deployment, security posture, availability, or an architectural commitment to AWS. No Azure migration is approved or implemented. |
| CI, link check, PR Safety and Kernel Guard workflows | Implemented | `.github/workflows/`; `tools/kernel_guard.py` | Workflow code exists. Protected-branch, required-review, Secret Scanning, Push Protection, HTTPS and ruleset settings remain external/unverified under #1743. Hardening changes remain drafts #1744–#1746. |
| Governance Intelligence protocol | Active document | `docs/governance/GOVERNANCE_INTELLIGENCE.md`; issue #1694; PR #1695 as recorded in the document | The repository declares this protocol ratified. It keeps human accountability mandatory and creates no AI authority or legal authority. |
| RFC lifecycle registry | Implemented | `docs/rfc/registry.v1.json`; `tests/test_rfc_registry.py` | Tracks evidence and missing records. It cannot ratify proposals and must be refreshed when RFC metadata changes. |
| HERMES PWA | Draft / RFC | `docs/rfc/hermes_pwa_interface_boundary.md`; `docs/rfc/hermes_pwa_gate_issue_pack.md` | No HERMES app, authentication, billing, dashboard, or public Semantic Engine API is implemented. |
| Post-quantum control plane | Draft / RFC | `docs/rfc/post_quantum_control_plane.md` | No ML-KEM exchange, ML-DSA/SLH-DSA signing, key management, node identity, quorum access, or production security claim is implemented. |
| Enterprise product | Draft / RFC | `docs/rfc/enterprise_boundary.md` | No accepted enterprise decision, product, customer configuration, billing, launch, or deployment evidence is recorded. |
| Professional RU / HE / zh-Hans parity | Not implemented | `docs/context/STATUS.md`; locale files | Native/qualified human review records are absent. Automated structure checks cannot supply them. |
| Public remote Semantic Engine or autonomous analysis | Not implemented | Semantic CLI and local ops boundaries above | No evidence supports a public engine, autonomous conclusions, truth verdicts, predictive authority, or human-replacing governance. |
| `Voxterrae/HUB-Optimus-labs` artifacts | External state | [HUB-Optimus-labs](https://github.com/Voxterrae/HUB-Optimus-labs) | GitHub reported the official public repository at size 0 on 2026-07-28. It is part of the portfolio as an incubation location, but contributes no released artifact or capability yet. |

## Interpretation rule

When project prose and executable evidence differ, describe both and keep the
narrower claim. A test proves only the behavior it asserts. A merged RFC proves
that proposal text is versioned, not that it was accepted. An external
deployment or repository setting requires fresh external evidence.
