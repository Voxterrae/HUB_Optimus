import { execFileSync } from 'node:child_process';

export const EXPECTED_ACCOUNT_ID = '904851777129';
export const EXPECTED_REGION = 'eu-west-1';
export const REQUIRED_COST_TAG_KEY = 'HUBOptimusCostUnit';
export const DEFAULT_DEPLOY_ROLE_NAME = 'HUBOptimusOperatorDeploy';
export type PredeployPhase = 'foundation' | 'private';

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
  caller: CallerIdentity;
  costTags: CostAllocationTagsResponse;
  actualCommit: string;
  expectedCommit: string;
  region: string;
  worktreeStatus: string;
}

export function isAllowedDeploymentRole(arn: string): boolean {
  const escapedRole = DEFAULT_DEPLOY_ROLE_NAME.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
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

  if (evidence.caller.Account !== EXPECTED_ACCOUNT_ID) {
    errors.push(`AWS account must be ${EXPECTED_ACCOUNT_ID}.`);
  }
  if (arn.endsWith(':root')) {
    errors.push('AWS root credentials are forbidden for deployment.');
  } else if (!isAllowedDeploymentRole(arn)) {
    errors.push(`Caller must use the ${DEFAULT_DEPLOY_ROLE_NAME} deployment role.`);
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
  if (phase === 'private' && !hasActiveUserCostTag(evidence.costTags)) {
    errors.push(`Cost allocation tag ${REQUIRED_COST_TAG_KEY} must be ACTIVE and UserDefined.`);
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
    throw new Error('Exactly one phase is required: --phase=foundation or --phase=private.');
  }
  if (args[0] === '--phase=foundation') {
    return 'foundation';
  }
  if (args[0] === '--phase=private') {
    return 'private';
  }
  throw new Error('Phase must be exactly --phase=foundation or --phase=private.');
}

export function collectPredeployEvidence(phase: PredeployPhase): PredeployEvidence {
  const region = process.env.AWS_REGION ?? process.env.AWS_DEFAULT_REGION ?? '';
  const expectedCommit = process.env.HUB_OPTIMUS_DEPLOY_SHA ?? '';
  const caller = JSON.parse(run('aws', [
    'sts', 'get-caller-identity', '--region', region || EXPECTED_REGION, '--output', 'json',
  ])) as CallerIdentity;
  const costTags = phase === 'private'
    ? JSON.parse(run('aws', [
      'ce', 'list-cost-allocation-tags',
      '--status', 'Active',
      '--type', 'UserDefined',
      '--tag-keys', REQUIRED_COST_TAG_KEY,
      '--region', 'us-east-1',
      '--output', 'json',
    ])) as CostAllocationTagsResponse
    : { CostAllocationTags: [] };

  return {
    caller,
    costTags,
    actualCommit: run('git', ['rev-parse', 'HEAD']),
    expectedCommit,
    region,
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
