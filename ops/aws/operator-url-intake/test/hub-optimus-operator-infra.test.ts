import * as cdk from 'aws-cdk-lib/core';
import { Match, Template } from 'aws-cdk-lib/assertions';
import { HubOptimusOperatorInfraStack } from '../lib/hub-optimus-operator-infra-stack';
import { Config } from '../lib/config';
import { OPERATOR_INTAKE_SCOPE } from '../frontend/pkce-client';

const APPROVED_SHA = 'a'.repeat(40);
const BASE_CONTEXT = {
  branchName: 'main',
  deploymentPhase: 'foundation',
  environmentName: 'private-canary',
  gitCommit: APPROVED_SHA,
  identityProviderDecision: 'cognito-temporary-canary',
  publicSignupEnabled: 'false',
  repoName: 'Voxterrae/HUB_Optimus',
};

function synthTemplate(context: Record<string, string> = {}): Template {
  const app = new cdk.App({ context: { ...BASE_CONTEXT, ...context } });
  const stack = new HubOptimusOperatorInfraStack(app, 'TestStack');
  return Template.fromStack(stack);
}

test('requires exact merged-main provenance and records the full SHA', () => {
  const template = synthTemplate();

  template.hasOutput('DeploymentInfo', {
    Description: 'Required source of this deployment: exact repository, main branch, and full commit',
    Value: `Voxterrae/HUB_Optimus (main) @ ${APPROVED_SHA}`,
  });
  template.hasOutput('SourceCommit', { Value: APPROVED_SHA });
  expect(() => synthTemplate({ gitCommit: 'main' })).toThrow(
    'gitCommit must be one exact 40-character lowercase commit SHA.',
  );
  expect(() => synthTemplate({ branchName: 'issue-1917-operator-url-intake-pilot' })).toThrow(
    'branchName must be exactly main.',
  );
  expect(() => synthTemplate({ environmentName: 'candidate' })).toThrow(
    'environmentName must be exactly private-canary.',
  );
});

test('creates a tightly bounded, VPC-free URL ingestion Lambda', () => {
  const template = synthTemplate();

  template.hasResourceProperties('AWS::Lambda::Function', {
    Architectures: ['arm64'],
    MemorySize: 128,
    FunctionName: 'hub-optimus-operator-url-intake',
    ReservedConcurrentExecutions: 0,
    Runtime: 'nodejs22.x',
    Timeout: 10,
    Environment: {
      Variables: Match.objectLike({
        FETCH_TIMEOUT_MS: '8000',
        MAX_CONTENT_BYTES: '1000000',
        MAX_EXTRACTED_TEXT_CHARS: '24000',
        MAX_REDIRECTS: '3',
        MAX_REQUEST_BYTES: '4096',
        CANARY_REQUESTS_TOTAL: '3',
        EXPECTED_CLIENT_ID: Match.anyValue(),
        REQUIRED_SCOPE: 'operator/intake',
      }),
    },
    VpcConfig: Match.absent(),
  });

  template.hasResourceProperties('AWS::DynamoDB::Table', {
    BillingMode: 'PAY_PER_REQUEST',
    KeySchema: [{ AttributeName: 'canaryWindow', KeyType: 'HASH' }],
    TimeToLiveSpecification: {
      AttributeName: 'expiresAt',
      Enabled: true,
    },
  });
  const clientLogicalId = Object.keys(template.findResources('AWS::Cognito::UserPoolClient'))[0];
  const intakeFunction = Object.values(template.findResources('AWS::Lambda::Function'))[0];
  expect(intakeFunction.Properties.Environment.Variables.EXPECTED_CLIENT_ID).toEqual({
    Ref: clientLogicalId,
  });
  template.resourceCountIs('AWS::SQS::Queue', 0);
  template.resourceCountIs('AWS::EC2::NatGateway', 0);
  template.resourceCountIs('AWS::EC2::VPC', 0);
});

test('exposes only authenticated POST /intake/url in private phase with exact-origin CORS and stage throttling', () => {
  const template = synthTemplate({ deploymentPhase: 'private' });

  template.hasResourceProperties('AWS::ApiGatewayV2::Api', {
    ProtocolType: 'HTTP',
    CorsConfiguration: {
      AllowHeaders: ['authorization', 'content-type'],
      AllowMethods: ['POST'],
      AllowOrigins: ['https://huboptimus.dev'],
      MaxAge: 600,
    },
  });
  template.hasResourceProperties('AWS::ApiGatewayV2::Route', {
    AuthorizationScopes: ['operator/intake'],
    AuthorizationType: 'JWT',
    RouteKey: 'POST /intake/url',
  });
  template.hasResourceProperties('AWS::ApiGatewayV2::Authorizer', {
    AuthorizerType: 'JWT',
    IdentitySource: ['$request.header.Authorization'],
  });
  template.hasResourceProperties('AWS::ApiGatewayV2::Stage', {
    AutoDeploy: true,
    DefaultRouteSettings: {
      ThrottlingBurstLimit: 2,
      ThrottlingRateLimit: 0.2,
    },
    StageName: '$default',
    AccessLogSettings: Match.objectLike({
      Format: Match.stringLikeRegexp('requestId'),
    }),
  });
});

test('defaults foundation service and public signup fail-closed with a scoped access-token client', () => {
  const template = synthTemplate();

  expect(Config.REQUIRED_SCOPE).toBe(OPERATOR_INTAKE_SCOPE);

  template.hasResourceProperties('AWS::Cognito::UserPool', {
    AdminCreateUserConfig: { AllowAdminCreateUserOnly: true },
    AutoVerifiedAttributes: ['email'],
    EnabledMfas: ['SOFTWARE_TOKEN_MFA'],
    MfaConfiguration: 'ON',
    UserPoolTier: 'LITE',
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', {
    AccessTokenValidity: 15,
    AllowedOAuthFlows: ['code'],
    AllowedOAuthScopes: Match.arrayWith(['openid', 'email']),
    CallbackURLs: [{ Ref: 'OperatorCallbackUrl' }],
    GenerateSecret: false,
    IdTokenValidity: 15,
    LogoutURLs: [{ Ref: 'OperatorLogoutUrl' }],
    ExplicitAuthFlows: ['ALLOW_REFRESH_TOKEN_AUTH'],
    RefreshTokenValidity: 60,
    TokenValidityUnits: Match.objectLike({
      AccessToken: 'minutes',
      IdToken: 'minutes',
      RefreshToken: 'minutes',
    }),
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolResourceServer', {
    Identifier: 'operator',
    Scopes: [{
      ScopeDescription: 'Submit one controlled URL to the HUB_Optimus Operator intake.',
      ScopeName: 'intake',
    }],
  });
  const clients = template.findResources('AWS::Cognito::UserPoolClient');
  const allowedOAuthScopes = Object.values(clients)[0].Properties.AllowedOAuthScopes;
  expect(allowedOAuthScopes).toHaveLength(3);
  expect(JSON.stringify(allowedOAuthScopes)).toContain('/intake');
  expect(JSON.stringify(allowedOAuthScopes)).toContain('OperatorResourceServer');
  template.resourceCountIs('AWS::Cognito::UserPoolDomain', 0);
  template.resourceCountIs('AWS::Scheduler::Schedule', 0);
  template.hasParameter('OperatorCallbackUrl', {
    Default: 'https://huboptimus.dev/operator/',
    AllowedPattern: '^https://huboptimus\\.dev/operator/$',
  });
  template.hasParameter('OperatorLogoutUrl', {
    Default: 'https://huboptimus.dev/operator/',
    AllowedPattern: '^https://huboptimus\\.dev/operator/$',
  });
  template.hasOutput('OperatorJwtIssuer', {});
  template.hasOutput('ServiceState', { Value: 'DISABLED' });
  template.hasOutput('DeploymentPhase', { Value: 'FOUNDATION' });
  template.hasOutput('PublicSignupState', { Value: 'DISABLED' });

  const routes = template.findResources('AWS::ApiGatewayV2::Route');
  expect(Object.values(routes)).toHaveLength(0);
  template.resourceCountIs('AWS::ApiGatewayV2::Stage', 0);
  template.resourceCountIs('AWS::Cognito::UserPoolDomain', 0);
});

test('enables a private smoke test without opening public signup', () => {
  const template = synthTemplate({ deploymentPhase: 'private' });

  template.hasResourceProperties('AWS::Lambda::Function', {
    ReservedConcurrentExecutions: 1,
  });
  template.hasResourceProperties('AWS::Cognito::UserPool', {
    AdminCreateUserConfig: { AllowAdminCreateUserOnly: true },
  });
  template.hasOutput('ServiceState', { Value: 'ENABLED' });
  template.hasOutput('DeploymentPhase', { Value: 'PRIVATE' });
  template.hasOutput('PublicSignupState', { Value: 'DISABLED' });
  template.hasParameter('CanaryStartedAt', { Type: 'String' });
  template.hasParameter('CanaryExpiresAt', { Type: 'String' });
  template.hasParameter('CanaryAllowedSubjectSha256', {
    Type: 'String',
    NoEcho: true,
    AllowedPattern: '^[0-9a-f]{64}$',
  });
  template.hasParameter('CanarySecurityBindingSha256', {
    Type: 'String',
    AllowedPattern: '^[0-9a-f]{64}$',
  });
  template.hasResourceProperties('AWS::Lambda::Function', {
    Environment: {
      Variables: Match.objectLike({
        CANARY_ALLOWED_SUBJECT_SHA256: { Ref: 'CanaryAllowedSubjectSha256' },
        CANARY_STARTED_AT: { Ref: 'CanaryStartedAt' },
        CANARY_EXPIRES_AT: { Ref: 'CanaryExpiresAt' },
        CANARY_SECURITY_BINDING_SHA256: { Ref: 'CanarySecurityBindingSha256' },
      }),
    },
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolDomain', {
    Domain: { Ref: 'OperatorAuthDomainPrefix' },
  });
  template.hasOutput('OperatorHostedUiBaseUrl', {});
  template.hasResourceProperties('AWS::Scheduler::Schedule', {
    FlexibleTimeWindow: { Mode: 'OFF' },
    GroupName: { Ref: Match.stringLikeRegexp('CanaryAutoStopScheduleGroup') },
    ScheduleExpressionTimezone: 'UTC',
    State: 'ENABLED',
    Target: Match.objectLike({
      Arn: 'arn:aws:scheduler:::aws-sdk:lambda:putFunctionConcurrency',
      DeadLetterConfig: {
        Arn: { 'Fn::GetAtt': [Match.stringLikeRegexp('CanaryAutoStopDeadLetterQueue'), 'Arn'] },
      },
      RetryPolicy: {
        MaximumEventAgeInSeconds: 300,
        MaximumRetryAttempts: 3,
      },
    }),
  });
  template.hasResourceProperties('AWS::IAM::Policy', {
    PolicyDocument: {
      Statement: Match.arrayWith([Match.objectLike({
        Action: 'lambda:PutFunctionConcurrency',
        Effect: 'Allow',
      })]),
      Version: '2012-10-17',
    },
  });
  template.hasResourceProperties('AWS::IAM::Policy', {
    PolicyDocument: {
      Statement: Match.arrayWith([Match.objectLike({
        Action: 'sqs:SendMessage',
        Effect: 'Allow',
      })]),
      Version: '2012-10-17',
    },
  });
  template.hasResourceProperties('AWS::SQS::Queue', {
    MessageRetentionPeriod: 345600,
    SqsManagedSseEnabled: true,
  });
  template.resourceCountIs('AWS::CloudWatch::Alarm', 3);
  template.resourceCountIs('AWS::SNS::Topic', 1);
  template.hasResourceProperties('AWS::SNS::Subscription', {
    Endpoint: { Ref: 'CostAlertEmail' },
    Protocol: 'email',
  });
  for (const alarm of Object.values(template.findResources('AWS::CloudWatch::Alarm'))) {
    expect(alarm.Properties.AlarmActions).toHaveLength(1);
  }
  template.hasResourceProperties('AWS::CloudWatch::Alarm', {
    Dimensions: [{ Name: 'ScheduleGroup', Value: 'TestStack-canary' }],
    MetricName: 'TargetErrorCount',
    Namespace: 'AWS/Scheduler',
    Threshold: 1,
    TreatMissingData: 'notBreaching',
  });
  template.hasResourceProperties('AWS::CloudWatch::Alarm', {
    Dimensions: [{ Name: 'ScheduleGroup', Value: 'TestStack-canary' }],
    MetricName: 'InvocationDroppedCount',
    Namespace: 'AWS/Scheduler',
    Threshold: 1,
    TreatMissingData: 'notBreaching',
  });
  const stopRole = Object.values(template.findResources('AWS::IAM::Role'))
    .find((role) => role.Properties.Description?.startsWith('Allows one fixed EventBridge'));
  const stopTrust = JSON.stringify(stopRole?.Properties.AssumeRolePolicyDocument);
  expect(stopTrust).toContain('scheduler.amazonaws.com');
  expect(stopTrust).toContain('904851777129');
  expect(stopTrust).toContain('schedule-group/TestStack-canary');
  expect(stopTrust).not.toContain('schedule/TestStack-canary-auto-stop');
});

test('rejects public signup even when the private service is enabled', () => {
  expect(() => synthTemplate({
    deploymentPhase: 'private',
    publicSignupEnabled: 'true',
  })).toThrow('Public signup is not authorized in this candidate');
});

test('requires an explicit bounded phase and temporary identity decision', () => {
  expect(() => synthTemplate({ deploymentPhase: 'disabled' })).toThrow(
    'deploymentPhase must be exactly foundation, controls, or private.',
  );
  expect(() => synthTemplate({ identityProviderDecision: 'entra' })).toThrow(
    'identityProviderDecision must be exactly cognito-temporary-canary',
  );
});

test('pins the target account and region exactly', () => {
  const app = new cdk.App({ context: BASE_CONTEXT });
  const stack = new HubOptimusOperatorInfraStack(app, 'EnvironmentStack');
  expect(stack.account).toBe(Config.AWS_ACCOUNT_ID);
  expect(stack.region).toBe(Config.DEFAULT_AWS_REGION);

  expect(() => new HubOptimusOperatorInfraStack(new cdk.App({ context: BASE_CONTEXT }), 'WrongAccount', {
    env: { account: '111111111111', region: 'eu-west-1' },
  })).toThrow(`This stack may only target AWS account ${Config.AWS_ACCOUNT_ID}.`);
  expect(() => new HubOptimusOperatorInfraStack(new cdk.App({ context: BASE_CONTEXT }), 'WrongRegion', {
    env: { account: Config.AWS_ACCOUNT_ID, region: 'us-east-1' },
  })).toThrow(`This stack may only target AWS region ${Config.DEFAULT_AWS_REGION}.`);
  expect(() => synthTemplate({ awsRegion: 'us-east-1' })).toThrow(
    `This stack may only target AWS region ${Config.DEFAULT_AWS_REGION}.`,
  );
});

test('applies operational ownership and lifecycle tags', () => {
  const template = synthTemplate();
  const table = Object.values(template.findResources('AWS::DynamoDB::Table'))[0];
  const tags = Object.fromEntries(
    table.Properties.Tags.map(({ Key, Value }: { Key: string; Value: string }) => [Key, Value]),
  );
  expect(tags).toMatchObject({
    HUBOptimusCostUnit: 'ControlledUrlIntake',
    Project: 'HUB_Optimus',
    Workload: 'Operator',
    Environment: 'private-canary',
    Owner: 'Voxterrae',
    ManagedBy: 'CDK',
    CostCenter: 'HUB-OPTIMUS-OPERATOR',
    Repository: 'Voxterrae/HUB_Optimus',
    DataClassification: 'internal-operational',
    Lifecycle: 'ephemeral',
  });
  expect(Object.keys(tags).filter((key) => key.startsWith('costTag-'))).toEqual([]);
  template.hasResourceProperties('AWS::Cognito::UserPool', {
    UserPoolTags: Match.objectLike({ DataClassification: 'restricted' }),
  });
});

test('keeps application and access logs for only seven days', () => {
  const template = synthTemplate();

  template.resourceCountIs('AWS::Logs::LogGroup', 2);
  template.allResourcesProperties('AWS::Logs::LogGroup', {
    RetentionInDays: 7,
  });
});

test('foundation adds only the gross budget and keeps tag-dependent controls absent', () => {
  const template = synthTemplate();

  template.resourceCountIs('AWS::Budgets::Budget', 1);
  template.resourceCountIs('AWS::CE::AnomalyMonitor', 0);
  template.resourceCountIs('AWS::CE::AnomalySubscription', 0);
  template.hasResourceProperties('AWS::Budgets::Budget', {
    Budget: {
      BudgetLimit: { Amount: 25, Unit: 'USD' },
      BudgetType: 'COST',
      CostFilters: Match.absent(),
      CostTypes: Match.objectLike({
        IncludeCredit: false,
        IncludeRefund: false,
      }),
      TimeUnit: 'MONTHLY',
    },
  });
});

test('controls phase adds tagged budget and anomaly detection without a public stage', () => {
  const template = synthTemplate({ deploymentPhase: 'controls' });

  template.resourceCountIs('AWS::Budgets::Budget', 2);
  template.resourceCountIs('AWS::ApiGatewayV2::Stage', 0);
  template.resourceCountIs('AWS::ApiGatewayV2::Route', 0);
  template.hasOutput('DeploymentPhase', { Value: 'CONTROLS' });
  template.hasOutput('ServiceState', { Value: 'DISABLED' });
  template.hasResourceProperties('AWS::Budgets::Budget', {
    Budget: {
      BudgetLimit: { Amount: 10, Unit: 'USD' },
      BudgetType: 'COST',
      CostFilters: {
        TagKeyValue: ['user:HUBOptimusCostUnit$ControlledUrlIntake'],
      },
      CostTypes: {
        IncludeCredit: false,
        IncludeDiscount: true,
        IncludeOtherSubscription: true,
        IncludeRecurring: true,
        IncludeRefund: false,
        IncludeSubscription: true,
        IncludeSupport: true,
        IncludeTax: true,
        IncludeUpfront: true,
        UseAmortized: false,
        UseBlended: false,
      },
      TimeUnit: 'MONTHLY',
    },
  });
  template.hasResourceProperties('AWS::Budgets::Budget', {
    Budget: {
      BudgetLimit: { Amount: 25, Unit: 'USD' },
      BudgetType: 'COST',
      CostFilters: Match.absent(),
      CostTypes: Match.objectLike({
        IncludeCredit: false,
        IncludeRefund: false,
      }),
      TimeUnit: 'MONTHLY',
    },
  });
  template.hasResourceProperties('AWS::CE::AnomalyMonitor', {
    MonitorName: 'TestStack-url-ingestion',
    MonitorType: 'CUSTOM',
    MonitorSpecification: Match.stringLikeRegexp('HUBOptimusCostUnit'),
  });
});

test('protects the deployment-time cost recipient and wires controls-phase alerts', () => {
  const template = synthTemplate({ deploymentPhase: 'controls' });

  template.hasParameter('CostAlertEmail', {
    Type: 'String',
    NoEcho: true,
    AllowedPattern: '^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$',
  });
  template.hasResourceProperties('AWS::CE::AnomalySubscription', {
    Frequency: 'DAILY',
    Subscribers: [{ Address: { Ref: 'CostAlertEmail' }, Type: 'EMAIL' }],
  });
  template.hasResourceProperties('AWS::Budgets::Budget', {
    NotificationsWithSubscribers: Match.arrayWith([
      Match.objectLike({
        Notification: Match.objectLike({ Threshold: 80 }),
        Subscribers: [{ Address: { Ref: 'CostAlertEmail' }, SubscriptionType: 'EMAIL' }],
      }),
    ]),
  });
  const budgets = template.findResources('AWS::Budgets::Budget');
  expect(Object.values(budgets)).toHaveLength(2);
  for (const budgetResource of Object.values(budgets)) {
    const budget = budgetResource.Properties;
    expect(budget.NotificationsWithSubscribers).toHaveLength(4);
    expect(budget.NotificationsWithSubscribers.map(
      (entry: { Notification: { NotificationType: string; Threshold: number } }) => [
        entry.Notification.NotificationType,
        entry.Notification.Threshold,
      ],
    )).toEqual([
      ['ACTUAL', 50],
      ['ACTUAL', 80],
      ['ACTUAL', 100],
      ['FORECASTED', 100],
    ]);
  }
});
