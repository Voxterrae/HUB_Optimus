import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const projectRoot = join(__dirname, '..');
const repositoryRoot = join(projectRoot, '../../..');
const deploymentWorkflow = readFileSync(
  join(repositoryRoot, '.github/workflows/operator-private-canary.yml'),
  'utf8',
);
const stopWorkflow = readFileSync(
  join(repositoryRoot, '.github/workflows/operator-private-canary-stop.yml'),
  'utf8',
);

function readPolicy(name: string): { Statement: Array<Record<string, unknown>> } {
  return JSON.parse(readFileSync(join(projectRoot, 'iam', name), 'utf8')) as {
    Statement: Array<Record<string, unknown>>;
  };
}

test('change-set validation uses documented fields and verifies the final stack role', () => {
  expect(deploymentWorkflow).not.toContain("jq -r '.ChangeSetType'");
  expect(deploymentWorkflow).not.toContain("jq -r '.RoleARN'");
  expect(deploymentWorkflow).toContain("jq -r '.Stacks[0].RoleARN'");
  expect(deploymentWorkflow).toContain('EXPECTED_CHANGE_SET_TYPE=CREATE');
});

test('Lambda deployment is bound to one immutable S3 object version and checksum', () => {
  expect(deploymentWorkflow).toContain('get-bucket-versioning');
  expect(deploymentWorkflow).toContain('S3ObjectVersion = $version');
  expect(deploymentWorkflow).toContain('--version-id "$EXPECTED_ASSET_VERSION_ID"');
  expect(deploymentWorkflow).toContain('Configuration.CodeSha256');
  expect(deploymentWorkflow).toContain('DEPLOYMENT_FINGERPRINT_KEY');
  expect(deploymentWorkflow).toContain('PUBLISH_SESSION_POLICY');
  expect(deploymentWorkflow).toContain('--policy "$PUBLISH_SESSION_POLICY"');
  expect(deploymentWorkflow).not.toContain('s3:DeleteObject');
});

test('emergency stop cancels the forward run and owns the only direct concurrency mutation', () => {
  expect(stopWorkflow).toContain('group: operator-private-canary-forward');
  expect(stopWorkflow).toContain('cancel-in-progress: true');
  expect(stopWorkflow.match(/set_concurrency_zero/g)).toHaveLength(3);

  const execute = readPolicy('execute-permissions-policy.json');
  const stop = readPolicy('stop-permissions-policy.json');
  expect(JSON.stringify(execute)).not.toContain('lambda:PutFunctionConcurrency');
  expect(JSON.stringify(stop)).toContain('lambda:PutFunctionConcurrency');
  expect(JSON.stringify(stop)).toContain('cloudformation:DescribeStacks');
});

test('private containment also runs when execution is cancelled or times out', () => {
  expect(deploymentWorkflow).toContain(
    "always() && (inputs.phase == 'private' || inputs.phase == 'deactivate') && needs.execute.result != 'success'",
  );
  expect(deploymentWorkflow).not.toContain("needs.execute.result == 'failure'");
  expect(deploymentWorkflow).toContain('timeout-minutes: 150');
  expect(deploymentWorkflow).toContain('for _ in $(seq 1 720); do');
  expect(deploymentWorkflow).toContain('try_concurrency_zero || true');
  expect(stopWorkflow).toContain('timeout-minutes: 150');
  expect(stopWorkflow).toContain('for _ in $(seq 1 720); do');
  expect(stopWorkflow).toContain('try_concurrency_zero || true');
  expect(deploymentWorkflow).toContain('role-duration-seconds: 10800');
  expect(stopWorkflow).toContain('role-duration-seconds: 10800');
});

test('prepare and execute policies constrain the service role and change-set name', () => {
  const prepare = JSON.stringify(readPolicy('prepare-permissions-policy.json'));
  const execute = JSON.stringify(readPolicy('execute-permissions-policy.json'));
  expect(prepare).toContain('cloudformation:RoleArn');
  expect(prepare).toContain('cloudformation:ChangeSetName');
  expect(execute).toContain('cloudformation:ChangeSetName');
  expect(prepare).toContain('DenyAssumingEveryOtherRole');
  expect(execute).toContain('DenyAssumingAnyRole');
});

test('postdeploy verifies live Cognito signup, MFA and OAuth configuration', () => {
  const execute = JSON.stringify(readPolicy('execute-permissions-policy.json'));
  expect(execute).toContain('cognito-idp:DescribeUserPool');
  expect(execute).toContain('cognito-idp:DescribeUserPoolClient');
  expect(execute).toContain('aws:ResourceTag/HUBOptimusCostUnit');
  expect(deploymentWorkflow).toContain('AdminCreateUserConfig.AllowAdminCreateUserOnly == true');
  expect(deploymentWorkflow).toContain('.UserPool.MfaConfiguration == "ON"');
  expect(deploymentWorkflow).toContain('SoftwareTokenMfaConfiguration.Enabled == true');
  expect(deploymentWorkflow).toContain('AllowedOAuthFlows[]?] | sort) == ["code"]');
  expect(deploymentWorkflow).toContain('== ["ALLOW_REFRESH_TOKEN_AUTH"]');
  expect(deploymentWorkflow.match(/verify_live_identity/g)).toHaveLength(3);
  expect(deploymentWorkflow.indexOf('verify_live_identity "$PRE_EXECUTE_STACK_JSON"'))
    .toBeLessThan(deploymentWorkflow.indexOf('aws cloudformation execute-change-set'));
});
