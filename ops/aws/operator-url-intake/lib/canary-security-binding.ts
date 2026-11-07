import { createHash } from 'node:crypto';

export function canarySecurityBinding(
  allowedSubjectSha256: string,
  startedAt: string,
  expiresAt: string,
): string {
  return createHash('sha256').update(JSON.stringify({
    allowedSubjectSha256,
    expiresAt,
    startedAt,
    version: 1,
  })).digest('hex');
}

export function hasValidCanarySecurityBinding(
  allowedSubjectSha256: string | undefined,
  startedAt: string | undefined,
  expiresAt: string | undefined,
  expectedBinding: string | undefined,
): boolean {
  return /^[0-9a-f]{64}$/.test(allowedSubjectSha256 ?? '')
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(startedAt ?? '')
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(expiresAt ?? '')
    && /^[0-9a-f]{64}$/.test(expectedBinding ?? '')
    && canarySecurityBinding(
      allowedSubjectSha256 as string,
      startedAt as string,
      expiresAt as string,
    ) === expectedBinding;
}
