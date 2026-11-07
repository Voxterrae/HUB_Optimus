# Device Bridge Windows offline prototype

Experimental fixture slice for [#1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933),
plan `HUB-DEVICE-BRIDGE-WINDOWS-PLAN-v0.1`.

Open [offline-prototype/index.html](offline-prototype/index.html) directly in a
local browser. No installation, server, npm project, CDN or connection is
required. The permanent banner states:
**Simulación offline — no accede a tu equipo**.

Select a synthetic scenario, review its fictional request, start it, then
explicitly complete or cancel it. Completion never runs automatically.
Only a completed displayed fixture can be exported, after an explicit click,
as `hub-optimus-device-bridge-fixture.json`. Cancellation removes pending
diagnostic data and later completion cannot revive that cancelled run.

## Boundary

The fixed operation is `windows.runtime_inventory.v0_1`, with Windows,
PowerShell 7 and Node fields. Every request and complete result is bounded
to 4,096 serialized UTF-8 bytes. Versions are fictional, at most 128 Unicode
characters; `missing` and `unverified` are distinct synthetic states.

Approval expiry (60,000 ms), duration (10,000 ms), invalid signature, binding
changes and replay are deterministic demonstrations. The explicitly
non-cryptographic fixture binding and caller-provided in-memory replay set
provide no real authentication or durable protection. Demonstration time is
fixed; this prototype does not measure or terminate Windows jobs.

`requestRealExecution()` always returns `EXECUTOR_DISABLED`, including after
a successful fixture, test flags or a reconstructed controller. There is no
device query, credential access, persistent provider session, network client,
collector, native application, biometric enforcement or Windows certification.
The Node VM harness catches accidental capability calls; it is not a sandbox.

## Validation

From the repository root, using the existing development dependency tier and
Node on PATH:

~~~powershell
python -m pytest -q products/device-bridge/windows/offline-prototype/tests/test_offline_windows_pilot.py
python -m pytest -q
python tools/check_mojibake.py products/device-bridge/windows
git diff --check
~~~

Node is resolved to an absolute executable for the test subprocess, with a
minimal environment and 20-second timeout. If Node is unavailable, JS tests
skip explicitly; a skipped suite does not validate this interface.
Exact candidate results and browser evidence are recorded in #1933; artifact
hashes and contribution boundaries are recorded in #1936.

## Native stage and rights

A separate reviewed slice must choose native framework/packaging and prove
protected enrollment, per-operation approval, isolated execution, durable
replay/revocation, trusted executable resolution, process cancellation,
legacy bypass denial and installation/uninstallation on the selected build.
No Store submission, service, cloud resource or tenant change follows here.

Original HUB_Optimus contributions follow [IP_NOTICE](../../../IP_NOTICE.md)
and the [owner-authority handoff](../../../docs/context/OWNER_AUTHORITY_HANDOFF.md).
This slice incorporates no upstream Desktop Commander code or new dependencies;
third-party tools retain their own rights. Provenance is not legal registration.

## Rollback

Before integration, discard only these seven candidate files in its isolated
checkout. After protected integration, use a focused reviewed revert. No account,
port, cloud resource or persisted session is created by the prototype.

## Candidate checkpoint (2026-09-30)

The focused suite passed 30 tests after independent review fixes. Encoding and
staged whitespace checks are required before publication. Full repository pytest
on Windows stops during collection in existing EC2 tests importing Unix-only
`fcntl` and `pwd`; no repository-wide green result is claimed.

Windows 10 build 19045: the unmodified page was visually inspected in Edge
154.0.4258.37. A test-only page using the same assets in Chrome 154.0.8037.57
produced a passing real-DOM receipt for all eleven scenarios, pending/cancel,
literal markup, focus/label binding and explicit synthetic export. The browser
launcher subsequently timed out; a clean launcher exit and manual keyboard
navigation are unverified. This evidence does not certify native Windows support.
The inspected browser download contains 339 bytes of completed synthetic JSON,
with `simulated: true`; exported contents and tamper refusal also pass focused tests.
