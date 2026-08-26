#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { HubOptimusOperatorInfraStack } from '../lib/hub-optimus-operator-infra-stack';
import { Config, resolveAwsRegion } from '../lib/config';

const app = new cdk.App({ analyticsReporting: false });
const region = resolveAwsRegion(app.node.tryGetContext('awsRegion'));
new HubOptimusOperatorInfraStack(app, 'hub-optimus-operator-infra', {
  stackName: 'hub-optimus-operator-infra',
  env: {
    account: Config.AWS_ACCOUNT_ID,
    region,
  },
});
