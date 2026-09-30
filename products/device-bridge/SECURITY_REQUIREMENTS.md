# Biometric access and continuity requirements

Status: proposed design only; no authentication runtime, persistent service or cloud deployment is implemented by this document. Related to [issue #1933](https://github.com/Voxterrae/HUB_Optimus/issues/1933).

## Requested outcome and present gap

Keep the owner's selected phone and computer reachable, but permit no device read or modification until that operation receives local biometric approval. A transport heartbeat must not imply consent to read files, contacts, screen contents or device diagnostics.

The current Desktop Commander terminal can run arbitrary programs within its OS privileges and holds an existing provider session. Its directory and command controls are accident-reduction guardrails, not a security sandbox. A script that calls a fingerprint prompt before one command cannot secure other terminal, file, ADB or API paths. App lock, an unlocked screen and a message claiming to be the owner do not establish authorization.

No always-on execution is activated. Existing legacy credentials and ADB grants remain active: the present pause is an operator decision, not technical enforcement. Before deployment of the gated design, disable or revoke every parallel privileged path; do that locally under the owner's control and verify denial from the old client.

## Proposed trust boundary

1. Enroll each exact device through an owner-visible ceremony. Pin its public key and the intended OS account/profile; reject unknown keys and profile changes. A hostname, display name, IP address or online status is insufficient. A different online server must never replace an offline selected computer.
2. Run the authorization UI and executor in an OS-protected component outside the remote client's writable trust domain. The untrusted transport must have no direct terminal/file tools, ADB keys, device-control grant or ability to replace the gate. Keeping an unrestricted MCP shell alongside the broker fails the design.
3. Accept only typed, bounded operations with validated arguments and explicit output limits. Do not offer an arbitrary shell command, executable upload, eval, unrestricted file path or generic proxy as an approved operation.
4. Show the operation, destination device, selected data and intended change locally. Generate a fresh challenge bound to protocol version, enrolled device key, account/profile, exact canonical request digest, unpredictable nonce and a short expiry. Proposed approval expiry: 60 seconds, consumed once, checked using a trustworthy time/counter strategy.
5. Require Android strong biometric authentication for each signature, using a non-exportable Android Keystore key, per-use authentication and a BiometricPrompt CryptoObject. Do not allow DEVICE_CREDENTIAL as an alternative for this application operation. Verify a cryptographic signature; a JSON flag saying fingerprint=true is not proof.
6. The isolated executor checks signature, registered key policy, request digest, target, expiry, revocation state and durable single-use replay state before releasing data or changing state. A new connection, app restart, failure, cancelled prompt or missing evidence grants no access.
7. Define bounded jobs and a visible cancel control. Revoke pending requests on lock or key revocation; recheck authorization at each separately authorized operation. A biometric prompt establishes approval at that moment, not continuous observation of the owner. Already committed changes require their normal rollback.

Key enrollment, secure storage and any attestation must be implemented and reviewed before relying on these claims. A software-only callback or a key stored beside a remotely writable verifier does not provide the stated boundary. This proposal does not claim resistance to a compromised OS, root or a hostile administrator.

## Android biometric limits

Android distinguishes Class 3/strong, Class 2/weak and Class 1/convenience biometrics. Only a suitable strong authenticator is proposed for the protected cryptographic operation. A face-unlock option does not establish that the camera qualifies. Check canAuthenticate(BIOMETRIC_STRONG), enrollment and a real per-use signature on the exact device before activation.

BiometricPrompt authenticates an enrolled biometric for the current Android user; it does not disclose a civil identity or prove that only the named owner has enrolled. The owner must inspect enrollment locally. Invalidate the key when biometric enrollment changes, then require explicit secure re-enrollment.

Do not capture faces, gaze streams, fingerprints or templates in Termux or the cloud. Raw biometric material remains under the platform's control.

"No PIN for bridge operations" is distinct from removing Android's primary recovery credential. Android requires a PIN, pattern or password for biometric enrollment and recovery. Preserve that credential. If biometrics lock out or become unavailable, deny the remote operation; do not silently fall back to the device credential.

## Availability and battery

Only after the gate and legacy-path revocation pass verification:

- Maintain a lightweight, visible foreground connection with reconnect backoff and no device-data collection while unauthenticated.
- Use a supported startup method for the installed Termux distribution. Companion apps must be distribution/signature-compatible; do not mix installation sources or install an arbitrary APK.
- A wake lock prevents sleep; it does not grant permissions or provide authentication. Prefer bounded locks during approved work, release them on completion/failure, and avoid indefinite locks on battery.
- Confirm vendor background settings on the actual OS version. An exemption may improve availability but can increase drain. Do not exempt every Microsoft app or disable thermal limits.
- Test screen-off behavior, Wi-Fi changes, process termination and reboot. After a reboot, require normal local unlock and fresh authorization before operations. Android may still stop a service; do not promise an unbreakable connection.

For performance, use the existing [checklist](ANDROID_CHECKLIST.md), measure the affected workload and record before/after battery and latency. A brief normal temperature reading is not proof of long-term performance. Screen timeout reduction is a possible local adjustment to review, not an applied change.

## Contacts

Cloud contact collections and the phone's combined agenda have different coverage. Record account provenance before proposing a merge. Keep personal and organization-managed sources separate.

Use additive labels for observable facts; preserve names, numbers, addresses, notes and prior categories. Before any substantive edit, keep a private original export or exact before-state and verify read-back. Do not infer professional/family relationships from surnames, or merge people merely because they share a name, household number or organization address.

For the complete phone agenda, request a user-created VCF export of the selected personal accounts. Keep originals immutable. Produce a review table distinguishing identical records, shared identifiers and conflicting records. Do not normalize local numbers to an invented country code or delete duplicates without a justified, reversible merge plan. No contact content or contact-level hashes belong in this public repository.

## Windows and Microsoft infrastructure

The computer must be online and explicitly bound before inspecting Windows Hello, TPM, account or device-management state. Ordinary Windows Hello and passkey flows can accept a PIN as well as biometrics; they must not be described as biometric-only merely because Hello is enabled.

A candidate approach for a future scoped implementation is a strong-biometric signature from the enrolled phone over a request bound to the enrolled computer and its isolated executor. This still needs secure provisioning and enforcement; it is not available today.

Microsoft Entra, Intune and Azure may later support account/device policy, deployment and audit storage if the owner controls the tenant and the selected plan supports it. They do not automatically add per-command biometric enforcement to an existing Termux shell. Start with existing capabilities, preserve organization policy and specify required roles, cost and data locations before deployment. No subscription, resource, tenant policy or billing change is part of this proposal.

## Required acceptance evidence before activation

| Test | Expected result |
|---|---|
| Unknown or substituted device key | No operation and no private result |
| Missing approval, cancellation, lockout or wrong authenticator | Denied |
| PIN fallback attempted for a bridge operation | Denied; OS recovery credential retained |
| Request or destination changed after approval | Signature/request binding rejected |
| Same approval replayed, including after restart | Denied |
| Approval expired or key revoked | Denied |
| Enrollment changed | Old key unusable; secure enrollment required |
| Legacy terminal/file/ADB path used directly | No privileged access |
| Remote client tries to alter verifier or executor | OS isolation prevents modification |
| Screen locks or session disconnects before execution | Pending action cancelled |
| Screen-off/reconnect/reboot tests | Availability measured; fresh operation approval preserved |
| Contact label operation | Only intended categories differ; original data retained |

Record evidence privately, minimize public receipts and retain exact version/commit references. None of these acceptance tests is claimed to have passed by writing this document.

## Rights, provenance and integration

The repository's existing IP notice, owner identity and protected review process remain controlling. Original contributions are tracked in Git; third-party components retain their rights and licenses. Neither an AI contribution nor use of Microsoft infrastructure creates shared project ownership, a patent, a trademark registration or a guarantee against copying.

Keep secrets and personal data out of commits. Require the repository's verified commit history, owner review and passing checks on the exact proposed head before integration. Do not weaken those controls to merge a documentation draft. This proposal changes no runtime, governance contract or owner-authority handoff.

## Primary references

- [Desktop Commander security model](https://github.com/wonderwhy-er/DesktopCommanderMCP/blob/main/SECURITY.md)
- [Android biometric authentication](https://developer.android.com/identity/sign-in/biometric-auth)
- [Android Keystore](https://developer.android.com/privacy-and-security/keystore)
- [Android biometric classes](https://source.android.com/docs/security/features/biometric)
- [Termux Boot instructions](https://github.com/termux/termux-boot)
- [Android contacts export](https://support.google.com/contacts/answer/7199294)
- [Windows Hello for Business operation](https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/how-it-works)
