import { deploymentParameterFingerprint } from '../scripts/deployment-parameter-fingerprint';

const fingerprintKey = '9f'.repeat(32);

function privateInput() {
  return {
    authDomainPrefix: 'hub-optimus-canary',
    canaryExpiresAt: '2026-08-26T14:00:00Z',
    canaryStartedAt: '2026-08-26T12:00:00Z',
    costAlertEmail: 'owner@example.com',
    phase: 'private' as const,
    subjectHash: 'a'.repeat(64),
  };
}

test('fingerprint binds every private deployment parameter without exposing it', () => {
  const initial = privateInput();
  const changedSubject = privateInput();
  changedSubject.subjectHash = 'b'.repeat(64);
  const changedWindow = privateInput();
  changedWindow.canaryExpiresAt = '2026-08-26T13:30:00Z';

  expect(deploymentParameterFingerprint(initial, fingerprintKey)).toMatch(/^[0-9a-f]{64}$/);
  expect(deploymentParameterFingerprint(changedSubject, fingerprintKey)).not.toBe(
    deploymentParameterFingerprint(initial, fingerprintKey),
  );
  expect(deploymentParameterFingerprint(changedWindow, fingerprintKey)).not.toBe(
    deploymentParameterFingerprint(initial, fingerprintKey),
  );
  expect(deploymentParameterFingerprint(initial, '8e'.repeat(32))).not.toBe(
    deploymentParameterFingerprint(initial, fingerprintKey),
  );
  expect(() => deploymentParameterFingerprint(initial, 'predictable')).toThrow(
    'fingerprint key',
  );
});

test('deactivation fingerprint is fixed to previous-value semantics', () => {
  const first = { ...privateInput(), phase: 'deactivate' as const };
  const second = {
    ...first,
    authDomainPrefix: 'ignored',
    costAlertEmail: 'ignored@example.com',
    subjectHash: 'f'.repeat(64),
  };
  expect(deploymentParameterFingerprint(first, fingerprintKey)).toBe(
    deploymentParameterFingerprint(second, fingerprintKey),
  );
});
