import * as cdk from 'aws-cdk-lib/core';
import { Match, Template } from 'aws-cdk-lib/assertions';
import { HubOptimusOperatorInfraStack } from '../lib/hub-optimus-operator-infra-stack';

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
    AuthorizationType: 'JWT',
    RouteKey: 'POST /intake/url',
  });
  template.hasResourceProperties('AWS::ApiGatewayV2::Stage', {
    AutoDeploy: true,
    DefaultRouteSettings: {
      ThrottlingBurstLimit: 2,
      ThrottlingRateLimit: 0.5,
    },
    StageName: '$default',
    AccessLogSettings: Match.objectLike({
      Format: Match.stringLikeRegexp('requestId'),
    }),
  });
});

test('defaults fail-closed while retaining short-lived Cognito JWT and PKCE-compatible Hosted UI', () => {
  const template = synthTemplate();

  template.hasResourceProperties('AWS::Cognito::UserPool', {
    AdminCreateUserConfig: { AllowAdminCreateUserOnly: true },
    AutoVerifiedAttributes: ['email'],
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', {
    AccessTokenValidity: 15,
    AllowedOAuthFlows: ['code'],
    AllowedOAuthScopes: ['openid', 'email'],
    CallbackURLs: [{ Ref: 'OperatorCallbackUrl' }],
    GenerateSecret: false,
    IdTokenValidity: 15,
    LogoutURLs: [{ Ref: 'OperatorLogoutUrl' }],
    TokenValidityUnits: Match.objectLike({
      AccessToken: 'minutes',
      IdToken: 'minutes',
    }),
  });
  template.hasResourceProperties('AWS::ApiGatewayV2::Authorizer', {
    AuthorizerType: 'JWT',
    IdentitySource: ['$request.header.Authorization'],
  });
  template.hasResourceProperties('AWS::Cognito::UserPoolDomain', {
    Domain: { Ref: 'OperatorAuthDomainPrefix' },
  });
  template.hasParameter('OperatorAuthDomainPrefix', {
    Type: 'String',
  });
  template.hasOutput('OperatorJwtIssuer', {});
  template.hasOutput('OperatorHostedUiBaseUrl', {});
  template.hasOutput('PublicPilotState', { Value: 'DISABLED' });

  const routes = template.findResources('AWS::ApiGatewayV2::Route');
  expect(Object.values(routes)).toHaveLength(1);
  expect(Object.values(routes)[0].Properties.AuthorizationType).toBe('JWT');
});

test('enables one Lambda concurrency and public signup only with explicit context', () => {
  const template = synthTemplate({ publicPilotEnabled: 'true' });

  template.hasResourceProperties('AWS::Lambda::Function', {
    ReservedConcurrentExecutions: 1,
  });
  template.hasResourceProperties('AWS::Cognito::UserPool', {
    AdminCreateUserConfig: { AllowAdminCreateUserOnly: false },
  });
  template.hasOutput('PublicPilotState', { Value: 'ENABLED' });
});

test('applies operational ownership and lifecycle tags', () => {
  const template = synthTemplate();
  const table = Object.values(template.findResources('AWS::DynamoDB::Table'))[0];
  const tags = Object.fromEntries(
    table.Properties.Tags.map(({ Key, Value }: { Key: string; Value: string }) => [Key, Value]),
  );
  expect(tags).toMatchObject({
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
});

test('keeps application and access logs for only seven days', () => {
  const template = synthTemplate();

  template.resourceCountIs('AWS::Logs::LogGroup', 2);
  template.allResourcesProperties('AWS::Logs::LogGroup', {
    RetentionInDays: 7,
  });
});

test('adds a tagged monthly budget and a cost anomaly monitor', () => {
  const template = synthTemplate();

  template.hasResourceProperties('AWS::Budgets::Budget', {
    Budget: {
      BudgetLimit: { Amount: 10, Unit: 'USD' },
      BudgetType: 'COST',
      CostFilters: {
        TagKeyValue: ['user:costTag-project$HUB_Optimus'],
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
  template.hasResourceProperties('AWS::CE::AnomalyMonitor', {
    MonitorName: 'TestStack-url-ingestion',
    MonitorType: 'CUSTOM',
    MonitorSpecification: Match.stringLikeRegexp('costTag-project'),
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
  const budget = Object.values(budgets)[0].Properties;
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
});
