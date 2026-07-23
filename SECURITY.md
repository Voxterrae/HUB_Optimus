# Security Policy — HUB_Optimus

## Supported versions

| Version | Supported |
|---|---|
| `main` (latest) | ✅ |
| Tagged releases (`v2.3.4`, etc.) | ✅ |
| Legacy (`legacy/`) | ❌ (historical only) |

## Reporting a vulnerability

If you discover a security vulnerability in HUB_Optimus, please report it
responsibly. **Do not open a public issue.**

### How to report

1. **Email:** Send a description to **operator@huboptimus.dev** with the
   subject line `SECURITY: <brief description>`.
2. **GitHub private vulnerability reporting:** If enabled for this repository,
   use GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
   feature under the **Security** tab.

### What to include

- A clear description of the vulnerability.
- Steps to reproduce (if applicable).
- Affected files, endpoints, or components.
- Severity assessment (your best estimate).
- Whether you believe the issue is actively exploitable.

### What to expect

- **Acknowledgement** within 72 hours of receipt.
- **Triage and initial assessment** within 7 days.
- **Resolution timeline** communicated after triage; critical issues are
  prioritized.
- **Credit** offered to the reporter (unless anonymity is preferred).

### Scope

The following are in scope:

- Repository code and configuration (CI, workflows, scripts).
- Deployed static site (`huboptimus.dev`).
- Operator PWA (`huboptimus.dev/operator/`).
- EC2 backend API endpoints (if publicly exposed).
- Credential or secret leaks in repository history.

The following are **out of scope**:

- Legacy documents under `legacy/` (historical, not maintained).
- Theoretical vulnerabilities in planned/RFC features not yet implemented.
- Social engineering attacks against maintainers.

## Security practices

- No analytics, cookies, forms, or external JavaScript on the public site.
- CORS-locked API proxy (origin-restricted to `huboptimus.dev`).
- Rate limiting on public endpoints.
- No secrets committed to the repository.
- CI includes mojibake guard and encoding validation.

## Disclosure policy

HUB_Optimus follows coordinated disclosure. We will work with reporters to
agree on a disclosure timeline. We aim to resolve confirmed vulnerabilities
before public disclosure.
