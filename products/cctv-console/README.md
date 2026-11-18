# Optimus CCTV Console

Isolated source distribution of the existing Windows CCTV console. It receives
video and alarms from an explicitly configured recorder; it does not change
camera configuration or firmware. The contained `vox_home` boundary controls
local metadata, event access, credential use and evidence reads.

New captures preserve the received stream's resolution rather than the tile
size. The inspector supports fit, original size, zoom, pan and crop. Main-stream
event sequences request 10 seconds before and 15 after an event, extending up
to 60 seconds while activity continues. Receipt timestamps and incomplete
coverage are recorded. Body/face selection requires adequate image quality;
there is no person identification or inferred hostile intent.

## Install and bind one recorder

Use Windows, Python 3.14 and Tk. Install in an isolated environment:

```powershell
python -m pip install -e .
# Optional local body/face selection:
python -m pip install -e '.[vision]'
```

Set the exact recorder address, verified serial and existing Windows generic
credential target in the launching environment. The credential remains in the
Windows credential store; this product never enumerates it or provisions it.

```powershell
$env:HUB_OPTIMUS_CCTV_HOST='10.20.30.40' # Replace with your recorder's private IPv4
$env:HUB_OPTIMUS_CCTV_SERIAL='YOUR_VERIFIED_RECORDER_SERIAL'
$env:HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET='YOUR_EXISTING_CREDENTIAL_TARGET'
optimus-cctv
```

These are examples, not discovery defaults. Missing configuration fails before
credential lookup. Source import reads only these explicit environment values;
it does not open a socket or read a credential. The current console supports
seven configured channels. Device identity is checked by the native transport.

Data uses the local application directory by default. An installation may add
`src/capture_storage.json` (untracked, version 1) with an absolute `directory`
and optional absolute `vision_directory`. Inspect the disk's health first.
Evidence quotas are 128 MiB images and 256 MiB/25 clips/48 hours video. Files
remain local; this source distribution adds no cloud upload or public listener.

## Verify

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -p 'test_*.py' -q
python scripts/build-package-manifest.py --check
```

Fixture tests set a synthetic binding in `tests/conftest.py` for pytest; for
unittest use the three environment variables above with serial
`unit-test-recorder` and credential target `example/testing/recorder`.
No real recorder or credential is required for offline tests. Tk and codec
checks are skipped when their required runtime/display is absent.

## Provenance and limits

Tracked by issue #1951. The deployment that preceded this source import passed
130 CCTV tests on Windows and a real original-stream replay check. This is
dated external deployment evidence; it does not prove this package's deployment
or protected-main integration. The public distribution removes live addresses,
device IDs, zone names, credential targets, photos and recordings. The packaged
metadata defaults make no claim about unobserved device AI capabilities.

Ownership and third-party rights remain governed by the repository's
[owner-authority handoff](../../docs/context/OWNER_AUTHORITY_HANDOFF.md) and
[rights notice](../../IP_NOTICE.md). No new licensing exception is introduced.
