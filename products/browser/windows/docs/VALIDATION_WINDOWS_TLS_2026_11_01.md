# Native Windows TLS correction — #2031 / draft #2034

This record distinguishes the original native failures from the correction proposal.
Current run links and acceptance results are recorded in
[issue #2031](https://github.com/Voxterrae/HUB_Optimus/issues/2031) and the
[Windows/Linux coordination](https://github.com/Voxterrae/HUB_Optimus/issues/2021).
No source manifest, Linux build or draft PR grants release acceptance.

## Observed Windows failures

| Run | Product source | Observed result |
| --- | --- | --- |
| [41325505050](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41325505050) | `178e52efbc84428653e004b8c9f02cda30fc74b0` | Core39/39; Windows Search30/48. Eighteen failures included initial TLS failures and a later port17831 leak. Publication, packaged service and GUI were not reached. |
| [41327022528](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41327022528) | `7cd90a685bff0e492a3d9d525b82affa6ab04a2c` | Core39/39; Windows Search38/51. The forced-assertion/rebind regression passed and the port cascade disappeared. The safe server diagnostic exposed Win32 `0x8009030E`; thirteen TLS-related failures remained. Publication, packaged service and GUI were not reached. |
| [41328508505](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41328508505) | `c929bfe80d57d3d9eb24e1dfae0499c184637965` | Core39/39, Windows Search56/56, Privacy24/24. Backend45/49, including all five Windows CNG checks passing; four child-process tests failed because their test launcher assumed `DOTNET_ROOT` was defined. Publication, packaged service and GUI were not reached. |
| [41329111534](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41329111534) | `46085be8dec5676271290eb3e2906546fc7efd77` | All169 native checks passed and all three self-contained publications succeeded. Workflow catalog import then failed because dotnet run changed the child working directory. |
| [41329948417](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41329948417) | `46085be8dec5676271290eb3e2906546fc7efd77` | All169 native checks, three publications, catalog import and packaged-service acceptance passed. PowerShell5.1, verified product versions, actual authenticated TLS/search, normal exit0 and no cleanup failures. GUI deliberately unrun. |
| [41330205280](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41330205280) | `46085be8dec5676271290eb3e2906546fc7efd77` | All169 native checks and service passed again. Actual GUI with WebView2 131.0.2903.86 passed home, help-index result and local guide; failed before the controlled loopback page was requested. Forced GUI cleanup was correctly reported as unconfirmed. Page rendering, private/settings/capture and final graceful close were not accepted. |

The first two used standard `windows-2022`, image `win22/20261026.347.1`, SDK10.0.403.
The third used the same SDK; its setup log reports image `20261025.346.1`,
while preflight records `ImageVersion=20261026.347.1`. Retain both reported values
when comparing runner evidence.
The workflow SHA is separate from the product SHA. The latter is checked before
building and embedded through SourceRevisionId in the published entry assemblies.
Microsoft documents the observed Schannel/ephemeral-key error in its
[SslStream troubleshooting guide](https://learn.microsoft.com/en-us/dotnet/core/extensions/sslstream-troubleshooting#handshake-failed-with-ephemeral-keys).

## Correction and acceptance requirements

Local preparation of this proposal recorded Core39/39, Windows Search harness59/59
on Linux, Privacy24/24 and backend46/46. The five CNG lifecycle checks are explicitly
Windows-only and were not executed by those Linux runs. WPF and the native smoke
helper cross-build with zero warnings/errors; packaging tests passed21 cases and93
subtests. These are preparation results, not native Windows acceptance. Independent
review's shutdown race was reproduced by a real child with stdin left open (58/59),
then fixed with the reader on a background worker (59/59); application disposal also
gets its finally-protected attempt after a stop failure.

The additional child-launch correction reuses the active .NET muxer for DLL runs,
then valid SDK hints or the executable on PATH for apphost runs. It does not require
the optional `DOTNET_ROOT` variable or modify the runner environment. Its regression
runs the real CLI and token worker with that variable absent; the backend passes
47/47 on Linux in this mode. The later exact-source Windows runs above pass all50
backend tests. The catalog path fix is isolated to protected workflow PR2038;
production catalog validation and input bytes remain unchanged.
The existing real CLI service test also uses owner stdin EOF and requires bounded,
normal exit zero. Its previous forced kill failed the new assertion with exit137;
the corrected test passes with its original TLS, result and log-secrecy assertions.

Service acceptance is now observed for product46085be in the runs above; this is not
GUI acceptance for subsequent proposals. The next GUI diagnostic records only
bounded own-window booleans and whitelisted status categories, excluding raw UI
strings, addresses, queries, tokens and profile paths. Error cleanup requests normal
close of the exact owned HWND/PID with a deadline covering request and exit; forced
or nonzero cleanup remains a failure and never erases the original test failure.

- Keep the listener alive only inside its owned scope, including assertion,
  constructor, cancellation and disposal failures; prove release by actual rebind.
- Report bounded exception types/HResult/native codes, excluding arbitrary messages,
  query/token values, profile paths and key material.
- Use one shared P-256 signing-key owner. Linux remains ephemeral; Windows uses a
  unique named current-user Microsoft Software KSP key with private export disabled.
  Certificate disposal precedes signer/key disposal and explicit CNG deletion.
- Prove exact-name deletion, independent concurrent owners, exceptional cleanup,
  refusal to create another identity after disposal and real positive TLS health.
- Close the private stdin pipe only for an owned host, wait for clean exit and use
  bounded termination only as an unverified fallback. Preserve independent hosts,
  owned-process failure reporting and blocked reconfiguration.
- Run Core, Search, Privacy and backend suites, publish the actual three executables,
  then run packaged-service acceptance through Windows PowerShell5.1. Attempt GUI
  separately only after service acceptance; absence, skipped and blocked never pass.

The CNG strategy changes the former memory-only promise on Windows. It does not
install trust, export private keys or disable HMAC/SPKI, loopback, token or TLS
checks. Crash, power loss, forced termination or deletion errors can leave an orphan
key. No broad startup key deletion or user/machine permission change is proposed.
The product remains a draft; this record does not ratify its distribution or merge.

Themes/Easy mode, keyboard, Narrator/NVDA, physical Windows10/11 and general web
search need their own acceptance evidence. The local help index is a finite corpus.
No paid runner, subscription, personal profile, user secret, artifact or cache upload
is needed for these manual isolated test runs.

Historical SOURCE_MANIFEST files remain historical snapshots. A new correction
inventory, when present, covers its stated source bytes only and does not sign or
execute a binary. Follow the exact PR/run SHA for current provenance.
