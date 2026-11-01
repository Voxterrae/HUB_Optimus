# HUB_Relay bootstrap inventory candidate

Governance issue [#2056](https://github.com/Voxterrae/HUB_Optimus/issues/2056).
This generated diagnostic application implements the proposed fixed-route
read-only inventory. It does not ratify the complete bootstrap proposal or
activate HUB_Relay. Every receipt and bundle retains `activation=blocked` and
`loaded_image_provenance=not_established`.

The route observes only its own process/current thread and local NTFS directory
metadata from the volume root to the fixed64-bit ProgramFiles known folder.
There are no collector arguments, stdin configuration, environment-selected
paths/PIDs/services or trust flags. It opens no product tree or executable file,
enumerates no processes/modules/services/devices, changes no token, and creates
no key, service, protected root, account, listener, trust or firewall rule.
The separate build/verification/capture tools use explicit local file paths.

## Components and bounds

- Isolated Rust1.99/edition2024 executable with locked windows-sys0.61.2 and
  windows-link0.2.1. The historical native runtime crate is not imported.
- The pure token decoder is copied byte-for-byte from #2046 blob
  `4b80bb59b7a932d8e8057323327dc836f315295b`; it remains unmodified.
- Complete declared token capture with bounded aligned native buffers, identity/
  ModifiedId brackets, canonical multiplicity-preserving comparison, recapture
  of the primary currently associated with the retained process, and final
  thread nonimpersonation check. Only ERROR_NO_TOKEN permits filesystem capture.
- Native AMD64 only: x86_64-pc-windows-msvc, process_machine0/native_machine8664.
  ARM64, emulation, x86 and unsupported returned layouts refuse.
- Fixed DONT_VERIFY known-folder capture/recheck, relative no-reparse NTFS walk,
  exact metadata access0x00120080, retained identities, conservative owner/DACL
  parsing and checks, independent call/IOSB/Information and checked cleanup.
- One96MiB arena is allocated before acquisition;32MiB is reserved for output
  first, leaving64MiB for immutable copies and alignment. All payload ranges are
  charged before copying; actual reported allocator capacity must match.
  Errors have256 fixed slots (255 acquisition/cleanup plus one receipt reserve);
  a128KiB minimum-refusal buffer and aligned64KiB native scratch are bounded.
  Path ceiling32767UTF16 units;128 retained directories/129 transient-live;
  four process/token handles; groups2048 and privileges256 per declared array.
- The owned arena capacity is not a total heap/RSS limit. Allocator metadata,
  Rust/stdio infrastructure and bounded/identified OS-owned allocations remain
  outside that logical arena ledger. Native calls can block beyond the10s
  observation budget; this is an acceptance budget, not cancellation. A backwards
  wall-clock observation also conservatively refuses; no clock supplies authority.
- Pending NT completion or the retained unwritten-IOSB sentinel aborts without
  unwinding or a valid receipt while native storage is live. Checked cleanup
  runs in reverse acquisition order and consumes each closer exactly once.
- UTF8JSON v0.1 output is at most32MiB, including escapes/hex. On wire overflow,
  all five observations become null and the reserved receipt_bound error is
  appended without losing primary/cleanup failures. Reserve failure, incomplete
  write, unrepresentable errors or crash supplies no valid receipt.

The class21 TokenHasRestrictions adapter explicitly treats returned length1 as a
DWORD-aligned BOOLEAN payload and length4 as a DWORD, preserving raw values;
all other lengths refuse, and the standalone decoder's DWORD rule is unchanged.
This is a candidate compatibility interpretation requiring native/review evidence,
not an adopted normative amendment. Microsoft's
[maintainer discussion](https://github.com/microsoft/win32metadata/discussions/2308)
and the existing proposal identify the discrepancy. Portable route binding uses
ASCII case-insensitive comparison and exact non-ASCII units in addition to
Windows ordinal comparison; equivalences outside that subset conservatively refuse.

## Build from the reviewed source

Use native Windows AMD64 with Python3.12+, PowerShell7, Git, the exact preinstalled
Rust1.99.0 MSVC toolchain, its locked dependency cache and a reviewed Visual Studio
x64 Developer PowerShell with a known linker/WindowsSDK. Maintain at least2GiB
free on the chosen build/output volume. No toolchain/SDK installation is performed
by the build script; it refuses conflicting inherited Rust flags and dirty source.

```powershell
$sourceCommit = (git rev-parse HEAD).Trim()
$policyDigest = (Get-FileHash -LiteralPath src/os_policy.rs -Algorithm SHA256).Hash.ToLowerInvariant()
.\scripts\Build-RelayInventory.ps1 -SourceCommit $sourceCommit -PolicySha256 $policyDigest -LinkerVersion '<exact linker version>' -SdkVersion '<exact SDK version>' -OutputDirectory '<new local build folder>'
```

Policy bytes here mean the exact `src/os_policy.rs` bytes; the source commit binds
the other route/limit/implementation files as a separate build claim. These stamps
do not authenticate the binary or its running image. The recipe uses locked/
offline dependencies, /Brepro and path remapping; independent binary reproducibility
is not inferred from those flags. The package test verifies deterministic ZIP
construction for equal inputs.

The resulting ZIP contains the EXE, README, unmodified project IP notice as
LICENSE, dependency notice, activation evidence template, build/capture scripts
and strict Python validators. It contains no native receipt, SID/path/ACL/token
dump or host-derived digest. Build staging is not itself a verified bundle:
extract the generated ZIP to a new local directory first and run its capture script from that extracted directory.

## Verify the extracted files and capture privately

Use PowerShell7 and Python3.12+ on native Windows AMD64. The release uses the
Microsoft VC140/UCRT runtime and Windows COM/core components named exactly in
`manifest.json` static imports; these must already be available on the host.
The bundle contains no DLLs and performs no prerequisite installation.

```powershell
python -B tools/package_inventory.py --verify '<extracted bundle folder>'
.\scripts\Run-RelayInventory.ps1 -PrivateCaptureDirectory '<new private evidence folder>'
```

The capture helper verifies artifact equality, creates the evidence directory
with a private user/SYSTEM descriptor atomically, validates/retains its parent
namespace by handle, and retains directory handles without delete sharing during
writes. These capture-namespace handles request directory-list access so they
participate in Windows sharing checks, but perform no enumeration. The collector
keeps its separate exact metadata-only access mask. A parent namespace writable by an untrusted principal refuses. Existing
destinations, reparse/unsupported routes or unknown ACL layouts refuse. This does
not isolate against the same unrestricted principal, administrators, SYSTEM,
kernel compromise or later privileged mutation.

The binary receives no arguments and closed stdin. Output, exit, complete-transfer
length and digest are retained privately and checked together. The EXE exits0 for
a fully delivered diagnostic receipt, including `refused`; exit2, partial transfer
or timeout cannot be accepted. A parseable JSON prefix is insufficient. Timeout/
termination is never evidence of successful collector cleanup. Fixed/redacted
messages are the only public console output of the helper.

The package validator requires the complete closed, fully pending activation
template. Missing or unknown fields, completed statuses, non-null evidence and
contradictory authority/creation claims refuse both package creation and
verification, even if file digests are recomputed. Completed private evidence
records do not belong in this public diagnostic bundle.

`verify_inventory.py` is a strict data verifier, not an authority constructor.
File hashes and PE AMD64/import checks establish equality to an unauthenticated
manifest and static file structure only. They do not establish authorship,
approved host/volume/token policy, secure launch, the actual loaded image or its
dependencies. Keep evidence and host-derived hashes private.

## Activation evidence

`activation-plan.template.json` names the missing independently reviewed launch/
loaded-image mechanism, exact source/toolchain/artifacts, private volume, expected
token profile, serviceSID and descriptors, owned resources/rollback and exact owner
disposition. Its status remains blocked; editing a field to say approved grants
nothing. There is no installer or activation command in this diagnostic package.
A later creation/service implementation needs those actual gates and its own
governed review; generation and read-only tests cannot manufacture them.

## Validation

```powershell
cargo +1.99.0 test --locked --all-targets -- --test-threads=1
python -B -m unittest discover -s tools -p 'test_*.py' -v
```

Tests use synthetic cases and explicitly scoped private native observations.
The workflow records exact source/compiler/test outcomes and omits raw receipts.
Consult the associated PR/run for executed results; this document does not
predeclare native success, full Windows10/11 coverage or operational readiness.
