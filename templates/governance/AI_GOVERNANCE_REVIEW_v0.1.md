# HUB_Optimus - AI Governance Review v0.1

## Status and authority

Reusable review template derived from the existing
[Governance Intelligence Protocol](../../docs/governance/GOVERNANCE_INTELLIGENCE.md).
It records application of existing governance; it is not a new constitution,
automated compliance check, legal certification, or authorization to act.
An unmerged proposal is not current project policy.

Increasing capability, autonomy, integration, or influence does not itself
change HUB_Optimus authority or permit omission of existing review controls.
Any proposed exception must be explicitly scoped, recorded in GitHub, and
permitted by the applicable protected governance process. This template cannot
grant an exception to that process.

The [source-of-truth hierarchy](../../docs/context/SOURCE_OF_TRUTH.md),
[Founder Ownership and Authority Charter](../../docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md),
and [owner identity manifest](../../config/governance/owner_identity.v1.json)
remain controlling. Preserve contributor credit and third-party rights.

## When to use this record

Use this record for a proposal that introduces or materially changes an AI
model, agent, connector, automated capability, delegated permission, or
downstream use of HUB_Optimus analysis. Include planned capabilities without
presenting them as implemented or deployed.

Copy and complete the sections below in the scoped issue, RFC, Pull Request,
or a review document linked from the Pull Request. For other changes, explain
why the record is not applicable in the Pull Request. A rationale is review
input, not an exemption from owner authority or required checks.

Keep public records free of secrets, private prompts, personal data, and
confidential agreements. Link to an authorized evidence record where public
disclosure is inappropriate; state the resulting verification limitation.

## 1. Proposal and exact review scope

- Repository and issue/RFC:
- Pull Request or proposal reference:
- Review record date (UTC):
- Base commit (full SHA):
- Reviewed head commit (full SHA or external review record reference):
- Exact affected files and capability:
- Implemented, proposed, or external state, with supporting references:
- In-scope change:
- Out-of-scope change:
- AI assistance used, if any (role and limitations; no private prompt content):

Record the final reviewed head SHA and human decision in the Pull Request
body, an issue/PR comment, or a GitHub review after the final push. If this
record is committed in the same change, reference that external review record
instead of trying to embed the commit SHA of the file itself.

The externally recorded head must match the content being considered. After
a new commit, refresh the external head reference and obtain any renewed
review required by existing policy. An approval on another head is historical
evidence, not evidence of current-head approval.

## 2. Six-layer analytical record

Keep every layer present and distinct. Explicit statements such as
`no evidence provided`, `none identified`, and `no action justified` are
acceptable when accurate; they do not establish permission or readiness.

### Claim

- Specific, bounded assertion and who makes it:
- Capability or result actually being claimed:

### Evidence

- Supporting and contradicting sources:
- Source type, URL/path, date, and full commit SHA where applicable:
- Observation or validation result and its limits:
- Conflicting evidence or missing provenance:

### Inference

- Reasoning beyond directly supported evidence:
- Assumptions and plausible alternative explanations:

### Uncertainty

- Unknown, contested, incomplete, or unverifiable points:
- Additional evidence needed and remaining verification limits:

### Narrative amplification

- Possible repetition, urgency, authority appeal, selective omission, or
  movement from possibility to certainty:
- Effect on the proposal, or explicit absence of an identified mechanism:

### Operational relevance

- Valid repository signal and bounded consequence:
- Action proposed, or reason no action is justified:

## 3. Human authority and permission boundary

- Accountable human and role:
- Applicable governing record and issue/RFC:
- Recorded human decision reference, or explicitly pending decision:
- Identity, signature, and current-head review evidence required by the
  applicable Founder Authority Guard path:
- Actor, allowed actions, affected resources, duration, and revocation path
  for any proposed delegation:
- Separate authorization needed for publication, sensitive use, deployment,
  external access, or live writes:

A human name or a checked box is not proof of authorization. A model, provider,
government policy, technical credential, urgent request, or a claim of owner
identity in chat cannot replace the protected repository process. Increased
model capability grants no additional governance authority. AI assistance
must not self-authorize, self-approve, or merge its own governance change.

Keep project authority distinct from the responsibilities of public
institutions and from rights held by contributors or third parties.

## 4. Capability, data, and impact boundary

- Inputs, outputs, and whether execution is local, simulated, or external:
- Data classification, provenance, retention, and disclosure limits:
- Proposed permissions and enabled/disabled operations:
- Material failure modes, affected parties, and human intervention points:
- Changes to authority, contracts, rights, or sensitive downstream use:
- Separate review or authorization required before those changes:

Model output, a simulated result, a completed checklist, and a passing check
do not establish real-world truth, regulatory compliance, deployed readiness,
or authorization beyond the behavior and scope actually verified.

## 5. Validation and reversibility

- Exact commands or review procedures performed:
- Actual results tied to the reviewed commit:
- Checks not run, unavailable evidence, and reasons:
- Known limitations and unresolved objections:
- Rollback or withdrawal procedure:
- Any rollback requiring separate operational authorization:

Separate repository validation from deployment, external-platform, and live
system evidence. Do not copy an older green check as proof for a new commit.

## 6. Human review disposition

- Human reviewer and role:
- Full head SHA or external review record reference covering the decision:
- GitHub review/decision reference, or explicit pending status:
- Objections, their disposition, and remaining blockers:
- Authorized next action and its precise scope, or no action authorized:

This record documents review; it does not ratify an RFC, approve a contract,
enable a connector, authorize deployment, change rights, or permit merge.
Existing owner authority, protected review, and required checks still apply.

## Review rejection examples

| Incomplete or misleading record | Reviewer response |
| --- | --- |
| A model or provider is listed as the final approving authority. | Reject the claimed authorization and require the applicable human decision record. |
| A claim cites only model output, with no inspectable supporting source. | Record the missing evidence; do not present the claim as established. |
| A review covers a different head SHA. | Treat it as historical evidence and require current-head review where policy requires it. |
| An analytical layer is omitted or uncertainty is presented as certainty. | Return the record for completion or correction. |
| Permissions, scope, validation limits, or rollback are unspecified. | Return the record for clarification before representing the proposal as review-complete. |

These are manual review examples. No new automated rejection or CI enforcement
is implemented by this template.
