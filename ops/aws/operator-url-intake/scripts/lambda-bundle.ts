import { resolve } from 'node:path';
import { isBuiltin } from 'node:module';
import { build, type Metafile } from 'esbuild';

export const PROJECT_ROOT = resolve(__dirname, '..');
export const LAMBDA_BUNDLE_PATH = resolve(
  PROJECT_ROOT,
  'lambda',
  'url-ingest-handler.bundle.js',
);

export function validateLambdaBundleMetafile(metafile: Metafile): void {
  // Include resolved inputs even when tree shaking removes their emitted code.
  const forbiddenInput = Object.keys(metafile.inputs).find((path) =>
    /(?:^|\/)node_modules\/(?:aws-cdk-lib|aws-cdk|constructs|minimatch|glob|esbuild|@aws-cdk\/[^/]+)(?:\/|$)/
      .test(path.replace(/\\/g, '/')),
  );
  if (forbiddenInput !== undefined) {
    throw new Error(`Lambda bundle includes an infrastructure or build dependency: ${forbiddenInput}`);
  }

  const imports = [
    ...Object.values(metafile.inputs).flatMap((input) => input.imports),
    ...Object.values(metafile.outputs).flatMap((output) => output.imports),
  ];
  const externalImport = imports.find((entry) => entry.external && !isBuiltin(entry.path));
  if (externalImport !== undefined) {
    throw new Error(`Lambda bundle includes a nonbuiltin external import: ${externalImport.path}`);
  }
}

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
    metafile: true,
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
  validateLambdaBundleMetafile(result.metafile);
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
