# Personal bootstrap and anchor inventory proposal v0.1

**PROPOSAL / DIAGNOSTIC ONLY / NO ACTIVATION OR ROOT AUTHORITY.**

Date: 2026-10-30. Source baseline:
`37a9bbd293536070149e762af24140751b9a3a64`.
Scope follows [PR #2015's approval record](https://github.com/Voxterrae/HUB_Optimus/pull/2015#issuecomment-6529999806).
This document proposes the next implementation boundary. It neither adopts an
executable contract nor approves a host, executable, launcher or activation bundle.

## Existing foundation and proposed increment

The [parent proposal](protected-root-ancestors.v0_1.md) controls ancestor policy,
application descriptors, independent acquisition and the three-directory rehearsal.
Its original proposal banner is historical; use the exact GitHub disposition for
adoption state. This document does not change its masks, principals or descriptors.

- `ancestor_chain.rs` has a fixed, read-only ProgramFiles OS-policy diagnostic.
- `relative_ntfs.rs` retains metadata handles and checks identity and namespace.
- `security_descriptor.rs` captures bounded owner/DACL bytes and separates OS
  ancestor policy from strict application descriptor policy.
- `bootstrap_peer.rs` captures selected process/token facts for a separate exchange.
- `service_identity.rs` observes SCM/process facts; pathname equality is not loaded
  image provenance. Its existing literal image path is not this proposal's anchor.
- These components do not independently approve their initial observations.
- Proposed next increment: one fixed collector, bounded validation and a private
  versioned receipt; no authority object, creator, installer or service launcher.

There are three distinct phases: read-only inventory; independent review and
approval of an exact activation bundle; later acquisition and separately approved
creation. Inventory may complete while every activation gate remains closed.

## Fixed route and observation limits

Propose a private `collect_personal_bootstrap_inventory()` entry point with no
arguments. A later diagnostic executable accepts no additional CLI arguments,
stdin configuration, environment-selected paths, PIDs, service names or trust flags.
An output stream carries evidence only; it is not an input to trusted acquisition.

Observe only the current process and current thread, their token context, and
the retained OS directory chain from its volume root through 64-bit ProgramFiles.
Select `FOLDERID_ProgramFiles` (`905e63b6-c1bf-494e-b29c-65b732d3d21a`) in a native
64-bit process. Refuse unsupported architecture; no x86, ProgramData, drive-letter
fallback, caller-selected root or remote-machine option.

Stop at ProgramFiles. Do not open or enumerate `HUB_Relay`, `Personal`, `State`,
other product trees or the pathname returned for this executable. Do not enumerate
processes, modules, services, disks, profiles or USB devices. Do not query SCM or
resolve account names in this slice. Product/service collision status is explicitly
`not_observed`; later absence checks are advisory and never authorize creation.
A preexisting object remains a collision under the parent's exclusive-create rule.

## Candidate API plan and access rights

These are proposed collection obligations, not a claim that their composition is
implemented. Existing directory/descriptor helpers may be reused only after review
of their actual bounds and cleanup behavior. No right is broadened on access denial.

| Observation | Candidate calls and smallest requested rights |
| --- | --- |
| Own process | `DuplicateHandle(GetCurrentProcess(), GetCurrentProcess(), GetCurrentProcess(), ...)`, noninheritable, options zero, desired `PROCESS_QUERY_LIMITED_INFORMATION` (`0x1000`); retain the real handle. No arbitrary `OpenProcess` or VM-read access. |
| Process facts | `GetProcessId`, `GetProcessTimes`, `QueryFullProcessImageNameW` with flags `0` and `PROCESS_NAME_NATIVE`, and `IsWow64Process2`, using that retained process handle. No process wait is needed, so no `SYNCHRONIZE` request. |
| Primary token | `OpenProcessToken` with `TOKEN_QUERY` (`0x0008`); `GetTokenInformation` for the classes below. No duplicate, adjustment, assignment or source-query rights. |
| Thread context | `OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, TRUE, ...)`; retain and inspect a returned token, then refuse further collection. Only `ERROR_NO_TOKEN` establishes observed nonimpersonation; other errors refuse. |
| Known folder | `CoInitializeEx(NULL, COINIT_MULTITHREADED)` and `SHGetKnownFolderPath` with the fixed ID, flags zero, token NULL. Copy bounded UTF-16; always `CoTaskMemFree` a returned allocation. Balance successful COM initialization, including `S_FALSE`, with `CoUninitialize`. |
| Directory chain | Existing volume-root open and relative `NtCreateFile` observation path, with `READ_CONTROL \| FILE_READ_ATTRIBUTES \| SYNCHRONIZE` (`0x00120080`), noninheritable handles, `FILE_OPEN`, no mutation or backup-intent rights. Retain existing no-reparse and terminal-completion checks. |
| Object and volume | `GetFileInformationByHandleEx` with `FileIdInfo`, `FileStandardInfo`, `FileAttributeTagInfo`; `GetFileType`; `GetVolumeInformationByHandleW`; `GetFinalPathNameByHandleW` with normalized GUID and NT-device formats. Use the retained metadata handles. |
| Mount observation | `GetVolumeNameForVolumeMountPointW` on the known-folder drive root; `GetDriveTypeW` on the observed GUID root. These name-based results are compared with handle observations, not accepted as independently trusted identities. |
| Owner/DACL | `GetSecurityInfo(SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION \| DACL_SECURITY_INFORMATION)` using `READ_CONTROL`; checked copy, then `LocalFree`. No SACL query or security privilege. |
| Privilege names | `LookupPrivilegeNameW` with system name NULL, for each captured LUID; bounded local lookup, no remote account or domain lookup. |
| Timing | `GetSystemTimeAsFileTime` for diagnostic UTC timestamps; monotonic elapsed time from the standard library. Wall-clock time is not freshness authority. |

Microsoft documents [process duplication](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle),
[process-token access](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocesstoken)
and [thread-token access](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openthreadtoken).
`OpenAsSelf=TRUE` changes the access-check context; it does not remove impersonation.
[Process times](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes),
[image names](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-queryfullprocessimagenamew)
and [architecture](https://learn.microsoft.com/en-us/windows/win32/api/wow64apiset/nf-wow64apiset-iswow64process2)
are observations available with limited process-query access.

[Known-folder allocation](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shgetknownfolderpath),
[NtCreateFile dispositions](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile)
and [descriptor access/lifetime](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo)
support the proposed ownership rules. API documentation does not prove this
user-mode binding or exact rights work on a particular Windows build.

A volume record combines the observed GUID, NT-device name, 64-bit volume serial
from `FILE_ID_INFO`, root file ID and anchor file ID. Retain any separately queried
32-bit filesystem serial as a distinct field; never silently substitute widths.
[File identity](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info),
[handle volume information](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationbyhandlew)
and [final paths](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew)
describe current objects, not cryptographic disk identities.
[GUID mapping](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumenameforvolumemountpointw)
can return one of several GUID paths; aliases are not silently approved.
[DRIVE_FIXED](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdrivetypew)
does not prove that storage is non-USB or independently approved personal hardware.

## Token capture and interpretation

Query `TokenUser`, `TokenOwner`, `TokenPrimaryGroup`, `TokenGroups`,
`TokenRestrictedSids`, `TokenPrivileges`, `TokenIntegrityLevel`, `TokenStatistics`,
`TokenType`, `TokenSessionId`, `TokenElevationType`, `TokenElevation`,
`TokenHasRestrictions`, `TokenIsAppContainer`, `TokenCapabilities`,
`TokenMandatoryPolicy`, `TokenUIAccess`, `TokenVirtualizationAllowed` and
`TokenVirtualizationEnabled`. Query `TokenImpersonationLevel` only for an
impersonation token; primary-token absence is explicitly not applicable.

Bracket every token capture with `TokenStatistics` on that same retained handle;
require identical `TokenId` and `ModifiedId` before and after all class queries.
Before acceptance, reopen the token currently associated with the retained process
using `OpenProcessToken(TOKEN_QUERY)`, capture it with the same brackets and compare
its identity, modification ID and complete declared context with the initial token.
Close the new handle with checked cleanup. Capture-time modification or persistent
token replacement refuses; equality still cannot exclude ABA or changes afterward.

Preserve every returned entry and all raw attribute bits in the selected group,
restricted-SID, capability and privilege arrays. Do not discard disabled,
deny-only, default-enabled or used-for-access entries. Sort a copied comparison
view while retaining multiplicity; never normalize unexpected bits into approval.
This is complete capture of these arrays, not every security property Windows
might associate with a token. No effective-access or unrestricted-token claim follows.

Use [GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation)
and its [information classes](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class).
Preserve [group attributes](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_groups),
[privilege attributes](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_privileges)
and [token identifiers](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_statistics).
[LUID name lookup](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupprivilegenamew)
is local interpretation, not a cross-boot identity guarantee.

Require a primary process token and observed nonimpersonation before filesystem
collection. Present impersonation, anonymous-token error, unsupported class,
unknown layout or partial capture refuses. Do not clear impersonation or retry
with a different identity. App-container context refuses this narrowly scoped route.
The existing `TokenHasRestrictions` one-byte compatibility handling is historical
native evidence; this collector must explicitly validate any adopted exception.

An administrator group, elevation state, integrity label or SYSTEM TokenUser
does not approve execution. No privilege is enabled, removed or adjusted.
This proposal does not select SYSTEM, a scheduled task, service or elevation
launcher. The future approved profile must specify exact principal, groups,
privileges and attributes, session/context, supported layouts and launch procedure.
Any required creation privilege or SYSTEM-owner assignment remains a separate
design and native-evidence obligation; an elevated inventory does not satisfy it.

## Proposed private receipt v0.1

Propose UTF-8 JSON with fixed `schema="hub_relay.bootstrap_inventory.v0.1"`.
This is a proposed representation, not an adopted schema file or public API.
Reject unknown fields and duplicate keys in future validation. It has no handle
field, capability, trusted flag, approved-root wrapper or authority deserializer.

`u16/u32` are JSON integers in their unsigned ranges; `i32` is a JSON integer
from -2147483648 through 2147483647. `u64s` is decimal text (`0` or a nonzero
leading digit followed by digits) within 0..18446744073709551615. `hex(N)` is
exactly 2*N lowercase hexadecimal digits. `bytes={hex:string,byte_count:u32}`
requires exactly 2*byte_count lowercase hex digits. `path={text:string,utf16_units:u32}`
requires lossless valid UTF-16, no embedded NUL, and an exact code-unit count
excluding terminator; reject malformed encoding. `Luid={low:u32,high:i32}`.

| Field | Type, origin and meaning |
| --- | --- |
| `schema`, `mode` | Fixed strings above and `diagnostic_only`. |
| `outcome` | `observed` or `refused`; `observed` means complete declared capture, policy match and checked cleanup only. |
| `activation` | Fixed `blocked`; `loaded_image_provenance` fixed `not_established`. |
| `collector` | `{source_commit:hex(20),policy_sha256:hex(32),target:string}` embedded build claims, independently unverified by this receipt; target at most 128 ASCII bytes. |
| `started_utc`, `finished_utc` | `u64s`, FILETIME 100-nanosecond ticks since 1601-01-01 UTC from the system clock. |
| `elapsed_ms` | `u64s`, monotonic elapsed milliseconds, including checked cleanup; no trusted freshness claim. |
| `process` | `{pid:u32,creation_utc:u64s,process_machine:u16,native_machine:u16,image_win32:path,image_native:path}` from the retained process handle and APIs above. |
| `primary_token`, `thread_token` | Token records below; thread token null only with explicit `thread_context="no_token"` or recorded failure. |
| `thread_context` | `no_token`, `present` or `unknown`; present/unknown requires refusal. |
| `anchor` | `{known_folder_id:string,resolved_path:path,volume_guid:path,native_root:path,volume_serial64:u64s,filesystem_serial32:u32,filesystem:string,drive_type:u32}`; fixed ID and API observations above, filesystem bounded to 31 UTF-16 units. |
| `ancestors` | Root-to-anchor array of `{index:u32,path:path,native_path:path,volume_serial64:u64s,file_id:hex(16),attributes:u32,reparse_tag:u32,delete_pending:bool,owner_dacl:bytes,policy_result:string}`; policy result `match` or `refused`. |
| `recheck` | `equal`, `changed` or `not_completed`, covering process identity, primary token, thread context, mapping and every retained ancestor. |
| `product_collision`, `service_collision`, `service_sid_binding` | Fixed `not_observed`, `not_observed`, `external_evidence_required`. |
| `errors` | Ordered array of `{kind:string,phase:string,operation:string,domain:string,code:u32_or_null,reason:string_or_null,ancestor_index:u32_or_null}` with the closed enums below; no arbitrary error text. |
| `cleanup` | `complete` or `failed`; errors retain each cleanup failure after the primary failure. |

Each token record contains `type:u32`, `impersonation_level:u32_or_null`,
`user:bytes`, `owner:bytes`, `primary_group:bytes`, `integrity:{sid:bytes,attributes:u32}`,
`groups`, `restricted_sids` and `capabilities` arrays of `{sid:bytes,attributes:u32}`,
and `privileges` array of `{luid:Luid,name:string,attributes:u32}`.
It also contains `token_id`, `authentication_id`, `modified_id` as Luid;
and `session_id`, `elevation_type`, `elevation`, `has_restrictions`,
`is_app_container`, `mandatory_policy`, `ui_access`, `virtualization_allowed`,
`virtualization_enabled` as u32 from the corresponding information classes.
These IDs support within-run comparison, not serialized authorization.

All listed keys are mandatory. Only `process`, `primary_token`, `thread_token`,
`anchor`, `ancestors` and the explicitly `_or_null` fields may be null; no nested
partial records. Refusal may null unavailable/omitted observation records; complete
records retain every field. An observed receipt requires nonnull process/primary
token/anchor/ancestors, `thread_context=no_token`, null thread token, `recheck=equal`,
`cleanup=complete` and empty errors. Refused requires at least one error.
Arrays are complete or their entire top-level observation record is null.

Error enums: `kind` = `primary`, `cleanup`, `receipt`; `phase` = `initial`,
`capture`, `recheck`, `cleanup`, `serialize`; `domain` = `win32`, `hresult`,
`ntstatus`, `internal`. `operation` is exactly one of `DuplicateHandle`,
`GetProcessId`, `GetProcessTimes`, `QueryFullProcessImageNameW`, `IsWow64Process2`,
`OpenProcessToken`, `OpenThreadToken`, `GetTokenInformation`, `CoInitializeEx`,
`SHGetKnownFolderPath`, `CreateFileW`, `NtCreateFile`, `NtQueryInformationFile`,
`GetFileInformationByHandleEx`,
`GetFileType`, `GetVolumeInformationByHandleW`, `GetFinalPathNameByHandleW`,
`GetVolumeNameForVolumeMountPointW`, `GetDriveTypeW`, `GetSecurityInfo`,
`LookupPrivilegeNameW`, `CompareStringOrdinal`, `CloseHandle`, `LocalFree`,
`validate` or `serialize`. Native domains require `code:u32` holding the exact
32-bit status bits (including HRESULT/NTSTATUS), with `reason=null`. Internal
errors require `code=null` and `reason` exactly `unsupported`, `malformed`,
`bound`, `policy`, `impersonation`, `app_container`, `token_changed`, `drift`,
`budget` or `receipt_bound`. Index is null or 0..127 for the affected ancestor.

Allow at most one primary and one receipt error; cleanup errors have phase `cleanup`.
Keep the primary error first if present, then every cleanup error in occurrence
order, then any receipt error; never replace an earlier error with `receipt_bound`.
On output overflow, null all five observation records and append one
`{kind:receipt,phase:serialize,operation:serialize,domain:internal,code:null,reason:receipt_bound,ancestor_index:null}`
error, retaining metadata, context/recheck outcomes and every existing error.
The complete minimum refused shape is shown below; C is the complete collector
record, T0/T1/D are the collected u64s timings, X/R/K are the retained thread,
recheck and cleanup enums, and E is the complete nonempty error array:
`{schema:"hub_relay.bootstrap_inventory.v0.1",mode:"diagnostic_only",outcome:"refused",activation:"blocked",loaded_image_provenance:"not_established",collector:C,started_utc:T0,finished_utc:T1,elapsed_ms:D,process:null,primary_token:null,thread_token:null,thread_context:X,anchor:null,ancestors:null,recheck:R,product_collision:"not_observed",service_collision:"not_observed",service_sid_binding:"external_evidence_required",errors:E,cleanup:K}`.
This is typed notation; serialize every property name as a quoted JSON string.

## Bounds, lifetime and failure rules

Retain the existing 32,767 UTF-16-unit path ceiling and 128-directory chain ceiling.
These bound a fixed known-folder walk, not an arbitrary filesystem scan.
Token buffers and each descriptor copy are limited to 65,536 bytes; each SID to
68 bytes; each group-like array to 2,048 entries; privileges to 256 entries and
each privilege name to 256 UTF-16 units. Oversized but valid Windows data refuses.
These conservative caps limit local copying/parsing, not all Windows allocations.

Use at most one size query and one bounded retrieval per variable token class;
growth or inconsistent returned length refuses. Validate alignment, header size,
checked count arithmetic and every embedded SID pointer/extent against the
returned buffer before dereferencing. Copy owned values before releasing buffers.
Never infer readable memory from a claimed count or `IsValidSid` alone.

Bound serialized output to 32 MiB, including JSON escaping and hex expansion,
and errors to 256 entries. Before acquisition reserve all error slots and 128 KiB
for the minimum refused envelope above. Stop collection on the first failure;
retain at most 128 directory handles, four process/token handles and one descriptor
allocation, with no cleanup retries. Their errors plus primary/receipt errors fit
the reserve. Preserve all errors when discarding oversized observation data; if
reserve allocation or final output fails, emit no valid receipt. Individual bounds
do not override the aggregate bound.

Apply a 10,000 ms monotonic observation budget checked between calls and before
acceptance; exceeding it refuses. This bounds accepted elapsed observation, not
native-call execution time. A blocked synchronous OS call may exceed it.
Keep the existing non-unwinding fatal-pending rule while NT buffers may be live;
do not invent cancellation, successful timeout cleanup or a receipt after abort.

Recheck before acceptance, then close resources in reverse acquisition order:
directory children before parents, token before process, and paired allocations
before their owning scope ends. Check `CloseHandle` and `LocalFree` results;
COM/path frees have no success return to invent. Preserve cleanup failures
alongside the primary error. Emit `observed` only after checked cleanup.
An incomplete output write or process crash supplies no valid receipt.

Pre/post equality can miss ABA, privileged mutation, transient token replacement
or replacement after the final check. Retained IDs and sharing do not freeze the namespace or process.
Refuse detected drift without repair, rights escalation, retry under another
principal, create/delete operations or reopening a changed object as trusted.

## Independent bundle and the closed loaded-image gate

Read-only capture establishes reported process names, creation time and token
observations. It does not open this executable by pathname, hash its bytes,
enumerate loaded modules, verify signatures or inspect process memory.
Even adding a file hash, version, signature or SCM string would not prove that
those bytes supplied the currently loaded image or its executable dependencies.

**Activation remains blocked until a separately reviewed launch/provenance design
provides independently verifiable binding from approved executable artifacts to
the actual created process and its loaded image/dependencies.** That design must
name its supported Windows mechanism, exact APIs/access rights, protected launch
inputs, verifier trust root, retained evidence/lifetimes and failure behavior.
Native negative evidence must cover pathname replacement after launch, an
unexpected executable dependency, wrong process/token and missing provenance.
Each must refuse before any creation. No mechanism or proof is claimed here.

The next concrete decision is owner review of that launch/evidence design and
its measured limits. Until it is adopted and demonstrated, a bundle cannot pass
this gate. Human approval of a pathname, collector receipt or unmeasured promise
does not manufacture missing native evidence. Code injection, kernel compromise,
privileged ABA and unrestricted same-principal code remain outside the parent's
isolation claim; this proposal does not assert arbitrary loaded-memory integrity.

The later exact-hash activation bundle must independently bind:

1. Reviewed source commit, build recipe, compiler/linker/SDK/dependency digests,
   output artifacts, policy bytes/digest and supported Windows build/architecture.
2. One approved personal volume GUID/native identity and exact component route,
   with evidence independently checked by the owner; observations cannot approve
   themselves. Serial/GUID/NT-device names do not establish physical provenance.
3. Approved launch procedure and loaded-image evidence above; exact primary-token
   profile and nonimpersonation; live process creation/token binding at execution.
   Do not pin an old PID or LUID as the identity of a future process.
4. Independently verified binary SID for `NT SERVICE\HUBRelayBrokerPersonal`,
   exact planned descriptor bytes and their parent-policy interpretation.
   The no-install SID derivation/binding method requires separate review and
   reproducible evidence; absent evidence blocks creation. Do not create a service
   merely to derive its SID, or accept an observed service-shaped SID as approval.
5. Exact owned-resource list, creation mode, rollback plan, native evidence,
   approval scope/window and explicit reapproval triggers for any relevant drift.

Pin exact artifact bytes and evidence digests. Mutable documentation, current
network lookups, self-reported build stamps and a freshly copied observed ACL
cannot become runtime expectations. Local private evidence needs controlled
retention; a public hash does not make secret or low-entropy data anonymous.

Approval remains with Benjamin Gerrit Hoff under the existing
[owner authority handoff](../../../../../docs/context/OWNER_AUTHORITY_HANDOFF.md)
and [identity manifest](../../../../../config/governance/owner_identity.v1.json).
Verify the applicable GitHub owner record and immutable account ID `249308740`;
AI reports, technical reviews and repository access do not independently approve
the bundle. Do not describe pending hardware-key enrollment as completed.

## Ordered acceptance and delivery

These are requirements for subsequent work, not executed results.

| Order / evidence class | Required evidence and result |
| --- | --- |
| 1. Source review | Fixed no-argument route, no mutating imports/call paths, no authority constructor/deserializer; parent policy and application descriptors unchanged. |
| 2. Mocked parser/receipt tests | Exact-limit and limit-plus-one cases for every bound; malformed offsets, SID extents, arithmetic overflow, size growth, truncation, unknown layouts/fields/enums, null rules and JSON escaping refuse without partial success. Oversized observations preserve the primary and all cleanup errors in a complete minimum refused receipt. |
| 3. Mocked token/API tests | Preserve disabled/deny-only/all attribute bits and duplicate entries; impersonation, anonymous/access errors and unsupported classes refuse. ModifiedId change between capture brackets and replacement of the process token while the old handle remains stable each refuse; reopen/close failures refuse. No privilege adjustment, identity fallback or ABA-exclusion claim. |
| 4. Mocked lifecycle tests | Inject failure at every acquisition/query/recheck/close; reverse cleanup, primary plus cleanup errors, output failure and fatal-pending behavior remain distinct. |
| 5. Separately authorized native read-only evidence | Exact built artifact/host, actual access masks, complete bounded token capture, native architecture, fixed NTFS chain, owner/DACL policy and checked cleanup. No root/service/key creation; preserve the existing 2 GiB capacity floor. |
| 6. Native negative evidence in separately owned fixtures | Wrong volume/mapping, reparse, rename, descriptor drift, token modification during capture, persistent primary-token replacement, denial and exceeded budget refuse. Mocked success is not native evidence; do not mutate OS ancestors for tests. |
| 7. Independent launch/provenance decision | Approved mechanism and measured positive/negative evidence satisfy the closed image gate; otherwise stop before activation-bundle acceptance. |
| 8. Exact owner-approved bundle | Independent volume, build, token/image, SID and descriptor bindings all present and reviewed; no observed value approves itself. |
| 9. Separate creation implementation and approval | Only then consider the parent's three empty directories and verified owned reverse rollback. No retained installation, service or key follows from that rehearsal. |

After proposal adoption, the smallest following implementation is read-only
collection, bounded validation and receipt tests only. Do not combine it with
launcher engineering, SID provisioning, creation or service integration.
Native runs require their own concrete reviewed scope and capacity check.

Keep raw SIDs, paths, volume/file IDs, tokens, descriptors and native receipts
private. Public PR evidence contains source/artifact identifiers, commands,
redacted outcomes and limitations; never publish raw host receipts automatically.
Inventory performs no company-network operation or device probe. Personal files,
USB/OST/backups and synced `sources/` remain untouched; Android stays deferred.

Validation delivered here is source/document review and primary Microsoft API
research only. No native result, installability or operational readiness is claimed.
