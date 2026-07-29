# Security reporting — HUB_Optimus

Use this process for suspected vulnerabilities, exposed credentials, sensitive
data, or security-relevant misuse connected to this repository.

## Do not publish sensitive material

Do not place any of the following in a public issue, pull request, commit,
discussion, screenshot, log, or test fixture:

- passwords, API keys, tokens, private keys, or connection strings;
- personal, banking, health, identity, or contact data;
- private agreements, internal URLs, infrastructure details, or operational
  secrets;
- complete exploit instructions for a vulnerability that is not yet fixed.

If a credential may have been exposed, revoke or rotate it through the owning
service first. Removing a value from the latest commit does not remove it from
Git history.

## How to report

1. If **Private vulnerability reporting** is available under this repository's
   **Security** tab, use it and include the sensitive details there.
2. Otherwise, use a private channel you already have with a repository
   maintainer.
3. If no private channel is available, open a minimal public issue asking for a
   private security contact. Include no secret, personal data, exploit detail,
   or sensitive attachment in that issue.

In the private report, include the affected component or commit, the observed
behavior, the smallest safe reproduction, and any immediate containment already
performed. Share only the data needed to investigate.

## Maintenance boundary

The actively maintained source is the current `main` branch. Files explicitly
labelled as legacy, historical, draft, RFC, prototype, or unavailable do not
become supported operational controls merely because they are present in the
repository.

This file records a cautious reporting route. It does not promise a response
time, remediation deadline, bounty, disclosure agreement, or independently
verified security programme. Repository code and documentation also do not, by
themselves, attest the configuration or security of any external deployment.
