import {
  EXECUTE_DEPLOY_ROLE_NAME,
  EXPECTED_ACCOUNT_ID,
  EXPECTED_GITHUB_ENVIRONMENTS,
  EXPECTED_GITHUB_REF,
  EXPECTED_GITHUB_REPOSITORY,
  EXPECTED_REGION,
  PREPARE_DEPLOY_ROLE_NAME,
  hasActiveUserCostTag,
  isValidImmediateCanaryWindow,
  isAllowedDeploymentRole,
  parseCurrentStackPhase,
  parsePredeployPhase,
  validatePredeployEvidence,
} from '../scripts/predeploy-check';

const sha = 'a'.repeat(40);

function validEvidence(
  currentStackPhase: 'ABSENT' | 'FOUNDATION' | 'CONTROLS' | 'PRIVATE' | 'UNKNOWN' = 'CONTROLS',
) {
  const nowMs = Date.parse('2026-08-26T12:00:00Z');
  return {
    canaryExpiresAt: '2026-08-26T14:00:00Z',
    canaryStartedAt: '2026-08-26T12:00:00Z',
    caller: {
      Account: EXPECTED_ACCOUNT_ID,
      Arn: `arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/${PREPARE_DEPLOY_ROLE_NAME}/operator-smoke`,
    },
    costTags: {
      CostAllocationTags: [{
        Status: 'Active',
        TagKey: 'HUBOptimusCostUnit',
        Type: 'UserDefined',
      }],
    },
    currentReservedConcurrency: 0,
    actualCommit: sha,
    currentStackPhase,
    deployedSourceCommit: sha,
    expectedCommit: sha,
    githubActions: 'true',
    githubEnvironment: EXPECTED_GITHUB_ENVIRONMENTS[0] as string,
    githubRef: EXPECTED_GITHUB_REF,
    githubRepository: EXPECTED_GITHUB_REPOSITORY,
    githubSha: sha,
    nowMs,
    originMainCommit: sha,
    region: EXPECTED_REGION,
    stackExists: currentStackPhase !== 'ABSENT',
    stackStatus: currentStackPhase === 'FOUNDATION'
      ? 'CREATE_COMPLETE'
      : currentStackPhase === 'CONTROLS' || currentStackPhase === 'PRIVATE'
        ? 'UPDATE_COMPLETE'
        : '',
    worktreeStatus: '',
  };
}

test('accepts only the exact account deployment role and active cost tag', () => {
  expect(validatePredeployEvidence(validEvidence())).toEqual([]);
  expect(isAllowedDeploymentRole(
    `arn:aws:iam::${EXPECTED_ACCOUNT_ID}:role/${PREPARE_DEPLOY_ROLE_NAME}`,
    PREPARE_DEPLOY_ROLE_NAME,
  )).toBe(false);
  expect(hasActiveUserCostTag(validEvidence().costTags)).toBe(true);
});

test('foundation phase skips only the not-yet-activatable cost tag gate', () => {
  const foundationEvidence = validEvidence('ABSENT');
  const controlsEvidence = validEvidence('FOUNDATION');
  const privateEvidence = validEvidence('CONTROLS');
  foundationEvidence.costTags.CostAllocationTags[0].Status = 'Inactive';
  controlsEvidence.costTags.CostAllocationTags[0].Status = 'Inactive';
  privateEvidence.costTags.CostAllocationTags[0].Status = 'Inactive';

  expect(validatePredeployEvidence(foundationEvidence, 'foundation')).toEqual([]);
  expect(validatePredeployEvidence(controlsEvidence, 'controls')).toContain(
    'Cost allocation tag HUBOptimusCostUnit must be ACTIVE and UserDefined.',
  );
  expect(validatePredeployEvidence(privateEvidence, 'private')).toContain(
    'Cost allocation tag HUBOptimusCostUnit must be ACTIVE and UserDefined.',
  );
});

test('private phase requires an immediate window of at most two hours', () => {
  const nowMs = Date.parse('2026-08-26T12:00:00Z');
  expect(isValidImmediateCanaryWindow(
    '2026-08-26T12:00:00Z',
    '2026-08-26T14:00:00Z',
    nowMs,
  )).toBe(true);
  expect(isValidImmediateCanaryWindow(
    '2026-08-26T12:00:00Z',
    '2026-08-26T14:00:01Z',
    nowMs,
  )).toBe(false);
  expect(isValidImmediateCanaryWindow(
    '2026-08-26T12:00:00Z',
    '2026-08-26T12:29:59Z',
    nowMs,
  )).toBe(false);
  const evidence = validEvidence();
  evidence.canaryExpiresAt = '';
  expect(validatePredeployEvidence(evidence, 'private')).toContain(
    'Private canary window must start within 15 minutes, retain at least 30 minutes, and last at most two hours.',
  );
  expect(validatePredeployEvidence(evidence, 'controls')).not.toContain(
    'Private canary window must start within 15 minutes, retain at least 30 minutes, and last at most two hours.',
  );
});

test('requires one exact predeploy phase', () => {
  expect(parsePredeployPhase(['--phase=foundation'])).toBe('foundation');
  expect(parsePredeployPhase(['--phase=controls'])).toBe('controls');
  expect(parsePredeployPhase(['--phase=private'])).toBe('private');
  expect(parsePredeployPhase(['--phase=deactivate'])).toBe('deactivate');
  expect(() => parsePredeployPhase([])).toThrow('Exactly one phase is required');
  expect(() => parsePredeployPhase(['--phase=private', '--extra'])).toThrow(
    'Exactly one phase is required',
  );
  expect(() => parsePredeployPhase(['--phase=public'])).toThrow(
    'Phase must be exactly',
  );
});

test('enforces exact phase order and a protected merged-main GitHub run', () => {
  expect(validatePredeployEvidence(validEvidence('ABSENT'), 'foundation')).toEqual([]);
  expect(validatePredeployEvidence(validEvidence('FOUNDATION'), 'controls')).toEqual([]);
  expect(validatePredeployEvidence(validEvidence('CONTROLS'), 'private')).toEqual([]);
  expect(validatePredeployEvidence(validEvidence('PRIVATE'), 'deactivate')).toEqual([]);

  const wrong = validEvidence('FOUNDATION');
  wrong.githubRef = 'refs/pull/1918/merge';
  wrong.originMainCommit = 'b'.repeat(40);
  expect(validatePredeployEvidence(wrong, 'private')).toEqual(expect.arrayContaining([
    expect.stringContaining('Deployment must run from protected'),
    'Approved commit must be the fetched origin/main tip.',
    expect.stringContaining('AWS stack state is not valid for private/'),
  ]));
  expect(parseCurrentStackPhase('PRIVATE', true)).toBe('PRIVATE');
  expect(parseCurrentStackPhase(undefined, false)).toBe('ABSENT');
  expect(parseCurrentStackPhase(undefined, true)).toBe('UNKNOWN');
  expect(parseCurrentStackPhase('BROKEN', true)).toBe('UNKNOWN');
});

test('accepts a foundation CREATE placeholder only in the execute environment', () => {
  const evidence = validEvidence('ABSENT');
  evidence.stackExists = true;
  evidence.stackStatus = 'REVIEW_IN_PROGRESS';
  evidence.currentStackPhase = 'UNKNOWN';
  evidence.githubEnvironment = EXPECTED_GITHUB_ENVIRONMENTS[1];
  evidence.caller.Arn =
    `arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/${EXECUTE_DEPLOY_ROLE_NAME}/operator-smoke`;
  expect(validatePredeployEvidence(evidence, 'foundation')).toEqual([]);

  evidence.githubEnvironment = EXPECTED_GITHUB_ENVIRONMENTS[0];
  evidence.caller.Arn =
    `arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/${PREPARE_DEPLOY_ROLE_NAME}/operator-smoke`;
  expect(validatePredeployEvidence(evidence, 'foundation')).toContainEqual(
    expect.stringContaining('AWS stack state is not valid'),
  );
});

test('blocks an existing stack without a governed phase and a stale rollout source', () => {
  const unknown = validEvidence('CONTROLS');
  unknown.currentStackPhase = 'UNKNOWN';
  expect(validatePredeployEvidence(unknown, 'private')).toContainEqual(
    expect.stringContaining('AWS stack state is not valid'),
  );

  const stale = validEvidence('CONTROLS');
  stale.deployedSourceCommit = 'b'.repeat(40);
  expect(validatePredeployEvidence(stale, 'private')).toContain(
    'Deployed SourceCommit must match the exact rollout commit.',
  );
});

test('deactivation is tied to the deployed source while the workflow stays on current main', () => {
  const activationSha = 'b'.repeat(40);
  const evidence = validEvidence('PRIVATE');
  evidence.actualCommit = activationSha;
  evidence.expectedCommit = activationSha;
  evidence.deployedSourceCommit = activationSha;
  expect(validatePredeployEvidence(evidence, 'deactivate')).toEqual([]);

  evidence.currentReservedConcurrency = 1;
  expect(validatePredeployEvidence(evidence, 'deactivate')).toContain(
    'Deactivate requires the emergency stop to set Lambda concurrency to zero first.',
  );
  evidence.currentReservedConcurrency = 0;

  evidence.deployedSourceCommit = 'c'.repeat(40);
  expect(validatePredeployEvidence(evidence, 'deactivate')).toContain(
    'Deployed SourceCommit must match the exact rollout commit.',
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
    `arn:aws:sts::111111111111:assumed-role/${PREPARE_DEPLOY_ROLE_NAME}/session`,
    PREPARE_DEPLOY_ROLE_NAME,
  )).toBe(false);
  expect(isAllowedDeploymentRole(
    `arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/Admin/session`,
    PREPARE_DEPLOY_ROLE_NAME,
  )).toBe(false);
});

test('requires different roles for prepare and execute environments', () => {
  const executeEvidence = validEvidence();
  executeEvidence.githubEnvironment = EXPECTED_GITHUB_ENVIRONMENTS[1];
  executeEvidence.caller.Arn =
    `arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/${EXECUTE_DEPLOY_ROLE_NAME}/operator-smoke`;
  expect(validatePredeployEvidence(executeEvidence)).toEqual([]);

  executeEvidence.caller.Arn =
    `arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/${PREPARE_DEPLOY_ROLE_NAME}/operator-smoke`;
  expect(validatePredeployEvidence(executeEvidence)).toContain(
    'Caller must use the phase-specific protected deployment role.',
  );
});
