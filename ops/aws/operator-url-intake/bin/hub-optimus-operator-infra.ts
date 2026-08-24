#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { HubOptimusOperatorInfraStack } from '../lib/hub-optimus-operator-infra-stack';
const app = new cdk.App();
new HubOptimusOperatorInfraStack(app, 'hub-optimus-operator-infra', { stackName: 'hub-optimus-operator-infra' });
