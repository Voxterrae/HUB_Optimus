# Android, Microsoft and call checks

These are recommendations and controlled follow-up checks. Applied local changes and their dates are listed separately in [VALIDATION.md](VALIDATION.md). The initial Termux session had limited visibility; later authorized ADB access supported scoped diagnostics. Current device operations must first satisfy the user\'s [biometric access prerequisite](SECURITY_REQUIREMENTS.md).

## Performance profile

Use balanced mode for everyday work. Xiaomi documents that performance mode consumes more power; use it only for a measured task when temperature and battery allow. Preserve Android thermal protection and normal memory management. Do not introduce a RAM cleaner, permanent high-performance mode, root, a global background-process limit or indiscriminate app termination.

Keep system and app updates current through their official update channels. Check battery use in Android before changing background behavior. Optimize the apps actually causing delays or abnormal drain. No full-phone performance improvement or battery-life gain has been measured here.

## Microsoft configuration to review in the app UI

Menu names vary with Android/HyperOS and organization policies. Keep organization-managed protections intact.

| App or function | Review | Completion evidence |
|---|---|---|
| Outlook | Notifications, background data and background battery permission; keep needed mail/calendar synchronization enabled | A real incoming notification and updated calendar with screen off |
| Authenticator | Notifications and background operation; retain all registered accounts | A normal, user-initiated sign-in approval succeeds |
| Company Portal, if installed | Compliance and required background operation | App reports compliant; no policy bypass |
| Teams | Notifications, quiet time and suppression while active on desktop; inspect Xiaomi battery restrictions if delayed | An agreed incoming call/message is received while screen is off |
| OneDrive | Correct backup account and quota; optional Wi-Fi/charging-only camera backup for lower battery and data use | A user-selected test photo appears in the intended account; originals retained |
| Edge, Microsoft 365, Copilot and other apps | Review measured battery use and needed notifications individually | Normal task completes; no duplicate background workload identified |

Microsoft recommends removing battery optimization for Outlook, Authenticator and Company Portal when it prevents background synchronization. Teams has its own notification troubleshooting guidance. Granting every app unrestricted background access is not a general performance optimization. Do not clear Authenticator data, remove work accounts or delete local files as a diagnostic shortcut.

## Busy calls: isolate the failure

A busy indication alone does not identify a compromised handset, prove a block or reveal the other person's activity. Cellular calls and WhatsApp calls use different services; both need independent checks. Two SIM states reported as loaded do not establish voice registration or identify the selected calling line.

The user should perform a small agreed test, without repeated calls to someone who may not want contact:

1. Call another consenting contact once over the cellular network, then once on WhatsApp. Record only success/failure, the selected SIM and the displayed error.
2. For WhatsApp, compare Wi-Fi and mobile data with the same consenting test contact. Restore the preferred network afterwards.
3. If other contacts work, verify the affected contact's current number and country code. Ask the contact, through an already agreed channel, to test an incoming call. The remote assistant must not contact them without authorization.
4. If cellular calls fail generally, check the default calling SIM, service status, signal and any call restrictions with the operator. Give the operator the failure time and exact message, not a speculative diagnosis.
5. If WhatsApp calls fail generally, check app updates, microphone permission, notifications and network stability. A successful WhatsApp homepage request does not test the call media path.

Do not reset network settings, erase app data, reinstall WhatsApp or change call forwarding until the narrower tests justify it and backups/recovery are confirmed. The cause remains unresolved until those observations are available.

## Sources consulted on 2026-09-28

- [Xiaomi battery modes](https://www.mi.com/es/support/article/KA-48290/)
- [Microsoft Outlook mobile FAQ](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/outlook-for-ios-and-android/outlook-for-ios-and-android-faq)
- [Teams mobile notification troubleshooting](https://support.microsoft.com/en-us/teams/notifications-settings/troubleshoot-notifications-in-microsoft-teams-mobile-apps)
- [OneDrive Android camera backup](https://support.microsoft.com/en-us/onedrive/automatically-save-photos-and-videos-with-onedrive-for-android)
- [Xiaomi: unable to make calls](https://www.mi.com/global/support/faq/details/KA-311126/)
- [WhatsApp calling help](https://faq.whatsapp.com/1450422198902579)
