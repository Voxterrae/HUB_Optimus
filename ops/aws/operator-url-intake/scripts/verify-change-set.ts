import { readFileSync } from 'node:fs';

interface TemplateResource {
  Type?: string;
  [key: string]: unknown;
}

interface CloudFormationTemplate {
  Resources?: Record<string, TemplateResource>;
}

interface ResourceChange {
  Action?: string;
  LogicalResourceId?: string;
  Replacement?: string;
  ResourceType?: string;
}

interface ChangeSetDescription {
  Changes?: Array<{ ResourceChange?: ResourceChange }>;
}

export interface ExpectedResourceChange {
  action: 'Add' | 'Modify' | 'Remove';
  logicalId: string;
  resourceType: string;
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right));
    return `{${entries.map(([key, item]) =>
      `${JSON.stringify(key)}:${canonicalJson(item)}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function deriveExpectedResourceChanges(
  currentTemplate: CloudFormationTemplate,
  targetTemplate: CloudFormationTemplate,
): ExpectedResourceChange[] {
  const current = currentTemplate.Resources ?? {};
  const target = targetTemplate.Resources ?? {};
  const logicalIds = [...new Set([...Object.keys(current), ...Object.keys(target)])].sort();
  const expected: ExpectedResourceChange[] = [];

  for (const logicalId of logicalIds) {
    const before = current[logicalId];
    const after = target[logicalId];
    if (!before && after) {
      expected.push({ action: 'Add', logicalId, resourceType: after.Type ?? '' });
    } else if (before && !after) {
      expected.push({ action: 'Remove', logicalId, resourceType: before.Type ?? '' });
    } else if (before && after && canonicalJson(before) !== canonicalJson(after)) {
      expected.push({ action: 'Modify', logicalId, resourceType: after.Type ?? '' });
    }
  }
  return expected;
}

export function validateChangeSet(
  currentTemplate: CloudFormationTemplate,
  targetTemplate: CloudFormationTemplate,
  changeSet: ChangeSetDescription,
): string[] {
  const errors: string[] = [];
  const expected = deriveExpectedResourceChanges(currentTemplate, targetTemplate);
  const actual = (changeSet.Changes ?? []).map(({ ResourceChange: change = {} }) => change);
  const actualById = new Map<string, ResourceChange>();

  for (const change of actual) {
    const logicalId = change.LogicalResourceId ?? '';
    if (!logicalId || actualById.has(logicalId)) {
      errors.push('Change set contains a missing or duplicate logical resource ID.');
      continue;
    }
    actualById.set(logicalId, change);
    if (change.Action === 'Modify' && change.Replacement !== 'False') {
      errors.push(`Modify must declare Replacement=False for ${logicalId}.`);
    } else if (change.Replacement && change.Replacement !== 'False') {
      errors.push(`Replacement is forbidden for ${logicalId}.`);
    }
  }

  const expectedIds = new Set(expected.map(({ logicalId }) => logicalId));
  for (const expectedChange of expected) {
    const actualChange = actualById.get(expectedChange.logicalId);
    if (!actualChange) {
      errors.push(`Expected ${expectedChange.action} for ${expectedChange.logicalId} is missing.`);
      continue;
    }
    if (actualChange.Action !== expectedChange.action) {
      errors.push(
        `${expectedChange.logicalId} must be ${expectedChange.action}, not ${actualChange.Action ?? 'unknown'}.`,
      );
    }
    if (actualChange.ResourceType !== expectedChange.resourceType) {
      errors.push(`Resource type mismatch for ${expectedChange.logicalId}.`);
    }
  }
  for (const logicalId of actualById.keys()) {
    if (!expectedIds.has(logicalId)) {
      errors.push(`Unexpected change for ${logicalId}.`);
    }
  }
  return errors;
}

export function templatesMatch(expected: unknown, actual: unknown): boolean {
  return canonicalJson(expected) === canonicalJson(actual);
}

function readJson(path: string): unknown {
  if (path === 'ABSENT') {
    return { Resources: {} };
  }
  return JSON.parse(readFileSync(path, 'utf8')) as unknown;
}

function main(): void {
  const [mode, ...paths] = process.argv.slice(2);
  if (mode === 'template' && paths.length === 2) {
    if (!templatesMatch(readJson(paths[0]), readJson(paths[1]))) {
      console.error('CHANGE_SET_BLOCKED: CloudFormation change-set template differs from reviewed template.');
      process.exitCode = 1;
      return;
    }
    console.log('CHANGE_SET_TEMPLATE_OK');
    return;
  }
  if (mode === 'changes' && paths.length === 3) {
    const errors = validateChangeSet(
      readJson(paths[0]) as CloudFormationTemplate,
      readJson(paths[1]) as CloudFormationTemplate,
      readJson(paths[2]) as ChangeSetDescription,
    );
    if (errors.length > 0) {
      for (const error of errors) {
        console.error(`CHANGE_SET_BLOCKED: ${error}`);
      }
      process.exitCode = 1;
      return;
    }
    console.log('CHANGE_SET_ACTIONS_OK');
    return;
  }
  console.error(
    'CHANGE_SET_BLOCKED: use `template <reviewed.json> <cloudformation.json>` or '
      + '`changes <current.json> <target.json> <change-set.json>`.',
  );
  process.exitCode = 1;
}

if (require.main === module) {
  main();
}
