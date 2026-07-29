# HUB_Optimus AI Handoff

This file records operational handoff state for ChatGPT/Codex repo execution.
GitHub remains the source of truth; chat summaries are advisory unless reflected in issues, PRs, commits, or repo docs.

## Operating Discipline

- Release: use GitHub Releases as source of truth.
- Current branch and active assignment: use the active GitHub issue or PR.
- CI status: use GitHub Checks on the active PR as source of truth.
- Default loop: observe -> detect -> decide -> act.
- Default rule: no build without signal.

## Current Constraints

- No big rewrites.
- No roadmap edits without RFC or approved issue.
- Runtime contract must remain stable unless explicitly scoped.
- Small PRs only.
- Keep source-of-truth conflicts resolved by `docs/context/STATUS.md`.

## PowerShell Tooling Boundary

- Mutation-capable PowerShell utilities are preview-only unless the operator
  supplies `-Apply`.
- They are limited to Git-tracked, non-link paths inside the detected repository.
- Their current support status is provisional/manual and requires PowerShell 7
  plus Git.
- The dedicated `PowerShell tooling` CI job must fail when `pwsh` 7 is missing
  and must execute the temporary-repository behavior tests. Local or generic
  pytest runs without `pwsh` report those tests as skipped; a skip is not
  certification.
- Do not describe PowerShell behavior as CI-verified from repository code or a
  local result alone. Only a green dedicated job on the reviewed PR is evidence
  for the behavior covered on its Ubuntu runner; Windows and macOS remain
  unverified by that job.

## Human Stewardship and Technical Review Boundary

- Benjamin Gerrit Hoff is the creator, project owner, primary human steward, and final human-accountability layer of HUB_Optimus.
- `@Voxterrae` is the GitHub repository identity used for administration under that human authority.
- Rodrigo / `@itteamrod` is the trusted Core Technical Steward of HUB_Optimus.
- The GitHub enforcement of Rodrigo's role remains limited to paths explicitly assigned in `.github/CODEOWNERS` and requires Write collaborator access.
- Core Technical Stewardship does not imply project co-ownership, final human accountability, constitutional governance ownership, or unilateral repository-settings authority.
- AI operators must read `docs/governance/PROJECT_STEWARDSHIP.md` and must not infer authority beyond versioned GitHub records.
- Foundational principle: technology amplifies human judgment; it never replaces human responsibility.

## Governance Intelligence Boundary

Issue #1694 and PR #1695 are the ratification record for the canonical Governance Intelligence protocol.

Operational boundary:

- The canonical protocol lives at `docs/governance/GOVERNANCE_INTELLIGENCE.md` and is active through the reviewed merge record of PR #1695.
- Governance Intelligence requires explicit separation of claim, evidence, inference, uncertainty, narrative amplification, and operational relevance.
- Chat messages, hidden prompts, conversation memory, model output, and external AI reviews remain advisory until represented in versioned GitHub artifacts.
- No model family, model version, provider, or hidden control path may ratify governance, override repository evidence, approve its own work, or merge its own governance change.
- Model capability may improve analytical depth; it does not increase governance authority.
- Human accountability remains mandatory for ratification, publication, escalation, and sensitive use.
- `docs/rfc/constitutional_governance_ai_regulatory_boundary.md` remains a separate Draft RFC and is not accepted or superseded by this ratification.

## Handoff Update Discipline

Update this file only when the scoped issue or PR changes operational handoff state, including:

- operational state
- active priorities
- architecture
- governance posture
- runtime, CI, or benchmark posture
- contributor handoff requirements

Do not update this file for narrowly scoped translation, typo, link, formatting, or parity-only PRs unless the issue or PR explicitly requires it.

If this file is not updated, say why in the PR body.

## Current Recommended Action

Return to controlled observation. Act only when a new regression, architecture ambiguity, contributor friction, documentation drift, CI/runtime signal, governance risk, or explicit user request is recorded in GitHub.

## PR Enrichment Helper Boundary

Issue #1762 keeps `tools/pr_pro.py` as a supported, optional helper for an
existing PR. It is not a PR creator, merge authority, or authentication
provider.

Operational boundary:

- Write mode requires an existing PR target and the GitHub CLI.
- The helper uses the caller's existing authentication and scopes; it does
  not create, persist, exchange, or expand tokens.
- Failed GitHub or required local diff commands return non-zero and cannot
  emit the success status.
- `--dry-run` invokes no GitHub commands and performs no GitHub mutation.
- The active workflow file, not this helper or chat context, determines
  whether scheduled maintenance invokes it.

## EC2 Run Identity and Deployment Provenance Boundary

Issue #1764 scopes the manually installed `ops/ec2` layer:

- each `hub-core` operation creates its run directory exclusively, using a UTC
  timestamp plus a random suffix, and emits that exact run ID;
- the local `/analyze` API uses a per-request mode-`0600` temporary input,
  removes it after execution, and binds its response to the run ID returned by
  its own `hub-core` process rather than a shared "latest" lookup;
- `deploy-current` requires one explicit full commit SHA or exact tag, resolves
  it to a full commit SHA, and never deploys implicit branch HEAD;
- deployment state records the actual validation command, exit code, result
  line, and log instead of a hard-coded test count;
- rollback verifies the target release against its recorded commit, restores
  that release's deployment state and launcher, and writes an explicit
  transition record;
- deploy and rollback share one fail-fast host lock; neither operation
  implicitly restarts the API service.

These scripts remain a manually installed EC2 backend layer. Repository tests
exercise their isolated contracts; only a reviewed deployment and runtime
inspection can attest the state of a real EC2 host.

## Python Packaging Boundary

Issue #1763 records drift between the documented Python minimum, executable
syntax, bootstrap checks, and the dependency files. The scoped correction
in PR #1776 establishes:

- supported Python is 3.11 or newer;
- `requirements.txt` is the runtime tier and contains `jsonschema`;
- `requirements-dev.txt` includes the runtime tier and adds `pytest` and
  `PyYAML`;
- `python scripts/bootstrap.py --runtime-only` installs/checks runtime
  dependencies and executes the supported scenario CLI smoke test;
- the default bootstrap remains the development path and fails when tests or
  frozen benchmarks fail rather than printing an ambiguous ready state.

The dependency check enumerates all three direct packages in the development
tier. `PyYAML` is verified by distribution name and by its importable `yaml`
module, so `--check` cannot report a ready development environment while that
declared dependency is absent.

The runtime-only install path has been verified in a newly created virtual
environment without development requirements.

## Maintenance Drift Boundary

Issue #1788 replaces branch-producing scheduled maintenance with a read-only
drift check on trusted `main`.

Operational boundary:

- the scheduled workflow has only `contents: read` permission and persists no
  checkout credentials;
- it creates no GitHub App token, commit, branch, pull request, or remote ref;
- the legacy maintenance helper runs only inside an isolated copy of committed
  `HEAD`;
- proposed changes fail the check and appear in the GitHub Actions step
  summary; they are never applied to the source checkout;
- retiring historical maintenance branches remains a separate audited action
  and is not authorized or performed by the scheduled drift check;
- the 881 numbered candidates and six semantic exclusions are fixed in
  `docs/maintenance/issue-1788/maintenance-branches.manifest.v1.json`;
- their standalone, complete-history recovery bundle is versioned beside the
  manifest and is verified by SHA-256, empty-repository restore, exact refs,
  commit metadata, cutoff, and strict `git fsck`;
- `.github/workflows/retire-maintenance-branches.yml` is manual-only and
  defaults to a `contents: read` dry-run; merge or schedule cannot activate it;
- execution requires an exact current `main` SHA and confirmation sentence,
  refreshes GitHub REST, open-PR, protection, and Git ref state, and permits
  only one atomic deletion push with an exact lease for every candidate;
- there is no batch or non-atomic fallback, and postflight records counts only
  after all candidates are absent and pre-existing non-candidates are intact;
- merging the retirement package does not execute or authorize the destructive
  mode. A maintainer must review a fresh dry-run and explicitly dispatch it.

## Repository Health Count Boundary

Issue #1806 keeps the weekly repository-health summary exhaustive within an
explicit, fail-closed audit boundary.

Operational boundary:

- every PR or issue total used as a repository metric requests up to 10,001
  records, making counts through the documented 10,000-item ceiling exhaustive;
- a result beyond that ceiling, invalid JSON, or any failed GitHub CLI/API call
  stops the run before it can publish a partial or plausible-zero snapshot;
- remote branch refs are fetched once and a failed fetch is terminal;
- the established anomaly thresholds and `contents: read` / `issues: write`
  permissions remain unchanged;
- the top-author field remains an explicitly labelled last-100-PR sample and is
  not represented as an exhaustive repository count.

## Simulator Isolation Boundary

Issue #1755 records a verified mismatch between the runtime contract and the
simulation kernel: seeded runs used module-global random state, repeated runs
accumulated history, and previously returned results exposed the simulator's
mutable history.

PR #1770 restores the documented boundary:

- one run-local `random.Random` instance drives all built-in actor policies;
- seeded execution does not mutate caller-global random state;
- each `run()` starts with empty run history;
- returned history is a snapshot rather than live simulator state;
- changed seed-42 benchmark bytes are reviewed and frozen explicitly.

Issue #1775 regenerates the laboratory observations derived from the previous
random stream on commit
`af89e420efb7b60eb95867b840ebeaf23dd989b6`. The regenerated evidence,
commands, and hashes are recorded separately from the runtime correction in
`docs/lab_regeneration_1775.md`.

## Narrative-risk Contract Coverage Boundary

Issues #1546–#1549 and merged PRs #1550/#1555 define a narrative-risk lane
that remains separate from the scenario runtime.

Current evidence boundary:

- the claim schema owns the only stored closed risk-domain,
  verification-status, and evidence-tier vocabularies under `$defs`; direct
  Draft 2020-12 validation and the consistency checker reuse those exact
  definitions and reject unknown domains or missing required fields;
- the report renderer rejects missing `evidence` or `mitigation` before
  writing output;
- five byte-frozen narrative benchmarks include explicit `verified`, `mixed`,
  and `unsupported` handling;
- the 16-row screenshot-derived seed remains provisional because the source
  images are not stored in the repository;
- screenshot text remains dirty input requiring human review and is never
  promoted to repository truth by the dataset, renderer, or benchmarks;
- no narrative component imports or changes `run_scenario.py`,
  `hub_optimus_simulator.py`, or the scenario schema.

This evidence does not close the GitHub issues or provide human verification
of the source-image transcriptions. Issue state and any closure decision remain
explicit GitHub actions.

## Boundary Search Integrity Boundary

Issue #1754 and PR #1774 record that the laboratory boundary tool treated
non-monotonic observations as monotonic and could collapse runner errors into
ordinary failures. The scoped correction establishes:

- `rounds_min` retains binary search because a larger round budget preserves
  the deterministic execution prefix;
- `actors_min` enumerates actor counts 1–6 because actor count changes the
  random stream and role-sensitive policies can lose success at a larger
  count;
- `threshold_max` enumerates thresholds 1–5 because success checks exact
  equality and can fail between successful values;
- actor and threshold state maps are retained with seed, policy, and method
  provenance;
- runner or result errors are explicit probe errors, not failed simulations;
- verification re-enumerates each complete axis, including reported `None`
  extrema, rather than checking only an adjacent value.

The boundary section was regenerated from the isolated simulator in #1774.
Issue #1775 subsequently regenerates base telemetry, mutation, gradient,
frontier, and policy-comparison observations on the merged corrections.

## Scenario Input Integrity Boundary

Issue #1790 defines one authoritative external scenario-loading path:
`run_scenario.load_validated_scenario`.

Operational boundary:

- the decoder accepts standard JSON and rejects the non-standard constants
  `NaN`, `Infinity`, and `-Infinity`;
- `scenario.schema.json` remains the structural field contract;
- the authoritative loader additionally enforces unique actor names before
  runtime construction, preventing dictionary-key collapse in simulation
  history;
- the supported CLI and the retained `Scenario.from_json()` convenience
  method use that same loader and required-field behavior;
- `Scenario.from_json()` supplies no permissive defaults and claims no YAML
  support;
- direct construction of `Scenario` remains an internal data-container path
  for already validated or test-controlled values, not an external file
  loader.

These checks validate executable input integrity. They do not verify evidence,
real-world claims, policy quality, or predictions.

## Human and Executable Scenario Contract Boundary

Issue #1659 records that HUB_Optimus intentionally has two different scenario
contracts.

- `v1_core/workflow/04_scenario_template.md` is a rich human authoring and
  review workflow.
- `scenario.schema.json` plus the authoritative loader in `run_scenario.py`
  define the separate executable JSON input.
- Moving from the human workflow to executable JSON is a manual, lossy
  modelling decision. The repository provides no automatic converter.
- Only `title`, `description`, `roles`, `success_criteria`, and `max_rounds`
  exist in the executable document. Human metadata, timelines, interests,
  constraints, proposals, verification, risks, round agendas, post-mortem
  evaluation, and meta-learning have no current executable field.
- Mechanical JSON success uses any-actor/any-criterion matching. It is not the
  human definition of a verified, durable, stable, legitimate, or advisable
  outcome.
- `docs/governance/SCENARIO_SCHEMA.md` is the canonical field mapping for this
  governance surface. Its German, Spanish, Catalan, French, and Russian
  mirrors remain `review-needed`; Hebrew and Simplified Chinese remain `stub`.
  No mirror gains professional-review or parity status from this documentation
  update.

This clarification changes no runtime, schema, simulator, benchmark, or CI
behavior.

## Telemetry Input Boundary

Issue #1757 records that malformed scenario files could crash telemetry or
be subtracted from multiple aggregate categories. The scoped correction
in PR #1771 restores the following behavior:

- every discovered input receives exactly one processing outcome:
  `agreement`, `no_agreement`, `parse_error`, `schema_error`, or
  `runtime_error`;
- malformed JSON roots, invalid UTF-8, schema errors, and runner-output
  errors are recorded per file without stopping safe collection;
- aggregate counts remain non-negative and sum to the discovered total;
- exit `0` means complete collection, exit `2` means outputs were written
  with one or more partial data errors, and exit `1` means fatal setup or
  output failure;
- the canonical generated seed-42 set is 60/60 runtime-complete with
  39 agreements, 21 no-agreements, and average convergence round 2.26 after
  the issue-#1775 regeneration on commit `af89e420`.

## Canonical Scenario Tool Boundary

Issue #1804 removes independent permissive scenario parsing from telemetry and
mutation input selection.

Operational boundary:

- `run_scenario.load_validated_scenario` remains the one external-file boundary
  for standard JSON parsing, structural schema validation, and actor-identity
  validation;
- controlled loader errors expose stable categories and codes without changing
  the supported CLI's exit status or message prefixes;
- telemetry classifies non-standard JSON constants and non-object roots as
  parse errors, invalid UTF-8 as an input parse failure, and structural or
  actor-identity failures as schema errors;
- manifested telemetry validates and executes the same temporary snapshot made
  from the exact bytes retained after SHA-256 verification;
- the mutator validates every selected base through the authoritative loader
  before creating output and applies the same structural and actor-identity
  checks to generated mutations;
- this alignment does not change simulator behavior, frozen benchmark output,
  or previously published research evidence.

## Scenario Behavior Report Boundary

Issue #118 adds a read-only, standard-library report over the current
`scenarios/telemetry.json` record contract.

- `tools/scenario_report.py` groups records by their declared telemetry family
  and renders either a fixed-width text table or a Markdown table.
- Agreement rate is calculated only from runtime-complete `agreement` and
  `no_agreement` outcomes. Parse, schema, and runtime errors remain visible in
  a separate error count and are never reclassified as behavioral failures.
- Average convergence round uses agreement records only.
- Accepted records must be internally consistent with the current telemetry
  status, round, schema, runtime-error, and error-code fields.
- The report can atomically publish an explicit output file, rejects source
  aliases, and does not mutate telemetry, generated scenarios, benchmarks,
  runtime, schema, or CI.
- The aggregates describe deterministic synthetic runs; they are not evidence
  of real-world agreement rates, policy quality, or prediction.

## Scenario Generation Provenance Boundary

Issue #1758 scopes the laboratory generator/telemetry correction for stale
generated scenarios.

Operational boundary:

- Each generator run writes a content-addressed
  `generation_manifest.json` containing the exact current scenario set and
  SHA-256 hashes.
- Manifest verification retains the exact verified scenario bytes; telemetry
  validates and executes an isolated snapshot of those same bytes rather than
  reopening a mutable source path.
- Telemetry auto-detects and verifies the manifest, excludes retained stale
  files, and records the generation run identifier in records and the index.
- Generation stages the complete new set and publishes scenarios plus manifest
  as one rollback-protected transaction. A staging, write, backup, or publish
  failure restores the previous generated set and previous manifest.
- Default generation reports but retains stale generator-owned files.
  `--clean` removes only immediate
  `<family>/<family>_<number>.json` paths inside the resolved output
  directory; unrelated files and nested user content remain outside cleanup
  ownership.
- `--count` must be greater than zero and invalid counts do not create or
  modify output.
- A missing manifest remains a supported legacy telemetry scan, explicitly
  marked as unverified and without generation-run provenance. Legacy recursive
  telemetry and benchmark scans exclude only the root
  `generation_manifest.json`; a nested valid scenario with that basename is
  still processed.

## Laboratory Evidence Regeneration Boundary

Issue #1775 separates evidence interpretation from the runtime and laboratory
tool corrections in #1770, #1774, and #1779.

Operational boundary:

- The evidence base is commit
  `af89e420efb7b60eb95867b840ebeaf23dd989b6`, generator seed 42, and
  generation run
  `sha256:cab1baacc6cd3494487a59dd3f75ca9584dc872e8b3b3ec65dbd822f9bf0de92`.
- `docs/lab_regeneration_1775.md` records the exact command sequence, tool
  hashes, raw-artifact hashes, and comparison with the previously published
  values. Ignored bulk outputs are not silently promoted into Git.
- The regenerated base telemetry changes the published laboratory posture from
  55/60 to 39/60 agreements and from average convergence round 1.8 to 2.26.
- The 62-mutation total remains 57 agreements and 5 no-agreements, but the
  no-agreement outcomes move between axes; previous common-minimum and
  threshold-always-converges interpretations are retracted.
- All 27 boundary extrema for seeds 1, 42, and 123 pass fresh exhaustive
  verification.
- Explicit uniform and biased frontier runs contain zero probe errors, and
  recomparison of their preserved raw matrices reproduces all six comparison
  objects exactly.
- Results, inferences, hypotheses, and uncertainties are labeled separately.
  All observations remain synthetic simulator evidence, not external facts,
  causal proof, policy quality, or prediction.
- This regeneration changes documentation and handoff posture only. It does
  not change runtime, schema, benchmarks, CI, governance, or policy
  implementations.

## Mobile Intake Storage Boundary

Issue #1759 records that the mobile helper wrote raw claims to a non-ignored
repository-root file without stable classification or retention guidance.

PR #1777 restores the following boundary:

- default raw mobile intake is stored under the git-ignored
  `.local/intake/` directory;
- on supported POSIX systems, the protected default path is traversed and
  opened through no-follow directory descriptors, eliminating parent-path
  check-to-open races;
- platforms without those descriptor primitives fail closed for the protected
  default and require an explicit operator-managed `--output` path;
- every opened output descriptor must reference a regular file; the protected
  default additionally requires a single link, rejecting FIFOs, devices,
  sockets, and hard-linked targets before permission or content changes;
- the default directory/file and newly created custom files use private POSIX
  permissions where supported; an existing custom file retains its operator-set
  permissions;
- appends restore a missing LF boundary before writing the next JSONL record;
- option-like argv claims are accepted without being echoed by parser errors;
- each record carries schema version, intake ID, capture time, source,
  classification, verification status, and publication status;
- raw intake remains unverified, local-only material and is never promoted or
  published automatically;
- `--output` permits an explicit operator-managed path with a warning;
- the operator remains responsible for classification, access, retention,
  backup, and deletion.

No encryption, managed confidential storage, evidence verification, or
multi-writer locking is claimed.

## Semantic CaseInput Integrity Boundary

- Issue #1756 defines the versioned `CaseInput v1` contract as the combination
  of the structural JSON Schema in
  `semantic_engine/contracts/case_input.schema.json` and the complete Python
  validator `semantic_engine.contracts.case_input.validate_case_input`.
- Schema-only validation is structural pre-validation, not complete contract
  conformance: uniqueness and cross-record reference integrity are enforced by
  the Python validator.
- The Semantic Engine CLI rejects unknown fields, duplicate claim/evidence IDs,
  and evidence references to undeclared claims with controlled JSON-path
  errors.
- `metadata` is the only open extension object, remains preserved in output,
  and is opaque rather than executable or authoritative.
- Input `decision_trace` and `audit_log` are forbidden; they remain output-only
  engine records.
- Operator `/analyze` handoff and the local API reach the same contract through
  `hub-core analyze`; browser-local draft rendering remains a non-authoritative
  preview.
- Missing, unreadable, invalid UTF-8, invalid JSON, and contract-invalid inputs
  fail through the CLI's controlled error channel without a traceback.
- This change adds no evaluator, scoring, model judge, or autonomous conclusion.

## Strict JSON Boundary

Issue #1803 closes the permissive-number gap at the Semantic Engine file
boundary and the embedded API JSON body boundary.

- `NaN`, `Infinity`, and `-Infinity` are rejected during decoding, including
  when nested inside open metadata.
- `/analyze` and `/intake/url` share the same strict request-body decoder.
- Semantic Engine output, temporary API case input, and API responses use
  fail-closed serialization and cannot emit those non-standard constants.
- Analysis-result files containing a non-standard constant are rejected before
  the API constructs its response.
- Finite numeric metadata remains opaque and round-trippable. These checks add
  no scoring, truth evaluation, or public-service claim.

## Public Site Link and Contrast Boundary

Issue #1810 scopes repository-level checks for the three public HTML entry
points: the portfolio, the branded 404 page, and Operator.

- Same-origin links, assets, routes, and fragments are resolved against the
  checked-out `site/` artifact; repository evidence links resolve against
  local paths and are pinned to commit
  `f99bfed196dbcb76c8a29a4bab31559fdb567ee5` rather than mutable `main`.
- Live navigation to the repository, its issue tracker, and the separate Labs
  repository is allowlisted structurally. Pytest performs no external network
  request and therefore does not attest current remote availability.
- The reported muted normal-text selectors share one versioned dark-surface
  token. Its conservative contrast against `--graphite-3` is greater than
  4.5:1; representative 404 and Operator muted-text pairs are checked
  separately.
- These checks do not constitute accessibility certification or qualified
  human review. Keyboard/focus, reduced-motion behavior, Hebrew RTL, WebGL
  fallback, and representative desktop/mobile layout still require
  controlled-browser QA on the reviewed deployment.

## GitHub Actions supply-chain boundary

The CI, link-check, Pages, PR-safety, and repository-health workflows pin
external Actions to reviewed full commit SHAs. The corresponding release
version remains beside each SHA as an inline comment, and
`tests/test_workflow_action_pins.py` is the reviewed allowlist for those
workflows.

Dependabot may propose Action updates, but it must not auto-merge them. Review
the upstream tag, commit, release notes, `action.yml`, runtime, inputs, and
permission impact before updating the SHA, version comment, and allowlist
together. The complete procedure is versioned in `docs/context/WORKFLOWS.md`.
Kernel Guard and the maintenance workflow remain separate security scopes
because their changes also affect execution or credential behavior.

## Controlled URL Intake Network Follow-up

- Issue #1753 establishes
  `ops/ec2/controlled_url_intake.v1.schema.json` as the versioned application
  payload contract for `POST /intake/url`.
- The only meaningful request field is `url`. Success and application errors
  are flat objects: `final_url` is the accepted final resource and `error` is
  the stable failure-code field. There is no nested `intake`, `resolved_url`,
  or `error_code` contract.
- HTTP framing, malformed UTF-8/JSON, non-object JSON, and oversized request
  bodies fail before the URL-intake application contract.
- Contract tests couple the schema examples, exact application error set,
  Operator request, launcher User-Agent, 4,096-byte request body, 2,048
  URL-character, 1,000,000 raw-byte, 24,000 extracted-character, three
  redirect, and eight-second limits.
- Issue #1761 converts malformed and out-of-range URL ports into controlled
  intake errors.
- URL intake resolves and validates every address once per URL/redirect hop,
  rejects the hop if any address is non-global or multicast, disables
  environment proxies, opens a numeric family-specific socket, and verifies
  the connected peer against the validated IP set.
- Raw spaces, control characters, and Unicode IRIs are rejected before DNS;
  international hostnames require an IDNA A-label, international path/query
  text must be supplied as a percent-encoded ASCII URI, and redirects follow
  the same policy.
- Known IPv6 transition formats are rejected when they embed a non-global IPv4
  destination, including the `64:ff9b::/96` NAT64 well-known prefix.
- Candidate IP connections, redirects, TLS, headers, and response reading share
  one eight-second monotonic application budget on the current synchronous
  Linux main-thread server. The remaining connection budget is divided across
  remaining candidate IPs so one stalled address cannot consume it all.
- The budget is checked immediately after system DNS returns. `SIGALRM`
  interruption of a blocking libc resolver is best-effort, not a portable DNS
  cancellation guarantee; off-main-thread deadline use fails with a controlled
  service error.
- The original hostname remains in HTTP `Host` handling and HTTPS SNI and
  certificate verification.
- Intake still accepts one user-supplied URL, follows at most three validated
  redirects, and never fetches document links or embedded resources.
- Fetched material and failure records remain unreviewed provenance, not truth
  verification.
- Infrastructure-specific NAT64/6rd prefixes and egress routing remain outside
  application pinning and require outbound-network controls.
- Repository tests and launcher source do not assert that this change is
  deployed on any host.

## Capability Truth Snapshot Boundary

Issue #1807 establishes one precedence map in
`docs/context/SOURCE_OF_TRUTH.md` and refreshes the derived capability ledger
against repository-tree baseline
`df0ef345e5ac627f3e2735573c802fe2f60821f4`.

Operational boundary:

- GitHub `main` and each live GitHub object's own state remain authoritative
  for the repository and mutable object state that they respectively contain.
- `STATUS.md` resolves language/canonical policy; applicable governance,
  runtime contracts, schemas, source, and executable tests govern their
  narrower domains.
- `AI_HANDOFF.md` summarizes operational boundaries and cannot override those
  sources.
- `docs/architecture/capability_status.md` is a derived view. Its versioned
  offline evidence snapshot is
  `docs/architecture/capability_evidence.v1.json`.
- Deployment, GitHub settings, Releases, another repository, current PR
  lifecycle, and qualified professional review remain external unless
  directly inspected at a stated time.
- `docs/context/hub_optimus_checkpoint.md` is an archived, non-authoritative
  historical snapshot; its release, phase, CI, and task values are not current
  claims.
- The offline regression rejects draft wording for PRs recorded as terminal
  in the versioned baseline and rejects restoring that checkpoint as a current
  source. It does not replace live GitHub inspection.

## System Architecture Map Boundary

Issue #1586 establishes
`docs/architecture/system_architecture_map.md` as the current repository-level
navigation map.

Operational boundary:

- “system” names the governed repository project and its source-of-truth
  relationships; it is not a synonym for one executable program;
- the scenario runtime remains defined by its applicable schema, source,
  tests, and `docs/architecture/runtime_contract.md`;
- the Semantic Engine CLI, Operator, local operations scripts, and laboratory
  tools remain separate executable surfaces; their narrower boundaries are
  recorded by the applicable source, documents, and tests;
- the framework/methodology is human-readable and broader than those programs;
  `docs/context/STATUS.md` keeps `v1_core/languages/es/` canonical for the v1
  methodology;
- documentation, RFCs, datasets, fixtures, provisional claims, and synthetic
  observations retain their own evidence status and are not promoted into
  runtime capabilities or verified real-world facts by the map; and
- the map adds no runtime, schema, simulator, CI, deployment, roadmap,
  governance authority, or professional-review claim.

## Catalunya Fire-Response Documentation Boundary

Issue #1685 corrects the documentation boundary around the conceptual
Catalunya fire-response draft:

- The repository has no implemented or authorized fire-response module, API,
  emergency-service connector, prediction model, operational alert, tactical
  dashboard, deployment, or operator procedure.
- Payloads, data shapes, roles, routes, storage locations, actions, and metrics
  in the draft are illustrative review material, not executable configuration,
  available endpoints, operational instructions, or evidence of readiness.
- Code, infrastructure as code, CI/CD, deployment, dashboards, AI, alerts,
  prioritization, and use of real data or channels require a separately scoped
  issue, an approved RFC, and explicit human repository review before work
  starts. This includes any proposed backlog for Copilot or another AI tool.
- Any real-world use additionally requires authorization from the competent
  public authority and relevant professional safety review. Repository review
  cannot confer operational authority.
- Hypothetical operational and critical priorities require validation by a
  human holding an authorized role. AI tools cannot treat the document as a
  backlog, implementation order, or permission to open or merge work.
- The hotspot example is a valid top-level GeoJSON `FeatureCollection`; its
  incident and model metadata are contained in the foreign `metadata` member.
- The regression tests guard these documentation statements and example
  shapes only. They do not attest to a system implementation, model validity,
  deployment, integration, security, or operational safety.

## Meta-learning Follow-up

- `.github/copilot-instructions.md` currently identifies `v1_core/workflow/05_meta_learning.md` as the meta-learning update location.
- Other meta-learning copies or link targets require canonical/parity/legacy classification in a separate PR.
- Do not consolidate or delete meta-learning files in this handoff/status discipline PR.

## Do Not Do

- Do not touch runtime unless an issue explicitly says so.
- Do not add LLM-as-judge yet.
- Do not replace byte-for-byte benchmark guard.
- Do not add dashboards, semantic scoring, or new metrics without approved issue scope.
- Do not treat chat-only decisions as roadmap changes.

## Historical AI Sync Blocks

The entries below are retained as historical execution notes. They are not current branch, PR, issue, or priority state.

### AI Sync Block

Date: 2026-07-08
Source: Copilot Coding Agent execution for GitHub issue #1690
Repo state: local branch for RFC/github-platform-strategy
Branch: rfc/github-platform-strategy
Active issue: #1690
Decision made: add RFC-only GitHub platform strategy document
Reason: issue #1690 requests a governed, traceable record of which GitHub platform capabilities HUB_Optimus should adopt now, next, later, or avoid — grounded in current repository evidence
Files changed:
- docs/rfc/github_platform_strategy.md
- docs/context/AI_HANDOFF.md
Validation:
- `python tools/check_mojibake.py docs/rfc/github_platform_strategy.md` passed
- `git diff --check -- docs/rfc/github_platform_strategy.md` passed
- `python tools/check_mojibake.py docs/context/AI_HANDOFF.md` passed
- `git diff --check -- docs/context/AI_HANDOFF.md` passed
Risks: documentation-only; no runtime, CI, benchmark, schema, settings, or security claim changes
Next action: review RFC content and open follow-up issues only after explicit approval
Out of scope:
- runtime changes
- CI changes
- benchmark changes
- schema changes
- GitHub Settings mutation
- GitHub Organization migration
- Copilot/GitHub App automation
- dashboards
- LLM-as-judge
- roadmap changes

### AI Sync Block

Date: 2026-05-24
Source: Codex execution for GitHub issue #1589
Repo state: local branch `docs/capability-status-table`
Branch: `docs/capability-status-table`
Active issue: #1589
Decision made: add a capability status table and correct benchmark/drift rows to match implemented runner behavior
Reason: issue #1589 requests a source-backed table to avoid overpromising or under-reporting current runtime behavior
Files changed:
- docs/architecture/capability_status.md
- docs/context/AI_HANDOFF.md
Validation:
- `python tools/check_mojibake.py docs/architecture/capability_status.md` passed
- `git diff --check -- docs/architecture/capability_status.md` passed
- `python tools/check_mojibake.py docs/context/AI_HANDOFF.md` passed
- `git diff --check -- docs/context/AI_HANDOFF.md` passed
Risks: documentation-only; table wording must remain conservative and source-backed
Next action: review table wording against issue #1589 and PR #1580 before opening a PR
Out of scope:
- runtime changes
- CI changes
- benchmark changes
- schema changes
- roadmap changes
- multilingual docs
- crypto implementation
- dependency additions

### AI Sync Block

Date: 2026-05-24
Source: Codex execution for RFC branch `rfc/post-quantum-control-plane`
Repo state: local RFC branch
Branch: rfc/post-quantum-control-plane
Active issue: none provided in task
Decision made: add RFC-only post-quantum control plane planning document
Reason: explicit user request for a governed RFC covering artifact signing, sealed exchange, node identity, quorum access, auditability, and crypto-agility
Files changed:
- docs/rfc/post_quantum_control_plane.md
- docs/context/AI_HANDOFF.md
Validation:
- `python tools/check_mojibake.py docs/rfc/post_quantum_control_plane.md` passed
- `git diff --check -- docs/rfc/post_quantum_control_plane.md` passed
- `python tools/check_mojibake.py docs/context/AI_HANDOFF.md` passed
- `git diff --check -- docs/context/AI_HANDOFF.md` passed
Risks: documentation-only; no runtime, CI, benchmark, schema, dependency, or production security claim changes
Next action: review RFC scope and open follow-up issues only after explicit approval
Out of scope:
- crypto implementation
- runtime changes
- CI changes
- benchmark changes
- schema changes
- roadmap changes
- dashboards
- LLM-as-judge

### AI Sync Block

Date: 2026-05-08
Source: Codex execution for GitHub issue #1577
Repo state: governance protocol merged to main
Branch at the time: see active GitHub issue or PR; `main` is the source of truth after merge
Merged PR for this historical block: #1578
Active issue at the time: none
Decision made: add persistent repo-level handoff protocol for ChatGPT/Codex sync
Reason: align AI work through GitHub state instead of fragile chat-memory synchronization
Files changed:
- AGENTS.md
- docs/context/AI_HANDOFF.md
Validation:
- `git diff --check` passed
- `python tools/check_mojibake.py AGENTS.md docs/context/AI_HANDOFF.md` passed
- `python -m pytest -q` passed, 42 tests
Risks: low; documentation-only change
Next action: observe CI and collaborator friction; open scoped issue only when signal appears
Out of scope:
- runtime changes
- CI changes
- benchmark changes
- schema changes
- roadmap changes
- LLM-as-judge
- dashboards

## Governance RFC handoff — constitutional governance and AI regulatory boundary

PR #1628 introduces a draft RFC defining HUB_Optimus constitutional governance and AI regulatory boundary posture.

Operational meaning:
- HUB_Optimus is framed as an evidence-structured analysis and governance system, not an autonomous enforcement, censorship, surveillance, or persuasion system.
- Future regulated, high-risk, automated, or externally exposed capabilities require explicit RFC review before implementation.
- High-risk downstream use triggers include consequential decisions about people, surveillance/profiling, political persuasion, automated moderation/enforcement, and legal/regulatory bypass risk.
- This PR is documentation-only and does not authorize runtime, CI, schema, benchmark, roadmap, licensing, IP, ingestion, dashboard, scoring, or provider changes.

Review note:
- The RFC lives under docs/rfc/ to avoid creating governance translation mirror drift under docs/governance/.
