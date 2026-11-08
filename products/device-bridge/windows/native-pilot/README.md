# Windows native CNG and HTTP.sys resource foundation

Experimental software signing primitive for
[#1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933), exact slice
[approved for review](https://github.com/Voxterrae/HUB_Optimus/issues/1933#issuecomment-6402100533).
This library does not establish enrollment, admission or release authority.

## Scope

The Windows-only library creates a new user-scoped persistent P-256 key in the
Microsoft Software Key Storage Provider. Names use the fixed
`HUB_Relay.NativePilot.Test.` namespace and an internally generated random
128-bit suffix. Creation never overwrites an existing key. Export policy zero
and signing-only usage are set before finalization.

The opaque in-memory `KeyReference` has private fields and no deserializer or
constructor from a caller-supplied name. Reopening checks the expected algorithm,
256-bit length, export and usage policies, public SEC1 point and SHA256 identity.
Explicit deletion performs the same checks before deleting that exact object.
Dropping a handle releases it; persistent keys require explicit deletion. A later
creation failure attempts deletion of its owned object and preserves any cleanup
failure alongside the original error. Errors expose operations and status codes,
never key names or private bytes.

The public point is exactly 65-byte uncompressed SEC1. Its identity is SHA256 of
those 65 bytes, computed with BCrypt. Signing accepts an already computed 32-byte
SHA256 digest and returns the native 64-byte IEEE-P1363 signature, without
rehashing, DER conversion or low-S normalization. Only a normal invalid-signature
status maps to `false`; other native failures remain errors. Handles stay private.

These are software keys. Export denial is not evidence of TPM, hardware or
biometric protection, nor isolation from an administrator or another process with
the same unrestricted user token. The reference provides no cross-process
recovery or authoritative protected reference store. Losing it can leave an
owned persistent object without an application recovery path.

There is no `EnrolledBrokerKey`, `VerifiedEnrollment`, trusted pending/store
producer, request-signing authority, collector, durable replay/admission/release,
listener, certificate, network connection or production channel activation.
Protected principal/token and ACL/bootstrap, validated enrollment, T6 durable
storage and T7 collection remain separate gates. The existing protocol, result,
fixtures and their dependencies are unchanged. TLS and chat-to-Windows MCP remain
unavailable.

## Dependency and rights boundary

The target-Windows dependency is exactly `windows-sys 0.61.2`, with only
`Win32_Foundation`, `Win32_Security_Cryptography` and
`Win32_Networking_HttpServer`. The unchanged lock contains two registry
packages: `windows-sys 0.61.2` and `windows-link 0.2.1`; their complete registry
checksums are recorded in `Cargo.lock`. No new backend, DER codec or Android
component is included. Original contributions follow the root
[IP notice](../../../../IP_NOTICE.md); third-party rights remain applicable.

Both cached package archives match the lock checksums, and all 265 extracted
files match those archives. Both packages declare `MIT OR Apache-2.0`; their
MIT and Apache 2.0 license files were checked in the existing NAS cache.

## Native validation

On 2026-10-26, eight native unit tests passed with no failures or skips on
Windows 10 Pro 19045 x64, using `rustc 1.99.0 (b940084d7)` and
`cargo 1.99.0 (5f94df478)`, target `x86_64-pc-windows-gnu`. Clippy with warnings
denied and the format check passed. A separate Node 24.21 verification passed
for the emitted public SEC1 identity and empty-message P1363 signature, including
changed-message/signature and other-public-key negatives.

From the repository root in that validated environment:

~~~powershell
cargo fmt --manifest-path products/device-bridge/windows/native-pilot/Cargo.toml -- --check
cargo test --manifest-path products/device-bridge/windows/native-pilot/Cargo.toml --target x86_64-pc-windows-gnu --locked --offline -- --test-threads=1 --nocapture
cargo clippy --manifest-path products/device-bridge/windows/native-pilot/Cargo.toml --all-targets --target x86_64-pc-windows-gnu --locked --offline -- -D warnings
~~~

The local GNU run used reviewed GNU Binutils `2.47.20260726` for import-library
generation and the existing Rust self-contained startup objects/libraries. After
refusing conflicting existing Rust flags, its launcher supplied exactly two
arguments through child-only `CARGO_ENCODED_RUSTFLAGS`, separated by ASCII 31:
`-Cdlltool=<VERIFIED_IMPORT_RUNTIME>\bin\dlltool.exe` and
`-Clink-self-contained=yes`. The parent and global environment were unchanged.
The placeholder is a verified local build-tool path, not a product setting.

On the current constrained host, all Cargo and native actions must run through
the task-owned supervisor and existing portable runner: 128 MiB C: preflight,
96 MiB abort, and existing NAS cache/build/TEMP. Do not bypass these guards.
Dependency availability, a space rejection or a non-Windows skipped test is not
native evidence. No SDK, Android or MSVC installation is required by this slice.
GNU evidence does not close production MSVC compatibility.

The native tests create only fresh owned test keys, close handles and explicitly
delete their own keys. Cleanup failures fail the test. They cover
persistence/policy, valid and changed digest/signature/wrong-key verification,
private-export denial without a private output buffer, altered-reference delete
denial, deletion followed by failed reopening, and cleanup after an injected
post-finalization failure. One test emits only a public SEC1/digest/signature
vector over SHA256 of the empty message for separate Node P1363 verification.
Internal CNG sign/verify alone is not independent verification evidence.
The export test first demonstrates that an otherwise matching exportable owned
control supports the identical `BCRYPT_ECCPRIVATE_BLOB` size-only query and
reports a required size of 104 bytes. The policy-zero key must refuse that query with `NTE_PERM` or
`NTE_NOT_SUPPORTED`; success and every other status fail the test. Both keys are
explicitly deleted and checked for failed reopening before the status assertions.
Neither query supplies a private output buffer or requests private bytes.

## Unregistered HTTP.sys resources and later gate

`UnregisteredHttpSys::create_owned()` initializes the v2 HTTP Server API with
`HTTP_INITIALIZE_SERVER`, then creates one server session, an anonymous queue
with null security attributes and flags zero, and an empty URL group. Handles
and IDs remain private; there is no raw constructor, clone or serialization.
No URL is added and no group is bound to a queue. There is no HTTP parser,
receive/send operation or channel-ready API.

`close(self)` attempts all applicable closers in order: `HttpCloseUrlGroup`,
`HttpCloseRequestQueue`, `HttpCloseServerSession`, then `HttpTerminate` with the
same SERVER flag. Setup errors preserve their primary failure plus every cleanup
failure. Explicit-close errors retain the first failure plus every later failure.
Public errors contain operation names and native status codes, never handles or
IDs. Ownership is consumed before each close attempt; uncertain resources are
not retried by Drop. A failed cleanup can leave resources until process exit.
Drop is a best-effort fallback and cannot provide checked cleanup evidence.

[`HttpInitialize`](https://learn.microsoft.com/en-us/windows/win32/api/http/nf-http-httpinitialize)
can start the Windows HTTP driver if it is stopped. On this host, native tests
must use the private supervisor and a runner which reads `Get-Service HTTP`
immediately before the actual harness, requires `Running`, records the after
state and refuses stopped or unavailable states. There is no explicit service
start. That preflight is not atomic and proves neither global-state isolation
nor absence of unrelated traffic. No URLACL, SSL binding, certificate, trust,
firewall, VPN, service/account provisioning or HTTP configuration is performed.

On 2026-10-26 in the same Windows GNU environment, seven HTTP.sys native tests
passed. The final full-crate run passed all 15 cases (eight existing CNG and
seven HTTP.sys), with no failures or ignored cases. Both credited harness runs
recorded the HTTP driver already `Running` before launch and still `Running`
afterward. Their raw native output was captured explicitly and hashed before
decoding; an earlier exit-zero invocation without harness output was not counted
as passing evidence.

The HTTP.sys cases check live v2 property queries, queue non-inheritance,
independent owners, eight repeated lifecycles and setup failures after each of
the four acquisitions. Post-close session/group queries have successful live
controls and a still-initialized observer; stale queue handles fail the same
handle-information query that succeeds on live controls. One test deliberately
closes only its own queue first, then verifies that the real queue-close error
is preserved while group/session/termination cleanup continues successfully.
Two additional cases inject reported cleanup statuses only after the real
native closers succeed, testing aggregation of all errors. Those synthetic
statuses are not evidence of real native failures. All raw snapshots and fault
hooks remain test-private, and checked explicit cleanup supplies the evidence.

The HTTP-only command used the same guarded launcher and flags as above:

~~~powershell
cargo test --manifest-path products/device-bridge/windows/native-pilot/Cargo.toml --target x86_64-pc-windows-gnu --locked --offline approval_https::tests -- --test-threads=1 --nocapture
~~~

HTTP.sys/Schannel remains the selected later channel direction. Resource
ownership does not establish TLS or admission. A CTL is not proof of a private trust anchor.
`HTTP_SSL_CLIENT_CERT_INFO` can deliver `CERT_E_UNTRUSTEDROOT`; native evidence
must still establish the intended handshake, receipt of the client certificate,
exclusive chain validation and pin checks without global trust changes. There
is no claim that every private certificate must always fail. See the
[HTTP_SSL_CLIENT_CERT_INFO documentation](https://learn.microsoft.com/en-us/windows/win32/api/http/ns-http-http_ssl_client_cert_info)
and the existing [T5 proposal](../../common/enrolled-key/proposal/README.md).

## Rollback

For this resource increment, revert only its four reviewed paths: `Cargo.toml`,
`src/lib.rs`, `src/approval_https.rs` and this README. After protected
integration, use a focused reviewed revert. Code removal does not delete
persistent CNG keys: delete only references owned by the test or application
while they remain available. Never enumerate or delete unrelated containers.
