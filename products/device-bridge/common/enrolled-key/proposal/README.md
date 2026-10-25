# T5 enrolled-key resolution proposal

**PROPOSED / NON-NORMATIVE / SYNTHETIC ONLY.** This AI-prepared increment is
review material for [#1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933),
with its five-file scope recorded in
[the preparatory scope comment](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6391120109).
It has no human adoption, enrollment or device evidence. Independent technical
review, owner disposition of an exact head, stable adoption and activation are
separate events. GitHub and the protected owner-authority records remain controlling.

The operational report remains **T5 enrolled-key resolution unavailable**.
This is remote-pilot T5 key/enrollment/channel preparation. It does not renumber
original AUTH-plan Task 5 (IPC/isolation), edit the roadmap or enable the fixture.

## Small deliverable and evidence

The schema is a closed Draft 2020-12 projection of fictional decoded scenarios.
The corpus contains one baseline and named expected outcomes. `conformance.cjs`
is a `node:test` executable with fixed mutation recipes and a lexical evaluator;
it has no exports, input handler, listener or runtime entry point. Python checks
schema boundaries and runs Node. No new dependency or native module is introduced.
Existing protocol/result schemas, vectors, crates and lockfiles stay unchanged.

Every outcome has exactly `status`, `code`, `operationalAuthority`:
`candidate-consistent` with null code, or `denied` with one proposed local code.
**Every outcome has operationalAuthority `absent`.** It contains no key, enrolled
or verified token, capability, inventory, admission lease or release permission.
These diagnostics do not change `ProtocolError`, `ResultError`, native-result
error codes, channel receipts, wire schemas, stdout or MCP behavior.

Baseline personal/account-a/authorizer-a and matching company/account-b/
authorizer-b controls exercise separation. All refs are fictional; none identifies
a SID, tenant, Android user, device or chat. Local context selects the realm,
target and profile. Presented requests and keys are observations, never lookup
arguments. There is no alias, first-record choice or cross-realm fallback.

Enrollment generation belongs to a registration. Broker start generation belongs
to the current process and its pending request; it is absent from records. A
valid restart test changes current/pending/presented start together and the
pending digest while retaining the exact registration. Restart is not reenrollment.

## Evaluation order and limits

Only decoded, schema-valid synthetic inputs enter this model. It performs these
comparisons in order and returns only the first failure:

1. Unavailable store or any null epoch: `StoreUnavailable`; before/snapshot
   disagreement: `StoreChanged`. Record contents are unused after these failures.
2. Null, empty, reversed, not-yet-valid or expired policy: `PolicyUnavailable`;
   policy ref/digest disagreement with local expectation: `PolicyMismatch`.
   The interval includes its start and excludes its end.
3. Local namespace/account/target/profile selects zero records: `NoRecord`;
   two records, even identical: `AmbiguousRecord`.
4. Selected authorizer mismatch: `BindingMismatch`; record policy mismatch:
   `PolicyMismatch`; revoked lifecycle: `Revoked`.
5. Pending target/profile mismatch: `BindingMismatch`; enrollment or current
   process start disagreement: `GenerationMismatch`.
6. Off-curve record/presented SEC1 points, or broker key-ID disagreement:
   `KeyMismatch`. SHA256 of raw uncompressed broker SEC1 must equal both IDs.
7. Duplicated signing roles, a transport pin identifying a signing role, or any
   of six directed presented-role substitutions: `RoleMismatch`. Only after all
   cross-role checks do ordinary presented-key mismatches yield `KeyMismatch`.
8. Pending domain-prefixed signing-byte digest mismatch or unequal complete
   presented/pending request signing bytes: `PendingMismatch`.
9. A final after/before epoch disagreement: `StoreChanged`; otherwise the result
   is only `candidate-consistent` with authority absent.

All isolated mutations declare their changed dimensions and restore them to
prove unrelated inputs stayed unchanged. Compound precedence tests are explicit
exceptions, paired with effective isolated controls. The exact case-ID set must
equal the recipe registry. Pending comparison includes requestId, nonce, target,
profile, both generations, broker key ID and the fixed version/operation/fields/TTL.
Wrong operation, fields and TTL are schema negatives. Presented realm/trust fields
and trust booleans at baseline/local/record are schema-invalid.

The broker, biometric approver and TLS transport roles are separate. P-256
points are checked by OpenSSL through Node conversion/JWK import. TLS pins are
SHA256 of SPKI DER exported by `KeyObject.export`, never SHA256(SEC1). Transport
role consistency grants no biometric approval. No DER/X509 parser is implemented.

The frozen [protocol request/approval](../../native-protocol/vectors/native_signature.v0_1.json)
and [native-result](../../native-result/proposal/vectors/native_result_signature.v0_1.json) signatures actually run
through `crypto.verify`, including both existing low-S and high-S forms. The
attacker-selected public request plus matching public broker key passes the
actual frozen request/result mathematics and digest/target/profile bindings.
It can also match the fictional baseline. This is no protected pending request:
all values and software scalars 1/2/3 are public. Scalar 4 supplies adversarial
unknown-key cases. In-memory signing of three independently changed requests
passes mathematics and still fails selected pending comparison. Nothing treats
signature bytes as replay IDs. The frozen `otherKey` result verifies under its
actual scalar-2 key but fails selected broker binding; its old request digest
is retained, with no claim of a newly forged matching request.

Equal fixture epochs prove no protectedness, provenance, monotonicity, ABA
resistance or freshness. A future producer must change a durable, never-reused
epoch for every registration/policy/revocation mutation, including restore and
restart. Changed-after tests only model an interleaving; they prove no native
atomic transaction. Synthetic ticks 0..1000000 are ordered numbers, not clocks
or attestation/revocation freshness. The zero-to-two record bound is corpus-only.
Schema/JSON.parse claim no raw byte limits, duplicate decoded-name detection,
UTF-8/DER validity, platform properties or normalization. No schema success,
self-reported flag, signature, signed commit or AI review establishes enrollment.

## Future private integration boundary

Pseudocode only:
`resolve_for_pending(local_context, pending_handle, protected_store_view, current_policy_view) -> private role-key view | local denial`.
Authenticated local broker components create these inputs; they are never
deserialized transport values. The private role-key view is ephemeral, neither
serializable nor caller-constructible. Only a separately validated protected
enrollment producer may create an enrolled-key type. This increment implements
no `EnrolledBrokerKey`, `VerifiedEnrollment`, factory or boolean authority API.

The eventual chat-to-Windows adapter must retain the authenticated caller/chat
association in its private pending handle. A title, caller-provided thread
string or opaque token alone is not identity. This specific chat must receive
only its own operation's result. No caller/thread wire field or synthetic trust
flag is added. Authentication and T6 same-caller release remain protected gates.

1. Existing `parse_request_envelope` parses the request. Protected local/pending
   selection supplies the broker key to
   `verify_request_signature(&RequestEnvelope, &[u8])`. Broker SEC1 digest plus
   signature mathematics is necessary but does not establish enrollment.
2. Existing `parse_approval_envelope` parses approval. Compare its complete nested
   request with independently selected pending; only the selected biometric key
   reaches `verify_approval_signature(&ApprovalEnvelope, &[u8])`. The library
   does not perform enrollment, pending selection or one-use admission.
3. Existing `parse_native_result` parses result. Use
   `verify_native_result_signature(&NativeResult, &RequestPayload, &[u8])`
   with independently retained expected request and selected broker key. A
   caller-selected matching request/key pair is insufficient.
4. T6 revalidates generation, current policy/revocation, freshness, full pending
   and durable one-use consumption before bounded T7 admission. Before any data
   leaves, it revalidates and atomically commits release to the same authenticated
   caller/operation. Even error receipts must not leak private inventory.

Windows-Xiaomi approval transport and chat-to-Windows MCP are separate trust
boundaries. Reachability implements neither. Resolver or signature success gives
no T6 admission/release permission and no T7 collector implementation.

## Candidate later native map; no files created now

Exact candidate paths:

| Exact candidate path | Responsibility |
| --- | --- |
| `products/device-bridge/windows/native-pilot/Cargo.toml` | Reviewed native dependencies/features. |
| `products/device-bridge/windows/native-pilot/Cargo.lock` | Complete reviewed closure/checksums/licenses. |
| `products/device-bridge/windows/native-pilot/src/lib.rs` | No unprotected enrolled-key constructor. |
| `products/device-bridge/windows/native-pilot/src/identity.rs` | CNG broker identity and role separation. |
| `products/device-bridge/windows/native-pilot/src/enrollment.rs` | Private producer/resolver orchestration. |
| `products/device-bridge/windows/native-pilot/src/attestation.rs` | CryptoAPI exclusive in-memory roots; rasn typed parsing. |
| `products/device-bridge/windows/native-pilot/src/approval_https.rs` | HTTP Server API v2/HTTP.sys/Schannel bounded pending/submit. |
| `products/device-bridge/windows/native-pilot/tests/identity_enrollment.rs` | Actual protected-boundary evidence after gates pass. |

This Rust map is the current private-plan candidate alongside older public
C#/Kotlin sketches; it is not adopted architecture. Durable SQLite storage,
admission and release remain T6, with no dependency or storage implementation here.
Pinned candidates: Rust 1.99.0; rasn, rasn-pkix, rasn-derive, rasn-derive-impl
0.26.6; windows-sys 0.61.2; windows-link 0.2.1. Existing protocol/result
dependencies and their 50-package lock closure stay byte-identical. Full features,
transitive closure/checksums/licenses and production `x86_64-pc-windows-msvc`
compatibility remain unresolved. GNU host evidence is not MSVC evidence. No
Cargo resolve, build, fetch, install or trust download is part of this proposal.

Later Android changes are `ApprovalClient.kt` and
`res/xml/network_security_config.xml` under the T4 candidate module. Its historical
module/package paths disagree and must be resolved explicitly before edits; no
canonical path is invented here. Android system TLS, a separate transport key,
per-use AndroidKeyStore biometric signing and JNI remain selected directions,
with no validated Xiaomi facts. Android installs remain deferred for disk space.

Selected backend remains CNG + CryptoAPI + rasn + HTTP.sys/Schannel. The kernel
Schannel handshake must accept the intended private mTLS trust without global
trust mutation; later private CryptoAPI chain checks cannot repair a handshake
already rejected. An exact address/URLACL alone proves no NIC isolation. SAN/
endpoint checks, validity/EKU and TLS SPKI pins are separate. Channel bounds,
renewal/resumption/revocation and KSP/ACL isolation require a reviewed native test
plan. No global iplisten change, substitute server, public endpoint, ADB reuse,
push service or perpetual Android service is selected by this increment.

## Private runbook template; no actual values or live actions

| Private field | Placeholder and evidence needed later |
| --- | --- |
| Artifacts | `<WINDOWS_BUILD_SHA256>`, `<ANDROID_APK_SHA256>`, `<SOURCE_HEAD>`, `<LOCK_AND_TOOLCHAIN_RECORD>`; reviewed builds and healthy space. |
| Realm | `<LOCAL_PRINCIPAL_REF>`, `<NAMESPACE_REF>`, `<ACCOUNT_REF>`, `<TARGET_REF>`, `<PROFILE_REF>`, `<AUTHORIZER_REF>`; authenticated local mapping and ACL owner; personal/company separately selected. |
| Registration | `<ENROLLMENT_GENERATION>`, `<BROKER_CURRENT_START_GENERATION>`, `<POLICY_VERSION_DIGEST>`, `<STORE_EPOCH>`; current start is not immutable registration identity. |
| Keys | `<BROKER_SHA256_SEC1>`, `<BIOMETRIC_KEY_FINGERPRINT>`, `<ANDROID_TLS_SHA256_SPKI>`, `<WINDOWS_TLS_SHA256_SPKI>`; visible ceremony and independently authenticated roles. HTTP.sys certificate binding hash is another identifier. |
| Challenge | `<PRIVATE_CHALLENGE_RECORD_REF>`; unpredictable fresh 32 bytes, bounded lifetime, unused state, atomic consumption. Never publish challenge/device IDs/chain. |
| Policy | `<APP_SIGNER_POLICY_REF>`, `<APP_PACKAGE_REF>`, `<ROOT_POLICY_REF>`, `<REVOCATION_SNAPSHOT_REF>`; off-device chain/extension/challenge/key/app/boot/hardware/per-use checks, freshness, approved roots. KeyInfo alone is insufficient. |
| Endpoint | `<EXACT_PRIVATE_ADDRESS>`, `<URLACL_OWNER_REF>`, `<TLS_SERVER_NAME>`, `<PEER_PIN_REF>`; mTLS/pin/isolation evidence without global trust/network changes. |
| Withdrawal | `<REVOCATION_RECORD_REF>`, `<OWNED_RESOURCES_MANIFEST>`; atomic revocation, invalidate pending/reused sessions, fresh negative resolution, remove only owned test resources. |

Later rehearsal order: check gates/hashes; visible local ceremony with exact
realm/keys; off-device attestation and durable challenge consumption; private
transport with unknown/cross-profile/revoked peers denied; open app, fetch bounded
pending, review exact request, per-use biometric, submit bounded receipt; cancel
before collector/release. Record cancel, lock/background, key invalidation,
restart and revocation-between-checks negatives. Stop on unavailable evidence.
Template entries establish no enrollment. Actual A01/A02, collector, release
and this chat's MCP invocation require separate later evidence.

## Local validation

From repository root, run Node conformance and the unittest bridge:
`node --test products/device-bridge/common/enrolled-key/proposal/conformance.cjs`;
`python -B -m unittest discover -s tests -p test_device_bridge_t5_resolution_proposal.py -v`.
Use the existing Python/jsonschema environment. Missing artifacts/dependencies
fail visibly. Missing Node explicitly skips with synthetic conformance unverified;
a skip does not satisfy executable acceptance. No downloads or builds are needed.
