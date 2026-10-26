# Personal broker protected-store bootstrap candidate v0.1

**UNADOPTED PROPOSAL / NATIVE GATES UNPROVEN / OPERATIONAL AUTHORITY ABSENT.**

This private review draft selects an engineering candidate, not an adopted architecture or permission to provision Windows. Intended later proposal-only path: `products/device-bridge/windows/native-pilot/proposals/protected-store-bootstrap.v0_1.md`. No existing contract, source, enrollment record or roadmap is changed.

Traceability: [issue #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933), [PR #2000 exact-head disposition](https://github.com/Voxterrae/HUB_Optimus/pull/2000#issuecomment-6424561842) for `7db7e34454edef58545ec498bec49119da53916a`, and [continuation scope](https://github.com/Voxterrae/HUB_Optimus/pull/2000#issuecomment-6424852135). That disposition does not adopt this new candidate or activate the unmerged parent stack. Human disposition of this proposal, implementation review and live provisioning are separate events.

## Decision and smallest safe deliverable

Propose one dedicated, own-process, personal-only SCM service named `HUBRelayBrokerPersonal`, running as the virtual account `NT SERVICE\HUBRelayBrokerPersonal`. First deliverable after separate approval: private recovery of one newly created software CNG broker key across separate SCM process starts, with explicit owned cleanup and no operational request signing. No enrollment/admission/channel activation belongs to that deliverable.

Current architecture and change surface:

- `identity.rs` creates new user-scoped Microsoft Software KSP P-256 keys, signing-only, export policy zero, without overwrite or machine-key flags.
- Existing `KeyReference` is private-field, in-memory and nonserializable; checked reopen/delete compare name shape, key policy, public SEC1 and SHA256 identity.
- Existing checks do not establish an authenticated persisted ownership record, cross-process recovery, KSP descriptor isolation or a distinct service principal.
- Current `HUB_Relay.NativePilot.Test.` API and behavior remain compatible; existing test keys are never migrated or adopted.
- The proposed recovery boundary is a service token, protected root and independently sealed ownership receipt; a successful DPAPI decrypt is insufficient.
- The enrolled-key proposal remains synthetic: neither this recovery path nor its receipts construct enrollment or protected authoritative store views.
- CNG + CryptoAPI + rasn + HTTP.sys/Schannel remains the selected backend; this proposal adds no substitute listener or TLS trust mechanism.
- T6 SQLite durable admission/release and T7 collection remain separate; Android remains deferred for capacity. All personal, USB and OST data is retained.

Only this Markdown draft is written now. Expected later implementation files are explicitly listed below; none is authorized by their inclusion.

## Principal choice and threat boundary

| Candidate | Disposition and reason |
| --- | --- |
| Dedicated virtual account and own-process SCM service | Selected proposal: distinct local service identity without a manually managed account password; exact service/process binding must be measured. |
| Interactive-user DPAPI file | Recovery-only alternative; any unrestricted process with that same identity can use its protection context. It does not isolate an MCP/transport client from the broker. |
| LocalSystem or shared LocalService | Rejected for this candidate: excessive privilege or shared identity defeats the intended distinct-principal boundary. |
| Dedicated conventional local user | Technically possible alternative, but adds password/profile lifecycle and logon-policy decisions; not a fallback if the chosen candidate fails. |

Microsoft documents virtual-account service configuration and SCM profile loading; neither document proves this particular host/profile/KSP combination. [CreateServiceW](https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-createservicew), [Service User Accounts](https://learn.microsoft.com/en-us/windows/win32/services/service-user-accounts).

The unprivileged MCP/transport process must have a different effective identity. No caller-supplied SID, realm string, `protected=true`, service-name match, or presence of a SID in token groups establishes the broker principal. Capture the actual primary token's `TokenUser`, compare the resolved intended virtual-account SID, and bind it to SCM configuration, running status, PID, held process handle/creation identity and approved image hash. Recheck status/configuration while holding handles; reject PID reuse, impersonation, identity mismatch and unexpected privileges. The token-user SID must be distinct from the interactive/transport principal. [GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation), [QueryServiceStatusEx](https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-queryservicestatusex).

Administrators, SYSTEM, kernel compromise and unrestricted same-principal processes are outside this isolation guarantee. Service identity is not a sandbox or proof of absent network credentials: Microsoft documents that virtual accounts can use the machine identity on a domain network. Bootstrap/recovery code must make no enterprise/network calls; this draft grants no network resource or host access. [Service Accounts](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2012-R2-and-2012/dn617203%28v%3Dws.11%29).

Any company instance requires a different service, `TokenUser` SID, protected root and newly owned keys, plus separate adoption. No personal/company, account, profile, path or principal fallback is allowed.

## Concrete roots, descriptors and immutable bootstrap evidence

Resolve Windows known folders locally in the privileged bootstrap, never from caller environment variables. Candidate product roots are `<ProgramData>\HUB_Relay\Personal` and `<ProgramFiles>\HUB_Relay\Personal`; they must resolve to an approved fixed local NTFS volume. These are proposed future locations, not paths created by this draft.

Create the service and product-owned directory tree only when absent. An existing service or any existing product-owned ancestor/root/leaf causes a stop, including a seemingly compatible old installation. Do not change its ACL, reuse it or automatically select another name. Existing OS-owned known-folder ancestors are inspected, not adopted as application-owned resources. Later upgrade/reinstall needs a separately reviewed procedure.

| Object | Required candidate owner and protected DACL |
| --- | --- |
| ProgramData personal root | Owner SYSTEM; SYSTEM full control; bound service SID read/traverse/create children, without root delete, owner or DACL modification; no other allow ACEs. |
| Recovery artifacts inside that root | Owner bound service SID; SYSTEM full control; bound service SID only the documented read/write/delete rights needed for owned publication/cleanup. |
| ProgramFiles payload and bootstrap/ownership manifests | Owner SYSTEM; SYSTEM full control; bound service SID read/execute or read-only as appropriate; service cannot create, replace, delete or change owner/DACL. |
| SCM service configuration/control | Explicit descriptor permitting the reviewed privileged bootstrap/control identity and only the broker rights actually needed; no interactive or transport principal start/stop/change-config/delete grant. |
| Newly created CNG key | Owner bound service SID; exact allow-list of service SID and SYSTEM; signing/reopen/owned-delete rights and export policy zero. Exact KSP access masks/persistence behavior require native evidence. |

All application filesystem DACLs disable inherited grants; null DACLs, unexpected owners/ACEs, broad groups and effective interactive access fail closed. Descriptor comparisons inspect effective rights and inheritance semantics, not SDDL text equality. ProgramFiles artifacts are immutable to the broker, not to SYSTEM/administrators. KSP descriptor support/readback is a separate gate; do not weaken policy when it is unsupported. Microsoft documents the persistent-key security-descriptor and provider-support properties, not success of this candidate on this host. [Key Storage Property Identifiers](https://learn.microsoft.com/en-us/windows/win32/seccng/key-storage-property-identifiers).

Use handle-bound validation for every component: reject reparse points (including ancestors), UNC/device paths, alternate data streams, unexpected filesystem/volume, short-name or normalization aliases, and multiply linked artifact files. Record final resolved path and volume/file identity; hold directory/file handles to prevent unprivileged replacement while opening descendants, and revalidate after publication. No string-prefix containment check is sufficient. Use exclusive creation; inspect handle metadata and link count. `FILE_FLAG_OPEN_REPARSE_POINT` alone is not proof that ancestors were not traversed. These are requirements for a reviewed implementation, with races and power loss still unproven. [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew), [FILE_STANDARD_INFO](https://learn.microsoft.com/windows/win32/api/winbase/ns-winbase-file_standard_info).

File IDs assist live object binding, not rollback freshness: NTFS/file-system identifiers can be reused over time. No identity tuple or local UUID is treated as a monotonic authority. [BY_HANDLE_FILE_INFORMATION](https://learn.microsoft.com/en-us/windows/desktop/api/fileapi/ns-fileapi-by_handle_file_information).

## Proposed bootstrap ceremony; not a deployment instruction

1. A separately reviewed, hash-pinned privileged bootstrap verifies the exact approved build/source/lock/toolchain manifest, platform/capacity preflight, absent product objects and known-folder parents. Its manifest fixes realm `personal`, service/account, exact service image/arguments, root identities, descriptor expectations, owned-resource list, rollback rules and a random bootstrap correlation ID. This ID provides context binding, never antirollback evidence.
2. It creates only its own roots and immutable payload, applies/readbacks descriptors, then creates a demand-start `SERVICE_WIN32_OWN_PROCESS` service using the virtual account. No automatic restart action, interactive service, listener, URLACL, certificate, trust-store or firewall change is included. Only an explicit approved bootstrap-mode start is permitted.
3. Capture SCM and actual process/token evidence before key work. Verify the effective service profile was loaded, remains distinct, and supports current-user DPAPI and user-scoped Microsoft Software KSP after SCM logon. Missing/temporary/unusable profile or any identity uncertainty stops. Do not provision ad hoc credentials or use interactive-user or `CRYPTPROTECT_LOCAL_MACHINE` fallback.
4. The approved service in bootstrap mode creates exactly one fresh owned key, with a future fixed internal candidate namespace `HUB_Relay.Personal.BrokerOwned.v1.` plus an internally generated random suffix. This is a separate private production-candidate path; it does not change `create_owned()` or accept names from public input. Preserve the exact live creation handle and provenance until publication completes. Read back provider, algorithm, size, export/usage policies, public identity and descriptor.
5. The service creates a bounded recovery artifact in its protected root, protects it with current-user DPAPI and no UI, writes/flushes an exclusive staging object, then publishes to an absent fixed destination without replacement. Reopen through checked handles and verify bytes, DPAPI round trip, context, descriptor and CNG identity. A documented publication/flush sequence must be reviewed and subjected to crash tests; atomic rename is not alone a power-loss durability claim.
6. A bounded, one-shot local bootstrap exchange binds the service's freshly created-key receipt to the verified SCM process and the current ceremony. Both endpoints authenticate the actual OS peer; a PID/string/nonce supplied by the peer is insufficient. The exact peer-authentication API and anti-replay/handle-lifetime checks are an implementation-review gate. No general import/adopt or transport-facing receipt endpoint exists.
7. The privileged bootstrap seals an immutable ownership manifest under ProgramFiles, create-only, with the creation ceremony, service SID, root identity, fixed purpose/namespace, exact private key reference, public SEC1/SHA256, recovery-artifact digest and descriptor policy. It may seal only provenance from this still-live creation session, never an arbitrary decrypted file. Read back and verify the seal's owner/DACL, exact bytes and all bindings. Stop bootstrap mode; a later SCM process must independently recover before a rehearsal is accepted.

The immutable plan manifest and final ownership manifest are separate local artifacts. The latter proves ownership only within this trusted-bootstrap threat model; its hash is integrity evidence relative to the protected installation, not attestation, human approval or restore detection. Recovery requires both protected manifests and the exact published artifact. The service cannot mint a replacement ownership seal for a different key.

Microsoft documents DPAPI's user-scoped default and machine-scope relaxation. This proposal uses `CRYPTPROTECT_UI_FORBIDDEN`, no prompt, and never `CRYPTPROTECT_LOCAL_MACHINE`. Optional entropy, if fixed context is used, is not a secret or independent authority. Actual virtual-account decryption after process restart/reboot is still untested. [CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).

## Recovery format, ownership and failure behavior

Candidate private binary artifact: fixed magic/version, checked total length, one field order and no optional/unknown/trailing fields; maximum encrypted artifact 16 KiB and decoded payload 4 KiB, enforced before allocation/DPAPI decoding and afterward. Exact encoding/length arithmetic is reviewed before implementation; no public serializer/deserializer is added to `KeyReference`.

Decoded fields bind schema version, personal realm/context digest from the immutable bootstrap plan, service `TokenUser` SID, root volume/file identity, bootstrap correlation ID, fixed broker-signing purpose/provider/namespace, exact internally generated key name, 65-byte uncompressed SEC1 and its 32-byte SHA256. No private key bytes, enrollment generation, current broker-start generation, caller identity, TLS pin or transport-controlled value is stored as ownership authority. The manifest independently pins the same fields and the published encrypted artifact digest.

Recovery accepts no caller path/name/reference. It first authenticates process/root/manifests, verifies the exact artifact hash and bound fields, then opens the exact CNG object and reads back KSP, algorithm, length, policy, public identity and security descriptor. Only then may an unexported `OwnedBrokerKey` wrapper exist. Unknown names, a valid DPAPI artifact for another owned key, a different purpose/root/realm and a substituted key+matching-public-point pair all fail before adoption or deletion. DPAPI authenticity and signature mathematics alone never mint this wrapper.

Restart retains the exact own key identity but creates a new in-memory broker-start generation for later pending-request binding. Restart is not reenrollment. Missing, malformed, mismatched, unpublished or inaccessible evidence causes a bounded local denial with no reference/name/private-path leakage. Never repair, regenerate, overwrite or silently choose another key.

Explicit owned deletion requires the protected ownership manifest, exact current artifact binding, private ownership wrapper and fresh CNG policy/public-identity/descriptor readback. It is not a public `delete(name)` facility. Existing test `KeyReference` deletion behavior stays unchanged. A valid foreign artifact must confer neither reopen/adoption nor cleanup authority.

On failure before a trustworthy persisted receipt, cleanup may delete the exact newly created key only while the live creation provenance/handle remains available. A crash after CNG finalization but before the ownership receipt can leave an orphan. Record an unresolved resource count/status if known; do not enumerate, adopt or delete unknown containers to hide the gap. After restart, absence of the receipt is a denial, not a scavenging instruction.

Rollback checks the exact owned-resource journal and current identities/descriptors before each removal; it removes only resources created by this ceremony and keys with live provenance or a validated persisted ownership receipt. No recursive sweeping, foreign service/profile cleanup or deletion of personal/USB/OST data. Report each owned removal, refusal, orphan possibility and cleanup failure alongside the original failure; a cleanup error fails acceptance. Do not claim the SCM-created profile can safely be deleted by application rollback.

## Explicit unresolved authority gates

Full backup restoration can restore the protected artifacts, key/profile and local UUID together. DPAPI, a local seal, file IDs and an epoch beside its own backup cannot detect that rollback. This proposal deliberately selects no antirollback anchor. Before authoritative enrollment/admission/release, a separately adopted design must provide externally justified, durable, never-reused mutation epochs through restart and restore, a trustworthy recovery procedure and native adverse-restore evidence. Unavailable freshness must deny authority.

There is no enrollment row, `EnrolledBrokerKey`, `VerifiedEnrollment`, authoritative `StoreView`, protected pending request or accepted app/biometric/TLS identity here. App attestation, per-use biometric proof, distinct signing/TLS roles, freshness/revocation and exclusive trust validation remain gated. T6 SQLite transactions, durable one-use admission and same-caller atomic release are not smuggled into this owned-reference slice. T7 and real chat-to-Windows invocation stay unavailable.

## Exact later implementation map and private interfaces

All paths below are relative to `products/device-bridge/windows/native-pilot/` and require their own approved implementation scope.

| Candidate file | Narrow responsibility |
| --- | --- |
| `src/service_identity.rs` | Private SCM/process/token/profile binding; no claimed protectedness from flags or caller strings. |
| `src/protected_root.rs` | Checked known-folder root handles, ownership/DACL/path/link checks and bounded create-only publication. |
| `src/owned_reference.rs` | Bounded private DPAPI codec and recovery against the immutable owned-key manifest; no enrollment types. |
| `src/bootstrap.rs` | One-key creation provenance, authenticated one-shot receipt, fail-closed state transitions and owned rollback journal. |
| `src/bin/personal_broker_service.rs` | Minimal SCM lifecycle and fixed bootstrap/recovery test modes; no operational listener or collector. |
| `src/bin/personal_broker_bootstrap.rs` | Reviewed privileged create-only ceremony and SYSTEM-owned manifests; isolated explicit provisioning entry point. |
| `src/identity.rs` | Private namespace-separated creation and KSP descriptor validation; preserve existing public test API. |
| `src/lib.rs`, `Cargo.toml`, `Cargo.lock` | Private wiring and only necessary reviewed Windows features/dependency closure; no unrelated dependency change. |
| `tests/protected_store_bootstrap.rs` | Native process/principal/crash/substitution/ACL fixtures with exact owned cleanup. |
| `tests/verify_recovered_identity.cjs` | Independent Node verification using only public points/digests/signatures from two service processes. |

Private sketch only: `capture_service_identity() -> ServiceIdentity`; `open_bound_root(&ServiceIdentity, &SealedBootstrapManifest) -> ProtectedRoot`; `create_new_owned(&BootstrapSession, &ProtectedRoot) -> UnpublishedOwnedKey`; `publish_owned(&mut BootstrapSession, UnpublishedOwnedKey) -> SealedOwnershipReceipt`; `recover_owned(&ServiceIdentity, &ProtectedRoot, &SealedOwnershipReceipt) -> OwnedBrokerKey`; `delete_owned(OwnedBrokerKey, &SealedOwnershipReceipt) -> OwnedCleanupReport`. Types are private/nonserializable, constructors require measured inputs, and errors grant no authority. Root/manifest inputs come from fixed protected installation selection, never request deserialization.

## Required native acceptance evidence

| Gate | Required positive and negative evidence; none claimed now |
| --- | --- |
| Actual principal | SCM configuration/status/PID/image and actual `TokenUser` agree; distinct unprivileged transport principal is measured. Wrong token, changed configuration, service replacement and stale/reused PID deny. |
| Profile/persistence | SCM-started process A creates/protects; stopped A and separately started B reopen the same public identity and sign a fresh challenge; repeat after approved reboot. Missing/unusable profile denies, without machine-scope fallback. |
| Independent verification | Node verifies both processes' P1363 signatures and SHA256(SEC1); changed challenge/signature/wrong public key fail. CNG sign/verify alone does not satisfy this gate. |
| Actual isolation | Authorized service can read/decrypt/reopen/sign. Distinct unprivileged principal cannot read/replace artifacts or open/use/delete the KSP key; copied ciphertext cannot decrypt. Collect actual OS denial statuses. ACL inspection alone is insufficient. |
| Same-user control | A second unrestricted process under the same test identity can access its own DPAPI/KSP control as expected. Report this successful control explicitly; it proves no same-principal isolation. |
| Ownership substitution | Replace with a legitimately DPAPI-protected foreign record, including one with a matching foreign key/public hash, same SID and valid format. Immutable receipt/root/purpose/hash binding rejects adoption and deletion; both genuine keys remain usable until their own cleanup. |
| Byte and path bounds | Tampered, truncated, oversized, unknown-version, trailing bytes and length-overflow records deny; wrong owners/DACLs, reparse ancestors/leaves, hardlinks, path aliases and concurrent replacement deny without touching foreign objects. |
| Interrupted publication | Inject termination/failure before/after key finalization, artifact write/flush/publish and ownership-manifest publication. No partial state becomes authority; no overwrite/regeneration; finalization-before-receipt orphan remains visible and unadopted. |
| Restart and restore | Restart preserves key identity and changes process-start generation. Restored whole-installation snapshot is explicitly not shown fresh; no enrollment/admission/release is emitted. |
| Rollback | Exact owned service/files/keys are accounted for; owned-key deletion is checked by failed reopen. Original failure and every cleanup failure/refusal are preserved. Unrelated data is untouched. |

Native runs need a reviewed isolated test/provisioning plan, existing capacity guards and a distinct unprivileged test principal; no existing personal/enterprise data supplies fixtures. GNU foundation results do not satisfy MSVC production compatibility. Approval of a proposal does not waive these gates or authorize installing a toolchain.

## Concrete human approval artifact and disposition

Before any real service/root/account-context/key provisioning, present one reviewed activation bundle: exact source head and build SHA256s; lock/toolchain/platform evidence; this proposal's adopted revision; fully resolved personal-only service/account/paths and exact descriptors/privileges; fixed disabled-network test modes; bounded bootstrap exchange; one-key namespace and publication/receipt format; exact owned resource manifest; capacity limits; native test matrix; stop conditions and rollback/orphan report format. The human approves that immutable bundle's hash, scope and target host. Placeholder paths, a branch title, earlier exact-head approval or this AI document are insufficient.

This candidate still needs human disposition, independently reviewed peer-authentication/publication details, native virtual-account profile/KSP/ACL evidence and later antirollback design. It makes the principal/root/ownership direction concrete without claiming those gates passed. This draft performs no bootstrap, build, installation, service/account change, deletion, trust/network mutation or data collection.
