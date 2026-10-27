# Personal protected-root ancestor policy candidate v0.1

**UNADOPTED PROPOSAL / NO ROOT AUTHORITY / NO PROVISIONING OR ACTIVATION.**

Date: 2026-10-28. Source baseline: `8ab0585e9f37fd1d84d6715347a063251b87aa38`
([draft PR #2011](https://github.com/Voxterrae/HUB_Optimus/pull/2011)). This single
add-only document selects a reviewable policy and creation protocol. It changes
no executable, existing contract, dependency, governance rule or roadmap.

## Adopted direction and the missing decision

[PR #2001's exact-head record](https://github.com/Voxterrae/HUB_Optimus/pull/2001#issuecomment-6426000761)
adopted the personal principal/root/ownership direction at
`50ff6a70b2da581962f945ee8158ddb0fa53976c`. Its
[original document](https://github.com/Voxterrae/HUB_Optimus/blob/50ff6a70b2da581962f945ee8158ddb0fa53976c/products/device-bridge/windows/native-pilot/proposals/protected-store-bootstrap.v0_1.md)
is on that separate branch, not copied here. The later
[scope reduction](https://github.com/Voxterrae/HUB_Optimus/pull/2001#issuecomment-6427658371)
requires trusted ancestor protection: sharing restrictions and stable file IDs
did not prevent an attribute-only junction mutation. Related: [#1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933).

Already adopted: `NT SERVICE\HUBRelayBrokerPersonal`, own-process personal
service, fixed known-folder roots `<ProgramData>\HUB_Relay\Personal` and
`<ProgramFiles>\HUB_Relay\Personal`, no adoption/repair of existing product
objects, and separately approved native activation. No company fallback.
New decisions here: a single ProgramFiles tree with a separate writable State
child, trusted OS owners/mutators, a child-directory-only exception, accepted
ACL syntax, independent volume evidence and create-only acquisition obligations.
Adoption of #2001 does not adopt these additions or amend its ProgramData root.
No current-head human disposition of #2011 is asserted.

**Selected location amendment:** `<ProgramFiles>\HUB_Relay\Personal` holds the
fixed `personal_broker_service.exe` and immutable manifests; its `State` child
holds future recovery artifacts. There is no ProgramData product tree in this
candidate. This preserves the current executable suffix, not the literal drive
or loaded-image identity. No existing files are moved, and no automatic fallback
from the adopted root is permitted before this amendment is adopted.

Current `ancestor_chain::ObservedAncestorChain` retains metadata, normalized
paths and ordered `OwnerDaclSnapshot` bytes. `relative_ntfs::DirectoryObservation`
opens metadata-only descendants. `DescriptorPolicy::root_shape` checks a strict
application-root shape. None supplies initial trust, effective-access analysis,
approved volume, privileged creation or a public protected-root constructor.

## Selected OS-ancestor candidate

Select **read/traverse plus child-directory creation only for untrusted OS
trustees**, with exact exclusive-create collision refusal below. Apply this
same rule to every retained OS directory from the volume root through the
64-bit ProgramFiles known-folder anchor. Do not apply it to application-owned
directories. The descriptor policy is not permission to modify Windows files.

Only these binary SIDs may own OS ancestors or receive otherwise mutating
self-applicable grants:

| Principal | Independent policy identity |
| --- | --- |
| SYSTEM | Well-known `S-1-5-18` |
| BUILTIN Administrators | Well-known `S-1-5-32-544`; no similarly named account |
| Windows Modules Installer / TrustedInstaller | Exact `S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464` |

Microsoft documents the [well-known identities](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-identifiers)
and identifies that exact TrustedInstaller SID in its
[Windows App SDK specification](https://github.com/microsoft/WindowsAppSDK/blob/main/specs/applicationdata/ApplicationData.md#341-machine-pathfolder).
These constants come from reviewed policy, never the observed ACL. No runtime
name lookup, domain lookup or observed service SID expands the trusted set.
Trusting TrustedInstaller is an explicit new decision, justified by its
[Windows servicing role](https://learn.microsoft.com/en-us/windows/win32/wfp/about-windows-file-protection),
not by its presence on this host. Other service SIDs, All Services, interactive
users and transport identities remain untrusted for this policy.

SYSTEM, administrators, trusted servicing, kernel compromise and unrestricted
same-principal code remain outside the intended isolation guarantee. This is
not protection against a privileged actor changing an ancestor between checks.
Reject an untrusted owner even when its visible grants appear harmless: owners
normally have implicit DACL-modification rights. OWNER_RIGHTS semantics are
not used to rescue an untrusted owner. See [object ownership](https://learn.microsoft.com/en-us/windows/win32/secauthz/owner-of-a-new-object)
and [OWNER_RIGHTS](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/understand-security-identifiers).

### Exact masks and conservative classification

Expand generic ACE bits using the file/directory mapping below, preserving
already specific bits and clearing the generic bits after expansion:

| Input bit | Expanded mask |
| --- | --- |
| GENERIC_READ `0x80000000` | `0x00120089` |
| GENERIC_WRITE `0x40000000` | `0x00120116` |
| GENERIC_EXECUTE `0x20000000` | `0x001200a0` |
| GENERIC_ALL `0x10000000` | `0x001f01ff` |

Mapping basis: [file security](https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights),
[standard rights](https://learn.microsoft.com/en-us/windows/win32/secauthz/standard-access-rights)
and [MapGenericMask](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-mapgenericmask).
This is ACE classification; native directory opens request explicit rights.
Reject zero masks and any expanded bit outside `0x001f01ff`, including
ACCESS_SYSTEM_SECURITY, MAXIMUM_ALLOWED and reserved bits, for every ACE.

| Untrusted self-applicable ALLOW | Candidate disposition |
| --- | --- |
| LIST_DIRECTORY `0x1`, READ_EA `0x8`, TRAVERSE `0x20`, READ_ATTRIBUTES `0x80`, READ_CONTROL `0x20000`, SYNCHRONIZE `0x100000` | Permit subsets of `0x001200a9` |
| ADD_SUBDIRECTORY `0x4` | Permit, giving combined allowed mask `0x001200ad` |
| ADD_FILE/WRITE_DATA `0x2`, WRITE_EA `0x10`, DELETE_CHILD `0x40`, WRITE_ATTRIBUTES `0x100`, DELETE `0x10000`, WRITE_DAC `0x40000`, WRITE_OWNER `0x80000` | Refuse any bit in `0x000d0152` |

The constants distinguish [creating a subdirectory from creating a file](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants).
The documented [reparse setter](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/4aeefef8-92c3-4abc-af7a-a610caf8a165)
requires WRITE_DATA or WRITE_ATTRIBUTES; `0x4` alone is neither. The design
inference is narrow: an untrusted sibling-directory creator can preoccupy a
product name, causing denial, but is not thereby authorized to replace our
successfully created protected child. Exclusive creation and final descriptors
from first creation are essential. This is not a complete proof of every NTFS
operation; native adversarial evidence below remains required.

Check each ALLOW independently without group expansion or subtracting DENY
entries. Ordinary DENY entries may remain in order, but cannot justify a broad
ALLOW. Duplicate/split safe ALLOWs are evaluated individually; their union
must remain within the allowed mask. This conservative policy may refuse an
ACL that Windows would deny in a particular token context. It does not claim
to reproduce AccessCheck or infer a caller's effective permissions.

### Supported ACEs, owners and inheritance

Require a bounded, valid revision-1 self-relative descriptor, valid owner SID,
present non-null revision-2/4 DACL, valid offsets/alignment and SID extents.
Use the existing 64 KiB copy bound; it does not bound the OS allocation.
An empty DACL grants no policy capability and cannot satisfy creation by itself.
OS DACLs may be protected or unprotected; every actual ancestor is inspected.
Do not import the application's protected-DACL requirement into OS ownership.

| Syntax | Exact proposed treatment |
| --- | --- |
| Ordinary ACCESS_ALLOWED `0x00`, ACCESS_DENIED `0x01` | Supported with complete bounded SID/mask parsing; retain original ordering |
| OI `0x01`, CI `0x02`, NP `0x04`, IO `0x08`, INHERITED `0x10` | Only supported flag bits; NP or IO without OI/CI refuses |
| IO absent, whether inherited or explicit | Applies to the current object; evaluate mask/trustee |
| IO present with valid propagation flags | Does not grant current-object access; still validate layout, SID and mask; do not infer descendant permissions |
| OI/CI/NP | Describe propagation only; inspect each actual child, never synthesize a trusted child descriptor |
| CREATOR_OWNER `S-1-3-0`, CREATOR_GROUP `S-1-3-1` | Accept only valid inherit-only ordinary ACEs; self-applicable forms refuse |
| OWNER_RIGHTS `S-1-3-4`, other creator-authority placeholders, PRINCIPAL_SELF `S-1-5-10`, null SID | Refuse anywhere, including inherit-only |
| Other valid revision-1 SIDs | Exact trusted-set match or untrusted; never resolve membership/name to promote trust |
| Object, callback, conditional, compound, audit or unknown ACE/type/flags | Refuse, including in inherit-only entries; no opaque acceptance |

[ACE_HEADER](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/628ebb1d-c509-4ea0-a10f-77ef97ca4586)
defines present-object versus inheritance behavior. Protected application DACLs
must suppress inherited grants at creation and retain the existing stricter
policy; supporting an inherited OS ACE does not relax application permissions.

## Independent acquisition and activation facts

Policy matching returns only a private diagnostic verdict tied to retained
handles. It cannot construct `ProtectedRoot`, authenticate a service or approve
a volume. A later exact-hash activation bundle must independently approve:

- Source/build/toolchain/dependency digests, policy version/digest, supported
  Windows build/architecture and the trusted bootstrap executable/launch path.
- One anchor record: 64-bit ProgramFiles known-folder ID, permitted normalized
  component path, volume GUID plus native volume identity and local fixed NTFS
  requirement. No ProgramFiles(x86), ProgramData or drive-letter fallback.
- Actual bootstrap primary identity, complete token/privilege expectations,
  expected nonimpersonation and protected loaded-image provenance. An admin
  group bit, elevation dialog, SCM string or hash of a mutable pathname is not
  independently sufficient. No automatic privilege-enabling fallback.
- Independently bound personal service SID and exact planned descriptor bytes,
  owned-resource list, bounded rollback rules and approved creation mode.

These host/build-specific facts are currently missing. A separately reviewed
read-only inventory can propose values; human approval of the concrete bundle
must precede their use. An observed GUID or ACL copied into an expectation in
the same acquisition cannot approve itself. The policy constants above are not
learned from that inventory. Environment variables, caller paths, `trusted=true`
and arbitrary serialized handle/identity values confer no authority.

## Proposed create-only sequence and first-root scope

This sequence is an implementation obligation, not an instruction to run an
installer. First native creation slice after adoption is **three empty product
directories**, then exact owned rollback: `HUB_Relay`, `Personal`, `State` under
ProgramFiles. All have SYSTEM owner, protected non-null DACL, exactly one
explicit SYSTEM full-control ALLOW `0x001f01ff` and exactly one bound-service
ALLOW below; all ACE flags zero. No additional/duplicate/inherited ACEs.

| Application object | Exact service mask / purpose |
| --- | --- |
| `HUB_Relay` and `Personal` directories | `0x001200a9`: list/traverse/read-EA/read-attributes/read-control/synchronize; no mutation |
| `Personal\State` directory | `0x001200ab`: same plus ADD_FILE/WRITE_DATA, preserving the existing root metadata candidate; no ADD_SUBDIRECTORY, DELETE/DELETE_CHILD, WRITE_DAC/OWNER or WRITE_ATTRIBUTES |
| Future fixed service executable | `0x001200a9` read/execute; SYSTEM owner/full control, protected DACL |
| Future immutable plan/ownership files | `0x00120089` read-only; SYSTEM owner/full control, protected DACL |

Future files have the same two explicit ALLOW entries and zero ACE flags; no
file is part of the empty-root rehearsal. State-file creation/recovery remains
the separate owned-reference design. The service cannot create siblings in
Personal, replace payload/manifests or change an ancestor descriptor. Explicit
protected descriptors on every product component prevent parent IO/creator
grants from becoming inherited service/transport authority.

The service SID must be independently pinned in the approved bundle to the
fixed personal account before any directory creation; an arbitrary supplied
service-shaped SID is insufficient. SID provisioning/binding must be reviewed
without installing a service merely to complete this rehearsal. Missing
independent binding refuses. This rehearsal provisions no service and proves
only its empty-directory scope; it neither requires an already installed service
nor supplies real service TokenUser/profile/isolation evidence. The separately
approved later service ceremony must follow the prerequisite and acceptance
ordering below.

1. Verify the approved bootstrap identity/image/token and anchor bundle before
   acquisition; refuse impersonation without clearing it. Retain and validate
   the complete OS chain using the selected policy. Never change OS ACLs.
2. Acquire a separate retained creation-parent handle relative to the verified
   chain, requiring explicit ADD_SUBDIRECTORY, READ_ATTRIBUTES, READ_CONTROL and
   SYNCHRONIZE (`0x00120084`). Bind it to the independently held observed object;
   check rights, identity, path, descriptor and policy before and after. Do not
   turn the existing metadata handle into a mutation capability by a flag.
3. For each fixed product component use `NtCreateFile`, one relative component,
   retained `RootDirectory`, `OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE`, no handle
   inheritance, `FILE_CREATE`, `FILE_DIRECTORY_FILE | FILE_OPEN_REPARSE_POINT |
   FILE_SYNCHRONOUS_IO_NONALERT`. Supply that object's final protected
   descriptor in `OBJECT_ATTRIBUTES.SecurityDescriptor` on that first call.
   No OPEN_IF, overwrite, absolute fallback, create-then-harden or ACL repair.
4. Request `0x00130084` on newly owned intermediate directories (the parent
   rights above plus DELETE); final empty leaves need `0x00130080` (metadata,
   synchronization and DELETE). Share READ/DELETE, not WRITE; this is not an
   immutability guarantee. Native proof must establish these exact requests,
   descriptor assignment and cleanup rights; unsupported behavior stops.
5. Only terminal success, independent IOSB success, FILE_CREATED and a valid
   handle establishes live creation provenance. Immediately record it in the
   bounded journal, then validate local fixed NTFS, expected directory type,
   volume/file identity, normalized full path, no delete-pending/reparse state,
   granted rights and exact owner/DACL before creating another component.
6. Any preexisting `HUB_Relay`, `Personal`, later leaf or service is a collision,
   even when apparently compatible. Preflight is advisory; exclusive creation
   decides. Recheck all retained ancestors and created objects between steps
   and before acceptance. No adoption, suffix retry or removal of a contender.
7. First-slice acceptance ends with verified reverse rollback of those three
   empty objects. It does not retain roots for an unapproved later
   installer. Actual installation must start absent again with its separately
   approved final descriptors and payload plan.

[OBJECT_ATTRIBUTES](https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes)
defines relative names and creation descriptors;
[NtCreateFile](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile)
defines dispositions/options and creation results. Documentation does not prove
the proposed user-mode binding, privilege profile or exact rights on this host.

Final service use remains a later focused composition: State service grant
`0x001200ab` is the existing metadata candidate, not a no-reparse promise
(it includes `0x2`). Trusted service code must retain no-reparse/identity checks;
this does not isolate against hostile same-service-principal code. The parent,
payload and manifests remain immutable to the service. The exact approved bundle,
payload/SCM plan and bootstrap identity, image and privileges precede provisioning.
After the approved service start, actual SCM/process/TokenUser and loaded-image
binding, distinct loaded profile and required DPAPI/user-scoped KSP support must
be validated before any broker-key work. Key-specific descriptor, policy,
public-identity and isolation evidence is then collected for the newly owned key
before publication, recovery acceptance or operational use. No policy-matching or
empty-root rehearsal result bypasses these gates or manufactures a final
protected-root wrapper.

## Failure, cleanup and evidence boundaries

Reserve journal capacity before each create: at most three directory entries in
the empty-root slice. Each records the live created handle, independent parent,
fixed component, identity, expected descriptor and completed/uncertain state.
Never allocate a larger accepted resource set after a partial failure.

On a terminal error, preserve call status, IOSB and any acquired-handle cleanup
error. If creation/provenance is uncertain, do not reopen by name to infer
ownership or delete the object; report a possible orphan. Retain the existing
non-unwinding fatal-pending rule while native buffers are alive. A timeout or
driver stall must not be redescribed as a successful cancellation.

Rollback only definitely created, freshly identity/descriptor-checked empty
directories, in reverse order through retained handles. Verify deletion/close
and exact absence; unexpected contents, identity drift or access failure stops
removal and reports residue. Never enumerate/delete unrelated entries, OS
ancestors, profiles or unknown keys. Cleanup failure fails acceptance and is
reported alongside the primary failure, never hidden by it. A crash can leave
residue; a later run stops on it. No automatic salvage or reinstall is defined.

Pre/post equality can miss ABA and immediately stale observations. Neither
sharing nor retained IDs freezes privileged mutations. A protected-root claim
must stay within the adopted threat model and measured implementation; no
atomic containment, historical integrity, rollback freshness, power-loss
durability, enrollment, app attestation, biometric or TLS authority follows.

## Planned acceptance matrix, not executed results

| Case / independent control | Required result |
| --- | --- |
| Trusted OS owner; supported readonly grants; ordinary supported inherited ACL | Policy match only, never root authority |
| Untrusted ADD_SUBDIRECTORY-only grant versus ADD_FILE or WRITE_ATTRIBUTES control | First may match; either hostile bit refuses; later owned native tests distinguish sibling creation from mutation |
| Broad generic WRITE/ALL, parent DELETE_CHILD, WRITE_DAC/OWNER, untrusted owner | Refuse independently of deny entries or display names |
| Inherit-only broad ordinary ACE versus same ACE with IO removed | First parsed without current grant; second classified and refused if unsafe; inspect actual child separately |
| Conditional/object/unknown ACE, unsupported flags, special trustee, malformed/null DACL | Refuse even when bytes remain stable |
| Compatible ACL but wrong/missing independently approved volume/bootstrap/image | No creation and no protected-root result |
| Existing component; attacker wins name race; correct-looking foreign root | Collision; preserve foreign object; no adoption/retry |
| Exclusive fresh child with restrictive descriptor at first creation | Readback exact shape; independent untrusted token cannot mutate/delete/replace it |
| Metadata handle substituted for creation handle; excessive requested rights | Refuse; do not silently duplicate upward or broaden rights |
| Reparse/alias/volume change, parent rename, wrong identity or descriptor drift | Refuse with checked owned cleanup; no string-prefix containment |
| Failed descriptor assignment, unexpected successful-open disposition, uncertain create | No ownership wrapper; preserve uncertainty and possible residue |
| Failure after each of three creates; foreign child injected; cleanup refusal | Delete only provably owned empty objects; report all residue/errors |
| Same-user fixtures or mocked service SID versus actual distinct principal | Synthetic/fixture evidence separately labeled; not service isolation |
| Reboot/restore or missing profile/loaded-image evidence after a root match | No inferred freshness, recovery, enrollment or release authority |

## Compatibility, alternatives and delivery order

A bounded read-only sample on 2026-10-27 at 23:02 UTC (2026-10-28 in Madrid)
observed an ordinary Users ALLOW on ProgramData with flags `0x02` and mask
`0x00000116`. CI is not IO: this includes self-applicable ADD_FILE/WRITE_DATA,
WRITE_EA and WRITE_ATTRIBUTES. The adopted ProgramData location therefore fails
this candidate, even with the ADD_SUBDIRECTORY exception. This is a conservative
policy rejection, not an AccessCheck result or a claim Windows is compromised.

The same private diagnostic recorded volume-root AuthenticatedUsers `0x4`,
TrustedInstaller ownership of the ProgramFiles chain, read/execute self grants
for untrusted package/user classes, and broad grants only where inherit-only.
That supports investigating the single ProgramFiles tree; it does not prove
retained-handle acquisition, absence of reparse/redirect, approved volume, real
service isolation or compatibility at activation. Rules were justified above,
not learned from these ACLs. Raw descriptors/host identifiers stay private.
The exact diagnostic receipt belongs to the PR evidence, not a shipped trust list.

The stricter alternative forbids ADD_SUBDIRECTORY too (`0x000d0156`), but can
reject harmless sibling creation. It is not selected and is not an automatic
fallback. Keeping ProgramData with these rules cannot deliver this host's pilot.
An observed-ACL allowlist, OS-ACL repair, or trusting Users to mutate ancestors
is not selected. The selected ProgramFiles State exception is a deliberate
product storage change, not a Windows recommendation that applications normally
write state there; its exact narrow ACL and servicing/update implications need
review. General access evaluation and upgrade/reinstall remain out of scope.

After adoption: (1) implement the separate bounded OS policy with deterministic
positive/negative fixtures, leaving application policy unchanged; (2) review
the exact bootstrap API/privilege/loaded-image plan and guarded native evidence,
then obtain its concrete activation-bundle approval before the three-root
rehearsal; (3) separately compose final service roots/payload and actual service
identity/profile isolation. Each step is one focused, reversible change.

Human decisions requested by this proposal: accept the exact three trusted OS
principals, the ADD_SUBDIRECTORY-only exception and conservative ACE rules;
explicitly amend the earlier two-root location to the single ProgramFiles tree
with immutable parent/payload/manifests and separate State; accept independent
volume/bootstrap approval and the three-empty-root rehearsal as the next bounded
objective. This is not renewed approval of #2001, permission
to provision now, or approval of a future unspecified executable/bundle.

Validation here is document/source review only. No native tests or installation
are claimed. Existing CNG test APIs, enrollment/T6/T7, personal/company boundary
and separate immutable activation gates remain unchanged. Android remains
deferred; personal/USB/OST files are untouched. Tailscale connectivity creates
no authorization. This document delivers no installable app, plugin or connector.
