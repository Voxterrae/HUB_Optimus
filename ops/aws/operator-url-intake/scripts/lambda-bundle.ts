import { resolve } from 'node:path';
import { build } from 'esbuild';

export const PROJECT_ROOT = resolve(__dirname, '..');
export const LAMBDA_BUNDLE_PATH = resolve(
  PROJECT_ROOT,
  'lambda',
  'url-ingest-handler.bundle.js',
);

export async function buildLambdaBundle(): Promise<Uint8Array> {
  const result = await build({
    absWorkingDir: PROJECT_ROOT,
    bundle: true,
    charset: 'utf8',
    entryPoints: ['lambda/url-ingest-handler.ts'],
    external: [],
    format: 'cjs',
    legalComments: 'none',
    logLevel: 'silent',
    minify: false,
    outfile: LAMBDA_BUNDLE_PATH,
    platform: 'node',
    sourcemap: false,
    target: 'node22',
    treeShaking: true,
    write: false,
  });

  if (result.outputFiles.length !== 1) {
    throw new Error(`Expected one Lambda bundle, received ${result.outputFiles.length}.`);
  }
  return result.outputFiles[0].contents;
}

export function validateLambdaBundle(bundle: Uint8Array): void {
  const bundleText = Buffer.from(bundle).toString('utf8');
  if (/require\(["']@aws-sdk\/client-dynamodb["']\)/.test(bundleText)) {
    throw new Error('Lambda bundle still depends on an external DynamoDB client package.');
  }
  if (!bundleText.includes('DynamoDBClient')) {
    throw new Error('Lambda bundle does not contain the reviewed DynamoDB client code.');
  }
}
