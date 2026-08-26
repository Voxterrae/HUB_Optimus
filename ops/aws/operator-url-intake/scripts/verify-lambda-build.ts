import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { buildLambdaBundle, LAMBDA_BUNDLE_PATH, validateLambdaBundle } from './lambda-bundle';

async function main(): Promise<void> {
  const bundle = await buildLambdaBundle();
  validateLambdaBundle(bundle);
  const reviewedBundle = readFileSync(LAMBDA_BUNDLE_PATH);
  if (!reviewedBundle.equals(Buffer.from(bundle))) {
    throw new Error('Reviewed Lambda bundle is stale; run npm run build:lambda and commit it.');
  }

  const digest = createHash('sha256').update(bundle).digest('hex');
  console.log(`LAMBDA_BUNDLE_OK sha256=${digest}`);
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : 'unknown bundle verification error';
  console.error(`LAMBDA_BUNDLE_BLOCKED: ${message}`);
  process.exitCode = 1;
});
