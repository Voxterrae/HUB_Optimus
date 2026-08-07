# Contributing to HUB_Optimus

Thank you for your interest in contributing to HUB_Optimus.

HUB_Optimus is a publicly visible repository with restricted rights. Public
visibility and contribution access do not create ownership, commercial rights,
repository authority, or an implied joint venture.

Before contributing, read:

1. [`IP_NOTICE.md`](IP_NOTICE.md)
2. [`docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`](docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md)
3. [`AGENTS.md`](AGENTS.md), when using an AI or coding agent
4. the relevant issue or RFC

## Founder and review authority

Benjamin Gerrit Hoff is the founder, architect, creator, project owner, and
final human authority of HUB_Optimus. `@Voxterrae`, immutable GitHub user ID
`249308740`, is the repository identity used under that authority.

Every repository path is assigned to `@Voxterrae` in `.github/CODEOWNERS`.
Contributors may propose changes, but no contribution modifies `main` without
owner-controlled review and merge.

A contribution, acknowledgement, technical role, access grant, commit, or pull
request does not create:

- ownership or co-ownership;
- constitutional or repository-administration authority;
- a permanent CODEOWNER or Write-access entitlement;
- equity, agency, partnership, or an implied joint venture;
- an unrestricted or commercial license.

## Contribution philosophy

We value:

- clarity over volume;
- structural reasoning over rhetoric;
- prevention over escalation;
- integrity and coherence over credentials;
- verifiable improvement over visibility;
- small, reversible changes with explicit evidence.

We do not accept:

- changes that weaken founder, ownership, Kernel, or governance protections;
- attempts to bypass owner review or impersonate the owner;
- narrative manipulation or propaganda;
- personal scapegoating as analysis;
- short-term wins presented as success while increasing long-term instability;
- coercive enforcement presented as HUB_Optimus authority;
- credentials, secrets, personal data, or private agreements committed to the
  public repository.

## Repository zones

### Historical material

`legacy/` preserves historical and exploratory material.

- Do not rewrite or modernize legacy documents retroactively.
- Add corrections as current notes with explicit provenance.

### Active Kernel and runtime

`v1_core/`, runtime source, schemas, benchmarks, governance, CI, and owner-
authority files are high-scrutiny surfaces.

All paths require owner review. The distinction between lower-risk and higher-
risk work affects review depth, not ownership or final authorization.

### Lower-risk proposals

Examples include:

- non-governance documentation;
- translations that preserve meaning;
- tests and examples;
- maintenance tooling that does not change runtime or authority.

### High-risk proposals

Examples include:

- founder, ownership, authority, licensing, or repository-control changes;
- Kernel or canonical-language changes;
- runtime, schema, benchmark, deployment, authentication, CI, or security
  changes;
- changes to `.github/`, CODEOWNERS, ruleset expectations, or guard workflows.

Founder and ownership clauses may not be proposed by a non-owner identity.

## How to propose work

1. Find or open a scoped issue.
2. Comment to make intent visible.
3. Create a focused branch.
4. Make one small, reversible change.
5. Open a pull request using `Related to #N`.
6. Disclose affected files, validation, risks, and rights provenance.
7. Wait for owner review; do not represent an unmerged proposal as current
   HUB_Optimus state.

## Required pull-request conditions

Before merge:

- the issue reference must match the actual work;
- the PR must have one objective;
- the description must match the diff;
- CI and required guards must pass;
- CODEOWNER review must be satisfied when enforced by GitHub Settings;
- only Benjamin Gerrit Hoff may give final authorization through `@Voxterrae`;
- constitutional files must pass the Founder Authority Guard;
- runtime, schema, benchmark, governance, CI, and security changes require
  explicit risk analysis;
- translations must preserve canonical meaning.

Use `Related to #N`, not automatic-closing keywords, unless the owner explicitly
chooses closure at merge.

## Contribution rights and provenance

By submitting work, a contributor represents that they have the right to submit
it and accurately disclose third-party material.

Submission alone does not create a joint venture or transfer HUB_Optimus
ownership. It also does not retroactively extinguish rights that may exist in a
contributor's original work. Where necessary, integration may be conditioned on
a separate contributor, license, assignment, employment, or services agreement
approved by Benjamin Gerrit Hoff.

Until such terms are explicit, do not assume that public visibility equals an
OSI open-source license or unrestricted commercial permission.

## Language policy

- `docs/context/STATUS.md` controls canonical-language and parity policy.
- `v1_core/languages/es/` is canonical for v1 where the status record says so.
- English is the parity reference.
- Translations must preserve meaning and must not alter founder, ownership, or
  authority clauses.

## Security and sensitive information

Do not upload:

- passwords, tokens, API keys, private keys, or signing secrets;
- personal, banking, medical, or private contractual data;
- production configuration that exposes systems or customers.

Report accidental disclosure immediately. Deleting the visible file alone may
not remove it from Git history.

## Conduct

- Be respectful and precise.
- Disagree with ideas, not people.
- Keep discussions focused on system improvement.
- Do not claim authority, identity, ownership, or endorsement that has not been
  explicitly granted.
