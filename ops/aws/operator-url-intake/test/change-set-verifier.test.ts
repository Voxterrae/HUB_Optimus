import {
  deriveExpectedResourceChanges,
  templatesMatch,
  validateChangeSet,
} from '../scripts/verify-change-set';

const current = {
  Resources: {
    Existing: { Type: 'AWS::Example::Resource', Properties: { Enabled: false } },
    Removed: { Type: 'AWS::Example::Old' },
  },
};
const target = {
  Resources: {
    Added: { Type: 'AWS::Example::New' },
    Existing: { Type: 'AWS::Example::Resource', Properties: { Enabled: true } },
  },
};
const validChangeSet = {
  Changes: [
    { ResourceChange: {
      Action: 'Add', LogicalResourceId: 'Added', ResourceType: 'AWS::Example::New',
    } },
    { ResourceChange: {
      Action: 'Modify', LogicalResourceId: 'Existing', Replacement: 'False',
      ResourceType: 'AWS::Example::Resource',
    } },
    { ResourceChange: {
      Action: 'Remove', LogicalResourceId: 'Removed', ResourceType: 'AWS::Example::Old',
    } },
  ],
};

test('derives an exact resource-action allowlist from reviewed templates', () => {
  expect(deriveExpectedResourceChanges(current, target)).toEqual([
    { action: 'Add', logicalId: 'Added', resourceType: 'AWS::Example::New' },
    { action: 'Modify', logicalId: 'Existing', resourceType: 'AWS::Example::Resource' },
    { action: 'Remove', logicalId: 'Removed', resourceType: 'AWS::Example::Old' },
  ]);
  expect(validateChangeSet(current, target, validChangeSet)).toEqual([]);
});

test('rejects replacements, unexpected resources and action mismatches', () => {
  const unsafe = structuredClone(validChangeSet);
  unsafe.Changes[1].ResourceChange.Replacement = 'True';
  unsafe.Changes[2].ResourceChange.Action = 'Modify';
  unsafe.Changes.push({ ResourceChange: {
    Action: 'Add', LogicalResourceId: 'Surprise', ResourceType: 'AWS::IAM::Role',
  } });
  expect(validateChangeSet(current, target, unsafe)).toEqual(expect.arrayContaining([
    'Modify must declare Replacement=False for Existing.',
    'Removed must be Remove, not Modify.',
    'Unexpected change for Surprise.',
  ]));
});

test('fails closed when a modify has no explicit replacement decision', () => {
  const indeterminate = structuredClone(validChangeSet);
  delete indeterminate.Changes[1].ResourceChange.Replacement;
  expect(validateChangeSet(current, target, indeterminate)).toContain(
    'Modify must declare Replacement=False for Existing.',
  );
});

test('compares templates independently of object key order', () => {
  expect(templatesMatch(
    { Resources: { A: { Type: 'X' } }, Parameters: { P: { Type: 'String' } } },
    { Parameters: { P: { Type: 'String' } }, Resources: { A: { Type: 'X' } } },
  )).toBe(true);
  expect(templatesMatch(current, target)).toBe(false);
});
