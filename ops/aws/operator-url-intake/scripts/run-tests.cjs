const { readdirSync } = require('node:fs');
const { join, resolve } = require('node:path');
const { spawnSync } = require('node:child_process');

const root = resolve(__dirname, '..');
const args = process.argv.slice(2);
if (args.some((arg) => arg !== '--runInBand')) {
  console.error('Unsupported test argument. Only --runInBand is supported.');
  process.exit(2);
}

function run(commandArgs) {
  const env = { ...process.env };
  // Each invocation starts a fresh runner, including calls made from a test.
  delete env.NODE_TEST_CONTEXT;
  const result = spawnSync(process.execPath, commandArgs, { cwd: root, stdio: 'inherit', env });
  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

// Compile with the installed compiler; never fetch a test runner or transformer.
run([require.resolve('typescript/bin/tsc')]);
function discover(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return entry.name === 'node_modules' ? [] : discover(path);
    return entry.isFile() && entry.name.endsWith('.test.ts') ? [path.replace(/\.ts$/, '.js')] : [];
  });
}
const tests = discover(join(root, 'test')).sort();
if (tests.length === 0) {
  console.error('No test sources found.');
  process.exit(1);
}
run(['--test', '--test-concurrency=1', ...tests]);
