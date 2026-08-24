# Operator URL intake candidate status

Status: **DRAFT / DISABLED / NOT DEPLOYED**  
Issue: `#1917`  
Prepared: 2026-08-24

This package defines the serverless candidate but does not activate it. The
default template has Lambda reserved concurrency `0` and administrator-only
Cognito signup. No AWS, DNS, EC2, Pages feature flag or production state was
changed while preparing it.

## Verified locally

- TypeScript compilation: passed.
- Jest: 48/48 passed.
- CDK synth with `publicPilotEnabled=false`: passed.
- No EC2, VPC, NAT Gateway, load balancer, SQS, custom domain or DNS record.

## Required before activation

1. Complete protected review and preserve verified commit provenance.
2. Record AWS Credits plus EC2/VPC/EBS inventory.
3. Confirm region, alert recipient and unique Cognito domain prefix.
4. Bootstrap CDK and approve a least-privilege GitHub OIDC deployment role.
5. Add reviewed DNS/TLS for `api.huboptimus.dev`.
6. Implement browser PKCE/token lifecycle and explicit 401/429 states.
7. Prove authenticated success, quota, SSRF/redirect negatives, log privacy,
   cost alerts and rollback in an approved non-production environment.
8. Only then consider exact context `publicPilotEnabled=true` and the separate
   public Operator feature-flag change.

The AWS mutation block and stale EC2 boundary in `#1831` remain unchanged.
