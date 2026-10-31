# Native Appearance Implementation Plan

> **For agentic workers:** one coupled Core/WPF implementation, independent whole-diff review, root release.

**Goal:** native themes and optional reversible Easy mode.
**Architecture:** pure Core policy and existing semantic WPF resources; same effective state everywhere.
**Tech Stack:** existing .NET10/WPF/WebView2, no new dependency.
**Spec:** products/browser/windows/docs/superpowers/specs/2026-10-31-appearance-design.md

## Global Constraints
DefaultDark/Easyoff; systemHCwins; storedmanualsettingspreserved; effectivefloor1.25/effectivemax2. ProductWindowsfilesonly, no provider/privacy/network/CI/router changes. Windows execution remainsUNRUN.

## Review Focus
Legacy JSON and corrupt files; stale theme in modal/modeless windows; all scale callsites; settingsfocus/privatependingprompt; EasyMode fold notresetonsystemevent.

### Task1 coupled implementation
- [ ] Add meaningful failing Core tests before behavior; real SettingsStore IO and resolver matrices.
- [ ] Implement BrowserSettings/SettingsStore/AppearancePolicy and integrate WPF NativeTheme/MainWindow/Chrome/dialogs/DownloadController using same state. Controls and fold per spec.
- [ ] Run Core and WPF builds, preserve actual RED/GREEN. No root version edits by worker; report files and limits.

### Task2 release
- [ ] Root version0.3.3/packagerfixtures/guide/inventory; source review and corrections.
- [ ] Run final appropriate153baseC#+newpolicytests and21Python, app/helpercrossbuild, publishall3winx64 from exactpublichead; verifyPEsources/ZIP.
- [ ] DraftPR stacked on#2026, privateZIP/hash saved, #2021 handoff. Give three shortmanual observations; do not claim Windows/cloudWin run.
