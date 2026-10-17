# HUB Relay native protocol candidate v0.1

Experimental common Rust library for strict request/approval parsing, canonical
signing bytes, named SHA-256 digests and mathematical P-256 ECDSA verification.
Implementation scope was approved in [issue #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6144746363).
This candidate does not replace existing Device Bridge contracts or activate
`requestRealExecution()`: `EXECUTOR_DISABLED` and `fixture.v0.1` remain unchanged.

## Wire profile and public API

Both envelopes contain exactly `payload` and `signatureDerHex`. Request payloads
use version `relay.native-request.v0.1`, operation
`windows.runtime_inventory.v0_1`, ordered fields `["windows","powershell7","node"]`
and the integer JSON token `60000` for `ttlMs`. All fields are required. IDs and
generations are 32 lowercase hex characters; `brokerKeyId` and nonce are 64.
Approval payloads contain version `relay.native-approval.v0.1` and the complete
request payload, without the broker signature. See the self-contained
[request schema](schemas/native_request.v0_1.schema.json) and
[approval schema](schemas/native_approval.v0_1.schema.json).

`parse_request_envelope` / `parse_approval_envelope` return validated types with
private fields and getters. `serialize_request_envelope` /
`serialize_approval_envelope` apply the same 4096-byte envelope limit.
`request_signing_bytes`, `approval_signing_bytes`, `request_digest` and
`approval_digest` take a validated request payload; approval construction nests
the full request automatically. `verify_request_signature` and
`verify_approval_signature` receive the public key separately. No signing,
private-key, enrollment, authority or execution API is exposed.

Signed bytes are exactly UTF-8 domain, one NUL byte, and RFC 8785 JCS payload:

```text
HUB-RELAY-REQUEST-v0.1  || 0x00 || JCS(RequestPayload)
HUB-RELAY-APPROVAL-v0.1 || 0x00 || JCS(ApprovalPayload)
```

ECDSA hashes those bytes with SHA-256 once. Each named digest is SHA-256 of its
corresponding signing bytes. Verification requires a valid uncompressed P-256
SEC1 public key of exactly 65 bytes and strict minimal DER with nonzero in-range
r/s. Both high-S and low-S are accepted. Request origin verification also checks
that SHA-256 of the supplied SEC1 bytes equals the declared `brokerKeyId`.

## Local validation

From this directory, with the reviewed Rust 1.99.0 GNU Windows compiler,
standard library, linker and exact dependency closure available in an isolated
task environment:

```powershell
cargo fmt --check
cargo clippy --locked --all-targets --target x86_64-pc-windows-gnu -- -D warnings
cargo test --locked --target x86_64-pc-windows-gnu
```

The toolchain file pins Rust 1.99.0 and the rustfmt/clippy components. The explicit
GNU Windows target above is for local tests only; production target selection and
Linux validation remain pending. `Cargo.lock` and
[DEPENDENCIES.v0_1.json](DEPENDENCIES.v0_1.json) record the approved five direct
pins and 50 registry packages. Avoid inherited compiler wrappers, bootstrap
overrides, injected flags or unrelated Cargo configuration; use an isolated
task build environment when validating this candidate. These commands execute
Rust sources and dependency build scripts locally. Existing repository Python
CI is separate and does not establish that this Rust crate was tested.

## Independent synthetic vectors

[native_signature.v0_1.json](vectors/native_signature.v0_1.json) was generated
with Node **v24.19.0**, OpenSSL **3.5.7** using `node:crypto`, `prime256v1` and
`crypto.sign('sha256', signingBytes, { dsaEncoding: 'der' })`. It records the
literal JSON sources, canonical payload strings, complete domain/NUL signing
bytes, digests, DER signatures and exact generator source. Public fictitious
private scalars 1 and 2 are included solely to reproduce software tests. They
are not secret and must never represent an enrolled identity.

The generator's independent canonicalizer recursively sorts keys using default
JavaScript UTF-16 `.sort()` and `JSON.stringify`. It covers this closed ASCII
payload and integer-TTL profile only; it is not a general JCS engine. Rust's
separate internal conformance tests cover Unicode ordering and preservation
without expanding the operational schema.

Reproduce from the **repository root** using the recorded Node version. This
extracts the embedded generator into a task temporary file; its only output is
the fixed module vector path. It reads no environment secrets or key files.

```powershell
$vector = Get-Content -Raw -Encoding utf8 'products/device-bridge/common/native-protocol/vectors/native_signature.v0_1.json' | ConvertFrom-Json
$generatorPath = Join-Path ([IO.Path]::GetTempPath()) ('hub-relay-vector-' + [guid]::NewGuid().ToString('N') + '.cjs')
[IO.File]::WriteAllText($generatorPath, $vector.generator.source, [Text.UTF8Encoding]::new($false))
node $generatorPath
```

ECDSA uses OpenSSL randomness. Regeneration must reproduce the canonical bytes
and digests and verify both S forms; it need not reproduce identical signature
bytes. The generator verifies every positive signature and rejects its malformed
DER cases independently. `tests/signature_vectors.rs` consumes the public API
and compares the Rust bytes/digests to the independent recorded values. Its
negative origin vector is correctly signed by the broker test key while
declaring the other key's ID.

## Boundaries retained

1. Mathematical verification establishes consistency with a supplied key, not
   identity, enrollment, owner authority or permission to execute.
2. The approval API verifies key mathematics; a future adapter must resolve the
   key from protected enrollment, never a transport key selector.
3. Biometrics, Android Keystore/StrongBox and Windows protected keys are absent.
4. Replay prevention, nonce consumption, deadlines, clocks and revocation are
   future broker/admission responsibilities; TTL alone proves no freshness.
5. A valid nonce format proves neither entropy, uniqueness nor CSPRNG origin.
6. Schema validation cannot detect duplicate decoded keys, enforce byte caps or
   distinguish lexical `60000` from `60000.0`/`6e4`; the Rust parser is normative.
7. Signatures can be malleable high-S/low-S; do not use signature bytes as request
   identity, deduplication keys or consumed-approval keys.
8. Future admission must compare the canonical complete request and relevant
   named digests against its own pending request. This library performs no
   admission, pending-request lookup or generation-state comparison.
9. No Android APK, Windows service, IPC/ACL, collector, installation, hardware
   access, network operation or runtime integration is included.
10. Local tests on this host do not certify Android signing, Windows 10 hardware,
    a production target, operational compliance or deployment. Owner review and
    separate execution gates remain required.

The original module follows [IP_NOTICE.md](../../../../IP_NOTICE.md) and the
[owner-authority handoff](../../../../docs/context/OWNER_AUTHORITY_HANDOFF.md).
Third-party dependencies retain their respective rights and terms; their license
metadata is not a license grant for HUB_Optimus. This scoped candidate changes no
owner-authority record; the existing handoff remains controlling.
