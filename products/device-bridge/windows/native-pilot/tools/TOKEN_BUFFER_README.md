# Dormant Windows x64 token-buffer decoder

Prerequisite candidate under [issue #2044](https://github.com/Voxterrae/HUB_Optimus/issues/2044).
This standalone module is not registered in a runtime crate. It does not collect
tokens, approve context, perform I/O, call Windows APIs or adopt the complete
[collector proposal](../proposals/protected-root-bootstrap-acquisition.v0_1.md).
The collector, allocation ledger, complete capture/recheck/cleanup, loaded-image
provenance and independent activation evidence remain pending.

## Proposed interface and interpretation

`decode(Layout::WindowsX64, class: u32, bytes: &[u8], base_address: u64)` returns
one fully validated borrowed `TokenInformation` view or a fixed `DecodeError`.
`base_address` is the numeric address of byte zero in the original returned
buffer. Embedded pointers are checked numeric offsets only; they are never
dereferenced. The byte slice must be exactly the successful retrieval's returned
length, not the allocation capacity. The caller remains responsible for that
claim and for the buffer's acquisition, lifetime and immutable contents.

Views expose SID bytes, identifier authority and subauthorities, ordered
group-like entries, ordered privilege LUID/attribute entries, statistics and
raw scalar DWORDs. Aliased/duplicate SIDs and privileges remain separate entries;
disabled, deny-only and unknown attribute bits remain unchanged. A successful
decode establishes a supported byte layout only, never token completeness,
identity binding, nonimpersonation, effective access, policy match or authority.
The module has no allocation, unsafe code, OS import, serialization or logging.
Data-bearing views intentionally do not implement `Debug`.

Only the little-endian Windows x64 layout is supported. Unsupported layout
markers and unknown information classes refuse. Buffer lengths are at most
65,536 bytes; base plus length uses checked arithmetic; each native header has
its documented alignment. Every SID pointer is nonzero, DWORD aligned, contained
in the returned buffer and after the complete fixed header/entry array. SID
revision is 1, with 0..15 subauthorities and an exact borrowed extent of 8..68
bytes. SID payloads may alias; header/array bytes cannot be interpreted as SIDs.
Group-like counts are at most 2,048 and privileges at most 256. Every entry is
validated before any view is returned. Native padding outside SID payloads is
ignored, because these pointer-bearing API structures do not prescribe a packed
SID-payload order. Fixed-size scalar/statistics/privilege layouts reject extra
bytes as well as truncated input.

| Information class | x64 little-endian layout |
| --- | --- |
| TokenUser (1), TokenIntegrityLevel (25) | SID_AND_ATTRIBUTES: pointer at 0, attributes DWORD at 8, header 16 bytes / alignment 8 |
| TokenOwner (4), TokenPrimaryGroup (5) | SID pointer at 0, header 8 bytes / alignment 8 |
| TokenGroups (2), TokenRestrictedSids (11), TokenCapabilities (30) | Count DWORD at 0; entries at 8 with 16-byte stride / alignment 8 |
| TokenPrivileges (3) | Count DWORD at 0; entries at 4 with 12-byte stride, LUID low/high at entry 0/4, attributes at entry 8 / alignment 4 |
| TokenStatistics (10) | Exactly 56 bytes / alignment 8; TokenId 0, AuthenticationId 8, ExpirationTime 16, TokenType 24, ImpersonationLevel 28, DynamicCharged 32, DynamicAvailable 36, GroupCount 40, PrivilegeCount 44, ModifiedId 48 |
| TokenType (8), TokenImpersonationLevel (9), TokenSessionId (12), TokenElevationType (18), TokenElevation (20), TokenHasRestrictions (21), TokenVirtualizationAllowed (23), TokenVirtualizationEnabled (24), TokenUIAccess (26), TokenMandatoryPolicy (27), TokenIsAppContainer (29) | Exactly one DWORD / alignment 4 |

TokenType accepts 1..2, impersonation level 0..3, elevation type 1..3.
Statistics' impersonation level is validated only for an impersonation token;
Microsoft does not define its meaning for a primary token, so that field stays
raw there. Boolean-like DWORDs preserve every u32, since the API documents
nonzero truth, not only the value 1. TokenHasRestrictions has no one-byte
compatibility exception. Statistics' memory sizes describe internal token
storage, not the returned-buffer allocation, and are preserved as u32 values.

## Primary references and independent ABI check

Microsoft's [TOKEN_INFORMATION_CLASS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-token_information_class),
[SID_AND_ATTRIBUTES](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-sid_and_attributes),
[TOKEN_GROUPS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_groups),
[TOKEN_PRIVILEGES](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_privileges),
[TOKEN_STATISTICS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_statistics)
and [SID](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-sid)
define the fields. Offset/stride values above follow those C definitions and
the [x64 type/storage alignment rules](https://learn.microsoft.com/en-us/cpp/build/x64-software-conventions?view=msvc-170).
The Windows x64 synthetic test independently declares those documented C field
orders with `repr(C)` and checks the compiler's sizes, alignments and offsets;
it does not import offsets from the decoder or query native token data.

## Synthetic conformance

From the repository root with the fixed compiler installed:

```powershell
$tokenBufferTests = Join-Path $env:TEMP 'relay-token-buffer-tests.exe'
rustup run 1.99.0 rustc --edition=2021 --test products/device-bridge/windows/native-pilot/tools/native_token_buffer_tests.rs -o $tokenBufferTests
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed' }
& $tokenBufferTests
if ($LASTEXITCODE -ne 0) { throw 'Conformance failed' }
```

All fixtures are synthetic. A passing Windows run establishes standalone native
compilation and those synthetic properties; it is not a native token-capture or
collector result. Never publish host-derived buffers, SIDs, receipts or digests.
