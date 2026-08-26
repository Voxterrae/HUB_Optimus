import { writeFileSync } from 'node:fs';
import { buildLambdaBundle, LAMBDA_BUNDLE_PATH, validateLambdaBundle } from './lambda-bundle';

async function main(): Promise<void> {
  const bundle = await buildLambdaBundle();
  validateLambdaBundle(bundle);
  writeFileSync(LAMBDA_BUNDLE_PATH, bundle);
  console.log('LAMBDA_BUNDLE_WRITTEN');
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : 'unknown bundle build error';
  console.error(`LAMBDA_BUNDLE_BUILD_BLOCKED: ${message}`);
  process.exitCode = 1;
});
