import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { build, type Metafile } from 'esbuild';
import { expect, test } from './test-support';
import {
  buildLambdaBundle,
  LAMBDA_BUNDLE_PATH,
  PROJECT_ROOT,
  validateLambdaBundleMetafile,
} from '../scripts/lambda-bundle';

function inputGraph(path: string): Metafile {
  return {
    inputs: { [path]: { bytes: 1, imports: [] } },
    outputs: {
      'fixture.js': { bytes: 0, inputs: {}, imports: [], exports: [] },
    },
  };
}

async function fixtureGraph(contents: string, external: string[] = []): Promise<Metafile> {
  const result = await build({
    absWorkingDir: PROJECT_ROOT,
    stdin: { contents, resolveDir: PROJECT_ROOT, sourcefile: 'boundary-fixture.js' },
    bundle: true,
    platform: 'node',
    format: 'cjs',
    target: 'node22',
    external,
    write: false,
    metafile: true,
    logLevel: 'silent',
  });
  return result.metafile;
}

test('bundle boundary preserves the reviewed real Lambda bytes', async () => {
  const bundle = await buildLambdaBundle();
  expect(Buffer.from(bundle).equals(readFileSync(LAMBDA_BUNDLE_PATH))).toBe(true);
});

test('bundle boundary rejects the real installed bundled minimatch graph', async () => {
  const minimatchPath = require.resolve('minimatch', {
    paths: [dirname(require.resolve('aws-cdk-lib/package.json'))],
  });
  const graph = await fixtureGraph(
    `module.exports = require(${JSON.stringify(minimatchPath)}).minimatch('a', '*');`,
  );
  expect(Object.keys(graph.inputs).some((path) => path.includes('/minimatch/'))).toBe(true);
  expect(() => validateLambdaBundleMetafile(graph)).toThrow(/infrastructure or build dependency/);
});

test('central builder blocks forbidden dependencies before returning or writing a bundle', () => {
  const root = mkdtempSync(join(PROJECT_ROOT, '.lambda-boundary-fixture-'));
  try {
    mkdirSync(join(root, 'scripts'));
    mkdirSync(join(root, 'lambda'));
    copyFileSync(join(PROJECT_ROOT, 'scripts/lambda-bundle.ts'), join(root, 'scripts/lambda-bundle.ts'));
    copyFileSync(join(PROJECT_ROOT, 'tsconfig.json'), join(root, 'tsconfig.json'));
    const minimatchPath = require.resolve('minimatch', {
      paths: [dirname(require.resolve('aws-cdk-lib/package.json'))],
    });
    writeFileSync(join(root, 'lambda/url-ingest-handler.ts'),
      `module.exports = require(${JSON.stringify(minimatchPath)}).minimatch('a', '*');`);
    const env = { ...process.env };
    delete env.NODE_TEST_CONTEXT;
    const result = spawnSync(process.execPath, [
      '--require', 'ts-node/register/transpile-only', '-e',
      "require('./scripts/lambda-bundle').buildLambdaBundle().catch(e => { console.error(e.message); process.exitCode = 1; });",
    ], { cwd: root, env, encoding: 'utf8', timeout: 10_000 });
    expect(result.error).toBeUndefined();
    expect(result.status).toBe(1);
    expect(result.stderr).toMatch(/infrastructure or build dependency/);
    expect(() => readFileSync(join(root, 'lambda/url-ingest-handler.bundle.js'))).toThrow();
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test.each([
  'node_modules/aws-cdk-lib/index.js',
  'node_modules/aws-cdk/bin/cdk',
  'node_modules/constructs/lib/index.js',
  'node_modules/minimatch/dist/commonjs/index.js',
  'node_modules/glob/dist/commonjs/index.js',
  'node_modules/esbuild/lib/main.js',
  'node_modules/@aws-cdk/cloud-assembly-api/lib/index.js',
  'node_modules/aws-cdk-lib/node_modules/minimatch/dist/commonjs/index.js',
  'C:\\project\\node_modules\\aws-cdk-lib\\node_modules\\minimatch\\index.js',
])('bundle boundary rejects resolved infrastructure input %s even with no emitted contribution', (path) => {
  expect(() => validateLambdaBundleMetafile(inputGraph(path)))
    .toThrow(/infrastructure or build dependency/);
});

test.each([
  'lambda/url-ingest-handler.ts',
  'node_modules/@aws-sdk/client-dynamodb/dist-cjs/index.js',
  'node_modules/minimatch-helper/index.js',
  'src/minimatch/guide.js',
])('bundle boundary permits runtime input %s without substring false positives', (path) => {
  expect(() => validateLambdaBundleMetafile(inputGraph(path))).not.toThrow();
});

test('bundle boundary accepts genuine builtin external imports from a real build', async () => {
  const graph = await fixtureGraph("module.exports = [require('node:fs'), require('fs/promises')];");
  expect(() => validateLambdaBundleMetafile(graph)).not.toThrow();
});

test.each([
  'node:invented-builtin',
  '@aws-sdk/client-dynamodb',
  './outside.js',
  '/outside.js',
])('bundle boundary rejects emitted nonbuiltin external %s', async (path) => {
  const graph = await fixtureGraph(`module.exports = require(${JSON.stringify(path)});`, [path]);
  expect(() => validateLambdaBundleMetafile(graph)).toThrow(/nonbuiltin external import/);
});

test('bundle boundary rejects an input-only external import after tree shaking', () => {
  const graph = inputGraph('lambda/fixture.js');
  graph.inputs['lambda/fixture.js'].imports.push({
    path: 'outside-runtime-package', kind: 'import-statement', external: true,
  });
  expect(() => validateLambdaBundleMetafile(graph)).toThrow(/nonbuiltin external import/);
});
