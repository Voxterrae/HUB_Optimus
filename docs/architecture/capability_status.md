# Evidence-backed capability status

This ledger describes repository evidence at commit
`df0ef345e5ac627f3e2735573c802fe2f60821f4`, verified on 2026-07-29.
The machine-readable baseline, terminal-PR snapshot, external unknowns, and
reproduction commands are versioned in
[`capability_evidence.v1.json`](capability_evidence.v1.json).

This is a derived repository-tree snapshot. It is not a roadmap, deployment or
repository-settings attestation, release designation, legal conclusion,
scientific validation, professional translation review, or statement about
later GitHub activity. Apply the
[source-of-truth hierarchy](../context/SOURCE_OF_TRUTH.md) before using it.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| Active document | Versioned project or governance text exists; this is not runtime behavior. |
| Implemented | Versioned code and executable tests cover the stated narrow behavior on the baseline. |
| Prototype | Executable code and tests exist, but the surface is local, limited, or not release-attested. |
| Experimental | Research tooling and tests exist; outputs remain synthetic observations. |
| Partial | Some bounded pieces are evidenced, but the wider surface is incomplete or unverified. |
| Draft / RFC | Proposal text exists and authorizes nothing by itself. |
| Not implemented | The baseline contains no implementation evidence for the stated capability. |
| External / unresolved | The fact depends on mutable GitHub state, another repository, a deployment, settings, or professional review outside this commit. |

## Ledger

| Capability or surface | Status | Versioned or executable evidence | Verified boundary or unresolved gap |
| --- | --- | --- | --- |
| Normative governance documents | Active document | `docs/governance/KERNEL.md`; `docs/governance/CHARTER.md`; `docs/governance/CONSENSUS_PROCESS.md`; `docs/governance/TRUST_LAYER.md` | Human project rules, not executable code, AI authority, or legal authority. Proposed amendment mechanics are absent from this baseline; the current lifecycle of PR #1773 is external and unresolved here. |
| Canonical v1 methodology | Active document | `docs/context/STATUS.md`; `v1_core/languages/es/`; `tests/test_core_es_en_parity_matrix.py` | Spanish v1 is canonical and English is a parity target. The methodology is broader than the simulator. |
| Scenario JSON validation and CLI error contract | Implemented | `scenario.schema.json`; `run_scenario.py`; `tests/test_run_scenario_cli.py`; `tests/test_regression_runner.py`; `tests/test_scenario_loading.py` | One authoritative loader rejects non-standard JSON constants and duplicate actor names and exposes controlled parse/input/schema categories to repository tools. It validates structure and identity, not real-world truth or policy quality. |
| Round-based scenario simulator | Prototype | `hub_optimus_simulator.py`; `tests/test_simulator_isolation.py`; `benchmarks/scenarios/`; `benchmarks/expected/` | Isolated seeded runs, clean per-run history, result snapshots, simple policies, rounds, and exact offer matching are tested. Synthetic behavior is not diplomacy, prediction, or causal evidence. |
| Frozen runtime benchmarks | Implemented | `benchmarks/run_benchmarks.py`; `benchmarks/expected/`; `python benchmarks/run_benchmarks.py` | Three seed-42 outputs are compared byte for byte. The workflow benchmark job remains advisory through `continue-on-error: true`. |
| Scenario generator, mutator, telemetry, boundary, and frontier tools | Experimental | `tools/scenario_generator/`; `tools/scenario_mutator.py`; `tools/scenario_telemetry.py`; `tools/scenario_boundary_search.py`; `tests/test_scenario_mutator.py`; `tests/test_scenario_telemetry.py`; `docs/lab_regeneration_1775.md` | Mutator base selection and telemetry now reuse the authoritative scenario loader, including strict JSON, schema, and actor-identity boundaries. Generation manifests and complete non-monotonic boundary enumeration are tested. Results remain synthetic and do not establish policy quality, generalization, or prediction. |
| Semantic Engine contracts and CLI | Prototype | `semantic_engine/contracts/`; `semantic_engine/cli/`; `tests/semantic_engine/test_case_input_validation.py`; `tests/semantic_engine/test_cli_smoke.py` | `CaseInput v1` structural and cross-reference integrity is enforced. File decoding rejects nested `NaN`/infinities and serialization fails closed on non-finite values. The CLI is not a claim evaluator, scorer, model judge, autonomous analyst, or public service. |
| Operator browser/PWA | Prototype | `site/operator/`; `tests/test_operator_pwa_product_actions.py`; `tests/test_operator_pwa_record_integrity.py` | Browser intake has one canonical source state and prepares local drafts. Browser output is not automatically verified evidence or Semantic Engine output. |
| Controlled single-URL intake | Partial | `docs/rfc/operator_controlled_url_intake.md`; `ops/ec2/controlled_url_intake.v1.schema.json`; `ops/ec2/hub-api.sh`; `tests/test_hub_api_controlled_url_intake.py`; `tests/test_operator_pwa_product_actions.py` | The contract accepts one URL, enforces documented size/network/redirect limits, and uses strict JSON request/result/response boundaries. It records unreviewed provenance; it does not crawl, verify truth, or prove that an endpoint is deployed. |
| Raw mobile intake CLI | Prototype | `tools/mobile_ingest.py`; `tests/test_mobile_ingest.py`; `.gitignore` | Default raw intake is local and ignored, with tested path and file-safety checks. It provides no encryption, managed retention, truth verification, publication, or multi-writer guarantee. |
| Narrative-risk datasets and consistency checks | Implemented | `datasets/ai_risk_narratives/`; `datasets/geopolitical_claim_packs/`; `tests/test_ai_risk_narratives.py`; `tests/test_narrative_consistency.py`; `python benchmarks/run_narrative_benchmarks.py` | Deterministic schema, taxonomy, renderer, and frozen-output checks only. Seed transcripts remain provisional where source images are absent; passing checks do not verify claims or motives. |
| Multilingual documentation structure | Partial | `docs/context/STATUS.md`; `docs/i18n/maturity.v1.json`; `tests/test_i18n_maturity.py` | The manifest distinguishes canonical, parity, review-needed, machine draft, stub, and missing states at a revision. File presence and a green audit do not establish linguistic quality or professional review. |
| Static public site and PWA shell | Prototype | `site/`; `site/assets/geo/land-110m.geojson`; `site/assets/geo/land-110m.geojson.sha256`; `tests/test_public_portfolio.py`; `.github/workflows/pages.yml` | Repository code includes a tested WebGL globe, accessible fallback, multilingual public claims, Operator, and Pages workflow. Public availability, served bytes, custom-domain state, and Pages configuration are external. |
| Local EC2 operational scripts | Prototype | `ops/ec2/`; `tests/test_ec2_run_identity_and_provenance.py`; `tests/test_ec2_deploy_hub_api_sync.py`; `tests/test_ec2_operator_api_proxy_config.py` | Run identity, explicit deployment provenance, rollback records, and API synchronization are tested in isolated fixtures. No live host, availability, restart, security posture, or provider commitment is attested. |
| Repository workflow source | Implemented | `.github/workflows/`; `tests/test_workflow_action_pins.py`; `tests/test_kernel_guard.py`; `tests/test_repo_maintenance_workflow.py`; `tests/test_repo_health_summary_workflow.py` | External Actions are pinned and scheduled maintenance is read-only. Repository-health source requests exhaustive PR/issue counts through its stated 10,000-item ceiling, fails closed on incomplete data, and labels the top-author field as a last-100-PR sample. Tests do not attest a hosted run. |
| Governance Intelligence protocol | Active document | `docs/governance/GOVERNANCE_INTELLIGENCE.md`; commit `e82998079340f63807e506f6bd7a07ce5b184eee` (PR #1695) | The versioned protocol keeps human accountability mandatory. It creates no AI authority, legal authority, or autonomous ratification path. |
| RFC lifecycle registry | Implemented | `docs/rfc/registry.v1.json`; `tests/test_rfc_registry.py` | Machine-checkable lifecycle metadata and evidence paths exist. The registry cannot ratify proposals and its external PR state must be refreshed explicitly. |
| HERMES PWA | Draft / RFC | `docs/rfc/hermes_pwa_interface_boundary.md`; `docs/rfc/hermes_pwa_gate_issue_pack.md` | No HERMES app, authentication, billing, dashboard, or public Semantic Engine API is implemented. |
| Post-quantum control plane | Draft / RFC | `docs/rfc/post_quantum_control_plane.md` | No ML-KEM exchange, ML-DSA/SLH-DSA signing, key management, node identity, quorum access, or production security claim is implemented. |
| Enterprise product | Draft / RFC | `docs/rfc/enterprise_boundary.md` | No accepted enterprise decision, customer configuration, billing, launch, or deployment evidence is recorded. |
| Professional non-canonical translation parity | Not implemented | `docs/i18n/maturity.v1.json`; `tests/test_i18n_maturity.py`; external item `professional-translation-review` in `capability_evidence.v1.json` | The baseline contains no named qualified human reviewer record certifying professional parity. Automated audits cannot supply it. |
| Public remote Semantic Engine or autonomous analysis | Not implemented | `semantic_engine/cli/`; `docs/architecture/semantic_engine_cli.md`; public-deployment external item in `capability_evidence.v1.json` | No baseline evidence supports a public engine, autonomous conclusions, truth verdicts, predictive authority, or human-replacing governance. |
| Public deployment and GitHub repository settings | External / unresolved | External items `public-deployment`, `repository-settings`, and `release-state` in `capability_evidence.v1.json` | Source, tests, workflows, local tags, and prior observations do not certify current deployment bytes, availability, GitHub settings, or the current Release object. |
| Hosted repository-health execution | External / unresolved | External item `repository-health-hosted-run` in `capability_evidence.v1.json` | The updated workflow revision has source and isolated contract tests; this baseline does not prove that GitHub Actions executed it or published a complete live summary. |
| `Voxterrae/HUB-Optimus-labs` artifacts | External / unresolved | External item `labs-repository` in `capability_evidence.v1.json` | Another repository's current contents and releases are outside this baseline. No positive or negative capability claim is inferred. |

## Reproduction

The snapshot records these commands without claiming that command text is a
passing result:

```bash
python -m pytest -q
python benchmarks/run_benchmarks.py
python benchmarks/run_narrative_benchmarks.py
python tools/check_mojibake.py .
```

Validation results belong to the reviewed PR/commit and its GitHub Checks.
PowerShell behavior requires the dedicated CI job with PowerShell 7; local
skips are not certification.

## Interpretation rule

When project prose and executable evidence differ, describe both and keep the
narrower claim. A test proves only the behavior it asserts. A merged RFC proves
that proposal text is versioned, not accepted. A deployment, GitHub setting,
Release object, Pull Request lifecycle, professional review, or other
repository requires direct external evidence at a stated time.
