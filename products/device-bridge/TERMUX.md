# Termux compatibility and recovery

Related to [issue #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933). This is a manually validated local workaround for Desktop Commander Remote 0.2.51 on one Android 16 / Termux Google Play environment. Other distributions and versions require their own verification.

## Cause

The remote parent process retained `PREFIX`, `LD_PRELOAD`, `TMPDIR` and `TERMUX_VERSION`. Its local MCP child did not receive them because `StdioClientTransport` used a reduced default environment. A successful remote heartbeat therefore coexisted with `Permission denied` when starting Termux executables.

Restoring the Termux execution environment to a new system shell allowed Node and Bash to run. The repair then preserved those four variables when creating the MCP child. It did not pass the entire parent environment or change Android permissions.

Relevant upstream references:

- [DesktopCommanderMCP](https://github.com/wonderwhy-er/DesktopCommanderMCP)
- [Termux Google Play execution wrapper](https://github.com/termux-play-store/termux-exec)
- [Termux exec package](https://github.com/termux/termux-exec-package)

## Local change

The installed file was `dist/remote-device/desktop-commander-integration.js` inside the resolved package directory. The original was retained alongside it with suffix `.hub-optimus-before-20260928`.

The child environment now combines, in order:

1. The MCP SDK default environment.
2. On Android only, existing string values of `PREFIX`, `LD_PRELOAD`, `TMPDIR` and `TERMUX_VERSION`.
3. The existing explicit `config.env` override.
4. `DC_REMOTE_DEVICE=true`.

The local addition is equivalent to the following original snippet, inserted between the existing default environment and explicit config override:

```javascript
...(process.platform === 'android' ? Object.fromEntries(
    ['PREFIX', 'LD_PRELOAD', 'TMPDIR', 'TERMUX_VERSION']
        .filter(key => typeof process.env[key] === 'string')
        .map(key => [key, process.env[key]])
) : {}),
```

This directory does not vendor or automatically patch the upstream package. Do not apply this change blindly to an unreviewed version. The original file had exactly one matching environment expression; the replacement was checked and a separate MCP child passed the execution test before the active connector was restarted.

## Current prerequisite

The user subsequently required biometric approval before any device access. The launcher below belongs to the earlier manual compatibility repair and does **not** enforce that condition. Do not enable it at boot or use it to resume unattended access as though the biometric gate existed. See [SECURITY_REQUIREMENTS.md](SECURITY_REQUIREMENTS.md).

## Activation and recovery

The remote connector was restarted once, gracefully, and resumed the same provider-managed device connection. The phone itself was not rebooted. The previous npm launcher exited; the new launcher invokes the already installed Node and package directly.

A private launcher was saved on the tested device at `~/hub-optimus-device-bridge/start-dc.sh`. In that same Termux installation, after stopping an existing connector, it can be started with:

```sh
/system/bin/sh "$HOME/hub-optimus-device-bridge/start-dc.sh"
```

The launcher refers to the exact installed package path and the execution library present on that device. A package upgrade or npm-cache cleanup may remove the fix or invalidate the launcher. Do not start duplicate remote sessions against the same persisted device credentials. No automatic boot service, permanent wake lock or Android battery exemption was installed.

To roll back, stop the connector gracefully, restore the sibling backup to the exact original package file, and restart through the original Termux launch method. The backup is private local state, not a repository artifact. Verify the original checksum before restoring; restoration will reintroduce the known environment limitation on this version.

## Verification

After activation, ordinary `start_process` calls using the configured default Bash shell returned Node `v24.17.0`, npm `11.17.0` and a successful nested Bash marker. No per-call environment override was needed.

At the initial checkpoint, telemetry was disabled and allowed file directories were the private Termux home and prefix. A later authorized shared-storage extension is recorded in [VALIDATION.md](VALIDATION.md). The provider device configuration directory and session file were restricted to modes `0700` and `0600`; the private launcher uses `0700`. These settings do not grant control over Android apps or prevent authorized terminal commands from accessing other OS-permitted paths.
