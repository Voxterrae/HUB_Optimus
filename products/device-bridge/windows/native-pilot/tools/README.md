# Offline minimum-refusal receipt reference

`bootstrap_refusal_receipt.py` is a proposal-stage Python reference codec for the
minimum refused envelope described in
[`protected-root-bootstrap-acquisition.v0_1.md`](../proposals/protected-root-bootstrap-acquisition.v0_1.md).
It is not imported by the Rust crate. It has no CLI, collector, Windows binding,
service interface, host-file reader or authority constructor.

The two reference functions are `parse_refusal(raw: bytes) -> dict` and
`serialize_refusal(receipt: dict) -> bytes`; rejected input raises `ReceiptError`
with a fixed diagnostic message. Serialization revalidates the supplied record.
Return values remain untrusted diagnostic records. They are never capabilities.

## Supported subset

- Only `outcome=refused`, with `process`, `primary_token`, `thread_token`, `anchor`
  and `ancestors` all null. Populated observations and `observed` are rejected.
  Complete observation, token, descriptor and OS-policy validation are pending.
- All mandatory metadata, fixed blocked-activation literals, closed error enums,
  cleanup consistency and independent NT completion fields are checked.
- Input and serialized output are each at most 131072 bytes (128 KiB). This is
  intentionally narrower than the future full collector's 32 MiB output cap.
  JSON nesting is at most eight containers. Duplicate keys, malformed UTF-8,
  BOM, surrogate characters, nonfinite/floating numbers and trailing data refuse.
- At most 255 acquisition/cleanup errors; a 256th entry must be the final reserved
  `receipt_bound` error. Input is validated, never repaired or silently truncated.
- NT pending or the existing nonterminal unwritten-IOSB sentinel cannot appear
  in an accepted receipt. Call status, IOSB status and Information stay separate.
- Wall-clock reversal and elapsed time over 10000 ms remain representable in a
  refused receipt. Time observations establish no freshness authority.

The wire bounds and nesting preflight do not prove an aggregate Python heap or
working-set limit. Python objects, parser storage and allocator overhead coexist.
No future native memory budget is accepted by this reference implementation.
The serializer checks the escaped byte count before assembling its final result;
it is not a native reservation or fallible-allocation proof.

## Reproduce

From the repository root, using Python 3.12 or later and its standard library:

```sh
python3 -B -m unittest discover -s tests -p test_hub_relay_bootstrap_refusal_receipt.py -v
```

Tests use synthetic data and execute the Python codec. They are not Windows API,
Rust compilation, collector lifecycle, token-policy or native execution results.
The codec does not verify complete delivery, process exit, authenticated origin,
executable/dependency provenance, service SID binding or owner authorization.
Those obligations remain external and activation stays blocked.

Keep real receipts private. Do not include host-derived paths, SIDs, ACLs, volume
identities, tokens or their hashes in public test fixtures or CI artifacts.

The proposal remains subject to verified commits, independent review and the
owner's exact-content disposition. This tool neither adopts it nor activates a
service. No shared authority or operational handoff file changes follow.
