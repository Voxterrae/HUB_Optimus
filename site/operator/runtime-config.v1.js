(function installOperatorRuntimeConfig(globalObject) {
  "use strict";

  // Deployment-safe default: the public Pages artifact remains local-only.
  // A reviewed private deployment may replace only these public identifiers
  // with the exact CloudFormation outputs. This file must never contain a
  // client secret, AWS credential, token, authorization code or user data.
  const config = {
    schemaVersion: "1.0",
    enabled: false,
    apiInvokeUrl: "",
    authorizationEndpoint: "",
    tokenEndpoint: "",
    logoutEndpoint: "",
    issuer: "",
    clientId: "",
    callbackUrl: "https://huboptimus.dev/operator/",
    logoutUrl: "https://huboptimus.dev/operator/",
    scope: "operator/intake"
  };

  Object.defineProperty(globalObject, "HUB_OPTIMUS_OPERATOR_RUNTIME_CONFIG", {
    configurable: false,
    enumerable: true,
    writable: false,
    value: Object.freeze(config)
  });
})(globalThis);
