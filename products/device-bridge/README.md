# HUB_Optimus Device Bridge

Status: experimental, manually operated compatibility record. Related to [issue #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933).

This directory registers the Android/Termux connection used through Remote Desktop Commander. It is a module inside HUB_Optimus, not a nested Git repository or submodule. It records an existing MCP connection; it does not implement an AGI, HTTP API, autonomous device manager or deployed HUB_Optimus service.

## Connection record

| Field | Value |
|---|---|
| Module | Device Bridge / Android-Termux |
| Protocol | MCP through the installed Remote Desktop Commander connector |
| Provider entry point | [Desktop Commander Remote](https://mcp.desktopcommander.app) |
| Upstream implementation | [DesktopCommanderMCP](https://github.com/wonderwhy-er/DesktopCommanderMCP) |
| Observed upstream version | 0.2.51 |
| Authentication | Existing provider-managed device session; never committed |
| Device binding | Resolve the exact device through the connector on every session |
| HUB_Optimus runtime integration | None |
| New listening ports or public terminal endpoint | None introduced |
| Operation | Explicit human request, scoped tool calls, verification and rollback |

The provider URL is a service entry point, not a device-specific API endpoint. Device IDs, session IDs and tokens remain private. A label such as `localhost` does not authenticate a device or identify the computer executing this repository.

## Current access prerequisite

The user now requires biometric approval before **any** device read or modification. The existing connector does not enforce that condition. Unattended device access and unattended startup remain paused; this is an operator restriction, not an installed technical lock. The owner subsequently authorized the supervised session recorded in issue #1933; that bounded authorization does not establish biometric enforcement. Existing connector credentials and ADB authorization have not been revoked. See [security requirements](SECURITY_REQUIREMENTS.md) for the implementation and verification gap.

## Evidence and limits

| Capability | Status at the 2026-09-28 checkpoint |
|---|---|
| Remote Termux terminal and permitted files | Verified after the local environment repair |
| Node, npm and Bash | Verified through the default remote shell |
| Android application inventory | Initial Termux visibility was partial; later scoped ADB diagnostics are recorded in VALIDATION.md |
| Android settings and battery service | Later scoped ADB reads verified; no claim of cross-profile authority |
| Microsoft app configuration or account synchronization | One communication app received a reversible local permission/background adjustment; account sync and delivery remain untested |
| Cellular and WhatsApp call diagnosis | Unresolved; requires controlled call tests and app UI evidence |
| Automatic optimization, background monitoring or remediation | Not implemented |
| Per-operation biometric authorization | Required by the user; not implemented |

The [platform policy](../../docs/architecture/platform_compatibility.md) remains unchanged. Mobile reading and review do not imply a native Android runtime guarantee.

## Operating documents

- [Termux compatibility and recovery](TERMUX.md)
- [Android and Microsoft checks](ANDROID_CHECKLIST.md)
- [Validation receipt and handoff](VALIDATION.md)
- [Biometric access and continuity requirements](SECURITY_REQUIREMENTS.md)

For a future API implementation, first define one allowlisted read-only operation, authenticated device binding, a bounded result and private audit retention in a separate scoped issue. A live mutation needs an exact plan, human authorization, rollback and read-back verification. The current MCP terminal has broad privileges within its app sandbox; folder restrictions are not a terminal sandbox.

## Rights and authority

The [project rights notice](../../IP_NOTICE.md) and [owner-authority handoff](../../docs/context/OWNER_AUTHORITY_HANDOFF.md) govern this proposal. Third-party software remains subject to its own terms. This record claims no ownership or endorsement of Desktop Commander, Termux, Android, Xiaomi, Microsoft or WhatsApp.

No merge, deployment, repository permission change or device-wide authority follows from this directory. Public provenance is not a legal IP registration.
