import * as path from 'node:path';
import { existsSync } from 'node:fs';
import {
  Duration,
  RemovalPolicy,
  Stack,
  Tags,
  CfnOutput,
  CfnParameter,
} from 'aws-cdk-lib';
import { AccessLogFormat } from 'aws-cdk-lib/aws-apigateway';
import type { StackProps } from 'aws-cdk-lib';
import * as budgets from 'aws-cdk-lib/aws-budgets';
import * as ce from 'aws-cdk-lib/aws-ce';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import {
  CorsHttpMethod,
  HttpApi,
  HttpMethod,
  HttpStage,
  LogGroupLogDestination,
} from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpJwtAuthorizer } from 'aws-cdk-lib/aws-apigatewayv2-authorizers';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { Construct } from 'constructs';
import { Config, resolveAwsRegion } from './config';

function readBooleanContext(scope: Construct, name: string): boolean {
  const value = scope.node.tryGetContext(name) as unknown;
  if (value === undefined || value === false || value === 'false') {
    return false;
  }
  if (value === true || value === 'true') {
    return true;
  }
  throw new Error(`${name} must be the boolean true or false.`);
}

export class HubOptimusOperatorInfraStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    const account = props?.env?.account ?? Config.AWS_ACCOUNT_ID;
    if (account !== Config.AWS_ACCOUNT_ID) {
      throw new Error(`This stack may only target AWS account ${Config.AWS_ACCOUNT_ID}.`);
    }
    const region = resolveAwsRegion(props?.env?.region ?? scope.node.tryGetContext('awsRegion'));
    super(scope, id, {
      ...props,
      env: { account: Config.AWS_ACCOUNT_ID, region },
    });

    Tags.of(this).add(Config.COST_TAG_KEY, Config.COST_TAG_VALUE);
    Tags.of(this).add('managedBy', Config.MANAGED_BY);
    Tags.of(this).add('backup-required', Config.BACKUP_REQUIRED);

    const gitCommit = this.node.tryGetContext('gitCommit') as string | undefined;
    const repoName = this.node.tryGetContext('repoName') as string | undefined;
    const branch = this.node.tryGetContext('branchName') as string | undefined;
    const environmentName = (this.node.tryGetContext('environmentName') as string | undefined) ?? 'candidate';
    const serviceEnabled = readBooleanContext(this, 'serviceEnabled');
    const publicSignupEnabled = readBooleanContext(this, 'publicSignupEnabled');
    if (publicSignupEnabled) {
      throw new Error(
        'Public signup is not authorized in this candidate; use one administrator-created smoke user.',
      );
    }
    Tags.of(this).add('Project', 'HUB_Optimus');
    Tags.of(this).add('Workload', 'Operator');
    Tags.of(this).add('Environment', environmentName);
    Tags.of(this).add('Owner', 'Voxterrae');
    Tags.of(this).add('ManagedBy', 'CDK');
    Tags.of(this).add('CostCenter', 'HUB-OPTIMUS-OPERATOR');
    Tags.of(this).add('Repository', 'Voxterrae/HUB_Optimus');
    Tags.of(this).add('DataClassification', 'public');
    Tags.of(this).add('Lifecycle', 'ephemeral');
    const deployInfo = gitCommit && repoName && branch
      ? `${repoName} (${branch}) @ ${gitCommit.substring(0, 7)}`
      : 'Manually deployed';

    const costAlertEmail = new CfnParameter(this, 'CostAlertEmail', {
      type: 'String',
      allowedPattern: '^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$',
      constraintDescription: 'Provide a valid email address for mandatory pilot cost alerts.',
      description: 'Mandatory recipient for the $10 workload, $25 gross account, and anomaly alerts.',
    });
    const operatorCallbackUrl = new CfnParameter(this, 'OperatorCallbackUrl', {
      type: 'String',
      default: 'https://huboptimus.dev/operator/',
      allowedPattern: '^https://huboptimus\\.dev/operator/$',
      constraintDescription: 'Callback must be exactly https://huboptimus.dev/operator/.',
      description: 'Hosted UI OAuth callback for the Operator PKCE client.',
    });
    const operatorLogoutUrl = new CfnParameter(this, 'OperatorLogoutUrl', {
      type: 'String',
      default: 'https://huboptimus.dev/operator/',
      allowedPattern: '^https://huboptimus\\.dev/operator/$',
      constraintDescription: 'Logout URL must be exactly https://huboptimus.dev/operator/.',
      description: 'Hosted UI logout destination for the Operator client.',
    });
    const operatorAuthDomainPrefix = new CfnParameter(this, 'OperatorAuthDomainPrefix', {
      type: 'String',
      allowedPattern: '^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$',
      constraintDescription: 'Use a unique 1-63 character lowercase Cognito domain prefix.',
      description: 'Mandatory globally unique Cognito Hosted UI domain prefix.',
    });

    const quotaTable = new dynamodb.Table(this, 'SubjectQuotaTable', {
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      partitionKey: {
        name: 'subjectDay',
        type: dynamodb.AttributeType.STRING,
      },
      removalPolicy: RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'expiresAt',
    });

    const functionLogs = new logs.LogGroup(this, 'UrlIntakeFunctionLogs', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });
    const accessLogs = new logs.LogGroup(this, 'UrlIntakeAccessLogs', {
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: RemovalPolicy.DESTROY,
    });
    const intakeRole = new iam.Role(this, 'UrlIntakeExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Least-privilege role for authenticated controlled URL intake.',
    });
    intakeRole.addToPolicy(new iam.PolicyStatement({
      actions: ['logs:CreateLogStream', 'logs:PutLogEvents'],
      resources: [`${functionLogs.logGroupArn}:*`],
    }));
    intakeRole.addToPolicy(new iam.PolicyStatement({
      actions: ['dynamodb:UpdateItem'],
      resources: [quotaTable.tableArn],
    }));

    const handlerAsset = path.join(__dirname, '../lambda/url-ingest-handler.js');
    if (!existsSync(handlerAsset)) {
      throw new Error('Compiled Lambda handler is missing; run npm run build before synth or deploy.');
    }
    const intakeFunction = new lambda.Function(this, 'UrlIntakeFunction', {
      code: lambda.Code.fromAsset(path.dirname(handlerAsset), {
        exclude: ['*.d.ts', '*.ts'],
      }),
      handler: 'url-ingest-handler.handler',
      runtime: lambda.Runtime.NODEJS_22_X,
      role: intakeRole,
      architecture: lambda.Architecture.ARM_64,
      memorySize: 128,
      timeout: Duration.seconds(10),
      reservedConcurrentExecutions: serviceEnabled ? 1 : 0,
      logGroup: functionLogs,
      loggingFormat: lambda.LoggingFormat.JSON,
      applicationLogLevelV2: lambda.ApplicationLogLevel.INFO,
      systemLogLevelV2: lambda.SystemLogLevel.WARN,
      environment: {
        FETCH_TIMEOUT_MS: '8000',
        MAX_CONTENT_BYTES: '1000000',
        MAX_EXTRACTED_TEXT_CHARS: '24000',
        MAX_REDIRECTS: '3',
        MAX_REQUEST_BYTES: '4096',
        PER_SUBJECT_REQUESTS_PER_DAY: '3',
        QUOTA_TABLE_NAME: quotaTable.tableName,
      },
    });

    const userPool = new cognito.UserPool(this, 'OperatorUserPool', {
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      autoVerify: { email: true },
      featurePlan: cognito.FeaturePlan.LITE,
      removalPolicy: RemovalPolicy.RETAIN,
      selfSignUpEnabled: false,
      signInAliases: { email: true },
      mfa: cognito.Mfa.REQUIRED,
      mfaSecondFactor: {
        otp: true,
        sms: false,
      },
      standardAttributes: {
        email: { mutable: true, required: true },
      },
      passwordPolicy: {
        minLength: 14,
        requireDigits: true,
        requireLowercase: true,
        requireSymbols: true,
        requireUppercase: true,
        tempPasswordValidity: Duration.days(1),
      },
    });
    const userPoolDomain = userPool.addDomain('OperatorHostedUiDomain', {
      cognitoDomain: {
        domainPrefix: operatorAuthDomainPrefix.valueAsString,
      },
    });
    const intakeScope = new cognito.ResourceServerScope({
      scopeName: 'intake',
      scopeDescription: 'Submit one controlled URL to the HUB_Optimus Operator intake.',
    });
    const operatorResourceServer = userPool.addResourceServer('OperatorResourceServer', {
      identifier: 'operator',
      scopes: [intakeScope],
    });
    const userPoolClient = userPool.addClient('OperatorWebClient', {
      accessTokenValidity: Duration.minutes(15),
      // The public browser client authenticates only through Hosted UI OAuth
      // authorization-code + PKCE. Keep direct Cognito password/SRP/custom
      // API authentication disabled; CDK retains refresh-token auth only.
      authFlows: {
        adminUserPassword: false,
        custom: false,
        userPassword: false,
        userSrp: false,
      },
      enableTokenRevocation: true,
      generateSecret: false,
      idTokenValidity: Duration.minutes(15),
      oAuth: {
        callbackUrls: [operatorCallbackUrl.valueAsString],
        flows: {
          authorizationCodeGrant: true,
          implicitCodeGrant: false,
        },
        logoutUrls: [operatorLogoutUrl.valueAsString],
        scopes: [
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.resourceServer(operatorResourceServer, intakeScope),
        ],
      },
      preventUserExistenceErrors: true,
      refreshTokenValidity: Duration.hours(1),
    });
    intakeFunction.addEnvironment('EXPECTED_CLIENT_ID', userPoolClient.userPoolClientId);
    intakeFunction.addEnvironment('REQUIRED_SCOPE', Config.REQUIRED_SCOPE);
    const authorizer = new HttpJwtAuthorizer(
      'OperatorCognitoJwt',
      userPool.userPoolProviderUrl,
      { jwtAudience: [userPoolClient.userPoolClientId] },
    );

    const api = new HttpApi(this, 'OperatorHttpApi', {
      apiName: `${this.stackName}-operator`,
      createDefaultStage: false,
      corsPreflight: {
        allowCredentials: false,
        allowHeaders: ['authorization', 'content-type'],
        allowMethods: [CorsHttpMethod.POST],
        allowOrigins: ['https://huboptimus.dev'],
        maxAge: Duration.minutes(10),
      },
    });
    api.addRoutes({
      path: '/intake/url',
      methods: [HttpMethod.POST],
      authorizer,
      authorizationScopes: [Config.REQUIRED_SCOPE],
      integration: new HttpLambdaIntegration('UrlIntakeIntegration', intakeFunction),
    });

    const stage = new HttpStage(this, 'DefaultStage', {
      httpApi: api,
      stageName: '$default',
      autoDeploy: true,
      throttle: {
        // One browser action is an automatic CORS preflight followed by POST.
        // Keep the sustained rate low while allowing that pair to complete.
        burstLimit: 2,
        rateLimit: 0.2,
      },
      accessLogSettings: {
        destination: new LogGroupLogDestination(accessLogs),
        format: AccessLogFormat.custom(JSON.stringify({
          requestId: '$context.requestId',
          routeKey: '$context.routeKey',
          status: '$context.status',
          responseLength: '$context.responseLength',
          integrationLatency: '$context.integrationLatency',
        })),
      },
    });

    const notifications = [50, 80, 100].map((threshold) => ({
      notification: {
        comparisonOperator: 'GREATER_THAN',
        notificationType: 'ACTUAL',
        threshold,
        thresholdType: 'PERCENTAGE',
      },
      subscribers: [{
        address: costAlertEmail.valueAsString,
        subscriptionType: 'EMAIL',
      }],
    }));
    notifications.push({
      notification: {
        comparisonOperator: 'GREATER_THAN',
        notificationType: 'FORECASTED',
        threshold: 100,
        thresholdType: 'PERCENTAGE',
      },
      subscribers: [{
        address: costAlertEmail.valueAsString,
        subscriptionType: 'EMAIL',
      }],
    });
    const grossCostTypes = {
      includeCredit: false,
      includeDiscount: true,
      includeOtherSubscription: true,
      includeRecurring: true,
      includeRefund: false,
      includeSubscription: true,
      includeSupport: true,
      includeTax: true,
      includeUpfront: true,
      useAmortized: false,
      useBlended: false,
    };
    new budgets.CfnBudget(this, 'MonthlyCostBudget', {
      budget: {
        budgetLimit: { amount: 10, unit: 'USD' },
        budgetName: `${this.stackName}-url-ingestion-monthly`,
        budgetType: 'COST',
        costFilters: {
          TagKeyValue: [`user:${Config.COST_TAG_KEY}$${Config.COST_TAG_VALUE}`],
        },
        costTypes: grossCostTypes,
        timeUnit: 'MONTHLY',
      },
      notificationsWithSubscribers: notifications,
    });
    new budgets.CfnBudget(this, 'GrossAccountMonthlyBudget', {
      budget: {
        budgetLimit: { amount: 25, unit: 'USD' },
        budgetName: `${this.stackName}-gross-account-monthly`,
        budgetType: 'COST',
        costTypes: grossCostTypes,
        timeUnit: 'MONTHLY',
      },
      notificationsWithSubscribers: notifications,
    });

    const anomalyMonitor = new ce.CfnAnomalyMonitor(this, 'UrlIngestionCostAnomalyMonitor', {
      monitorName: `${this.stackName}-url-ingestion`,
      monitorType: 'CUSTOM',
      monitorSpecification: JSON.stringify({
        Tags: {
          Key: Config.COST_TAG_KEY,
          MatchOptions: ['EQUALS'],
          Values: [Config.COST_TAG_VALUE],
        },
      }),
    });
    new ce.CfnAnomalySubscription(this, 'UrlIngestionCostAnomalySubscription', {
      frequency: 'DAILY',
      monitorArnList: [anomalyMonitor.attrMonitorArn],
      subscribers: [{
        address: costAlertEmail.valueAsString,
        type: 'EMAIL',
      }],
      subscriptionName: `${this.stackName}-url-ingestion`,
      thresholdExpression: JSON.stringify({
        Dimensions: {
          Key: 'ANOMALY_TOTAL_IMPACT_ABSOLUTE',
          MatchOptions: ['GREATER_THAN_OR_EQUAL'],
          Values: ['2'],
        },
      }),
    });

    new CfnOutput(this, 'DeploymentInfo', {
      value: deployInfo,
      description: 'Source of this deployment (repo, branch, commit) or manual deploy marker',
    });
    new CfnOutput(this, 'ApiInvokeUrl', {
      value: stage.url,
      description: 'Raw authenticated HTTP API URL; no api.huboptimus.dev DNS mapping is created.',
    });
    new CfnOutput(this, 'OperatorUserPoolId', {
      value: userPool.userPoolId,
    });
    new CfnOutput(this, 'OperatorWebClientId', {
      value: userPoolClient.userPoolClientId,
    });
    new CfnOutput(this, 'OperatorJwtIssuer', {
      value: userPool.userPoolProviderUrl,
    });
    new CfnOutput(this, 'OperatorHostedUiBaseUrl', {
      value: userPoolDomain.baseUrl(),
      description: 'Use OAuth authorization-code flow with S256 PKCE; implicit flow is disabled.',
    });
    new CfnOutput(this, 'OperatorCallbackUrlOutput', {
      value: operatorCallbackUrl.valueAsString,
    });
    new CfnOutput(this, 'OperatorLogoutUrlOutput', {
      value: operatorLogoutUrl.valueAsString,
    });
    new CfnOutput(this, 'ServiceState', {
      value: serviceEnabled ? 'ENABLED' : 'DISABLED',
      description: 'Fail-closed unless CDK context serviceEnabled=true is supplied explicitly.',
    });
    new CfnOutput(this, 'PublicSignupState', {
      value: 'DISABLED',
      description: 'Public signup is not authorized by this private-smoke candidate.',
    });
  }
}
