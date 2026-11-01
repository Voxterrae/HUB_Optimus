# Dormant native minimum-refusal reference

This is the next review candidate under [issue #2036](https://github.com/Voxterrae/HUB_Optimus/issues/2036),
following [the offline reference](README.md). It is not registered in `src/lib.rs`,
does not change Cargo or the Windows crate gate, and has no deployed caller.
These standalone tools do not introduce the unmerged parent native crate into
protected `main`.
It neither adopts the full bootstrap proposal nor creates operational authority.

`native_refusal_codec.rs` validates a closed borrowed typed record and serializes
only the minimum refused envelope. Fixed metadata emits `activation=blocked`,
`loaded_image_provenance=not_established` and five null observations. There is no
parser, observation collector, Windows API, filesystem/network operation, service,
launcher, key, privilege change or authority conversion.

Typed integer and byte-array fields avoid decimal/hex parsing. Contexts and
errors use closed enums. Validation retains error order and all three NT completion
values; pending and the unwritten native64 sentinel produce no valid receipt.
Wall-clock reversal and over-budget elapsed time remain representable refusals.

Serialization validates first, counts the escaped bytes without allocating output,
rejects more than 131072 bytes, uses fallible exact reservation, and emits through
the same bounded writer. It returns a complete `Vec<u8>` or a fixed zero-data error.
This bounds the requested output reservation and wire bytes, not the caller's
input allocations, allocator overhead or future collector working set.

## Run synthetic conformance

From the repository root with the fixed compiler installed:

```powershell
$codecTests = Join-Path $env:TEMP 'relay-refusal-codec-tests.exe'
rustup run 1.99.0 rustc --edition=2021 --test products/device-bridge/windows/native-pilot/tools/native_refusal_codec_tests.rs -o $codecTests
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed' }
& $codecTests
if ($LASTEXITCODE -ne 0) { throw 'Conformance failed' }
```

The wrapper imports the otherwise dormant module. Its synthetic cases cover
canonical bytes shared with Python, every ASCII escape including DEL, typed
extrema, exact/+1 bounds, error/cleanup consistency, independent NT status fields,
fatal-pending refusal, final-slot reservation and output failure without truncation.
Tests do not inspect the host, its tokens, filesystem ancestors or service identity.

The dedicated workflow runs only for the exact owner account/ID, public repository
and explicitly named candidate/integration branches. It checks the exact source SHA, uses the standard
disposable Windows runner and Rust1.99.0, persists no checkout credential and uploads
no artifacts. It does not grant a general CI command channel. Its initial expected
missing-module failure is a recorded TDD checkpoint, not a native runtime regression.

Read actual results at the exact commit/run before claiming success. A Windows
codec pass proves only standalone compilation and synthetic logic on that runner.
The full collector, descriptor/token validation, aggregate allocation ledger,
loaded-image/dependency provenance, independent service SID and exact operational
bundle remain separate pending gates. No service activation follows.
