const UTC_SECONDS = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const MAX_REVIEW_AGE_MS = 24 * 60 * 60 * 1_000;
const MIN_GROSS_HEADROOM_USD = 3;
const MIN_CREDIT_BALANCE_USD = 5;

export interface DeploymentAttestations {
  alertPathVerifiedAt: string;
  costReviewedAt: string;
  creditBalanceUsd: string;
  creditExpiresAt: string;
  creditsReviewedAt: string;
  deploymentsEnabled: string;
  governanceRecord: string;
  grossActualUsd: string;
  grossForecastUsd: string;
  identityDecision: string;
  mutationException: string;
  nowMs: number;
}

function isRecentUtcTimestamp(value: string, nowMs: number): boolean {
  if (!UTC_SECONDS.test(value)) {
    return false;
  }
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp)
    && timestamp <= nowMs
    && nowMs - timestamp <= MAX_REVIEW_AGE_MS;
}

function parseNonNegativeMoney(value: string): number | undefined {
  if (!/^\d+(?:\.\d{1,2})?$/.test(value)) {
    return undefined;
  }
  const amount = Number(value);
  return Number.isFinite(amount) && amount >= 0 ? amount : undefined;
}

export function validateDeploymentAttestations(
  evidence: DeploymentAttestations,
): string[] {
  const errors: string[] = [];
  if (evidence.deploymentsEnabled !== 'true') {
    errors.push('Protected canary deployments are not enabled.');
  }
  if (evidence.mutationException !== 'APPROVED_PRIVATE_CANARY_ONLY') {
    errors.push('The scoped AWS mutation exception is missing.');
  }
  if (!/^https:\/\/github\.com\/Voxterrae\/HUB_Optimus\/issues\/\d+$/.test(
    evidence.governanceRecord,
  )) {
    errors.push('A canonical HUB_Optimus GitHub governance issue is required.');
  }
  if (evidence.identityDecision !== 'cognito-temporary-canary') {
    errors.push('The temporary canary identity decision is not approved.');
  }
  if (!isRecentUtcTimestamp(evidence.costReviewedAt, evidence.nowMs)
    || !isRecentUtcTimestamp(evidence.creditsReviewedAt, evidence.nowMs)
    || !isRecentUtcTimestamp(evidence.alertPathVerifiedAt, evidence.nowMs)) {
    errors.push('Cost, credits, and alert-path reviews must all be within 24 hours.');
  }

  const actual = parseNonNegativeMoney(evidence.grossActualUsd);
  const forecast = parseNonNegativeMoney(evidence.grossForecastUsd);
  if (actual === undefined
    || forecast === undefined
    || 25 - Math.max(actual, forecast) < MIN_GROSS_HEADROOM_USD) {
    errors.push(
      'Gross actual and forecast cost must each leave at least USD 3 below the USD 25 account cap.',
    );
  }
  const creditBalance = parseNonNegativeMoney(evidence.creditBalanceUsd);
  if (creditBalance === undefined || creditBalance < MIN_CREDIT_BALANCE_USD) {
    errors.push('At least USD 5 of verified promotional credit is required.');
  }
  const creditExpiry = UTC_SECONDS.test(evidence.creditExpiresAt)
    ? Date.parse(evidence.creditExpiresAt)
    : Number.NaN;
  if (!Number.isFinite(creditExpiry) || creditExpiry <= evidence.nowMs + 24 * 60 * 60 * 1_000) {
    errors.push('Verified promotional credit must remain valid for more than 24 hours.');
  }
  return errors;
}

function main(): void {
  const errors = validateDeploymentAttestations({
    alertPathVerifiedAt: process.env.ALERT_PATH_VERIFIED_AT ?? '',
    costReviewedAt: process.env.COST_REVIEWED_AT ?? '',
    creditBalanceUsd: process.env.PROMOTIONAL_CREDIT_BALANCE_USD ?? '',
    creditExpiresAt: process.env.PROMOTIONAL_CREDIT_EXPIRES_AT ?? '',
    creditsReviewedAt: process.env.CREDITS_REVIEWED_AT ?? '',
    deploymentsEnabled: process.env.CANARY_DEPLOYMENTS_ENABLED ?? '',
    governanceRecord: process.env.CANARY_GOVERNANCE_RECORD ?? '',
    grossActualUsd: process.env.GROSS_ACTUAL_USD ?? '',
    grossForecastUsd: process.env.GROSS_FORECAST_USD ?? '',
    identityDecision: process.env.CANARY_IDENTITY_DECISION ?? '',
    mutationException: process.env.AWS_MUTATION_EXCEPTION ?? '',
    nowMs: Date.now(),
  });
  if (errors.length > 0) {
    for (const error of errors) {
      console.error(`ATTESTATION_BLOCKED: ${error}`);
    }
    process.exitCode = 1;
    return;
  }
  console.log('ATTESTATION_OK');
}

if (require.main === module) {
  main();
}
