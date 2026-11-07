import { after, afterEach, before, beforeEach, describe, mock, test as nodeTest, type TestFn } from 'node:test';
import { format } from 'node:util';
import { CloudAssembly } from 'aws-cdk-lib/cx-api';
import { expect } from 'expect';
import { ModuleMocker, type Mock } from 'jest-mock';

export { expect, describe, mock };

const DEFAULT_TIMEOUT = 5_000;

export function beforeAll(body: NonNullable<Parameters<typeof before>[0]>, timeout = DEFAULT_TIMEOUT): void {
  before(body, { timeout });
}

export function afterAll(body: NonNullable<Parameters<typeof after>[0]>, timeout = DEFAULT_TIMEOUT): void {
  after(body, { timeout });
}

export function beforeEachTest(body: NonNullable<Parameters<typeof beforeEach>[0]>, timeout = DEFAULT_TIMEOUT): void {
  beforeEach(body, { timeout });
}
export { beforeEachTest as beforeEach };

// Use the upstream mock implementation with the existing test call signatures.
const moduleMocker = new ModuleMocker(globalThis);
export const jest = {
  fn: moduleMocker.fn.bind(moduleMocker) as <R = any, A extends any[] = any[]>(
    implementation?: (...args: A) => R,
  ) => Mock<(...args: A) => R>,
  clearAllMocks: () => moduleMocker.clearAllMocks(),
};

type RowArguments<T> = T extends readonly unknown[] ? [...T] : [T];

function singleTest(title: string, body: TestFn, timeout = DEFAULT_TIMEOUT) {
  return nodeTest(title, { timeout }, body);
}

function each<const T>(rows: readonly T[]) {
  return (title: string, body: (...args: RowArguments<T>) => unknown, timeout = DEFAULT_TIMEOUT): void => {
    for (const row of rows) {
      const args = (Array.isArray(row) ? row : [row]) as RowArguments<T>;
      const name = row !== null && typeof row === 'object' && !Array.isArray(row)
        ? title.replace(/\$(\w+)/g, (_, key: string) => String((row as Record<string, unknown>)[key]))
        : /%[sdifjoO%]/.test(title) ? format(title, ...args) : title;
      singleTest(name, async () => { await body(...args); }, timeout);
    }
  };
}

export const test = Object.assign(singleTest, { each });

// Standalone expect needs the assertion-count checks normally run by Jest.
afterEach(() => {
  const errors = expect.extractExpectedAssertionsErrors();
  if (errors.length > 0) throw errors[0].error;
}, { timeout: DEFAULT_TIMEOUT });

after(() => {
  mock.restoreAll();
  if (!process.env.CDK_NO_CLEAN_TESTS) CloudAssembly.cleanupTemporaryDirectories();
}, { timeout: DEFAULT_TIMEOUT });
