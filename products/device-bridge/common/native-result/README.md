# Experimental HUB_Relay native result library

This isolated Rust library implements the candidate C1-C5 result profile frozen
at `117d661fd1565468e75c09fb180d7446753f6363` in [PR #1991](https://github.com/Voxterrae/HUB_Optimus/pull/1991).
Scoped implementation approval and exact pins are recorded in
[issue #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6390196483).
The historical [proposal](proposal/README.md), schema and vectors remain unchanged.
Implementation is experimental; it does not adopt a stable contract.

## API boundary

- `parse_native_result_payload(&[u8])` validates a payload before external signing.
- `parse_native_result(&[u8])` validates the complete envelope and strict minimal
  P-256 DER at parse time, including both low-S and high-S forms.
- `result_signing_bytes(&NativeResultPayload)` returns the exact UTF-8 domain
  `HUB-RELAY-RESULT-v0.1`, one NUL and RFC 8785 JCS of the closed payload.
- `serialize_native_result(&NativeResult)` returns complete-envelope JCS.
- `verify_native_result_signature(&NativeResult, &RequestPayload, &[u8])`
  checks supplied SEC1 key shape/point, key ID, expected-request digest, target,
  profile and the mathematical signature over the full signing bytes, hashing once.

Public values have private fields and read-only getters. They cannot be
constructed, deserialized or mutated without passing the raw parser. The parser
rejects duplicate decoded names before building values, unknown/missing members,
positional arrays, invalid UTF-8, BOM, trailing input and malformed Unicode.
Required nullable members remain explicit. Version length counts Unicode scalars
without normalization, trimming or interpretation; display these strings inertly.

Raw payload and envelope input are independently bounded to 4096 bytes, including
whitespace and escape spelling. Serialized complete envelopes are independently
bounded to 4096 bytes. Signing bytes are an internal domain-prefixed message and
have no envelope cap. Errors are closed, input-free `ResultError` values; their
precedence for multiply-invalid input is not contractual.

The caller must select the expected request and key from a separately trusted
boundary. An attacker controlling both values and the matching signing key can
satisfy mathematical consistency. That success proves no identity, enrollment,
biometric event, freshness, current generations, authorization, inventory truth,
collector execution, replay admission or hardware delivery.

**T5 enrolled-key resolution unavailable.** This library exposes no signing or
private-key API, enrollment token/constructor, `EnrolledBrokerKey`, collector,
network, device, activation or admission capability. Synthetic public vectors
remain test data; no actual Android or protected-storage test is claimed.

## Validation

From the repository root with the pinned cached Rust 1.99 environment:

```text
cargo fmt --manifest-path products/device-bridge/common/native-result/Cargo.toml -- --check
cargo test --offline --locked --target x86_64-pc-windows-gnu --manifest-path products/device-bridge/common/native-result/Cargo.toml
cargo clippy --offline --locked --target x86_64-pc-windows-gnu --manifest-path products/device-bridge/common/native-result/Cargo.toml --all-targets -- -D warnings
cargo test --offline --locked --target x86_64-pc-windows-gnu --manifest-path products/device-bridge/common/native-protocol/Cargo.toml
node --test products/device-bridge/common/native-result/proposal/conformance.cjs
python -m unittest discover -s tests -p test_device_bridge_native_result_proposal.py -v
```

Rust boundary tests exercise adversarial raw grammar, required nulls, all 27
completed inventory combinations, state/error pairs, Unicode and byte limits,
strict DER rejection, malformed SEC1 and independent expected-request mutations.
Frozen Node/OpenSSL vectors supply 11 canonical payloads, both S forms and eight
binding/domain/hash counterexamples. A test compares every complete registry
lock record with the unchanged protocol lock; no registry package is added.
Private serializer stress tests reach otherwise inaccessible envelope boundaries
without exposing an unchecked public constructor.
