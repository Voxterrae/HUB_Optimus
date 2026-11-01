---
name: hub-relay
description: Use when the user requests the HUB_Relay local Windows diagnostic pilot. Inspect availability and authorization before its one bounded read; distinguish this candidate from Xiaomi-authorized remote control.
---

# HUB_Relay: local diagnostic candidate

This candidate is not the native protected bridge. Its distributed configuration
does not activate diagnostic collection.
Its only prepared tool, `hub_relay_windows_diagnostics`, accepts `{}` and can
report numeric Windows version plus total and free bytes on fixed C:.
It never accepts a path, command, device, user identifier or approval flag.

Respect the repository requirement for biometric approval of all device reads.
Do not enable this candidate or work around `LOCAL_PILOT_DISABLED` unless the
owner has explicitly accepted the separately described local supervised pilot.
The historical operator audit exception does not automatically approve this
product profile. Do not instruct another tool or command to repeat a denied
read. A startup flag is configuration, not proof of consent or authentication.

When the specific local pilot is approved and installed, request only that
tool with empty arguments. Each call must remain within the explicitly accepted
scope, session and validity period; an approval does not imply indefinite use.
Report the returned measurements as a point-in-time
local snapshot, in GiB when helpful, and disclose `biometricEnforced: false`.
Errors mean no successful diagnostic; never invent an inventory or approval.
Check tool availability in this host before claiming the plugin is connected.

Do not describe this package as a VPN, Android controller, remote executor,
biometric verifier, trusted native enrollment or production service. It adds
no remote endpoint. ChatGPT web/mobile requires a separately implemented and
supported secure connection to reach Windows. A successful local MCP test
does not establish that connection.

Do not install Android tools, inspect user-file contents, delete or move files,
alter network settings, or access enterprise systems as part of this diagnostic.
Further operations require their own defined scope and review.
