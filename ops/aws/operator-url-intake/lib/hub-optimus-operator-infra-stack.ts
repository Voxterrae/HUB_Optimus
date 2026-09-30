import * as path from 'node:path';
import { existsSync } from 'node:fs';
import {
  Duration,
  ArnFormat,
  Fn,
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
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatchActions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as sqs from 'aws-cdk-lib/aws-sqs';
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

export type DeploymentPhase = 'foundation' | 'controls' | 'private';

function readDeploymentPhase(scope: Construct): DeploymentPhase {
  const value = scope.node.tryGetContext('deploymentPhase') as unknown;
  if (value === 'foundation' || value === 'controls' || value === 'private') {
    return value;
  }
  throw new Error(
    'deploymentPhase must be exactly foundation, controls, or private.',
  );
}

function readRequiredProvenance(scope: Construct): {
  gitCommit: string;
  repoName: string;
  branch: string;
  environmentName: string;
} {
  const gitCommit = scope.node.tryGetContext('gitCommit') as unknown;
  const repoName = scope.node.tryGetContext('repoName') as unknown;
  const branch = scope.node.tryGetContext('branchName') as unknown;
  const environmentName = scope.node.tryGetContext('environmentName') as unknown;

  if (typeof gitCommit !== 'string' || !/^[0-9a-f]{40}$/.test(gitCommit)) {
    throw new Error('gitCommit must be one exact 40-character lowercase commit SHA.');
  }
  if (repoName !== 'Voxterrae/HUB_Optimus') {
    throw new Error('repoName must be exactly Voxterrae/HUB_Optimus.');
  }
  if (branch !== 'main') {
    throw new Error('branchName must be exactly main.');
  }
  if (environmentName !== 'private-canary') {
    throw new Error('environmentName must be exactly private-canary.');
  }

  return { gitCommit, repoName, branch, environmentName };
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

    const { gitCommit, repoName, branch, environmentName } = readRequiredProvenance(this);
    const deploymentPhase = readDeploymentPhase(this);
    const privateActive = deploymentPhase === 'private';
    const costControlsEnabled = deploymentPhase !== 'foundation';
    const publicSignupEnabled = readBooleanContext(this, 'publicSignupEnabled');
    if (publicSignupEnabled) {
      throw new Error(
        'Public signup is not authorized in this candidate; use one administrator-created smoke user.',
      );
    }
    if (this.node.tryGetContext('identityProviderDecision') !== 'cognito-temporary-canary') {
      throw new Error(
        'identityProviderDecision must be exactly cognito-temporary-canary for this bounded pilot.',
      );
    }
    Tags.of(this).add('Project', 'HUB_Optimus');
    Tags.of(this).add('Workload', 'Operator');
    Tags.of(this).add('Environment', environmentName);
    Tags.of(this).add('Owner', 'Voxterrae');
    Tags.of(this).add('ManagedBy', 'CDK');
    Tags.of(this).add('CostCenter', 'HUB-OPTIMUS-OPERATOR');
    Tags.of(this).add('Repository', 'Voxterrae/HUB_Optimus');
    Tags.of(this).add('DataClassification', 'internal');
    Tags.of(this).add('Lifecycle', 'ephemeral');
    const deployInfo = `${repoName} (${branch}) @ ${gitCommit}`;

    const costAlertEmail = new CfnParameter(this, 'CostAlertEmail', {
      type: 'String',
      noEcho: true,
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
    const operatorAuthDomainPrefix = costControlsEnabled
      ? new CfnParameter(this, 'OperatorAuthDomainPrefix', {
        type: 'String',
        allowedPattern: '^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$',
        constraintDescription: 'Use a unique 1-63 character lowercase Cognito domain prefix.',
        description: 'Mandatory globally unique Cognito Hosted UI domain prefix.',
      })
      : undefined;
    const canaryWindow = privateActive
      ? {
        allowedSubjectHash: new CfnParameter(this, 'CanaryAllowedSubjectSha256', {
          type: 'String',
          noEcho: true,
          allowedPattern: '^[0-9a-f]{64}$',
          constraintDescription: 'Use the lowercase SHA-256 of the one invited Cognito subject.',
          description: 'Pseudonymous allowlist hash for the sole private-canary user.',
        }),
        startedAt: new CfnParameter(this, 'CanaryStartedAt', {
          type: 'String',
          allowedPattern: '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$',
          constraintDescription: 'Use one UTC timestamp such as 2026-08-26T12:00:00Z.',
          description: 'UTC start of the private canary window.',
        }),
        expiresAt: new CfnParameter(this, 'CanaryExpiresAt', {
          type: 'String',
          allowedPattern: '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$',
          constraintDescription: 'Use one UTC timestamp such as 2026-08-26T14:00:00Z.',
          description: 'UTC expiry of the private canary; the handler enforces a two-hour maximum.',
        }),
        securityBinding: new CfnParameter(this, 'CanarySecurityBindingSha256', {
          type: 'String',
          allowedPattern: '^[0-9a-f]{64}$',
          constraintDescription: 'Use the reviewed subject/window binding SHA-256.',
          description: 'Non-secret fail-closed binding for the private subject hash and UTC window.',
        }),
      }
      : undefined;

    const operationalAlertsTopic = costControlsEnabled
      ? new sns.Topic(this, 'OperatorOperationalAlertsTopic', {
        displayName: 'HUB Optimus Operator private canary alerts',
      })
      : undefined;
    operationalAlertsTopic?.addSubscription(
      new subscriptions.EmailSubscription(costAlertEmail.valueAsString),
    );

    const quotaTable = new dynamodb.Table(this, 'CanaryQuotaTable', {
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      partitionKey: {
        name: 'canaryWindow',
        type: dynamodb.AttributeType.STRING,
      },
      removalPolicy: RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'expiresAt',
    });
    Tags.of(quotaTable).add('DataClassification', 'internal-operational', { priority: 200 });

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

    const handlerAsset = path.join(__dirname, '../lambda/url-ingest-handler.bundle.js');
    if (!existsSync(handlerAsset)) {
      throw new Error('Reviewed Lambda bundle is missing; run npm run build:lambda.');
    }
    const intakeFunction = new lambda.Function(this, 'UrlIntakeFunction', {
      code: lambda.Code.fromAsset(path.dirname(handlerAsset), {
        // TypeScript compilation emits an unbundled sibling JavaScript file.
        // Ship only the reviewed self-contained bundle used by the handler.
        exclude: [
          'url-ingest-handler.d.ts',
          'url-ingest-handler.js',
          'url-ingest-handler.ts',
        ],
      }),
      handler: 'url-ingest-handler.bundle.handler',
      runtime: lambda.Runtime.NODEJS_22_X,
      role: intakeRole,
      functionName: 'hub-optimus-operator-url-intake',
      architecture: lambda.Architecture.ARM_64,
      memorySize: 128,
      timeout: Duration.seconds(10),
      reservedConcurrentExecutions: privateActive ? 1 : 0,
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
        CANARY_REQUESTS_TOTAL: '3',
        QUOTA_TABLE_NAME: quotaTable.tableName,
      },
    });
    if (canaryWindow) {
      intakeFunction.addEnvironment(
        'CANARY_ALLOWED_SUBJECT_SHA256',
        canaryWindow.allowedSubjectHash.valueAsString,
      );
      intakeFunction.addEnvironment('CANARY_STARTED_AT', canaryWindow.startedAt.valueAsString);
      intakeFunction.addEnvironment('CANARY_EXPIRES_AT', canaryWindow.expiresAt.valueAsString);
      intakeFunction.addEnvironment(
        'CANARY_SECURITY_BINDING_SHA256',
        canaryWindow.securityBinding.valueAsString,
      );

      const stopScheduleName = `${this.stackName}-canary-auto-stop`;
      const stopScheduleGroupName = `${this.stackName}-canary`;
      const stopScheduleGroup = new scheduler.CfnScheduleGroup(
        this,
        'CanaryAutoStopScheduleGroup',
        { name: stopScheduleGroupName },
      );
      const stopScheduleGroupArn = this.formatArn({
        arnFormat: ArnFormat.SLASH_RESOURCE_NAME,
        resource: 'schedule-group',
        resourceName: stopScheduleGroupName,
        service: 'scheduler',
      });
      const stopDeadLetterQueue = new sqs.Queue(this, 'CanaryAutoStopDeadLetterQueue', {
        encryption: sqs.QueueEncryption.SQS_MANAGED,
        removalPolicy: RemovalPolicy.DESTROY,
        retentionPeriod: Duration.days(4),
      });
      Tags.of(stopDeadLetterQueue).add('DataClassification', 'internal-operational', {
        priority: 200,
      });
      const stopRole = new iam.Role(this, 'CanaryAutoStopRole', {
        assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com', {
          conditions: {
            ArnEquals: { 'aws:SourceArn': stopScheduleGroupArn },
            StringEquals: { 'aws:SourceAccount': Config.AWS_ACCOUNT_ID },
          },
        }),
        description: 'Allows one fixed EventBridge Scheduler job to stop canary Lambda concurrency.',
      });
      stopRole.addToPolicy(new iam.PolicyStatement({
        actions: ['lambda:PutFunctionConcurrency'],
        resources: [intakeFunction.functionArn],
      }));
      stopRole.addToPolicy(new iam.PolicyStatement({
        actions: ['sqs:SendMessage'],
        resources: [stopDeadLetterQueue.queueArn],
      }));
      new scheduler.CfnSchedule(this, 'CanaryAutoStopSchedule', {
        flexibleTimeWindow: { mode: 'OFF' },
        groupName: stopScheduleGroup.ref,
        name: stopScheduleName,
        scheduleExpression: Fn.join('', [
          'at(',
          Fn.select(0, Fn.split('Z', canaryWindow.expiresAt.valueAsString)),
          ')',
        ]),
        scheduleExpressionTimezone: 'UTC',
        state: 'ENABLED',
        target: {
          arn: 'arn:aws:scheduler:::aws-sdk:lambda:putFunctionConcurrency',
          deadLetterConfig: { arn: stopDeadLetterQueue.queueArn },
          input: Stack.of(this).toJsonString({
            FunctionName: intakeFunction.functionName,
            ReservedConcurrentExecutions: 0,
          }),
          retryPolicy: {
            maximumEventAgeInSeconds: 300,
            maximumRetryAttempts: 3,
          },
          roleArn: stopRole.roleArn,
        },
      });

      const schedulerMetric = (metricName: string): cloudwatch.Metric => new cloudwatch.Metric({
        dimensionsMap: { ScheduleGroup: stopScheduleGroupName },
        metricName,
        namespace: 'AWS/Scheduler',
        period: Duration.minutes(1),
        statistic: 'Sum',
      });
      const alarmProps = {
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        evaluationPeriods: 1,
        threshold: 1,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      };
      const targetErrorAlarm = new cloudwatch.Alarm(this, 'CanaryAutoStopTargetErrorAlarm', {
        ...alarmProps,
        alarmDescription: 'EventBridge Scheduler could not invoke the canary auto-stop target.',
        metric: schedulerMetric('TargetErrorCount'),
      });
      const droppedInvocationAlarm = new cloudwatch.Alarm(
        this,
        'CanaryAutoStopDroppedInvocationAlarm',
        {
          ...alarmProps,
          alarmDescription: 'EventBridge Scheduler dropped the canary auto-stop invocation.',
          metric: schedulerMetric('InvocationDroppedCount'),
        },
      );
      const deadLetterAlarm = new cloudwatch.Alarm(this, 'CanaryAutoStopDeadLetterAlarm', {
        ...alarmProps,
        alarmDescription: 'The canary auto-stop dead-letter queue contains an undelivered event.',
        metric: stopDeadLetterQueue.metricApproximateNumberOfMessagesVisible({
          period: Duration.minutes(1),
          statistic: 'Sum',
        }),
      });
      if (!operationalAlertsTopic) {
        throw new Error('Private phase requires the confirmed operational alerts topic.');
      }
      const alertAction = new cloudwatchActions.SnsAction(operationalAlertsTopic);
      targetErrorAlarm.addAlarmAction(alertAction);
      droppedInvocationAlarm.addAlarmAction(alertAction);
      deadLetterAlarm.addAlarmAction(alertAction);
      new CfnOutput(this, 'CanaryAutoStopFailureAlarms', {
        description: 'Alarm names that must remain OK through the private canary expiry.',
        value: Fn.join(',', [
          targetErrorAlarm.alarmName,
          droppedInvocationAlarm.alarmName,
          deadLetterAlarm.alarmName,
        ]),
      });
    }

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
    Tags.of(userPool).add('DataClassification', 'restricted', { priority: 200 });
    const userPoolDomain = costControlsEnabled && operatorAuthDomainPrefix
      ? userPool.addDomain('OperatorHostedUiDomain', {
        cognitoDomain: {
          domainPrefix: operatorAuthDomainPrefix.valueAsString,
        },
      })
      : undefined;
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
    let stage: HttpStage | undefined;
    if (privateActive) {
      const authorizer = new HttpJwtAuthorizer(
        'OperatorCognitoJwt',
        userPool.userPoolProviderUrl,
        { jwtAudience: [userPoolClient.userPoolClientId] },
      );
      api.addRoutes({
        path: '/intake/url',
        methods: [HttpMethod.POST],
        authorizer,
        authorizationScopes: [Config.REQUIRED_SCOPE],
        integration: new HttpLambdaIntegration('UrlIntakeIntegration', intakeFunction),
      });

      stage = new HttpStage(this, 'DefaultStage', {
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
    }

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

    if (costControlsEnabled) {
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
    }

    new CfnOutput(this, 'DeploymentInfo', {
      value: deployInfo,
      description: 'Required source of this deployment: exact repository, main branch, and full commit',
    });
    new CfnOutput(this, 'SourceCommit', {
      value: gitCommit,
      description: 'Exact merged source commit used for this stack state.',
    });
    if (stage) {
      new CfnOutput(this, 'ApiInvokeUrl', {
        value: stage.url,
        description: 'Raw authenticated HTTP API URL; no api.huboptimus.dev DNS mapping is created.',
      });
    }
    new CfnOutput(this, 'OperatorUserPoolId', {
      value: userPool.userPoolId,
    });
    new CfnOutput(this, 'OperatorWebClientId', {
      value: userPoolClient.userPoolClientId,
    });
    new CfnOutput(this, 'OperatorJwtIssuer', {
      value: userPool.userPoolProviderUrl,
    });
    if (userPoolDomain) {
      new CfnOutput(this, 'OperatorHostedUiBaseUrl', {
        value: userPoolDomain.baseUrl(),
        description: 'Use OAuth authorization-code flow with S256 PKCE; implicit flow is disabled.',
      });
    }
    new CfnOutput(this, 'OperatorCallbackUrlOutput', {
      value: operatorCallbackUrl.valueAsString,
    });
    new CfnOutput(this, 'OperatorLogoutUrlOutput', {
      value: operatorLogoutUrl.valueAsString,
    });
    new CfnOutput(this, 'ServiceState', {
      value: privateActive ? 'ENABLED' : 'DISABLED',
      description: 'Fail-closed unless deploymentPhase=private is supplied explicitly.',
    });
    new CfnOutput(this, 'DeploymentPhase', {
      value: deploymentPhase.toUpperCase(),
      description: 'Explicit three-phase canary state: foundation, controls, or private.',
    });
    new CfnOutput(this, 'PublicSignupState', {
      value: 'DISABLED',
      description: 'Public signup is not authorized by this private-smoke candidate.',
    });
  }
}
