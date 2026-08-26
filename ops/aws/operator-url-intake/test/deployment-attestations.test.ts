import { validateDeploymentAttestations } from '../scripts/validate-deployment-attestations';

function validEvidence() {
  return {
    alertPathVerifiedAt: '2026-08-26T11:30:00Z',
    costReviewedAt: '2026-08-26T11:00:00Z',
    creditBalanceUsd: '10.00',
    creditExpiresAt: '2026-09-30T00:00:00Z',
    creditsReviewedAt: '2026-08-26T11:15:00Z',
    deploymentsEnabled: 'true',
    governanceRecord: 'https://github.com/Voxterrae/HUB_Optimus/issues/1917',
    grossActualUsd: '16.69',
    grossForecastUsd: '21.99',
    identityDecision: 'cognito-temporary-canary',
    mutationException: 'APPROVED_PRIVATE_CANARY_ONLY',
    nowMs: Date.parse('2026-08-26T12:00:00Z'),
  };
}

test('accepts a fresh bounded owner-governed economic attestation', () => {
  expect(validateDeploymentAttestations(validEvidence())).toEqual([]);
});

test('blocks stale reviews, insufficient headroom or credit, and missing governance', () => {
  const evidence = validEvidence();
  evidence.costReviewedAt = '2026-08-25T11:59:59Z';
  evidence.grossActualUsd = '24.01';
  evidence.grossForecastUsd = '24.01';
  evidence.creditBalanceUsd = '0.99';
  evidence.creditExpiresAt = '2026-08-27T12:00:00Z';
  evidence.mutationException = 'NO AWS MUTATION';
  evidence.governanceRecord = 'https://example.com/1917';

  expect(validateDeploymentAttestations(evidence)).toEqual(expect.arrayContaining([
    'The scoped AWS mutation exception is missing.',
    'A canonical HUB_Optimus GitHub governance issue is required.',
    'Cost, credits, and alert-path reviews must all be within 24 hours.',
    'Gross actual and forecast cost must each leave at least USD 3 below the USD 25 account cap.',
    'At least USD 5 of verified promotional credit is required.',
    'Verified promotional credit must remain valid for more than 24 hours.',
  ]));
});
