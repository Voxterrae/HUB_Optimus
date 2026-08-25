import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const projectRoot = resolve(__dirname, '..');
const sourceBuild = join(projectRoot, 'lambda', 'url-ingest-handler.js');
const temporaryOutput = mkdtempSync(join(tmpdir(), 'hub-optimus-lambda-build-'));

try {
  execFileSync(process.execPath, [
    join(projectRoot, 'node_modules', 'typescript', 'bin', 'tsc'),
    '--project', join(projectRoot, 'tsconfig.json'),
    '--outDir', temporaryOutput,
    '--declaration', 'false',
  ], {
    cwd: projectRoot,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  const expected = readFileSync(join(temporaryOutput, 'lambda', 'url-ingest-handler.js'));
  const actual = readFileSync(sourceBuild);
  if (!actual.equals(expected)) {
    throw new Error(
      'lambda/url-ingest-handler.js is stale or differs from the TypeScript compiler output.',
    );
  }

  const digest = createHash('sha256').update(actual).digest('hex');
  console.log(`LAMBDA_BUILD_OK sha256=${digest}`);
} finally {
  rmSync(temporaryOutput, { recursive: true, force: true });
}
