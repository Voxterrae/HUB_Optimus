# CCTV distribution validation

Source import: #1951 / draft PR #1952 at
`d83c4790b9ac1ee7f6bd1873f818687d02508946`. Follow-up: #1955. This contained
product delta changes no repository Kernel, governance, CI, settings or
canonical runtime contract.

## Assertions and evidence

- Explicit binding tests reject missing identifiers, non-private IPv4,
  hostnames, control characters and unconfigured startup before credential or
  socket access.
- Offline console tests cover capture resolution, photo fitting, playback,
  sequence boundaries, retention, selection and the contained Home boundary.
- Real subprocess fixtures exercise source/auth refusal, final event delivery,
  overflow, single-subscription lifecycle and permission revocation.
- Distribution scanning excludes installation data and reproducible hashes
  cover a positive source allowlist rather than runtime-generated directories.
- Usability regressions exercise immediate filters, contextual empty views,
  recorder transition labels, quality limits and original-pixel crop access,
  expiry and revocation.
- Sequence regressions select the full scene nearest the initial event receipt
  among decoded frames, including a sharper unrelated late frame, equal-distance
  ties, non-monotonic timestamps and invalid quality scores. Body/face detector
  sampling and quality selection remain independent; old stored clips are not
  rewritten. Receipt proximity does not certify the camera's internal clock.
- Mobile regressions use fake API/vault objects to exercise nonce-bound private
  chat pairing, expiry, stale responses, credential refusal, bounded queue,
  receipt freshness and cooldown. Slow vault/config operations stay on the
  notifier worker; Tk actions and snapshots remain responsive. No Telegram
  traffic occurs in these tests. Pairing keeps getUpdates offset at zero,
  preserves unrelated pending updates and fails closed on a full unpaired queue.

Local command:

```text
PYTHONPATH=src HUB_OPTIMUS_CCTV_HOST=10.20.30.40 HUB_OPTIMUS_CCTV_SERIAL=unit-test-recorder HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET=example/testing/recorder python -m unittest discover -s tests -p test_*.py -q
```

2026-10-05 Linux candidate: 202 tests, zero failures/errors, 11 skipped:
10 need an interactive Tk display and one needs native Windows Credential
Manager. All 40 Python source/test files parsed successfully. The deterministic
manifest verifies 45 distribution files; the publication inventory additionally
hashes the manifest itself. Source scanning
found no private installation literals. The old Home headless fixture now
initializes the inspector list; its sanitized adapter imports remain unchanged.

2026-10-05 Windows candidate, completed at 12:57:52 UTC: 202 tests, zero
failures/errors, one Linux-UID skip. All ten Tk tests and native Windows
Credential Manager tests ran on Python 3.14.7 with the existing PyAV 19.0.1
library. Captured stdout/stderr contains no Tk callback exception; the manifest
check passed. Test log SHA256:
`295a9b6a3a1f83569c4d53c4d28ef0d88e91163013b3c8f2ff9205dc7c3e8c61`.
An earlier harness lacked the installed codec path. After correcting that
dependency path, three temporary SQLite setup failures did not recur in the
focused Home suite or two complete runs; their underlying cause was not
reproduced. No production change was made for those failures.

Offline evidence does not claim live pairing, phone delivery or deployment of
this sanitized distribution.

The source-import baseline completed 125 tests on Linux and Windows. The draft
PR records four Linux Tk skips and one Windows Linux-UID skip on that baseline;
those results do not certify this follow-up.

The preceding Windows installation passed 130 CCTV tests with Tk present. A
real Main-stream validation saved HEVC 1920x1080 with 10.609 seconds before
and 14.969 after a synthetic event, verified its SHA256 and decoded an original
frame. Those dated external observations apply to that installation, not to
an arbitrary recorder or an unobserved build of this package.

A separate read-only review on 2026-10-05 decoded 691 frames from an existing
private clip. The closest scene was 0.001639 seconds after event receipt,
compared with the prior sharpness-selected scene at 13.216364 seconds. Its
original 2560x1440 pixels and the retained video SHA256 stayed unchanged.
That external observation supplies no camera-clock or detection-cause guarantee;
no recording, image or installation identifier is included in this distribution.

## Review and operational boundaries

AI Governance Review: advisory checks for this isolated receive-only connector
are recorded in the draft PR. Human decision and protected merge remain pending.
There is no recognition of identity or inferred hostile intent. Detector
absence/insufficient quality is reported; generated pixels do not replace
original evidence. Device timestamps are not treated as synchronised clocks.

`docs/context/AI_HANDOFF.md` is not changed: #1955 explicitly confines the work
to this product and its local handoff; it changes no broad governance state.
`OWNER_AUTHORITY_HANDOFF.md` remains the controlling authority record. TV,
camera exposure trials and disk repair are separate workstreams.
