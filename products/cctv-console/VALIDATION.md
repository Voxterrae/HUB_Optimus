# CCTV distribution validation

Issue: #1951. This product contains the existing local console; no repository
Kernel, governance, CI, settings or canonical runtime contract is changed.

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

Local command:

```text
PYTHONPATH=src HUB_OPTIMUS_CCTV_HOST=10.20.30.40 HUB_OPTIMUS_CCTV_SERIAL=unit-test-recorder HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET=example/testing/recorder python -m unittest discover -s tests -p test_*.py -q
```

Latest result: 125 tests, with 4 skipped because Tk display or PyAV was absent.
Python source compilation passed. The dependency/display omissions remain
explicit; the sanitised distribution has not been deployed to a real recorder.

The preceding Windows installation passed 130 CCTV tests with Tk present. A
real Main-stream validation saved HEVC 1920x1080 with 10.609 seconds before
and 14.969 after a synthetic event, verified its SHA256 and decoded an original
frame. Those dated external observations apply to that installation, not to
an arbitrary recorder or an unobserved build of this package.

## Review and operational boundaries

AI Governance Review: advisory checks for this isolated receive-only connector
are recorded in the draft PR. Human decision and protected merge remain pending.
There is no recognition of identity or inferred hostile intent. Detector
absence/insufficient quality is reported; generated pixels do not replace
original evidence. Device timestamps are not treated as synchronised clocks.

`docs/context/AI_HANDOFF.md` is not changed: this PR only proposes a contained
product import and does not change the broad operational or governance state.
`OWNER_AUTHORITY_HANDOFF.md` remains the controlling authority record. TV,
camera exposure trials and disk repair are separate workstreams.
