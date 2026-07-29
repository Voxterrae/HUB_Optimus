# GLOSSARY

These definitions classify current HUB_Optimus repository artifacts. They do
not add capabilities or replace the applicable source, contract, governance
text, or [source-of-truth hierarchy](SOURCE_OF_TRUTH.md).

- `Agreement`: Declared commitment between actors in a scenario.
- `Canonical`: The authoritative version when parallel language variants differ.
- `CI`: Continuous Integration checks executed on `pull_request` and `push`.
- `Classification`: Final scenario label derived from structural evidence.
- `Consensus process`: Governance path for high-impact kernel decisions.
- `Custodian`: Reviewer role responsible for protected governance/kernel areas.
- `Dataset / evidence artifact`: Versioned input, fixture, expected output,
  provisional corpus, or reproducible observation. Its evidence status is
  artifact-specific; it is not automatically a verified real-world fact.
- `Documentation`: Versioned material that describes, indexes, constrains, or
  proposes. Its authority follows the source-of-truth hierarchy, and its
  presence does not prove that a described capability is implemented.
- `Drift`: Meaning divergence between docs, languages, or policy statements.
- `Evaluation standard`: Rules used to score structure, verification, and incentives.
- `Fail-fast`: Immediate stop on invalid input with a stable, actionable error.
- `Framework / methodology`: Human-readable concepts, workflows, templates,
  and evaluation method that guide human use. It is broader than the current
  programs and is not automatically executed by them.
- `Governance`: Human-authored rules, stewardship, accountability, and
  change-control records for repository decisions. It is not executable AI
  authority or automatic ratification.
- `Incentive structure`: What behavior the scenario rewards over time.
- `Kernel`: Core normative framework and protected conceptual backbone.
- `Legitimacy model`: Criteria used to assess whether outcomes remain acceptable over time.
- `Link-check`: Automated validation of markdown links (Lychee in this repo).
- `Meta-learning`: Extraction of reusable rules from scenario outcomes.
- `MVP`: Minimum set of features required for a stable first public workflow.
- `No-go zone`: Explicitly out-of-scope area to prevent scope creep.
- `Parity reference`: Non-canonical language variant maintained close to canonical meaning.
- `Program`: Concrete executable surface whose supported behavior is bounded by
  its applicable source, contracts, and tests. Its presence does not establish
  deployment or implementation of the full framework.
- `Protected path`: Repository path that requires stricter review/guard rules.
- `RFC`: Structured proposal required for kernel/governance-impacting changes.
- `Runtime`: The supported execution boundary of a program or program family,
  including accepted inputs, implemented behavior, and outputs as defined by
  applicable source, schemas or contracts, and tests.
- `Scenario`: Structured case description used for evaluation and comparison.
- `Schema`: Contract defining required fields/types for scenario input.
- `Source-of-truth`: The question-specific authority selected through
  `docs/context/SOURCE_OF_TRUTH.md`; `STATUS.md` resolves canonical-language
  and parity questions only.
- `System`: The governed repository-level project: its programs,
  framework/methodology, documentation, datasets/evidence artifacts,
  governance, and source-of-truth relationships. It is not one executable
  program.
- `Trust layer`: Integrity lens that tests whether a claim is verifiable and stable.
- `Verification`: Evidence step that confirms claims beyond declarations.
- `Workflow`: Ordered procedure used to run, review, and iterate scenarios.

## Required distinctions

- **System vs. program:** the system is the governed project and the
  relationships among its artifact categories; a program is one concrete
  executable surface within that system.
- **Runtime vs. framework:** a runtime is an implemented execution boundary;
  the framework/methodology guides human use and is broader than the current
  runtimes. The current programs do not automatically execute the full
  framework.
