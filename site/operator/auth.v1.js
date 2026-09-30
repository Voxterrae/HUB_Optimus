(function installOperatorPrivateAuth(globalObject) {
  "use strict";

  const CONFIG_NAME = "HUB_OPTIMUS_OPERATOR_RUNTIME_CONFIG";
  const CALLBACK_NAME = "__HUB_OPTIMUS_OPERATOR_OAUTH_CALLBACK_V1__";
  const TRANSACTION_KEY = "hub_optimus.operator.oauth.pending.v1";
  const CALLBACK_URL = "https://huboptimus.dev/operator/";
  const LOGOUT_URL = "https://huboptimus.dev/operator/";
  const REQUIRED_SCOPE = "operator/intake";
  const REQUESTED_SCOPE = `openid email ${REQUIRED_SCOPE}`;
  const TRANSACTION_MAX_AGE_MS = 10 * 60 * 1000;
  const TOKEN_EXPIRY_SKEW_MS = 30 * 1000;
  const RANDOM_BYTES = 32;
  const CONFIG_FIELDS = Object.freeze([
    "schemaVersion",
    "enabled",
    "apiInvokeUrl",
    "authorizationEndpoint",
    "tokenEndpoint",
    "logoutEndpoint",
    "issuer",
    "clientId",
    "callbackUrl",
    "logoutUrl",
    "scope"
  ]);

  class OperatorAuthError extends Error {
    constructor(code, message) {
      super(message);
      this.name = "OperatorAuthError";
      this.code = String(code || "auth_failed");
    }
  }

  let callbackSnapshot = globalObject[CALLBACK_NAME] || null;
  try {
    delete globalObject[CALLBACK_NAME];
  } catch {
    callbackSnapshot = null;
  }

  let normalizedConfig;
  let memoryTokens = null;
  let initializationPromise = null;
  let currentState = Object.freeze({
    state: "uninitialized",
    enabled: false,
    authenticated: false,
    code: null
  });
  const subscribers = new Set();

  function fail(code, message) {
    throw new OperatorAuthError(code, message);
  }

  function isPlainRecord(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const prototype = Object.getPrototypeOf(value);
    return prototype === null || Object.getPrototypeOf(prototype) === null;
  }

  function exactFields(value, fields) {
    if (!isPlainRecord(value)) return false;
    const actual = Object.keys(value);
    const expected = new Set(fields);
    return actual.length === fields.length && actual.every((field) => expected.has(field));
  }

  function secureUrl(value, label, { pathSuffix = null } = {}) {
    let parsed;
    try {
      parsed = new URL(value);
    } catch {
      return fail("config_invalid", `${label} must be an absolute HTTPS URL.`);
    }
    if (
      parsed.protocol !== "https:" ||
      parsed.username ||
      parsed.password ||
      parsed.port ||
      parsed.search ||
      parsed.hash ||
      (pathSuffix && !parsed.pathname.endsWith(pathSuffix))
    ) {
      return fail("config_invalid", `${label} is not an allowed HTTPS endpoint.`);
    }
    return parsed;
  }

  function configuration() {
    if (normalizedConfig !== undefined) return normalizedConfig;
    const supplied = globalObject[CONFIG_NAME];
    if (!isPlainRecord(supplied) || supplied.enabled !== true) {
      normalizedConfig = null;
      return normalizedConfig;
    }
    if (!exactFields(supplied, CONFIG_FIELDS) || supplied.schemaVersion !== "1.0") {
      return fail("config_invalid", "Private Operator runtime configuration has an unexpected shape.");
    }
    if (
      supplied.callbackUrl !== CALLBACK_URL ||
      supplied.logoutUrl !== LOGOUT_URL ||
      supplied.scope !== REQUIRED_SCOPE ||
      typeof supplied.clientId !== "string" ||
      !/^[A-Za-z0-9]+$/.test(supplied.clientId)
    ) {
      return fail("config_invalid", "Private Operator OAuth identifiers do not match the fixed contract.");
    }

    const api = secureUrl(supplied.apiInvokeUrl, "apiInvokeUrl");
    const authorization = secureUrl(
      supplied.authorizationEndpoint,
      "authorizationEndpoint",
      { pathSuffix: "/oauth2/authorize" }
    );
    const token = secureUrl(
      supplied.tokenEndpoint,
      "tokenEndpoint",
      { pathSuffix: "/oauth2/token" }
    );
    const logout = secureUrl(
      supplied.logoutEndpoint,
      "logoutEndpoint",
      { pathSuffix: "/logout" }
    );
    const issuer = secureUrl(supplied.issuer, "issuer");
    if (authorization.origin !== token.origin || token.origin !== logout.origin) {
      return fail("config_invalid", "Hosted UI authorize, token and logout endpoints must share one origin.");
    }
    if (
      !/^[a-z0-9-]+\.auth\.eu-west-1\.amazoncognito\.com$/.test(authorization.hostname) ||
      authorization.pathname !== "/oauth2/authorize" ||
      token.pathname !== "/oauth2/token" ||
      logout.pathname !== "/logout"
    ) {
      return fail("config_invalid", "Hosted UI endpoints must be exact eu-west-1 Cognito endpoints.");
    }
    if (
      !/^[a-z0-9]+\.execute-api\.eu-west-1\.amazonaws\.com$/.test(api.hostname) ||
      api.pathname !== "/"
    ) {
      return fail("config_invalid", "apiInvokeUrl must be the raw eu-west-1 API Gateway output.");
    }
    if (
      issuer.hostname !== "cognito-idp.eu-west-1.amazonaws.com" ||
      !/^\/eu-west-1_[A-Za-z0-9]+$/.test(issuer.pathname)
    ) {
      return fail("config_invalid", "issuer must be an exact eu-west-1 Cognito user-pool issuer.");
    }

    const basePath = api.pathname.endsWith("/") ? api.pathname : `${api.pathname}/`;
    const intake = new URL(`${basePath}intake/url`, api.origin);
    normalizedConfig = Object.freeze({
      apiInvokeUrl: api.href,
      intakeEndpoint: intake.href,
      authorizationEndpoint: authorization.href,
      tokenEndpoint: token.href,
      logoutEndpoint: logout.href,
      issuer: issuer.href.replace(/\/$/, ""),
      clientId: supplied.clientId,
      callbackUrl: CALLBACK_URL,
      logoutUrl: LOGOUT_URL,
      requiredScope: REQUIRED_SCOPE
    });
    return normalizedConfig;
  }

  function publish(state, code = null) {
    const enabled = (() => {
      try {
        return configuration() !== null;
      } catch {
        return false;
      }
    })();
    currentState = Object.freeze({
      state,
      enabled,
      authenticated: state === "authenticated",
      code: code === null ? null : String(code)
    });
    subscribers.forEach((subscriber) => {
      try {
        subscriber(currentState);
      } catch {
        // A presentation callback must not change the authentication state.
      }
    });
  }

  function onChange(subscriber) {
    if (typeof subscriber !== "function") return () => {};
    subscribers.add(subscriber);
    subscriber(currentState);
    return () => subscribers.delete(subscriber);
  }

  function randomBase64Url() {
    const bytes = new Uint8Array(RANDOM_BYTES);
    globalObject.crypto.getRandomValues(bytes);
    let binary = "";
    bytes.forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return globalObject.btoa(binary)
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  }

  async function codeChallenge(verifier) {
    const digest = await globalObject.crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(verifier)
    );
    let binary = "";
    new Uint8Array(digest).forEach((byte) => {
      binary += String.fromCharCode(byte);
    });
    return globalObject.btoa(binary)
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  }

  function constantTimeEqual(left, right) {
    const a = String(left ?? "");
    const b = String(right ?? "");
    const length = Math.max(a.length, b.length);
    let difference = a.length ^ b.length;
    for (let index = 0; index < length; index += 1) {
      difference |= (a.charCodeAt(index) || 0) ^ (b.charCodeAt(index) || 0);
    }
    return difference === 0;
  }

  function readTransaction() {
    let raw;
    try {
      raw = globalObject.sessionStorage.getItem(TRANSACTION_KEY);
    } catch {
      return fail("storage_unavailable", "Browser session storage is unavailable.");
    }
    if (!raw) return fail("transaction_missing", "No pending sign-in transaction exists.");

    let transaction;
    try {
      transaction = JSON.parse(raw);
    } catch {
      return fail("transaction_invalid", "Pending sign-in transaction is malformed.");
    }
    if (
      !isPlainRecord(transaction) ||
      transaction.version !== 1 ||
      typeof transaction.verifier !== "string" ||
      !/^[A-Za-z0-9_-]{43,128}$/.test(transaction.verifier) ||
      typeof transaction.state !== "string" ||
      !/^[A-Za-z0-9_-]{43}$/.test(transaction.state) ||
      typeof transaction.nonce !== "string" ||
      !/^[A-Za-z0-9_-]{43}$/.test(transaction.nonce) ||
      typeof transaction.createdAt !== "number" ||
      !Number.isFinite(transaction.createdAt) ||
      transaction.clientId !== configuration()?.clientId ||
      transaction.callbackUrl !== CALLBACK_URL ||
      transaction.scope !== REQUIRED_SCOPE
    ) {
      return fail("transaction_invalid", "Pending sign-in transaction is invalid.");
    }
    const age = Date.now() - transaction.createdAt;
    if (age < 0 || age > TRANSACTION_MAX_AGE_MS) {
      return fail("transaction_expired", "Pending sign-in transaction expired.");
    }
    return transaction;
  }

  function clearTransaction() {
    try {
      globalObject.sessionStorage.removeItem(TRANSACTION_KEY);
    } catch {
      // Clearing remains best-effort when storage is unavailable.
    }
  }

  function callbackValue(name, { required = false } = {}) {
    const values = callbackSnapshot?.[name];
    if (!Array.isArray(values) || values.length === 0) {
      if (required) return fail("callback_invalid", `OAuth callback is missing ${name}.`);
      return null;
    }
    if (values.length !== 1 || typeof values[0] !== "string" || !values[0]) {
      return fail("callback_invalid", `OAuth callback contains invalid ${name}.`);
    }
    return values[0];
  }

  function decodeJwtPayload(token) {
    const segments = String(token).split(".");
    if (segments.length !== 3 || segments.some((segment) => !segment)) {
      return fail("token_invalid", "Token is not a compact JWT.");
    }
    const segment = segments[1];
    if (!/^[A-Za-z0-9_-]+$/.test(segment) || segment.length % 4 === 1) {
      return fail("token_invalid", "Token payload is not valid base64url.");
    }
    const padded = segment.replace(/-/g, "+").replace(/_/g, "/")
      + "=".repeat((4 - segment.length % 4) % 4);
    try {
      const binary = globalObject.atob(padded);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      const payload = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
      if (!isPlainRecord(payload)) return fail("token_invalid", "Token payload must be an object.");
      return payload;
    } catch (error) {
      if (error instanceof OperatorAuthError) throw error;
      return fail("token_invalid", "Token payload is malformed.");
    }
  }

  function validateTokens(payload, nonce) {
    if (
      !isPlainRecord(payload) ||
      typeof payload.access_token !== "string" ||
      !payload.access_token ||
      typeof payload.id_token !== "string" ||
      !payload.id_token ||
      payload.token_type !== "Bearer" ||
      !Number.isSafeInteger(payload.expires_in) ||
      payload.expires_in <= 0
    ) {
      return fail("token_response_invalid", "Hosted UI token response is incomplete.");
    }

    const config = configuration();
    const idClaims = decodeJwtPayload(payload.id_token);
    const accessClaims = decodeJwtPayload(payload.access_token);
    const nowSeconds = Math.floor(Date.now() / 1000);
    if (
      idClaims.token_use !== "id" ||
      idClaims.aud !== config.clientId ||
      idClaims.iss !== config.issuer ||
      typeof idClaims.sub !== "string" ||
      !idClaims.sub ||
      !Number.isSafeInteger(idClaims.exp) ||
      idClaims.exp <= nowSeconds ||
      typeof idClaims.nonce !== "string" ||
      !constantTimeEqual(idClaims.nonce, nonce)
    ) {
      return fail("id_token_invalid", "Hosted UI ID token claims do not match the sign-in transaction.");
    }
    const scopes = typeof accessClaims.scope === "string"
      ? new Set(accessClaims.scope.split(/\s+/).filter(Boolean))
      : new Set();
    if (
      accessClaims.token_use !== "access" ||
      accessClaims.client_id !== config.clientId ||
      accessClaims.iss !== config.issuer ||
      accessClaims.sub !== idClaims.sub ||
      !Number.isSafeInteger(accessClaims.exp) ||
      accessClaims.exp <= nowSeconds ||
      !scopes.has(REQUIRED_SCOPE)
    ) {
      return fail("access_token_invalid", "Hosted UI access token claims do not match the intake client.");
    }

    const responseExpiry = Date.now() + payload.expires_in * 1000;
    const claimExpiry = accessClaims.exp * 1000;
    return Object.freeze({
      accessToken: payload.access_token,
      expiresAt: Math.min(responseExpiry, claimExpiry)
    });
  }

  async function exchangeCallback() {
    const config = configuration();
    let transaction;
    try {
      transaction = readTransaction();
    } finally {
      // Any detected callback consumes the pending browser transaction,
      // including malformed, mismatched, rejected and expired callbacks.
      clearTransaction();
    }
    if (callbackSnapshot?.callbackUrl !== CALLBACK_URL) {
      return fail("callback_invalid", "OAuth callback URL does not match the fixed Operator callback.");
    }
    const state = callbackValue("state", { required: true });
    if (!constantTimeEqual(state, transaction.state)) {
      return fail("state_mismatch", "OAuth callback state does not match this browser session.");
    }
    const callbackIssuer = callbackValue("iss");
    if (callbackIssuer !== null && callbackIssuer.replace(/\/$/, "") !== config.issuer) {
      return fail("issuer_mismatch", "OAuth callback issuer does not match the configured user pool.");
    }

    const authorizationError = callbackValue("error");
    if (authorizationError !== null) {
      return fail("authorization_rejected", `Hosted UI returned ${authorizationError}.`);
    }
    const code = callbackValue("code", { required: true });
    const body = new URLSearchParams({
      grant_type: "authorization_code",
      client_id: config.clientId,
      code,
      redirect_uri: CALLBACK_URL,
      code_verifier: transaction.verifier
    }).toString();

    let response;
    try {
      response = await globalObject.fetch(config.tokenEndpoint, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body,
        cache: "no-store",
        credentials: "omit",
        redirect: "error"
      });
    } catch {
      return fail("token_exchange_failed", "Hosted UI token exchange failed.");
    }
    if (!response || response.ok !== true || response.status !== 200) {
      return fail("token_exchange_failed", "Hosted UI rejected the authorization code.");
    }

    let payload;
    try {
      payload = await response.json();
    } catch {
      return fail("token_response_invalid", "Hosted UI token response was not JSON.");
    }
    memoryTokens = validateTokens(payload, transaction.nonce);
    publish("authenticated");
    return currentState;
  }

  async function initialize() {
    if (initializationPromise) return initializationPromise;
    initializationPromise = (async () => {
      let config;
      try {
        config = configuration();
      } catch (error) {
        clearTransaction();
        publish("error", error?.code || "config_invalid");
        throw error;
      }

      if (!config) {
        clearTransaction();
        callbackSnapshot = null;
        publish("disabled");
        return currentState;
      }
      if (!callbackSnapshot) {
        publish(memoryTokens ? "authenticated" : "signed_out");
        return currentState;
      }

      publish("completing");
      try {
        return await exchangeCallback();
      } catch (error) {
        memoryTokens = null;
        publish("error", error?.code || "auth_failed");
        throw error;
      } finally {
        callbackSnapshot = null;
      }
    })();
    return initializationPromise;
  }

  async function login() {
    const config = configuration();
    if (!config) return fail("auth_disabled", "Private URL retrieval is disabled.");
    if (!globalObject.crypto?.subtle || typeof globalObject.crypto.getRandomValues !== "function") {
      return fail("crypto_unavailable", "Web Crypto is required for private sign-in.");
    }

    memoryTokens = null;
    const verifier = randomBase64Url();
    const state = randomBase64Url();
    const nonce = randomBase64Url();
    const challenge = await codeChallenge(verifier);
    const transaction = {
      version: 1,
      verifier,
      state,
      nonce,
      createdAt: Date.now(),
      clientId: config.clientId,
      callbackUrl: CALLBACK_URL,
      scope: REQUIRED_SCOPE
    };
    try {
      globalObject.sessionStorage.setItem(TRANSACTION_KEY, JSON.stringify(transaction));
    } catch {
      return fail("storage_unavailable", "Browser session storage is unavailable.");
    }

    const authorize = new URL(config.authorizationEndpoint);
    authorize.searchParams.set("response_type", "code");
    authorize.searchParams.set("client_id", config.clientId);
    authorize.searchParams.set("redirect_uri", CALLBACK_URL);
    authorize.searchParams.set("scope", REQUESTED_SCOPE);
    authorize.searchParams.set("state", state);
    authorize.searchParams.set("nonce", nonce);
    authorize.searchParams.set("code_challenge", challenge);
    authorize.searchParams.set("code_challenge_method", "S256");
    publish("redirecting");
    globalObject.location.assign(authorize.href);
  }

  function clearTokens(code = null) {
    memoryTokens = null;
    publish(configuration() ? "signed_out" : "disabled", code);
  }

  function getAccessToken() {
    if (!memoryTokens) return null;
    if (Date.now() + TOKEN_EXPIRY_SKEW_MS >= memoryTokens.expiresAt) {
      clearTokens("token_expired");
      return null;
    }
    return memoryTokens.accessToken;
  }

  function logout() {
    const config = configuration();
    clearTransaction();
    memoryTokens = null;
    publish(config ? "signed_out" : "disabled");
    if (!config) return;
    const endpoint = new URL(config.logoutEndpoint);
    endpoint.searchParams.set("client_id", config.clientId);
    endpoint.searchParams.set("logout_uri", LOGOUT_URL);
    globalObject.location.assign(endpoint.href);
  }

  function isEnabled() {
    try {
      return configuration() !== null;
    } catch {
      return false;
    }
  }

  function isAuthenticated() {
    return Boolean(getAccessToken());
  }

  function getIntakeEndpoint() {
    try {
      return configuration()?.intakeEndpoint || "";
    } catch {
      return "";
    }
  }

  Object.defineProperty(globalObject, "HUB_OPTIMUS_OPERATOR_AUTH", {
    configurable: false,
    enumerable: true,
    writable: false,
    value: Object.freeze({
      CALLBACK_URL,
      LOGOUT_URL,
      REQUIRED_SCOPE,
      clearTokens,
      getAccessToken,
      getIntakeEndpoint,
      initialize,
      isAuthenticated,
      isEnabled,
      login,
      logout,
      onChange,
      status: () => currentState
    })
  });
})(globalThis);
