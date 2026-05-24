# RFC: Post-Quantum Control Plane

## Status

- Draft / RFC only
- Planned capability
- Not implemented
- No production security claim

## Purpose

This RFC defines a governed post-quantum control plane for HUB_Optimus artifacts. The planned capability is limited to:

- artifact signing
- sealed artifact exchange
- node identity
- quorum access
- auditability
- crypto-agility

The control plane is intended to support custody, integrity, and reviewability around sensitive artifacts without changing the simulator runtime.

## Core Thesis

HUB_Optimus must not invent custom cryptographic algorithms. It may define a governed control and custody method using standardized post-quantum primitives.

Any future implementation must be explicit, reviewable, dependency-aware, and scoped through separate GitHub issues or RFC follow-up work.

## Allowed Primitives

The following primitives are allowed as design references for future implementation work:

- ML-KEM for key encapsulation / sealed exchange
- ML-DSA for digital signatures
- SLH-DSA for special long-lived or low-frequency signature cases
- SHA-256 / SHA-384 for hashing
- AES-256-GCM or ChaCha20-Poly1305 for symmetric content encryption, if implementation happens later

## Explicitly Prohibited

This RFC does not permit:

- custom cryptographic primitives
- private keys committed to the repository
- unauthorized node or network access
- network probing
- production-grade security claims
- "quantum-proof" or "unbreakable" claims
- runtime changes in this RFC
- CI changes in this RFC
- benchmark changes in this RFC
- dependency additions in this RFC

## Architecture Boundary

The post-quantum control plane is a wrapper/control layer around repository artifacts. It is not a simulator runtime change.

The simulator runtime remains governed by `docs/architecture/runtime_contract.md`. This RFC does not alter scenario schema validation, CLI behavior, deterministic output, benchmark expectations, kernel behavior, or CI gates.

The control plane may later define artifact envelopes, custody policies, node identity records, revocation records, audit references, and policy profiles. Those contracts must be proposed and reviewed separately before implementation.

## Protected Artifact Examples

The control plane may apply to artifacts such as:

- claim_record
- proposal
- evidence packet
- decision memo
- scenario report
- governance handoff

These examples are conceptual. This RFC does not introduce a new artifact schema.

## Initial Policy Profiles

| Profile | Intended custody posture |
| --- | --- |
| PQX-0 | Hash + signature only |
| PQX-1 | Signature + sealed envelope |
| PQX-2 | Sealed envelope + quorum access |
| PQX-3 | High-sensitivity custody |
| PQX-LOCKDOWN | Local-only / no export |

Policy profiles are planning labels only. They do not activate enforcement in this RFC.

## Node Model

Nodes are conceptual participants in a future control plane. A node record may include:

- `node_id`
- `node_role`
- public signing key
- public KEM key
- trust level
- revocation status
- rotation policy
- last attestation

No node access, node discovery, network probing, or remote attestation implementation is authorized by this RFC.

## Artifact Envelope Model

A future artifact envelope may use a structure similar to:

```json
{
  "envelope_version": "pqx-envelope-v0",
  "artifact_type": "decision_memo",
  "artifact_hash": {
    "algorithm": "SHA-384",
    "value": "hex-encoded-digest"
  },
  "classification": "internal_review",
  "created_at": "2026-05-24T00:00:00Z",
  "source_node": {
    "node_id": "node-example-001",
    "node_role": "review_author"
  },
  "policy_profile": "PQX-1",
  "signature": {
    "algorithm": "ML-DSA",
    "key_id": "signing-key-example",
    "value": "signature-bytes-reference"
  },
  "encryption": {
    "enabled": true,
    "kem_algorithm": "ML-KEM",
    "content_encryption": "AES-256-GCM",
    "recipient_key_ids": [
      "kem-key-example"
    ]
  },
  "audit_refs": [
    "github-issue-or-pr-reference"
  ]
}
```

The example is illustrative only. It is not a schema, implementation contract, or compatibility guarantee.

## Threat Model

The control plane should account for:

- harvest-now-decrypt-later: adversaries may store encrypted artifacts now and attempt decryption later.
- compromised node: a trusted participant may be taken over or may sign invalid material.
- stolen key: signing or KEM private keys may be copied, leaked, or misused.
- artifact tampering: an artifact may be altered after review, export, or exchange.
- insider risk: authorized participants may misuse access or bypass custody expectations.
- dependency maturity risk: post-quantum libraries, formats, and operational practices may change.
- overclaiming risk: documentation may imply stronger security than the project can verify.
- scope creep: control-plane work may drift into runtime, CI, benchmarks, dashboards, or roadmap changes.

## Non-Goals

This RFC does not authorize:

- crypto implementation
- runtime integration
- CI integration
- benchmark integration
- dashboard creation
- LLM-as-judge
- custom algorithm research
- production security certification

## Future Work

Future work should be opened as separate GitHub issues after RFC review:

1. capability status table rows
2. node identity contract
3. PQX artifact envelope contract
4. PQX policy profiles
5. post-quantum threat model
6. crypto-agility register
7. prohibited security claims
8. isolated local PoC only after RFC review
