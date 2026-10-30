# Startup Readiness Implementation Plan

> For agentic workers: bounded independent tasks; root integrates, reviewer gates whole diff.

**Goal:** Fix cold-start readiness and deliver an isolated Windows acceptance harness.
**Architecture:** Existing runtime/security contract; unchanged4s outerdeadline nowfullyusable. Windows-only diagnostics and dormantCIproposal, notactiveworkflow.
**Tech Stack:** .NET10, WindowsPowerShell5.1/UIAutomation, no production dependency.
**Spec:** products/browser/windows/docs/superpowers/specs/2026-10-30-startup-readiness.md

## Global Constraints
Only module code/test/script/docs; no .github/policy/secret/trust bypass or personalPC. Preserve TLS, cancellation, ownership and profile safety. Fixture/liveWindows/generalweb evidence separate.

## Review Focus
Fresh profile no-token delayed2.5s; deadline neverexceeds4s; cancellation cleanup; GUI existingprofile/portbusy failclosed; UIA/screenshot absence markedblocked.

### Task1 launcher
Write delayed-start regression andobserveRED. Replace20probe cutoffwithdeadline-bound polling. Assertoveralltimeout/caller-cancel behavior/cleanup; runSearchsuite, commit.

### Task2 Windowsharness
Prepare standalone product-scoped WindowsPowerShelltest withisolatedservice+optionalGUI/preflight, pinned dormantworkflow andactivationnotes. Parse/type-check wherepossible onLinux; nevercallunexecutedWindowschecks green. Commit.

### Task3 integration
Freshreview/fix, runappropriatenative suites/WPF/Python package. Version0.3.2 onlynecessaryreleasefields/fixtureexpectations; preserveoldmanifests andcreatecurrentinventory. Build/packageactualexe, saveprivateZIP/hash/script, scopedGitHubPR+issuehandoff. ActivationWindowsCIremainsblockeduntilprotectedprocessorverifiedWindowsendpoint available.

### Integration finding: token publication race
Fresh backend run failed38/39; isolated20rounds/8callersprobe diverged4times. Extend startupfix to serialize cooperating process/thread tokencreation, recheckexistingfile afterownership, preserveprivatepermissions/cancellation/invalidfilefailclosed. Strengthen regression beforefix, reviewdelta and rerunbackend; no inferenceaboutWindows fromLinux filesystem.
