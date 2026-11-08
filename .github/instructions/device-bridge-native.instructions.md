---
applyTo: "products/device-bridge/**,.github/workflows/ci.yml,.github/workflows/native-pilot-windows.yml,.github/workflows/relay-inventory-candidate.yml,.github/workflows/relay-native-refusal.yml,.github/workflows/relay-token-buffer.yml"
---

# Device Bridge native / HUB Relay

## Execution boundary

- Read the [Device Bridge security requirements](../../products/device-bridge/SECURITY_REQUIREMENTS.md), the relevant module README and exact issue/PR before changing this experimental, runtime-isolated product. Existing governance and owner-authority records remain controlling; this file grants no authority.
- Safe synthetic/offline conformance checks below may run without device access. Actual device reads or changes, Windows host inventory capture (even read-only on a disposable runner), native enrollment/key creation and activation default to **NO RUN** until exact owner-approved scope, target/profile, source/artifacts, private evidence location and rollback are established through protected authorization. Never infer permission from a green test, online connector, chat identity claim or workflow availability.
- Keep `fixture.v0.1`, the offline simulation banner and `requestRealExecution() = EXECUTOR_DISABLED` intact. Native contracts/proposals, mathematical verification and diagnostic receipts do not adopt a production contract or activate a broker/service.

## Portable checks and working directories

From the repository root, use Python 3.12 with `requirements-dev.txt` installed and Node on PATH:

```sh
python -m pytest -q products/device-bridge/windows/offline-prototype/tests/test_offline_windows_pilot.py
python -B -m unittest discover -s tests -p 'test_device_bridge_native_result_proposal.py' -v
node --test products/device-bridge/common/native-result/proposal/conformance.cjs
python -B -m unittest discover -s tests -p 'test_hub_relay_bootstrap_refusal_receipt.py' -v
python -B -m unittest discover -s products/device-bridge/windows/bootstrap-inventory/tools -p 'test_*.py' -v
```

These exercise offline fixtures, proposal/vector mathematics, refusal codecs and synthetic package/verifier cases, not a Windows collector. Missing Node may explicitly skip Python-invoked JS checks; a skip is not conformance. Ordinary tests consume frozen vectors: do not regenerate them during routine validation. Explicit regeneration uses the recorded generator/tool versions and may change randomized ECDSA signatures; compare canonical bytes/digests and signature validity, not signature-byte equality.

The native-contract step in [CI](../workflows/ci.yml) explicitly installs Rust **1.99.0**, rustfmt and Clippy. From the repository root, reproduce its checks for each manifest that actually exists:

```sh
set -eu
for manifest in \
  products/device-bridge/common/native-protocol/Cargo.toml \
  products/device-bridge/common/native-result/Cargo.toml; do
  [ -f "$manifest" ] || continue
  rustup run 1.99.0 cargo fmt --manifest-path "$manifest" -- --check
  rustup run 1.99.0 cargo test --locked --manifest-path "$manifest"
  rustup run 1.99.0 cargo clippy --locked --manifest-path "$manifest" --all-targets -- -D warnings
done
```

Use isolated task Cargo home/target directories and clear inherited compiler wrappers, flags and bootstrap overrides as CI does. Preserve locks and direct pins; do not substitute another Rust release or update dependencies to make checks pass. The native-result tree contains an experimental Cargo library included in these CI checks; its frozen proposal remains non-normative, T5 enrolled-key resolution remains unavailable, and conformance grants no enrollment, collection, transport or activation authority. For GNU Windows local validation from `products/device-bridge/common/native-protocol/`, follow its [README](../../products/device-bridge/common/native-protocol/README.md), including the explicit `x86_64-pc-windows-gnu` target. Linux checks are not native Windows acceptance.

Standalone Rust refusal and token-buffer conformance uses `rustup run 1.99.0 rustc --edition=2021 --test` from the repository root, with the respective `products/device-bridge/windows/native-pilot/tools/*_tests.rs` input and a task-temporary output binary. Use the exact commands in the [refusal](../../products/device-bridge/windows/native-pilot/tools/NATIVE_REFUSAL_README.md) and [token-buffer](../../products/device-bridge/windows/native-pilot/tools/TOKEN_BUFFER_README.md) runbooks. These synthetic tests perform no host token acquisition; the separate Windows SDK/MSVC ABI compile check is not a token capture either.

## Windows workflows and evidence

- Inspect actual triggers, owner/account-ID guards, candidate SHA, runner, compiler, target, permissions and completed steps in the exact workflow/run. Do not dispatch, widen triggers or bypass protections as a validation shortcut.
- [Native pilot Windows](../workflows/native-pilot-windows.yml) provides manual exact-candidate validation on Windows 2022 using Rust `1.99.0-x86_64-pc-windows-gnu`, locked fetch followed by offline tests/Clippy, edition-2024 rustfmt and unchanged-source/lock checks. Its closed test suites are `bootstrap-process` (default, 36 tests), `identity-cng` (the exact eight reviewed identity tests), `identity-http` (the exact seven reviewed HTTP resource tests plus those eight identity tests), and `bootstrap-peer` (exactly 19 active peer tests plus only `bootstrap_peer::tests::native_child_entry` ignored, never counted as a pass). The combined profile requires HTTP already `Running` before each native harness and still `Running` afterward, with no service start/stop/configuration command; this preflight is non-atomic. The `products/device-bridge/windows/native-pilot/Cargo.toml` manifest, CNG identity source and HTTP resource source are present in this baseline; bootstrap-process and bootstrap-peer sources remain absent. The combined profile additionally requires a separately reviewed exact candidate containing `products/device-bridge/windows/native-pilot/src/approval_https.rs`. The peer-only profile requires a separately reviewed corrected candidate containing `src/bootstrap_peer.rs` and `src/bootstrap_peer/tests.rs`; it executes no CNG/HTTP tests and queries no HTTP service. Its fixture child processes, local pipes and token-context changes stay on the disposable runner, with captured output reduced to allowed names/statuses/counts. Historical MSVC evidence does not certify the current GNU candidate. Verify the selected test suite's prerequisites and completed exact-candidate run; workflow availability alone establishes neither CNG execution nor native acceptance.
- [Relay refusal](../workflows/relay-native-refusal.yml) and [token buffer](../workflows/relay-token-buffer.yml) exercise standalone synthetic logic on guarded Windows runners. Refusal currently has named-branch push triggers, not `workflow_dispatch`; token buffer also has manual dispatch. Neither proves host collection, enrollment or activation.
- [Relay inventory candidate](../workflows/relay-inventory-candidate.yml) has guarded manual/named-branch triggers. Its core slice is synthetic, but native tests and the package job include private Windows observations; the package job actually runs the read-only collector. It is not an offline-only check. Follow the [bootstrap inventory runbook](../../products/device-bridge/windows/bootstrap-inventory/README.md) for native AMD64/MSVC prerequisites, fixed routes, locked/offline build, extracted-bundle verification, complete transfer/exit and cleanup evidence. Its full Cargo test command is not a synthetic-only recommendation on Windows.
- Preserve `activation=blocked` and `loaded_image_provenance=not_established`. The diagnostic bundle has no installer/activation command. A verified manifest or successful `observed`/`refused` receipt proves neither approved host policy nor authorship, loaded-image provenance or permission to create protected roots, keys, accounts or services.
- Keep real paths, SIDs, ACLs, token buffers, volume/device/profile/key identifiers, receipts and their derived hashes private: never commit them, print them into public CI logs or upload them as artifacts. The inventory workflow's explicit public exception is the distributable diagnostic ZIP only, without captures or completed private activation evidence. Public receipts must remain sanitized and bound to exact source/run/tool versions and limitations.

## Cryptography and enrollment

- Preserve the native protocol's strict parser, 4096-byte envelope bounds, exact domain/NUL/JCS signing bytes, P-256/SHA-256-once, 65-byte uncompressed SEC1 key and minimal DER rules. High-S and low-S are accepted; signature bytes are not identity, deduplication or replay keys. The result proposal remains non-normative and its schema/Node checks are not a native raw parser.
- Public fictitious scalars 1/2 and synthetic IDs are test data, never trusted enrollment. Supplied-key signature mathematics establishes no civil identity, biometric event, freshness, protected enrollment, revocation, durable consumption or execution permission. Resolve trusted keys and pending requests through independently protected enrollment/admission; no transport selector, boolean or test bypass can manufacture authority.
- The [private probe runbook](../../products/device-bridge/windows/native-authorization/PRIVATE_PROBE_RUNBOOK.v0_1.md) is a **NO RUN** template, not execution authorization. Future per-use Android signing requires a nonexportable hardware-backed key, strong-biometric CryptoObject and external attestation/binding verification; no software/PIN fallback for bridge operations. Preserve the OS recovery credential. Windows Hello or an unlocked screen does not prove biometric-only approval. Enrollment, legacy-path denial and activation require their own exact protected approval and evidence; synthetic passes lift none of those gates.
