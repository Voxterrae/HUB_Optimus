import {
  canarySecurityBinding,
  hasValidCanarySecurityBinding,
} from '../lib/canary-security-binding';

test('binding closes over the allowed subject and exact canary window', () => {
  const subject = 'a'.repeat(64);
  const start = '2026-08-26T12:00:00Z';
  const expiry = '2026-08-26T14:00:00Z';
  const binding = canarySecurityBinding(subject, start, expiry);
  expect(binding).toMatch(/^[0-9a-f]{64}$/);
  expect(hasValidCanarySecurityBinding(subject, start, expiry, binding)).toBe(true);
  expect(hasValidCanarySecurityBinding('b'.repeat(64), start, expiry, binding)).toBe(false);
  expect(hasValidCanarySecurityBinding(subject, start, '2026-08-26T13:00:00Z', binding))
    .toBe(false);
});

test('binding fails closed for missing or malformed values', () => {
  expect(hasValidCanarySecurityBinding(undefined, undefined, undefined, undefined)).toBe(false);
  expect(hasValidCanarySecurityBinding(
    'a'.repeat(64),
    'not-a-time',
    '2026-08-26T14:00:00Z',
    'b'.repeat(64),
  )).toBe(false);
});
