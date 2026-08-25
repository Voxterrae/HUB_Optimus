import * as cdk from 'aws-cdk-lib/core';
import { Match, Template } from 'aws-cdk-lib/assertions';
import { HubOptimusOperatorInfraStack } from '../lib/hub-optimus-operator-infra-stack';
import { Config } from '../lib/config';
import { OPERATOR_INTAKE_SCOPE } from '../frontend/pkce-client';

function synthTemplate(context: Record<string, string> = {}): Template {
  const app = new cdk.App({ context });
  const stack = new HubOptimusOperatorInfraStack(app, 'TestStack');
  return Template.fromStack(stack);
}

test('records a manual deployment when no Git context is provided', () => {
  const template = synthTemplate();

  template.hasOutput('DeploymentInfo', {
    Description: 'Source of this deployment (repo, branch, commit) or manual deploy marker',
    Value: 'Manually deployed',
  });
});

test('creates a tightly bounded, VPC-free URL ingestion Lambda', () => {
  const template = synthTemplate();

  template.hasResourceProperties('AWS::Lambda::Function', {
    Architectures: ['arm64'],
    MemorySize: 128,
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
        PER_SUBJECT_REQUESTS_PER_DAY: '3',
        EXPECTED_CLIENT_ID: Match.anyValue(),
        REQUIRED_SCOPE: 'operator/intake',
      }),
    },
    VpcConfig: Match.absent(),
  });

  template.hasResourceProperties('AWS::DynamoDB::Table', {
    BillingMode: 'PAY_PER_REQUEST',
    KeySchema: [{ AttributeName: 'subjectDay', KeyType: 'HASH' }],
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

test('exposes only authenticated POST /intake/url with exact-origin CORS and stage throttling', () => {
  const template = synthTemplate();

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

test('defaults service and public signup fail-closed with a scoped access-token client', () => {
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
  template.hasResourceProperties('AWS::ApiGatewayV2::Authorizer', {
    AuthorizerType: 'JWT',
    IdentitySource: ['$request.header.Authorization'],
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolDomain', {
    Domain: { Ref: 'OperatorAuthDomainPrefix' },
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
  template.hasParameter('OperatorAuthDomainPrefix', {
    Type: 'String',
  });
  template.hasParameter('OperatorCallbackUrl', {
    Default: 'https://huboptimus.dev/operator/',
    AllowedPattern: '^https://huboptimus\\.dev/operator/$',
  });
  template.hasParameter('OperatorLogoutUrl', {
    Default: 'https://huboptimus.dev/operator/',
    AllowedPattern: '^https://huboptimus\\.dev/operator/$',
  });
  template.hasOutput('OperatorJwtIssuer', {});
  template.hasOutput('OperatorHostedUiBaseUrl', {});
  template.hasOutput('ServiceState', { Value: 'DISABLED' });
  template.hasOutput('PublicSignupState', { Value: 'DISABLED' });

  const routes = template.findResources('AWS::ApiGatewayV2::Route');
  expect(Object.values(routes)).toHaveLength(1);
  expect(Object.values(routes)[0].Properties.AuthorizationType).toBe('JWT');
});

test('enables a private smoke test without opening public signup', () => {
  const template = synthTemplate({ serviceEnabled: 'true' });

  template.hasResourceProperties('AWS::Lambda::Function', {
    ReservedConcurrentExecutions: 1,
  });
  template.hasResourceProperties('AWS::Cognito::UserPool', {
    AdminCreateUserConfig: { AllowAdminCreateUserOnly: true },
  });
  template.hasOutput('ServiceState', { Value: 'ENABLED' });
  template.hasOutput('PublicSignupState', { Value: 'DISABLED' });
});

test('rejects public signup even when the private service is enabled', () => {
  expect(() => synthTemplate({
    serviceEnabled: 'true',
    publicSignupEnabled: 'true',
  })).toThrow('Public signup is not authorized in this candidate');
});

test('pins the target account and region exactly', () => {
  const app = new cdk.App();
  const stack = new HubOptimusOperatorInfraStack(app, 'EnvironmentStack');
  expect(stack.account).toBe(Config.AWS_ACCOUNT_ID);
  expect(stack.region).toBe(Config.DEFAULT_AWS_REGION);

  expect(() => new HubOptimusOperatorInfraStack(new cdk.App(), 'WrongAccount', {
    env: { account: '111111111111', region: 'eu-west-1' },
  })).toThrow(`This stack may only target AWS account ${Config.AWS_ACCOUNT_ID}.`);
  expect(() => new HubOptimusOperatorInfraStack(new cdk.App(), 'WrongRegion', {
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
    Environment: 'candidate',
    Owner: 'Voxterrae',
    ManagedBy: 'CDK',
    CostCenter: 'HUB-OPTIMUS-OPERATOR',
    Repository: 'Voxterrae/HUB_Optimus',
    DataClassification: 'public',
    Lifecycle: 'ephemeral',
  });
  expect(Object.keys(tags).filter((key) => key.startsWith('costTag-'))).toEqual([]);
});

test('keeps application and access logs for only seven days', () => {
  const template = synthTemplate();

  template.resourceCountIs('AWS::Logs::LogGroup', 2);
  template.allResourcesProperties('AWS::Logs::LogGroup', {
    RetentionInDays: 7,
  });
});

test('adds tagged workload and gross account budgets plus a cost anomaly monitor', () => {
  const template = synthTemplate();

  template.resourceCountIs('AWS::Budgets::Budget', 2);
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

test('requires a deployment-time cost recipient and always wires budget and anomaly alerts', () => {
  const template = synthTemplate();

  template.hasParameter('CostAlertEmail', {
    Type: 'String',
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
