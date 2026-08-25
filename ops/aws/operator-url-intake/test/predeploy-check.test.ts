import {
  DEFAULT_DEPLOY_ROLE_NAME,
  EXPECTED_ACCOUNT_ID,
  EXPECTED_REGION,
  hasActiveUserCostTag,
  isAllowedDeploymentRole,
  parsePredeployPhase,
  validatePredeployEvidence,
} from '../scripts/predeploy-check';

const sha = 'a'.repeat(40);

function validEvidence() {
  return {
    caller: {
      Account: EXPECTED_ACCOUNT_ID,
      Arn: `arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/${DEFAULT_DEPLOY_ROLE_NAME}/operator-smoke`,
    },
    costTags: {
      CostAllocationTags: [{
        Status: 'Active',
        TagKey: 'HUBOptimusCostUnit',
        Type: 'UserDefined',
      }],
    },
    actualCommit: sha,
    expectedCommit: sha,
    region: EXPECTED_REGION,
    worktreeStatus: '',
  };
}

test('accepts only the exact account deployment role and active cost tag', () => {
  expect(validatePredeployEvidence(validEvidence())).toEqual([]);
  expect(isAllowedDeploymentRole(
    `arn:aws:iam::${EXPECTED_ACCOUNT_ID}:role/${DEFAULT_DEPLOY_ROLE_NAME}`,
  )).toBe(false);
  expect(hasActiveUserCostTag(validEvidence().costTags)).toBe(true);
});

test('foundation phase skips only the not-yet-activatable cost tag gate', () => {
  const evidence = validEvidence();
  evidence.costTags.CostAllocationTags[0].Status = 'Inactive';

  expect(validatePredeployEvidence(evidence, 'foundation')).toEqual([]);
  expect(validatePredeployEvidence(evidence, 'private')).toContain(
    'Cost allocation tag HUBOptimusCostUnit must be ACTIVE and UserDefined.',
  );
});

test('requires one exact predeploy phase', () => {
  expect(parsePredeployPhase(['--phase=foundation'])).toBe('foundation');
  expect(parsePredeployPhase(['--phase=private'])).toBe('private');
  expect(() => parsePredeployPhase([])).toThrow('Exactly one phase is required');
  expect(() => parsePredeployPhase(['--phase=private', '--extra'])).toThrow(
    'Exactly one phase is required',
  );
  expect(() => parsePredeployPhase(['--phase=public'])).toThrow(
    'Phase must be exactly',
  );
});

test('blocks root, the wrong account, region, commit, dirty tree and inactive tag', () => {
  const evidence = validEvidence();
  evidence.caller = {
    Account: '111111111111',
    Arn: `arn:aws:iam::${EXPECTED_ACCOUNT_ID}:root`,
  };
  evidence.region = 'eu-north-1';
  evidence.expectedCommit = 'main';
  evidence.worktreeStatus = ' M package.json';
  evidence.costTags.CostAllocationTags[0].Status = 'Inactive';

  expect(validatePredeployEvidence(evidence)).toEqual(expect.arrayContaining([
    `AWS account must be ${EXPECTED_ACCOUNT_ID}.`,
    'AWS root credentials are forbidden for deployment.',
    `AWS region must be ${EXPECTED_REGION}.`,
    'HUB_OPTIMUS_DEPLOY_SHA must be one exact 40-character lowercase commit SHA.',
    'Git worktree must be clean before deployment.',
    'Cost allocation tag HUBOptimusCostUnit must be ACTIVE and UserDefined.',
  ]));
});

test('blocks a valid-looking role from a different account or with a different name', () => {
  expect(isAllowedDeploymentRole(
    `arn:aws:sts::111111111111:assumed-role/${DEFAULT_DEPLOY_ROLE_NAME}/session`,
  )).toBe(false);
  expect(isAllowedDeploymentRole(
    `arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/Admin/session`,
  )).toBe(false);
});
