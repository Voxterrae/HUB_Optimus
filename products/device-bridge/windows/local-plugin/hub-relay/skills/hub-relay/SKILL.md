---
name: hub-relay
description: Use for the explicitly authorized local Windows diagnostic pilot with one short-lived permission. Distinguish it from Xiaomi-authorized remote control.
---

# HUB_Relay local pilot 0.2

The only tool is `hub_relay_windows_diagnostics`: numeric Windows version and
fixed C: total/free bytes. Empty arguments refuse collection. The optional
`permission` field accepts one locally issued, short-lived bearer credential.
There is no other argument or MCP tool to mint permissions. Startup flags
cannot enable reads.

Use only after explicit human acceptance of the scoped local supervised
exception to Xiaomi biometric approval. Existing authorization persists in its
scope; do not ask for it again or infer indefinite use, other chats or operations.
Issue one permission only for the authorized operation through the local operator
workflow. Keep it in memory, pass it to the intended native call and discard it.
Never put it in reports, GitHub, process command lines or reusable files.
Do not ask for passwords or biometric codes.

Shared durable state is consumed before reading. Collector failure also consumes
permission. Do not automatically mint another after a timeout or uncertain result.
Repeating the consumed permission and calling with `{}` may verify refusal;
neither should collect again. Report errors as errors.

Verify actual host discovery and native invocation. Installation alone and
separate stdio scripts do not prove a native chat call. This bearer credential
does not authenticate chat identity or a person; the host may retain arguments.
Disclose `biometricEnforced: false` and report measurements as a local snapshot.
Never claim native enrollment, protected native authorization, VPN, remote
execution, Android control or a working Windows–Xiaomi channel.

Android installation, user-file contents, moving/deleting files, network changes
and enterprise access remain outside this pilot.