export const Config = {
  AWS_ACCOUNT_ID: '904851777129',
  DEFAULT_AWS_REGION: 'eu-west-1',
  COST_TAG_KEY: 'HUBOptimusCostUnit',
  COST_TAG_VALUE: 'ControlledUrlIntake',
  REQUIRED_SCOPE: 'operator/intake',
  MANAGED_BY: 'CDK',
  BACKUP_REQUIRED: 'no',
};

export function resolveAwsRegion(value: unknown): string {
  const region = value ?? Config.DEFAULT_AWS_REGION;
  if (region !== Config.DEFAULT_AWS_REGION) {
    throw new Error(
      `This stack may only target AWS region ${Config.DEFAULT_AWS_REGION}.`,
    );
  }
  return Config.DEFAULT_AWS_REGION;
}
