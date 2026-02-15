# Change Request Process

This document explains how to propose changes to governance or Kernel-adjacent documents without breaking integrity.

---

## 1) Scope

- Governance documents (Charter, Trust Layer, Evaluation Standard, Schema, etc.)
- Kernel-adjacent structural rules
- Translation policy and navigation structure changes

---

## 2) Required format

A change request must include:

- summary of the proposal,
- affected files or sections,
- rationale (structural, not rhetorical),
- impact analysis (risks and mitigations),
- Kernel coherence check (explicit),
- translation impacts (what needs syncing across languages).

---

## 3) Workflow

1. Open an issue (optional but recommended) to gather objections early.
2. Create a focused PR.
3. Follow `CONSENSUS_PROCESS.md`:
   - address objections,
   - revise until no sustained objections remain.
4. Custodian review (mandatory for governance or Kernel-adjacent changes).
5. Merge and record rationale in the PR thread.

---

## 4) Special rule for Kernel changes

Kernel changes require:

- elevated scrutiny,
- explicit custodian approval,
- synchronized language updates.

If not met, the request is rejected.

---

## 5) Post-merge checks

After merge:

- run link checks,
- confirm MkDocs navigation still resolves,
- confirm translation policy compliance (no placeholders, no drift).

