# Native result v0.1 — candidate for protected review

**PROPOSED / NON-NORMATIVE. Exact profile, file map and reviewed head await
protected owner disposition. This package does not adopt a contract.**

Traceability: [#1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933),
INV-01..05 / Tarea 6 (bounded Windows inventory). Delivery sequencing sometimes
calls this result proposal T3; the approved plan's original Tarea 3 concerns the
minimal biometric signer. Those scopes are distinct.

This candidate builds on experimental request/approval work in
[#1963](https://github.com/Voxterrae/HUB_Optimus/pull/1963) and request payload
preparation [#1990](https://github.com/Voxterrae/HUB_Optimus/pull/1990).
Its reviewed source checkpoint is `9367a16210d371199ce8de2baedfe396c9b4585d`.
Neither dependent proposal is adopted here. The existing
[security requirements](../../../SECURITY_REQUIREMENTS.md) and owner-governed
review process remain controlling; a green test is not approval.

## Delivered evidence and limits

The candidate JSON Schema projects the decoded structure. Python `unittest`
uses the existing Draft 2020-12 `jsonschema` validator. The Node built-in test
harness verifies frozen synthetic canonical bytes, SHA-256, ECDSA P-256,
independent request/key/target/profile bindings and fixture separation.
Its scoped canonicalizer covers this closed result and the existing fixed
request; it does not certify universal RFC 8785 conformance.

**No native raw parser, production verifier, collector, signer service or runtime
API is delivered.** Schema success does not enforce duplicate-name rejection,
raw UTF-8, BOM handling, byte caps, canonical input/output, strict DER, signature
math, trusted expected-request selection, enrollment or authorization.
The harness's decoded-value and DER helpers are test-only and export no API.
Node `JSON.parse` loses duplicates; it cannot establish raw-parser conformance.

All scalars, keys, identifiers and inventory strings in the vectors are public,
fictitious test data. Scalars **1 and 2** repeat the old public test vectors.
They must never serve as live identity, trusted enrollment or protected keys.

## Exact proposed decoded shape

Every object is closed. Every listed member is required, including nulls.
Object input order is insignificant; decoded names must occur once.

| Object | Members |
| --- | --- |
| Envelope | `payload`, `signatureDerHex` |
| Payload | `version`, `requestDigest`, `targetId`, `profileId`, `state`, `errorCode`, `inventory` |
| Non-null inventory | `windows`, `powershell7`, `node` |
| Each inventory field | `state`, `version` |

Payload version is exactly `relay.native-result.v0.1`. `requestDigest` is exactly
64 lowercase ASCII hex characters; `targetId` and `profileId` are each exactly
32. Whitespace, uppercase, prefixes and trailing LF are rejected.

| Result state | `errorCode` | `inventory` |
| --- | --- | --- |
| `completed` | explicit `null` | complete inventory object |
| `denied` | `NOT_AUTHORIZED`, `EXPIRED`, `REVOKED`, `REPLAY`, or `BINDING_MISMATCH` | explicit `null` |
| `failed` | `COLLECTOR_FAILED`, `TIMEOUT`, `OVERFLOW`, or `INTERRUPTED` | explicit `null` |
| `cancelled` | `CANCELLED` | explicit `null` |

| Field state | `version` |
| --- | --- |
| `available` | string of 1–128 Unicode scalar values |
| `missing` or `unverified` | explicit `null` |

Every other combination fails. All 27 combinations of field states can complete
a bounded collection attempt. There is no partial inventory, raw error,
diagnostic, message, command, path or environment output. No coercion, omission,
truncation, normalization, fallback result or silent state conversion is allowed.
The native envelope is separate from the unchanged `fixture.v0.1` shape:
fixture results use `simulated:true`, `data` and `code`; native results use
`inventory` and `errorCode`. Real fixture execution stays `EXECUTOR_DISABLED`.

## C1–C5: new choices proposed for review

**C1 — grammar and required nulls.** A future parser accepts one UTF-8 JSON
object with optional surrounding JSON whitespace. Reject BOM, invalid UTF-8,
unescaped controls, trailing values/garbage, NaN/Infinity, unpaired surrogates
and invalid pairs. Reject arrays at every object boundary. Detect duplicate
decoded names at every depth before building a map, including `state` alongside
`st\u0061te`. Unique escaped names decoding to allowed names are accepted.
Missing nullable members fail; absence is not null.

**C2 — Unicode.** Count scalars, not bytes, UTF-16 units or grapheme clusters:
an astral character counts once; base plus combining mark counts twice.
Preserve exact sequences without trimming, case folding or NFC/NFD conversion.
Equivalent escaped/literal spellings canonicalize equally; composed/decomposed
strings stay distinct. All valid scalars, including escaped controls and
noncharacters, are permitted. Display version strings inertly. The schema
explicitly excludes surrogate code points in decoded strings; strict decoding
still belongs to the future native boundary.

**C3 — bytes and serialization.** Cap raw payload and complete envelope input
separately at 4096 bytes before decoding/parsing. Whitespace and escape spelling
count. 4096 is accepted only when all other rules pass; 4097 fails. Cap final
serialized envelope bytes, including the signature, separately. Future output
is complete-envelope RFC 8785 JCS in UTF-8, without BOM/newline. Input need not
be canonical. Internal domain-prefixed signing bytes are not an envelope and
do not inherit its 4096-byte cap. Synthetic byte counts here prove no parser cap.

**C4 — DER.** Signature transport is nonempty, even-length lowercase ASCII hex,
at most 144 characters. Future envelope parsing must also require strict minimal
DER ECDSA P-256: correct tags/lengths, complete input, positive minimal nonzero
INTEGERs below the group order. Reject P1363, BER lengths, redundant padding,
negative/zero/out-of-range values and trailing bytes. This proposed parse-time
DER check is stricter than the existing request/approval transport parsing.
Both high-S and low-S remain valid. Signature bytes are not identity/replay keys.
The schema encodes hex syntax only; even `aa` passes that structural constraint.

**C5 — future mathematical API.** Recommend private validated types with
read-only getters and no unchecked constructor, mutable payload or public
unchecked deserialization. Proposed functions, **not implemented here**:

```text
parse_native_result_payload(bytes) -> NativeResultPayload / ResultError
parse_native_result(bytes) -> NativeResult / ResultError
result_signing_bytes(validated_payload) -> bytes / ResultError
serialize_native_result(validated_result) -> bytes / ResultError
verify_native_result_signature(result, expected_request, provided_SEC1_key)
    -> success / ResultError
```

Payload parsing precedes real signing; no placeholder signature is needed.
An external signer supplies real DER; the final envelope is then validated and
bounded. The future library exposes no private key/signing capability.
Suggested local bounded errors: `EnvelopeTooLarge`, `InvalidJson`,
`InvalidPayload`, `InvalidSignatureEncoding`, `InvalidDer`, `InvalidPublicKey`,
`KeyIdMismatch`, `RequestDigestMismatch`, `TargetMismatch`, `ProfileMismatch`,
`VerificationFailed`, `Serialization`. Error text must not retain/echo input.
Local errors do not automatically become signed wire `errorCode` values.
Ordering of simultaneous errors is not a wire contract.

## Canonical bytes and binding

For independently selected validated expected request `Q` and result payload `P`:

```text
request_signing_bytes(Q) = UTF8("HUB-RELAY-REQUEST-v0.1") || 0x00 || JCS(Q)
P.requestDigest = lowercase_hex(SHA256(request_signing_bytes(Q)))
result_signing_bytes(P) = UTF8("HUB-RELAY-RESULT-v0.1") || 0x00 || JCS(P)
Q.brokerKeyId = lowercase_hex(SHA256(provided_broker_public_key_SEC1))
```

Reuse the existing named request digest definition in any later library.
ECDSA P-256 hashes the full result signing bytes with SHA-256 **once**. A
high-level SHA-256 API receives those bytes, not an already-computed digest.
The envelope signature is excluded from `JCS(P)`; explicit nulls are signed.
JCS sorts names recursively by UTF-16 units and does not normalize Unicode.
Payload order is `errorCode,inventory,profileId,requestDigest,state,targetId,version`;
inventory order `node,powershell7,windows`; field order `state,version`.

Require a valid P-256 point in exactly 65 uncompressed SEC1 bytes starting `04`.
Check its hash against `Q.brokerKeyId`, check the named request digest, compare
target and profile separately, then verify strict-DER signature math.
Changing nonce, request ID, broker ID or either generation changes binding.
The request retains operation `windows.runtime_inventory.v0_1`, ordered fields
`["windows","powershell7","node"]` and integer token `ttlMs=60000` under its
existing parser. Inventory's 10-second deadline remains outside this package.

A correctly signed result from a different key fails against original `Q`.
An attacker choosing both `Q` and its matching key can satisfy the math;
transport-supplied values cannot establish trusted provenance.

## T5 and activation remain unavailable

Mathematical consistency proves no enrollment, protected key, biometric event,
freshness, inventory truth, execution, current generations, revocation, durable
single use, authorization or delivery through this chat.
Defer `EnrolledBrokerKey` and enrollment-aware verification to T5. No constructor,
deserializer, test bypass or `enrolled=true` can manufacture that authority.
T5 must resolve protected-store keys, check account/profile/device/generation
policy and revocation, bind broker ID to the pending request and admit release.
If unavailable, report **T5 enrolled-key resolution unavailable**, with no private
result. Signed denials and completed results do not authorize a collector.
Anonymous-request policy, denial emission and replay/delivery admission are
outside this candidate. Android hardware and actual chat MCP remain unverified.

## Future native rejection corpus — pending, not passed

- Raw duplicate/escaped names at every object depth; unique escaped allowed keys.
- Invalid UTF-8, BOM, unescaped controls, invalid surrogate escapes/pairs, trailing values.
- Required null versus omission; null/scalar/array substitutions at every object boundary.
- Payload and final envelope 4095/4096/4097 raw bytes, whitespace, UTF-8 and escapes;
  final serializer cap separately; no unchecked public stress-value constructor.
- Unicode 0/1/128/129 scalars, astral/combining/control/noncharacter cases,
  equivalent escapes, NFC/NFD distinction and recursive JCS ordering.
- DER tags, lengths, minimal signs/ranges, P1363/trailing input, both S forms;
  SEC1 compressed/hybrid/infinity/invalid-point/length matrix at the native boundary.

## Reproduce the delivered checks

From repository root, with existing Node and Python/jsonschema (no installation):

```text
python -m unittest discover -s tests -p test_device_bridge_native_result_proposal.py -v
node --test products/device-bridge/common/native-result/proposal/conformance.cjs
```

The unittest suite also invokes the Node tests, so existing pytest discovery can
exercise them. Missing Node produces an explicit skipped math test, never a pass
claim. Ordinary tests read frozen vectors without rewriting them. Explicit
`node .../conformance.cjs --generate-vectors` regenerates only this package's
vector; OpenSSL ECDSA is randomized, so compare canonical bytes/digests and valid
signatures rather than byte-identical signatures. Provenance records versions.
Native-parser tests and operational activation require separate exact-scope
authorization and protected review. This package changes no runtime or handoff.
