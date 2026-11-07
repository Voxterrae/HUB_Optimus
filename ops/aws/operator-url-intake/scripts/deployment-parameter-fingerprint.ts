import { createHmac } from 'node:crypto';
import { canarySecurityBinding } from '../lib/canary-security-binding';

export type FingerprintPhase = 'foundation' | 'controls' | 'private' | 'deactivate';

export interface ParameterFingerprintInput {
  authDomainPrefix: string;
  canaryExpiresAt: string;
  canaryStartedAt: string;
  costAlertEmail: string;
  phase: FingerprintPhase;
  subjectHash: string;
}

export function deploymentParameterFingerprint(
  input: ParameterFingerprintInput,
  fingerprintKeyHex: string,
): string {
  if (!/^[0-9a-f]{64}$/.test(fingerprintKeyHex)) {
    throw new Error('fingerprint key must be exactly 32 random bytes encoded as lowercase hex');
  }
  const fixed = {
    OperatorCallbackUrl: { value: 'https://huboptimus.dev/operator/' },
    OperatorLogoutUrl: { value: 'https://huboptimus.dev/operator/' },
  };
  const parameters = input.phase === 'deactivate'
    ? {
      CostAlertEmail: { usePreviousValue: true },
      OperatorAuthDomainPrefix: { usePreviousValue: true },
      OperatorCallbackUrl: { usePreviousValue: true },
      OperatorLogoutUrl: { usePreviousValue: true },
    }
    : {
      CostAlertEmail: { value: input.costAlertEmail },
      ...fixed,
      ...(input.phase === 'controls' || input.phase === 'private'
        ? { OperatorAuthDomainPrefix: { value: input.authDomainPrefix } }
        : {}),
      ...(input.phase === 'private'
        ? {
          CanaryAllowedSubjectSha256: { value: input.subjectHash },
          CanaryExpiresAt: { value: input.canaryExpiresAt },
          CanarySecurityBindingSha256: {
            value: canarySecurityBinding(
              input.subjectHash,
              input.canaryStartedAt,
              input.canaryExpiresAt,
            ),
          },
          CanaryStartedAt: { value: input.canaryStartedAt },
        }
        : {}),
    };
  return createHmac('sha256', Buffer.from(fingerprintKeyHex, 'hex'))
    .update(JSON.stringify({
      parameters,
      requestedPhase: input.phase,
    }))
    .digest('hex');
}

function parsePhase(value: string | undefined): FingerprintPhase {
  if (value === 'foundation'
    || value === 'controls'
    || value === 'private'
    || value === 'deactivate') {
    return value;
  }
  throw new Error('unsupported fingerprint phase');
}

function main(): void {
  try {
    if (process.argv[2] === '--canary-security-binding') {
      console.log(canarySecurityBinding(
        process.env.CANARY_ALLOWED_SUBJECT_SHA256 ?? '',
        process.env.CANARY_STARTED_AT ?? '',
        process.env.CANARY_EXPIRES_AT ?? '',
      ));
      return;
    }
    const phase = parsePhase(process.argv[2]);
    const fingerprint = deploymentParameterFingerprint({
      authDomainPrefix: process.env.OPERATOR_AUTH_DOMAIN_PREFIX ?? '',
      canaryExpiresAt: process.env.CANARY_EXPIRES_AT ?? '',
      canaryStartedAt: process.env.CANARY_STARTED_AT ?? '',
      costAlertEmail: process.env.COST_ALERT_EMAIL ?? '',
      phase,
      subjectHash: process.env.CANARY_ALLOWED_SUBJECT_SHA256 ?? '',
    }, process.env.DEPLOYMENT_FINGERPRINT_KEY ?? '');
    console.log(fingerprint);
  } catch {
    console.error('PARAMETER_FINGERPRINT_BLOCKED');
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main();
}
