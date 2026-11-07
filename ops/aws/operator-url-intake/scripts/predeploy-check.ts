import { execFileSync } from 'node:child_process';

export const EXPECTED_ACCOUNT_ID = '904851777129';
export const EXPECTED_REGION = 'eu-west-1';
export const REQUIRED_COST_TAG_KEY = 'HUBOptimusCostUnit';
export const PREPARE_DEPLOY_ROLE_NAME = 'HUBOptimusOperatorPrepare';
export const EXECUTE_DEPLOY_ROLE_NAME = 'HUBOptimusOperatorExecute';
export const EXPECTED_GITHUB_REPOSITORY = 'Voxterrae/HUB_Optimus';
export const EXPECTED_GITHUB_REF = 'refs/heads/main';
export const EXPECTED_GITHUB_ENVIRONMENTS = [
  'operator-private-canary-prepare',
  'operator-private-canary-execute',
] as const;
export const STACK_NAME = 'hub-optimus-operator-infra';
export type PredeployPhase = 'foundation' | 'controls' | 'private' | 'deactivate';
export type StackPhase = 'ABSENT' | 'FOUNDATION' | 'CONTROLS' | 'PRIVATE' | 'UNKNOWN';

export interface CallerIdentity {
  Account?: string;
  Arn?: string;
}

export interface CostAllocationTag {
  Status?: string;
  TagKey?: string;
  Type?: string;
}

export interface CostAllocationTagsResponse {
  CostAllocationTags?: CostAllocationTag[];
}

export interface PredeployEvidence {
  canaryExpiresAt: string;
  canaryStartedAt: string;
  caller: CallerIdentity;
  costTags: CostAllocationTagsResponse;
  currentReservedConcurrency: number | null;
  actualCommit: string;
  currentStackPhase: StackPhase;
  deployedSourceCommit: string;
  expectedCommit: string;
  githubActions: string;
  githubEnvironment: string;
  githubRef: string;
  githubRepository: string;
  githubSha: string;
  nowMs: number;
  originMainCommit: string;
  region: string;
  stackExists: boolean;
  stackStatus: string;
  worktreeStatus: string;
}

const MAX_CANARY_WINDOW_MS = 2 * 60 * 60 * 1_000;
const MAX_CANARY_START_SKEW_MS = 15 * 60 * 1_000;
const MIN_CANARY_REMAINING_MS = 30 * 60 * 1_000;

export function isValidImmediateCanaryWindow(
  startedAt: string,
  expiresAt: string,
  nowMs: number,
): boolean {
  const utcTimestamp = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
  if (!utcTimestamp.test(startedAt) || !utcTimestamp.test(expiresAt)) {
    return false;
  }
  const startMs = Date.parse(startedAt);
  const expiryMs = Date.parse(expiresAt);
  return Number.isFinite(startMs)
    && Number.isFinite(expiryMs)
    && Math.abs(startMs - nowMs) <= MAX_CANARY_START_SKEW_MS
    && expiryMs - nowMs >= MIN_CANARY_REMAINING_MS
    && expiryMs > startMs
    && expiryMs - startMs <= MAX_CANARY_WINDOW_MS;
}

export function isAllowedDeploymentRole(arn: string, roleName: string): boolean {
  const escapedRole = roleName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(
    `^arn:aws:sts::${EXPECTED_ACCOUNT_ID}:assumed-role/${escapedRole}/[^/]+$`,
  ).test(arn);
}

export function hasActiveUserCostTag(
  response: CostAllocationTagsResponse,
  tagKey = REQUIRED_COST_TAG_KEY,
): boolean {
  return (response.CostAllocationTags ?? []).some((tag) =>
    tag.TagKey === tagKey
      && tag.Status?.toUpperCase() === 'ACTIVE'
      && tag.Type?.toUpperCase() === 'USERDEFINED',
  );
}

export function validatePredeployEvidence(
  evidence: PredeployEvidence,
  phase: PredeployPhase = 'private',
): string[] {
  const errors: string[] = [];
  const arn = evidence.caller.Arn ?? '';
  const expectedRoleName = evidence.githubEnvironment === 'operator-private-canary-prepare'
    ? PREPARE_DEPLOY_ROLE_NAME
    : evidence.githubEnvironment === 'operator-private-canary-execute'
      ? EXECUTE_DEPLOY_ROLE_NAME
      : '';

  if (evidence.caller.Account !== EXPECTED_ACCOUNT_ID) {
    errors.push(`AWS account must be ${EXPECTED_ACCOUNT_ID}.`);
  }
  if (arn.endsWith(':root')) {
    errors.push('AWS root credentials are forbidden for deployment.');
  } else if (!expectedRoleName || !isAllowedDeploymentRole(arn, expectedRoleName)) {
    errors.push('Caller must use the phase-specific protected deployment role.');
  }
  if (evidence.region !== EXPECTED_REGION) {
    errors.push(`AWS region must be ${EXPECTED_REGION}.`);
  }
  if (!/^[0-9a-f]{40}$/.test(evidence.expectedCommit)) {
    errors.push('HUB_OPTIMUS_DEPLOY_SHA must be one exact 40-character lowercase commit SHA.');
  } else if (evidence.actualCommit !== evidence.expectedCommit) {
    errors.push('Checked-out commit does not match HUB_OPTIMUS_DEPLOY_SHA.');
  }
  if (evidence.worktreeStatus.trim() !== '') {
    errors.push('Git worktree must be clean before deployment.');
  }
  const protectedGitHubRun = evidence.githubActions === 'true'
    && evidence.githubRepository === EXPECTED_GITHUB_REPOSITORY
    && evidence.githubRef === EXPECTED_GITHUB_REF
    && EXPECTED_GITHUB_ENVIRONMENTS.includes(
      evidence.githubEnvironment as typeof EXPECTED_GITHUB_ENVIRONMENTS[number],
    );
  const trustedWorkflowSource = phase === 'deactivate'
    ? /^[0-9a-f]{40}$/.test(evidence.githubSha)
      && evidence.githubSha === evidence.originMainCommit
    : evidence.githubSha === evidence.expectedCommit
      && evidence.originMainCommit === evidence.expectedCommit;
  if (!protectedGitHubRun || !trustedWorkflowSource) {
    errors.push(
      `Deployment must run from protected ${EXPECTED_GITHUB_REPOSITORY} ${EXPECTED_GITHUB_REF} canary environments.`,
    );
  }
  if (phase !== 'deactivate' && evidence.originMainCommit !== evidence.expectedCommit) {
    errors.push('Approved commit must be the fetched origin/main tip.');
  }
  const foundationPrepare = phase === 'foundation'
    && evidence.githubEnvironment === 'operator-private-canary-prepare';
  const foundationExecute = phase === 'foundation'
    && evidence.githubEnvironment === 'operator-private-canary-execute';
  const validStackState = foundationPrepare
    ? !evidence.stackExists && evidence.currentStackPhase === 'ABSENT'
    : foundationExecute
      ? evidence.stackExists
        && evidence.stackStatus === 'REVIEW_IN_PROGRESS'
        && evidence.currentStackPhase === 'UNKNOWN'
      : phase === 'controls'
        ? evidence.stackExists
          && evidence.stackStatus === 'CREATE_COMPLETE'
          && evidence.currentStackPhase === 'FOUNDATION'
        : phase === 'private'
          ? evidence.stackExists
            && evidence.stackStatus === 'UPDATE_COMPLETE'
            && evidence.currentStackPhase === 'CONTROLS'
          : evidence.stackExists
            && evidence.stackStatus === 'UPDATE_COMPLETE'
            && evidence.currentStackPhase === 'PRIVATE';
  if (!validStackState) {
    errors.push(
      `AWS stack state is not valid for ${phase}/${evidence.githubEnvironment || 'unknown-environment'}.`,
    );
  }
  if (phase !== 'foundation' && evidence.deployedSourceCommit !== evidence.expectedCommit) {
    errors.push('Deployed SourceCommit must match the exact rollout commit.');
  }
  if (phase === 'deactivate' && evidence.currentReservedConcurrency !== 0) {
    errors.push('Deactivate requires the emergency stop to set Lambda concurrency to zero first.');
  }
  if ((phase === 'controls' || phase === 'private') && !hasActiveUserCostTag(evidence.costTags)) {
    errors.push(`Cost allocation tag ${REQUIRED_COST_TAG_KEY} must be ACTIVE and UserDefined.`);
  }
  if (phase === 'private' && !isValidImmediateCanaryWindow(
    evidence.canaryStartedAt,
    evidence.canaryExpiresAt,
    evidence.nowMs,
  )) {
    errors.push(
      'Private canary window must start within 15 minutes, retain at least 30 minutes, and last at most two hours.',
    );
  }

  return errors;
}

function run(command: string, args: string[]): string {
  return execFileSync(command, args, {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();
}

export function parsePredeployPhase(args: string[]): PredeployPhase {
  if (args.length !== 1) {
    throw new Error(
      'Exactly one phase is required: --phase=foundation, --phase=controls, --phase=private, or --phase=deactivate.',
    );
  }
  if (args[0] === '--phase=foundation') {
    return 'foundation';
  }
  if (args[0] === '--phase=private') {
    return 'private';
  }
  if (args[0] === '--phase=controls') {
    return 'controls';
  }
  if (args[0] === '--phase=deactivate') {
    return 'deactivate';
  }
  throw new Error(
    'Phase must be exactly --phase=foundation, --phase=controls, --phase=private, or --phase=deactivate.',
  );
}

export function parseCurrentStackPhase(raw: string | undefined, stackExists: boolean): StackPhase {
  return raw === 'FOUNDATION' || raw === 'CONTROLS' || raw === 'PRIVATE'
    ? raw
    : raw === undefined && !stackExists
      ? 'ABSENT'
      : 'UNKNOWN';
}

function collectCurrentStackState(region: string): {
  exists: boolean;
  phase: StackPhase;
  sourceCommit: string;
  status: string;
} {
  try {
    const result = JSON.parse(run('aws', [
      'cloudformation', 'describe-stacks',
      '--stack-name', STACK_NAME,
      '--region', region,
      '--output', 'json',
    ])) as {
      Stacks?: Array<{
        Outputs?: Array<{ OutputKey?: string; OutputValue?: string }>;
        StackStatus?: string;
      }>;
    };
    const stack = result.Stacks?.[0];
    if (!stack) {
      throw new Error('DescribeStacks returned no stack for the fixed stack name.');
    }
    const phase = stack.Outputs
      ?.find((output) => output.OutputKey === 'DeploymentPhase')?.OutputValue;
    const sourceCommit = stack.Outputs
      ?.find((output) => output.OutputKey === 'SourceCommit')?.OutputValue ?? '';
    return {
      exists: true,
      phase: parseCurrentStackPhase(phase, true),
      sourceCommit,
      status: stack.StackStatus ?? '',
    };
  } catch (error) {
    const stderr = (error as { stderr?: string | Buffer }).stderr?.toString() ?? '';
    if (/does not exist/i.test(stderr)) {
      return { exists: false, phase: 'ABSENT', sourceCommit: '', status: '' };
    }
    throw error;
  }
}

export function collectPredeployEvidence(phase: PredeployPhase): PredeployEvidence {
  const region = process.env.AWS_REGION ?? process.env.AWS_DEFAULT_REGION ?? '';
  const expectedCommit = process.env.HUB_OPTIMUS_DEPLOY_SHA ?? '';
  const caller = JSON.parse(run('aws', [
    'sts', 'get-caller-identity', '--region', region || EXPECTED_REGION, '--output', 'json',
  ])) as CallerIdentity;
  const costTags = phase === 'controls' || phase === 'private'
    ? JSON.parse(run('aws', [
      'ce', 'list-cost-allocation-tags',
      '--status', 'Active',
      '--type', 'UserDefined',
      '--tag-keys', REQUIRED_COST_TAG_KEY,
      '--region', 'us-east-1',
      '--output', 'json',
    ])) as CostAllocationTagsResponse
    : { CostAllocationTags: [] };
  const currentStack = collectCurrentStackState(region || EXPECTED_REGION);
  const currentReservedConcurrency = phase === 'deactivate'
    ? Number(run('aws', [
      'lambda', 'get-function-concurrency',
      '--function-name', 'hub-optimus-operator-url-intake',
      '--region', region || EXPECTED_REGION,
      '--query', 'ReservedConcurrentExecutions',
      '--output', 'text',
    ]))
    : null;

  return {
    canaryExpiresAt: process.env.CANARY_EXPIRES_AT ?? '',
    canaryStartedAt: process.env.CANARY_STARTED_AT ?? '',
    caller,
    costTags,
    currentReservedConcurrency,
    actualCommit: run('git', ['rev-parse', 'HEAD']),
    currentStackPhase: currentStack.phase,
    deployedSourceCommit: currentStack.sourceCommit,
    expectedCommit,
    githubActions: process.env.GITHUB_ACTIONS ?? '',
    githubEnvironment: process.env.HUB_OPTIMUS_GITHUB_ENVIRONMENT ?? '',
    githubRef: process.env.GITHUB_REF ?? '',
    githubRepository: process.env.GITHUB_REPOSITORY ?? '',
    githubSha: process.env.GITHUB_SHA ?? '',
    nowMs: Date.now(),
    originMainCommit: run('git', ['rev-parse', 'origin/main']),
    region,
    stackExists: currentStack.exists,
    stackStatus: currentStack.status,
    worktreeStatus: run('git', ['status', '--porcelain']),
  };
}

export function main(): void {
  try {
    const phase = parsePredeployPhase(process.argv.slice(2));
    const evidence = collectPredeployEvidence(phase);
    const errors = validatePredeployEvidence(evidence, phase);
    if (errors.length > 0) {
      for (const error of errors) {
        console.error(`PREDEPLOY_BLOCKED: ${error}`);
      }
      process.exitCode = 1;
      return;
    }
    console.log(
      `PREDEPLOY_OK phase=${phase} account=${EXPECTED_ACCOUNT_ID} region=${EXPECTED_REGION} commit=${evidence.actualCommit}`,
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : 'unknown predeploy error';
    console.error(`PREDEPLOY_BLOCKED: ${message}`);
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main();
}
