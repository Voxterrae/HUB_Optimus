# Read-only bootstrap inventory candidate

Governance issue #2056. Base source #2046 at fe9d5ad85157fdda17a13ac0c4b52e4b3731f6b0.
The user requested generation of the complete next diagnostic and package.
This candidate does not ratify the full bootstrap proposal or activate a service.

## Design
Keep Rust1.99, edition2024, windows-sys0.61.2/windows-link0.2.1 locked.
An isolated crate owns its reviewed modules. Copy the tested token decoder bytes
unchanged into token_buffer.rs with a source pin; do not import the historical
native-pilot crate. The accepted route is only native AMD64, own process/thread,
fixed DONT_VERIFY ProgramFiles, retained local NTFS directory metadata and conservative
OS owner/DACL policy. No CLI path/PID/root/trust selectors, environment route or stdin.

Alternatives considered: composing the historical crate would import unrelated
CNG/HTTP/service foundations and unchecked allocations; a Python collector would
change the chosen native architecture. A standalone Rust candidate preserves the
native direction and keeps every acquisition/cleanup/wire boundary reviewable.

Use the full typed data contract from native-pilot/proposals/protected-root-bootstrap-acquisition.v0_1.md.
src/model.rs defines shared field names and contains no observation authority.
All payloads borrow one fixed96MiB arena allocated before acquisition; reserve a32MiB
output region first. Errors use fixed256 slots and refusal output a128KiB reserve.
Token query buffers use aligned64KiB stack storage, group comparison index views
use fixed2048-entry arrays, paths are <=32767 UTF16 units, chain<=128 retained
directories/129 transient-live, process/token handles<=4. OS-owned allocations,
allocator overhead and process/runtime memory are separately identified; no total
working-set promise is made. Arena allocation, padding and reserved regions count
before copying. No unbounded String/Vec allocations belong in acquisition/wire code.

## Shared interfaces
- Arena::new(capacity:usize)->Result<Arena>; arena.rs implements one fallible aligned
  fixed block. Arena::bytes(&self,source:&[u8])->Result<&[u8]>;
  Arena::slice<T:Copy>(&self,source:&[T])->Result<&[T]>;
  Arena::copy_iter<T:Copy>(&self,count:usize,iter:impl IntoIterator<Item=T>)->Result<&[T]>;
  Arena::path(&self,utf16:&[u16])->Result<Path>; Arena::text(&self,utf16:&[u16],max:usize)->Result<&str>;
  Arena::output(&self,count:usize)->Result<&mut[u8]>; used/capacity/peak getters.
  Returned references are disjoint lifetime-bounded arena views; no rewind.
- ErrorBag::new(), primary(Error)->bool, cleanup(Error)->bool,
  receipt_bound()->bool, as_slice()->&[Error], cleanup_failed()->bool,
  unrepresentable()->bool. Preserve primary, all cleanup, then reserved receipt error.
- wire::encoded_len(&Receipt)->Result<usize>; wire::encode_into(&Receipt,&mut[u8])->Result<usize>.
  Both validate the typed contract and exact escaped-byte cap. No heap/format strings.
- Windows Context<'a> has arena:&'a Arena, errors:ErrorBag, resources:Resources,
  monotonic start and fixed test hooks. ctx.check(Operation,Phase)->Result<()> checks
  budget and test-private failure point. ctx.acquire(handle,ResourceKind)->Result<usize>,
  ctx.raw(slot)->HANDLE, ctx.close(slot)->Result<()>, ctx.finish_cleanup().
  ResourceKind::ProcessToken and Directory have separate4/129 live ceilings.
  Every handle is registered immediately, noninheritable, and closed once in reverse
  acquisition order. Cleanup injection is reported only after real owned cleanup.
- process::State<'a>::new(); process::capture(ctx:&mut Context<'a>,state:&mut State<'a>)->Result<()>;
  process::recheck(ctx:&mut Context<'a>,state:&State<'a>)->Result<()>. State exposes
  process:Option<Process>, primary:Option<Token>, thread:Option<Token>, thread_context.
  Private slots/metadata may be added. All token fields must be complete before setting
  an Option. Thread presence/unknown refuses before filesystem. Reopen process primary
  and bracket capture with TokenId/ModifiedId. Canonical copied comparison views retain
  multiplicity and raw bits. No privilege changes/identity fallback.
- directories::State<'a>::new(); directories::capture(ctx:&mut Context<'a>,state:&mut State<'a>)->Result<()>;
  directories::recheck(ctx:&mut Context<'a>,state:&State<'a>)->Result<()>. State exposes
  anchor:Option<Anchor>, ancestors:Option<&[Ancestor]>. Recheck uses bounded scratch
  and compares every retained identity/path/descriptor and known-folder mapping.
  Directory down-duplication and exact-granted mask remain0x00120080; share policy
  FILE_SHARE_READ|FILE_SHARE_DELETE matches the reviewed metadata foundation.
  Preserve call/IOSB/Information independently. STATUS_PENDING or unwritten sentinel
  aborts non-unwinding while native buffers remain live, with no valid receipt.

The wire output is the existing complete v0.1 shape, no extra ledger fields. Start,
finish and elapsed are diagnostic. observed requires complete records, no impersonation,
equal recheck, all OS policies matching, no errors and checked cleanup complete.
Otherwise refused with all errors and only complete or null top-level records.
On32MiB wire overflow discard all five observation records and append the reserved
receipt_bound error, then emit the complete minimum envelope from preallocated space.
An output write failure or any unrepresentable error/reserve failure emits no valid
receipt; caller must bind complete byte transfer and process exit separately.

## Tool/package boundary
A strict Python standard-library verifier checks the full receipt contract and
independent complete transfer/exit record; it never converts data into authority.
Build and package tools pin source/policy/toolchain and verify artifact hashes/PE
machine/dependency inventory without claiming those bytes are the running image.
Activation plan remains blocked until an independently adopted loaded-image mechanism,
exact private host/profile/volume/SID evidence and owner disposition exist. No install,
service/key/root creation, elevation, trust/firewall or corporate network operations.

## Plan and tests
1. Write core arena/error/wire tests, confirm RED before implementations; exact/+1,
   invalid UTF16/escaping, error ordering, output overflow and fallible bounds.
2. Implement process/token acquisition with tests for class length/pointer/layout,
   brackets/drift/replacement and borrowed source independence; native evidence private.
3. Implement directory acquisition/descriptor grammar with synthetic unsafe-grant,
   overlap/null/reparse/path/NT-completion cases and real fixed-route observation.
4. Compose collector and no-argument executable; inject failures at every operation,
   compare resource limits and cleanup order, test output failure and fatal-pending
   only in owned child fixtures. Do not mutate Windows OS ancestors.
5. Implement strict verifier and package/build scripts with synthetic malformed and
   tampered/foreign/missing-artifact cases. Keep raw receipts out of the package.
6. Independently review and execute all tests in a disposable Windows2022 runner;
   download diagnostic binaries/source/evidence only after tests pass. Record exact
   commits, dependencies, results and remaining gates in a draft PR.

Test results in this document are requirements until an exact run is recorded.
