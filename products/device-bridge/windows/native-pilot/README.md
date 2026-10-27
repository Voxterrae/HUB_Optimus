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
network listener, certificate, network connection or production channel activation.
Protected principal/token and production ACL/bootstrap, validated enrollment, T6 durable
storage and T7 collection remain separate gates. The existing protocol, result,
fixtures and their dependencies are unchanged. TLS and chat-to-Windows MCP remain
unavailable.

## Dependency and rights boundary

The target-Windows dependency is exactly `windows-sys 0.61.2`, with
`Win32_Foundation`, `Win32_Security_Cryptography`, `Win32_Networking_HttpServer`,
`Win32_Security_Authorization`, `Win32_Storage_FileSystem`, `Win32_System_IO`,
`Win32_System_Pipes` and `Win32_System_Threading`. The unchanged lock contains two registry
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

## Private process-bound bootstrap prerequisite

`bootstrap_peer` is private and dormant. Its module-level `dead_code` allowance
is limited to this prerequisite, which has no production caller or public API.
It neither constructs nor imports a broker key, enrollment, stored reference,
receipt, or admission/release authority. The existing CNG and HTTP.sys modules
and external contracts remain independent.

A trusted launcher must already own each expected peer's process handle. The
primitive duplicates that handle down to query-limited-information plus
synchronize rights, clears inheritance, and retains the resulting handle and a
query-only primary-token handle. It captures the kernel PID, creation time,
token ID, user SID, logon/group SIDs and attributes, authentication LUID,
session, restricted SIDs, privileges, integrity, elevation, app-container and
mandatory-policy context. Terminal checks re-query both the held primary token
and the process's current primary token. Group and privilege lists are compared
directly; the ever-filtered `TokenHasRestrictions` flag is not treated as
`IsTokenRestricted` or as an automatic rejection of an expected UAC context.
This host returns a one-byte `TokenHasRestrictions` value despite the documented
DWORD layout. The query uses initialized DWORD storage and permits only that
observed byte layout or the documented four bytes for this one class; every
other supported scalar requires exactly four bytes. Pipe-supplied identities never select
or open an expected process. Handles stay held throughout the exchange.

The server creates a random local pipe name with 256 random bits, one message
instance, `FILE_FLAG_FIRST_PIPE_INSTANCE`, `PIPE_REJECT_REMOTE_CLIENTS` and
overlapped I/O. Its explicit protected DACL grants only the expected logon SID
the individual client mask `0x00120183`. That mask excludes bit `0x4`,
`FILE_CREATE_PIPE_INSTANCE`; no `FILE_GENERIC_WRITE` grant is made. All endpoint,
event and retained process/token handles are noninheritable. The client opens
with `SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION` and verifies the kernel
server PID against its independently held expected server before its first byte.
The server compares the kernel client PID with its held expected client.

Every message is exactly 96 bytes: magic `HUBBSP01` (8 bytes), version `1`
(1 byte), role (1 byte), reserved zero (6 bytes), ceremony ID (16 bytes), server
nonce (32 bytes), and client nonce (32 bytes). Roles are hello `1`, challenge `2`,
finish `3`, terminal `4`. The ceremony ID is conveyed by the trusted launcher;
each side draws its own fresh nonce from the Windows system RNG. Hello alone
uses an all-zero server nonce. Every other field, role and correlation is exact;
zero nonces, oversized/truncated messages and a replayed hello as finish deny.
There are no keys, secrets, filenames, certificates or receipt payloads.
Consuming endpoints support one exchange and return a private terminal transcript.
This transcript is not creation provenance or durable replay/admission evidence.

On one fresh dedicated server thread, each exact hello and final inbound frame
is immediately followed by `ImpersonateNamedPipeClient`, a real thread-token
query, exact identification-level/context comparison with independently captured
primary evidence, and `RevertToSelf`. A zero `TokenIsAppContainer` value on an
identification token is not an independent app-container exclusion proof; this
primitive relies on the held primary context and the other message checks.
The native function binds the last message
read on that thread. Preexisting impersonation denies without clearing it.
A failed revert terminates the hosting process. See Microsoft's
[message impersonation documentation](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-impersonatenamedpipeclient).

The end-to-end deadline must be positive and at most ten seconds. Overlapped
timeouts request cancellation and observe completion before releasing the
buffer, event or `OVERLAPPED`; cancellation alone is insufficient. A canceled
operation has an additional bounded one-second drain. If completion cannot be
proven within it, the hosting process terminates with the buffers still alive.
No thread is detached. See Microsoft's
[cancellation lifetime requirements](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelioex).

The native fixture is a trusted parent/child launch under the same user/logon,
with an explicit handle-inheritance allow-list. Its process binding checks do
not prove distinct-principal isolation, real PID reuse, service readiness, a
protected broker principal, or protection against administrator/same-user code
with process-modification rights. Production launch, protected principal and
ACL bootstrap, authority construction, enrollment, T6 storage, T7 collection,
and HTTP.sys/Schannel TLS remain separate approved-spec gates. No service,
account/profile, permanent root, URL, network listener, certificate, trust,
firewall or VPN is provisioned by this module or its tests.

On 2026-10-26 in the Windows GNU environment above, the targeted bootstrap suite
passed 14 active cases: 13 native behavior cases and one deterministic frame
policy case. One subprocess fixture entry is intentionally ignored by the main
harness and invoked explicitly with `--ignored --exact` by the native parent
cases; it is not counted as a passing security case. The complete crate suite
passed 29 active cases with that same one ignored fixture entry, including the
15 existing CNG/HTTP.sys cases. Clippy with warnings denied and format check passed. Native output
was captured explicitly, hashed before decoding and checked for the exact counts;
the full suite observed HTTP already `Running` before and after launch.

The tests cover a held parent/child exchange, a different same-SID client,
substituted server rejection before any hello, a dead held expected process and
live replacement, anonymous identification denial, privilege-only filtering and
an additional real restricting logon SID. Both altered-token cases reach the
server's actual last-message context comparison and require its specific denial.
They also cover malformed hello/final/challenge fields, oversized/truncated input,
replayed hello, second connection and second server instance rejection, bounded
connect/read cancellation, disconnect and peer exit, exact preservation of a
preexisting impersonation token, and an inheritable event deliberately omitted
from the child allow-list. Native errors include 1347 (anonymous token), 234
(overlong message), 5 (second instance), 995 (canceled operation after drain) and
109 (broken pipe); frame/context denials are application policy, not fabricated
native statuses. The new peer cases create no CNG keys. No real revert failure,
non-completing driver, primary-token replacement or PID reuse was induced.

## Private file-security descriptor prerequisite

`security_descriptor` is private and dormant. It inspects an already-open
file/directory handle with `GetSecurityInfo`, copies the owner/DACL snapshot,
and compares exact metadata expectations. It opens no path and changes no
filesystem object. A match produces no protected root, authenticated service
identity, creation receipt, owned key, store, enrollment or release authority.
The observation can become stale immediately; it is not an effective-access
calculation or an isolation guarantee.

The application copy/parser accepts at most 64 KiB. `GetSecurityInfo` allocates
its buffer before that check, so the bound does not limit Windows' own
allocation. Explicit `LocalFree` cleanup preserves a primary failure and any
cleanup failure; Drop is only best effort. The parser reads bounded byte slices,
without typed unaligned dereferences or Windows calls on arbitrary test bytes.
It supports revision-1 self-relative descriptors, revision-2/4 ACLs and standard
allow ACEs containing revision-1 SIDs with at most 15 subauthorities. Offsets,
counts, sizes, overlap and supported layouts are checked. Absent/NULL/unprotected
DACLs, unexpected owners, ACE flags including inheritance, unsupported ACE
types, and missing/additional/changed grants deny. Equivalent allow-ACE ordering
matches. Duplicate or split grants to the same SID deliberately deny instead of
being combined; this is a conservative accepted-shape rule, not a claim of full
Windows access-check equivalence.

The candidate root **metadata** rule expects SYSTEM ownership, SYSTEM full
access `0x001f01ff` and an expected service grant of `0x001200ab`: read control,
synchronize, list/read data, add file/write data, read extended attributes,
traverse/execute and read attributes. It excludes add-subdirectory, root delete,
delete-child, write attributes, write DACL and write owner. Any future need for
broader rights requires review. The expected service input must have the
`S-1-5-80` prefix plus five DWORD subauthorities; SYSTEM, Everyone and All Services
are rejected. This is structural validation only: another fabricated service SID
has the same shape. Raw SID shape or equality does not authenticate the virtual
service account or prove that the selected service is running.
The `ADD_FILE` bit is also `FILE_WRITE_DATA`; excluding `WRITE_ATTRIBUTES` alone
does **not** exclude reparse mutation.

Publication remains blocked. A bounded native probe on this host retained a
directory handle with real read-data access and no write/delete sharing, then
successfully opened that same directory with only `FILE_WRITE_ATTRIBUTES` and
set an owned junction. Its file identity stayed unchanged. Both fresh empty
fixtures were deleted through retained identity-checked handles and verified
absent. This matches Microsoft's
[sharing-mode exception for attribute access](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
and [reparse mutation access rules](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/4aeefef8-92c3-4abc-af7a-a610caf8a165).
That short separate probe is not a credited Rust-suite test. No sharing-only
ancestor guard, traversal, staging, rename or publication API is implemented.
Trusted ancestor protection, any handle-relative publication design and its
native validation remain separate gates.

New descriptor tests use exclusively created zero-content local NTFS files and
explicit fixture ACLs. Test-only fixture selection is not a production root
selector. Cleanup uses each retained creation handle, verifies volume/file ID,
deletes that exact object, closes the handle and checks the exact path is absent.
No recursive cleanup or persistent key creation is added. A user-owned fixture
matching its test policy must fail the SYSTEM-owner rule. The current-token
attribute-write probe and the owner's ability to change its own DACL illustrate
why metadata equality does not prove distinct-principal isolation.
The fixture ACL includes `SYNCHRONIZE`, so a synchronous open's implicit request
for that right cannot masquerade as an attribute-write denial. A separate empty
regular-file control using `0x001200ab` allows a `FILE_WRITE_DATA` open, without
writing any content; it demonstrates the shared bit, not safe directory mutation.
Windows normalized duplicate allow entries and removed file inheritance flags
in the native fixtures. Tests inspect the resulting shape; raw-parser cases
separately establish duplicate and flag rejection without claiming those bytes
were retained by NTFS. No OS buffer-free failure is deliberately induced.

Descriptor coverage consists of 16 cases: 11 native file cases and five
deterministic parser/policy/error-accounting cases. The native cases include
equivalent ACE ordering, user-owner versus SYSTEM-owner rejection, null and
unprotected DACLs, changed/broad grants, a stored unsupported deny ACE, the
normalization controls, attribute denial followed by an owner DACL change,
the write-data-bit control, and `GetSecurityInfo` denial without `READ_CONTROL`.
The full crate expects 45 active cases and the existing one ignored subprocess
fixture entry; that entry is exercised explicitly by its native parent tests.
The existing guarded launcher, capacity reserves, raw-output capture and
already-running HTTP prerequisite remain mandatory on this host.

Actual SYSTEM-owned root provisioning, service identity/profile, virtual-account
DPAPI/KSP persistence, distinct-principal denial, immutable sealing,
antirollback/freshness, crash/power-loss durability, protected reference recovery,
enrollment, T6/T7 and HTTP.sys/Schannel TLS remain open gates.

## Private personal SCM/process binding prerequisite

`service_identity` is dormant and private. `HeldScmProcessBinding` owns a local
SCM CONNECT handle, a fixed `HUBRelayBrokerPersonal` service handle with only
QUERY_CONFIG and QUERY_STATUS, and retained noninheritable query/synchronize
process and query-only primary-token handles through `ExpectedPeer`. It returns
no authenticated-service authority, protected root, key, enrollment or receipt.
The fixed principal is `NT SERVICE\HUBRelayBrokerPersonal`; a service SID in a
group never substitutes for actual primary TokenUser equality. A separately
held, measured transport peer must have a different TokenUser.

The internal unmeasured build/test candidate expects OWN_PROCESS exactly,
DEMAND_START exactly, and the quoted command
`"C:\Program Files\HUB_Relay\Personal\personal_broker_service.exe"` with no
arguments. This literal is an expectation, not known-folder resolution, an
installation plan, protected payload or human approval. There is no consumer.
The observed full process path must match exactly; no disk hash is taken and
neither pathname nor SCM configuration proves which approved bytes were loaded.
[SCM configuration may describe the next start](https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-queryserviceconfigw),
so it cannot replace live retained process/token checks.

The candidate configured required-privileges list is empty. An explicit
QueryServiceConfig2 REQUIRED_PRIVILEGES query must succeed and return a bounded
valid MULTI_SZ; null or unsupported layouts conservatively deny. The actual
token inventory must contain exactly the locally resolved SeChangeNotifyPrivilege
with ENABLED_BY_DEFAULT and ENABLED, with no other privileges, even disabled
ones. USED_FOR_ACCESS is deliberately retained and its appearance also denies.
This strict starting policy has not been measured on the personal service;
mismatches require reviewed policy adjustment, never an observed allowlist.
An empty configured list alone does not restrict the OS default inventory.

Configuration buffers are capped at 8192 bytes, allocated from the explicit
sizing result, and parsed only within the supplied allocation, excluding
alignment padding. Interior pointer bounds/alignment, UTF-16 and MULTI_SZ
termination are checked. The API defines pcbBytesNeeded for insufficient-buffer
failure, not as a successful-query byte count. Unknown query errors never become
empty configuration. All base config fields and required privileges are retained
for equality checks; other optional configuration such as failure actions is
not queried and no claim is made about it.

Capture and every revalidation require RUNNING with a nonzero matching PID,
unchanged creation time and token ID, session zero, exact intended local SID,
no AppContainer or unsupported restriction context, unchanged full held/current
primary context (groups, restricted SIDs, privilege attributes, integrity,
authentication and scalar fields), and repeat SCM configuration/status checks.
Calling-thread impersonation denies without clearing it. These snapshots cannot
prove atomic SCM stability or that other service threads never impersonate.
Explicit cleanup preserves primary and cleanup failures; SCM handles use
CloseServiceHandle. Drop is a best-effort fallback.

Tests separate synthetic policy acceptance from native read-only SCM absence
and owned-process/token observations. The fixed-service absence case requires
exact ERROR_SERVICE_DOES_NOT_EXIST (1060); unexpected existence fails without
mutation. Native child tests create only their own hidden subprocesses and
reap them. Ignored child entries are helpers, not independent security passes.
Real personal-service success, actual config parsing on that service, loaded
profile, KSP/DPAPI persistence, cross-principal isolation, service replacement,
PID reuse and primary-token replacement remain uninduced. No service lifecycle,
account, root, profile, key or machine configuration is modified.

## Private relative NTFS metadata prerequisite

`relative_ntfs` is dormant and private. An `ObservedDirectory` consumes an
already-owned handle, verifies its granted rights and duplicates down to exactly
`FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE`. An independently captured
`HeldObjectExpectation` remains alive through the lifetime of each child result
and any checked consuming conversion into a stepped directory observation.
Neither object supplies protected-root, approved-name, service or key authority.
There is no public raw-handle escape, serialized identity, path constructor,
content read, mutation, provisioning or production caller.

Each native open uses one bounded internal ASCII component, a retained parent
as `OBJECT_ATTRIBUTES.RootDirectory`, `OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE`,
`FILE_OPEN`, and `FILE_SYNCHRONOUS_IO_NONALERT | FILE_OPEN_REPARSE_POINT`.
Metadata access shares READ and DELETE but not WRITE. The result must be a
completed `STATUS_SUCCESS` with independent IOSB success, `FILE_OPENED` and a
valid handle. Unsupported flags/statuses deny without retry or absolute-path
fallback. Generated declarations come from the already pinned `windows-sys`
package with only `Wdk_Foundation` and `Wdk_Storage_FileSystem` added.

File ID, standard metadata and attribute/tag queries require local fixed NTFS,
the intended type, no delete-pending state, no reparse tag/attribute, matching
volume and exactly one link for regular files. A bounded normalized volume-GUID
path is observed only to determine the drive type; it is never reopened or used
as prefix-containment proof. Parent and independent expectation checks run
before and after the native open. Calling-thread impersonation denies without
clearing it. Identity mismatch reports the observed IDs without reading content.
IDs and matching metadata confer no authority. Sharing does not freeze names or
prevent in-place tag conversion, and pre/post equality cannot detect ABA.

Synchronous calls unexpectedly reporting pending work, or successful calls
leaving the IOSB untouched, terminate the host while the native buffers remain
alive. Terminal errors retain call NTSTATUS and IOSB separately and close any
acquired handle with checked error aggregation. The classification is tested;
actual fatal termination and a stalled driver are deliberately uninduced.

Native host validation uses only fresh user-owned fixtures beneath the exact
private task directory, at most 1 MiB of
content, and identity-checked DELETE handles with checked cleanup even after
expected assertion failures. Junction targets and sentinel files are owned by
the same run; sentinel hashes use independently retained fixture read handles,
never the metadata primitive. Deterministic precheck/open replacement and
bounded concurrency use ordinary names of two independently held owned files.
Every successful name change is journaled; names are restored before checked
cleanup. Only agreement with the original held object or explicit refusal is
acceptable; an observed comparison identity must be refused. Counters report
actual identities/statuses, not inferred target encounters or independent tests.
During observed concurrent name changes, only the exact normalized-path query
operation with FILE_NOT_FOUND, PATH_NOT_FOUND or ACCESS_DENIED may be counted as
a query refusal. Primary and secondary details are retained in full. A failed
query has no inferred identity; any explicit mismatch must identify the held
original and comparison objects. Unknown identities, operations, out-of-family
errors and actual close failures still fail. PATH_NOT_FOUND is prospective
test coverage, not a previously observed result. Positive same-path child opens
are required before the worker and after name restoration, outside race counters.
The retained-parent rename case captures and renames an empty parent, then
creates its child and independent expectation plus a distinct replacement
directory. It does not claim a child expectation held across directory rename.
Static leaf, stepped-ancestor and empty-parent junction refusal remain separate
cases. Populated-directory conversion was an unsupported fixture precondition;
concurrent in-place reparse conversion remains unproved. These host observations
do not establish universal traversal/containment or absence of ABA. Symlink
privilege is not exercised. Actual SYSTEM/service-root
success, isolation, profile/DPAPI/KSP, publication, durability and activation
readiness remain separate gates.

## Private Windows ancestor observations

`ancestor_chain` is a dormant private observer of the fixed ProgramData and
64-bit ProgramFiles known folders. It rejects thread impersonation, uses flags
zero/null token and balances same-thread COM initialization and path allocation.
Five private Windows function declarations and four constants match the cached
`windows-sys 0.61.2` and `windows-link 0.2.1` ABI/DLL/link definitions, preserving
the original dependency features and lock. They avoid enabling broad Shell,
COM and Globalization modules; actual linking/export availability still requires
guarded native validation. Non-64-bit known-folder resolution remains refused.
The copied drive path is bounded to 32767 UTF-16 units, each OS component to 255,
and the retained chain to 128 steps including its volume root. Spaces and valid
Unicode are preserved; ambiguous namespaces, DOS/short-shaped names, alternate
separators, dot components and malformed UTF-16 refuse without repair.

A native drive-to-volume GUID mapping is observed, then a local fixed NTFS root
and every directory component are retained using metadata-only, noninheritable
handles. The observation-only relative helper shares the original native opener
and fatal-pending handling, but supplies no independent expected-object claim.
Original matched-child expectations and strict product descriptor rules remain
unchanged. Every step compares its complete normalized volume-GUID component
sequence by Windows ordinal comparison, and retains actual bounded owner/DACL
bytes in their original order. Unsupported ACEs remain opaque observations;
they never become policy grants. Parse-before-release ordering and checked
cleanup errors remain preserved for strict descriptor inspection.

Metadata, full paths and opaque bytes are rechecked before/after traversal and
explicitly on demand; known-folder and drive mapping are queried again. Checked
close walks retained handles in reverse and preserves all failures. These
observations can become stale immediately, conservatively reject equivalent
encodings, and do not exclude ABA or establish an atomic security boundary.
No actual product subtree is observed, adopted or created. No permissions are
changed by the observer and there is no service, network or public API wiring.

Tests use only newly owned bounded fixtures with sentinel verification and
identity-checked reverse cleanup. Fixed OS chains are read-only and their
observed/refused outcomes are labelled separately; a refusal is not acceptance.
Fatal pending termination remains deliberately uninduced. OS-ancestor owner/
trustee policy, approved-volume identity, trusted acquisition, privileged
create-only installation, immutable payload evidence and real service/profile
isolation remain separate gates. This prerequisite does not yet fulfil the
operational protected service-folder goal or authorize Android installation.

## Rollback

For the descriptor increment, revert only `src/security_descriptor.rs`,
`src/security_descriptor/tests.rs`, its registration in `src/lib.rs` and this
README section. It creates no persistent application resources or authority.

For this bootstrap increment, revert only its five reviewed paths: `Cargo.toml`,
`src/lib.rs`, `src/bootstrap_peer.rs`, `src/bootstrap_peer/tests.rs` and this README.
The HTTP.sys foundation remains independent. After protected
integration, use a focused reviewed revert. Code removal does not delete
persistent CNG keys: delete only references owned by the test or application
while they remain available. Never enumerate or delete unrelated containers.
