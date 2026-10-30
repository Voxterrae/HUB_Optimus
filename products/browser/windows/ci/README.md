# Isolated Windows acceptance proposal

`WindowsSmoke.workflow.yml` is dormant: its location outside `.github/workflows`
prevents registration and execution. No workflow was activated or dispatched.
It proposes a standard `windows-2022` runner, read-only contents permission,
manual dispatch, no secrets, no deployment, no environment changes, short
retention and bounded execution. Checkout reuses the repository's existing
immutable pin; artifact upload uses the official v4.6.2 release commit. Review
pins and current runner contents again during activation.

Activation is a separate protected change. Read `AGENTS.md`,
`docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md`,
`config/governance/owner_identity.v1.json`,
`docs/context/OWNER_AUTHORITY_HANDOFF.md` and `docs/context/AI_HANDOFF.md`.
The currently documented policy requires owner-authored protected-path commits,
verified commits, an owner-authored governance issue, applicable live guard
checks and completed conversations; changing these instructions does not waive
those requirements. Owner review and the live protected process must approve
any registration in `.github/workflows`. This proposal and an AI report grant
no activation, merge or ruleset exception. General contributor changes require
current-head owner approval under the documented policy.

The runner must already provide the module's .NET SDK 10.0.403. The proposal
fails preflight if unavailable; it neither installs software nor alters global
protection. Native suites run on Windows, while the packaging suite's platform
specific path/symlink/CON fixtures remain in their supported Linux validation.
The workflow publishes the actual browser, search host, public help index and
self-contained diagnostic helper from one head. Checkout uses the exact event PR
head when present, otherwise the dispatch head; the preflight checks the checked
out commit, and all three publications receive that same SourceRevisionId. It invokes the acceptance
script with Windows PowerShell 5.1. The default run tests only the host.

GUI has an additional explicit prerequisite: WebView2 Evergreen must already be
installed in that fresh hosted image/user and an interactive desktop must be
available. Standard `windows-2022` does not establish either fact; the packaged
loader preflight records the observed version. This template does not provision
WebView2. If it is absent, GUI exits 3 (blocked) and the job fails with retained
negative evidence. Select `gui: false` for the independent service check, or
prepare an authorized disposable Windows image with the runtime before choosing
`gui: true`. Activation review must decide that prerequisite up front; a template
approval never converts a missing runtime/desktop into a passing GUI signal.

Build integration must publish `scripts/WindowsSmoke/Optimus.Windows.Smoke.csproj`
with `-c Release -r win-x64 --self-contained true -o <publication>/Diagnostics`.
The helper references the production `Optimus.Core` TLS transport; .NET Framework
PowerShell cannot load .NET 10 assemblies directly. The user needs neither a
.NET SDK nor PowerShell 7 to execute the published diagnostics. Keep the entire
self-contained Diagnostics folder with the publication.

```powershell
powershell.exe -NoProfile -File .\Test-OptimusWindows.ps1 -Publication C:\Optimus -EvidenceDirectory C:\Evidence\service
# Optional: use only a new disposable Windows VM/user with an interactive desktop.
powershell.exe -NoProfile -File .\Test-OptimusWindows.ps1 -Publication C:\Optimus -EvidenceDirectory C:\Evidence\gui -Gui
```

The evidence directory must be new and outside default profiles. Service mode
creates one GUID temporary directory, a random 64-hex token and an owned
`Search/Optimus.SearchHost.exe` process with the packaged public index. A dynamic
loopback port is allocated and released immediately before launch. A collision
fails closed; no existing listener is stopped or queried with bearer/query
bytes before production TLS authenticates its token/SPKI/actual-port proof.
Health additionally proves the fresh nonce and listener port. The test rejects
a wrong-token TLS connection and unauthenticated search, then asserts the real
public help result for a fixed nonpersonal query. Only owned processes and the
GUID service temporary directory are cleaned. Startup failure and cleanup
failure are separate report fields. The outer 180-second limit terminates only
the exact still-live helper process tree created by the script.

`-Gui` additionally requires the entire default `%LOCALAPPDATA%\Optimus` path to
be absent and port 17831 free; existing profiles/services are never read or
removed. This is for a disposable user/VM. It probes WebView2 through the packaged
loader and does not install a runtime. It launches the real browser, uses
UIAutomation Value/Invoke patterns for the native home, public Index result and
local guide response,
renders an owned loopback page, opens a private tab and settings, captures only
the owned client HWND and requests graceful close. Missing desktop, UIAutomation,
WebView2 or a nonblank window capture is **blocked**, never success. Fresh GUI
profile state is deliberately retained; discard the test user/VM afterwards.
No keyboard, Narrator, physical Windows device, public web or provider coverage
is inferred from these checks.

Exit codes: 0 passed, 1 failed, 3 blocked (GUI prerequisites/capture unavailable).
`result.json` contains independent checks and cleanup failures; `metadata.json`
contains OS/PowerShell, optional supplied source head, executable versions,
bytes and SHA-256. When `-SourceCommit` is supplied, the full 40-character head
must occur in the ProductVersion of each browser, search-host and diagnostic
native executable, its managed entry DLL and each loaded Optimus.Core.dll before acceptance starts. Missing/mismatched version metadata
is `unverified-product-version` and fails preflight; metadata alone never turns
an operator-supplied string into verified provenance. An invocation without this
parameter records `not-requested` and makes no source-head verification claim.
This verifies embedded build provenance, not a signed-binary trust assertion.
The optional PNG has its own size/hash JSON. No token,
private certificate, profile content, personal query or captured desktop is
emitted. Artifact upload is restricted to these JSON files and owned PNG;
profiles, service temporaries and complete publication folders are excluded.

Linux cross-build or parsing establishes preparation only. Actual Windows
service/GUI execution and PowerShell 5.1 behavior remain unverified until a
corresponding Windows run produces structured evidence.
