import assert = require('node:assert/strict');
import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { test } from 'node:test';

const runner = resolve(__dirname, '../scripts/run-tests.cjs');
const support = JSON.stringify(resolve(__dirname, 'test-support.js'));

function withFixture(action: (root: string) => void): void {
  const parent = realpathSync(tmpdir());
  const root = mkdtempSync(join(parent, 'hub-node-test-runner-'));
  try {
    mkdirSync(join(root, 'scripts'));
    mkdirSync(join(root, 'node_modules/typescript/bin'), { recursive: true });
    mkdirSync(join(root, 'test'));
    copyFileSync(runner, join(root, 'scripts/run-tests.cjs'));
    // This controlled compiler fixture tests process handling, not TypeScript.
    writeFileSync(join(root, 'node_modules/typescript/bin/tsc'), 'process.exit(0);\n');
    action(root);
  } finally {
    if (dirname(root) !== parent || !basename(root).startsWith('hub-node-test-runner-')) {
      throw new Error('Refusing cleanup outside the owned runner fixture.');
    }
    rmSync(root, { recursive: true, force: true });
  }
}

function addCase(root: string, name: string, code: string): void {
  const source = join(root, 'test', `${name}.test.ts`);
  mkdirSync(dirname(source), { recursive: true });
  writeFileSync(source, '// Controlled runner fixture; compiled output is supplied separately.\n');
  writeFileSync(source.replace(/\.ts$/, '.js'), code);
}

function runFixture(root: string, args: string[] = []) {
  const result = spawnSync(process.execPath, [join(root, 'scripts/run-tests.cjs'), ...args], {
    cwd: root, encoding: 'utf8', timeout: 8_000,
    env: { ...process.env, FORCE_COLOR: '0' },
  });
  assert.ifError(result.error);
  return result;
}

test('runner discovers nested tests and accepts the existing --runInBand option', () => {
  withFixture((root) => {
    addCase(root, 'nested/example', "require('node:test').test('nested case', () => {});\n");
    const result = runFixture(root, ['--runInBand']);
    assert.equal(result.status, 0);
    assert.match(result.stdout, /nested case/);
    assert.match(result.stdout, /\btests 1\b/);
    assert.match(result.stdout, /\bpass 1\b/);
  });
});

test('runner propagates compiler failure before running tests', () => {
  withFixture((root) => {
    writeFileSync(join(root, 'node_modules/typescript/bin/tsc'), 'process.exit(7);\n');
    assert.equal(runFixture(root).status, 7);
  });
});

test('runner propagates a failing official expect assertion', () => {
  withFixture((root) => {
    addCase(root, 'failure', `const { test, expect } = require(${support});
test('assertion fails', () => { expect(1).toBe(2); });\n`);
    const result = runFixture(root);
    assert.equal(result.status, 1);
    assert.match(result.stdout, /Expected: 2/);
  });
});

test('runner rejects unsupported arguments', () => {
  withFixture((root) => {
    const result = runFixture(root, ['--unsupported']);
    assert.equal(result.status, 2);
    assert.match(result.stderr, /Unsupported test argument/);
  });
});

test('runner fails closed when there are no test sources', () => {
  withFixture((root) => {
    const result = runFixture(root);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /No test sources found/);
  });
});

test('each original case has the Jest-compatible default 5000 ms deadline', { timeout: 10_000 }, () => {
  withFixture((root) => {
    addCase(root, 'timeout', `const { test } = require(${support});
test('case timeout', async (context) => {
  await new Promise((done) => {
    const timer = setTimeout(done, 6500);
    context.signal.addEventListener('abort', () => { clearTimeout(timer); done(); }, { once: true });
  });
});\n`);
    const result = runFixture(root);
    assert.equal(result.status, 1);
    assert.match(result.stdout, /timed out after 5000ms/);
  });
});

test('lifecycle hooks retain explicit per-hook deadlines', () => {
  withFixture((root) => {
    addCase(root, 'hook-timeout', `const { test, beforeAll } = require(${support});
beforeAll(async () => { await new Promise((done) => setTimeout(done, 200)); }, 25);
test('hook timeout', () => {});\n`);
    const result = runFixture(root);
    assert.equal(result.status, 1);
    assert.match(result.stdout, /timed out after 25ms/);
  });
});

test('parameterized cases retain their individual deadline', () => {
  withFixture((root) => {
    addCase(root, 'table-timeout', `const { test } = require(${support});
test.each([1])('table timeout', async () => {
  await new Promise((done) => setTimeout(done, 200));
}, 25);\n`);
    const result = runFixture(root);
    assert.equal(result.status, 1);
    assert.match(result.stdout, /timed out after 25ms/);
  });
});

test('unmet expect assertion counts fail the native test', () => {
  withFixture((root) => {
    addCase(root, 'missing-assertion', `const { test, expect } = require(${support});
test('missing assertion', () => { expect.assertions(1); });\n`);
    const result = runFixture(root);
    assert.equal(result.status, 1);
    assert.match(result.stdout, /Expected one assertion/);
  });
});

test('standalone expect honors assertion counts without the vulnerable runner dependencies', () => {
  assert.throws(() => require.resolve('deepmerge'), { code: 'MODULE_NOT_FOUND' });
  assert.throws(() => require.resolve('jest-config'), { code: 'MODULE_NOT_FOUND' });
  withFixture((root) => {
    addCase(root, 'counted-assertion', `const { test, expect } = require(${support});
test('counted assertion', () => { expect.assertions(1); expect(true).toBe(true); });\n`);
    const result = runFixture(root);
    assert.equal(result.status, 0);
    assert.match(result.stdout, /counted assertion/);
    assert.match(result.stdout, /\btests 1\b/);
    assert.match(result.stdout, /\bpass 1\b/);
  });
});
