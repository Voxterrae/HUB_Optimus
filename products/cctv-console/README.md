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

The full-scene photo uses the original decoded frame nearest the initial event
receipt; sharpness only breaks equal-distance ties. Body/face selection remains
independent. Receipt proximity does not guarantee agreement with the camera's
internal clock or prove the cause of the detector report. Existing clips and
photos are not rewritten by this selection change.

Camera and event filters repaint immediately. Recorder transitions are labelled
Inicio/Finalizado; repeated reports remain a bounded session history, not proof
of separate detections. Empty galleries explain their camera/event filter and
capture limitations. Scene/body/face selection status distinguishes missing
detectors and insufficient quality. The inspector's authorized crop and manual
shadow display preserve the received original image.

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
Evidence quotas are 128 MiB images and 256 MiB/25 clips/48 hours video. Evidence
files remain local. Optional mobile alerts carry text only; there is no image
or recording upload or public listener.

## Optional phone alerts

A new installation starts unconnected. To connect and activate future alerts,
create a dedicated Telegram bot in BotFather, enter its token in the PC's
masked field and open the locally displayed pairing link on your own phone.
Press Start in that private bot chat within ten minutes. A fresh, single-use
256-bit nonce verifies the chat; entering a chat ID alone cannot enable sending.
Keep the token and pairing link private.

Pairing preserves the bot's pending message queue. A full queue without the
verified pairing reply blocks setup and asks for a new dedicated bot; it is
never flushed automatically.

The bot token and approved bot/chat binding are stored in one exact Windows
generic credential. The local `phone_alerts.json` stores metadata only and must
remain untracked. A missing, invalid or mismatched binding blocks alerts.
Conectar y activar avisos is explicit activation; an existing verified binding
can restore on a later launch. Desconectar stops future work and requests removal
of the local binding. Any failed persistent revocation is shown in the dialog.

Only fresh recorder HumanDetect, appEventHumanDetectAlarm and CarShapeDetect
Start reports qualify. Messages contain an allowlisted camera number, detector
category and optional validated device time; the detector report is unconfirmed.
They include no household labels, faces, identity, OCR, vehicle make/model,
photos, video or chat history. Motion, face and technical reports are excluded.
The single worker limits the queue to 16, expires queued reports after 30 seconds
and applies a 120-second camera cooldown. Network failure does not interrupt
local evidence capture; ambiguous sends are not retried automatically.

Telegram API acceptance does not confirm physical phone delivery. A request
already sent may arrive after disconnecting. No live pairing or delivery is
claimed by the offline package tests.

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

Source-import provenance is issue #1951 and draft PR #1952; the contained
usability and optional text-alert follow-up is tracked by issue #1955.
The deployment that preceded this source import passed
130 CCTV tests on Windows and a real original-stream replay check. This is
dated external deployment evidence; it does not prove this package's deployment
or protected-main integration. The public distribution removes live addresses,
device IDs, zone names, credential targets, photos and recordings. The packaged
metadata defaults make no claim about unobserved device AI capabilities.

Ownership and third-party rights remain governed by the repository's
[owner-authority handoff](../../docs/context/OWNER_AUTHORITY_HANDOFF.md) and
[rights notice](../../IP_NOTICE.md). No new licensing exception is introduced.
