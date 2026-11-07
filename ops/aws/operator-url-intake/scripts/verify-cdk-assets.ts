import { createHash } from 'node:crypto';
import { lstatSync, readFileSync, readdirSync } from 'node:fs';
import { basename, join, resolve } from 'node:path';
import { LAMBDA_BUNDLE_PATH } from './lambda-bundle';

function sha256(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex');
}

export function verifyCdkAssetDirectory(outputDirectory: string): void {
  const root = resolve(outputDirectory);
  const assetDirectories = readdirSync(root)
    .filter((entry) => entry.startsWith('asset.'))
    .filter((entry) => lstatSync(join(root, entry)).isDirectory());
  if (assetDirectories.length !== 1) {
    throw new Error(`${basename(root)} must contain exactly one staged asset directory.`);
  }
  const assetRoot = join(root, assetDirectories[0]);
  const entries = readdirSync(assetRoot);
  if (entries.length !== 1 || entries[0] !== 'url-ingest-handler.bundle.js') {
    throw new Error(`${basename(root)} Lambda asset must contain only the reviewed bundle.`);
  }
  const stagedBundle = join(assetRoot, entries[0]);
  if (!lstatSync(stagedBundle).isFile() || sha256(stagedBundle) !== sha256(LAMBDA_BUNDLE_PATH)) {
    throw new Error(`${basename(root)} staged Lambda bundle differs from the reviewed bundle.`);
  }
}

function main(): void {
  const outputs = process.argv.slice(2);
  if (outputs.length === 0) {
    throw new Error('Provide at least one synthesized CDK output directory.');
  }
  for (const output of outputs) {
    verifyCdkAssetDirectory(output);
  }
  console.log(`CDK_ASSETS_OK outputs=${outputs.length}`);
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    const message = error instanceof Error ? error.message : 'unknown CDK asset verification error';
    console.error(`CDK_ASSETS_BLOCKED: ${message}`);
    process.exitCode = 1;
  }
}
