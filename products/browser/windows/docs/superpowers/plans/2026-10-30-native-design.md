# Native Windows Design Implementation Plan

> **For agentic workers:** Execute bounded independent UI tasks; root integrates and a fresh reviewer checks the full diff.

**Goal:** Apply the approved Optimus visual identity to the actual Windows browser.
**Architecture:** Keep WPF/WebView2 and all existing search/privacy gates. Shared resource palette with high-contrast override, responsive shell and native home/search surfaces.
**Tech Stack:** Existing .NET10/WPF, no production dependencies.
**Spec:** products/browser/windows/docs/superpowers/specs/2026-10-30-native-design.md

## Global Constraints
Only products/browser/windows UI/docs/release metadata; keep backend/Core transport and privacy behavior unchanged. Reference palette/keys/copy and native44DIP controls per spec. Default hidden help/settings; real actions, no simulated capabilities. Existing0.3 sourcemanifest historical. Public PR coordinated#2021, no merge.

## Review Focus
- At420DIP/200% all controls reachable and panels close without losing safety prompts.
- Highcontrast affects home/search as well as shell/dialogs.
- Focus returns after Escape/settings/help dismissal.
- Private pending destination remains visible despite responsive changes.
- BrowserTab home search uses existing eligibility/cancellation, not a new remote path.

### Task1 — native shell (root)
- Add shared palette/styles/scale helper, merge in App.xaml; preserve logo.
- Replace MainWindow layout with compact navigation, single-row tabstrip, sidebar, closed settings/help and responsive partial class.
- Keep names/handlers used by code-behind; add only presentation handlers. Existing safety methods remain intact.
- Check XAML parse/build and existing native/privacy/search suites; visual styling gets visual checks rather than mirror tests.

### Task2 — native home and search presentation (isolated worker)
- Add native home view; replace only BrowserTab home construction; preserve lifecycle/gates.
- Restyle OptimusSearchView using shared resources, retain code behavior and inert result strings.
- Real query/source/button actions; no extra network requests or fake features.
- Build and report exact changed files/tests, commit.

### Task3 — integrate, review, package
- Fresh full native/backend suites and release Python; WPF crossbuild. Appropriate meaningful regressions only if behavior changes.
- Fresh whole-diff review; resolve important findings in one pass.
- Version0.3.1-alpha, new source inventory and build output, exact source alignment.
- Create faithful self-contained HTML visual reference and render desktop/narrow/200%; label WPF execution limit.
- Publish scoped stacked draft PR, private ZIP+checksum+visual reference and handoff#2021. No main merge or paid service.
