/**
 * Minimal browser-side OAuth 2.0 Authorization Code + PKCE client.
 *
 * The caller supplies sessionStorage, Web Crypto and fetch so this module can
 * be tested in Node without browser globals. Only the short-lived transaction
 * (verifier, state and nonce) is stored. Tokens are returned in memory and are
 * never written to storage.
 *
 * JWT claim checks below are a client-side defence-in-depth measure. They do
 * not replace signature, issuer and expiry validation by the API authorizer.
 */

export const OPERATOR_INTAKE_SCOPE = 'operator/intake';

const DEFAULT_SCOPE = `openid ${OPERATOR_INTAKE_SCOPE}`;
const DEFAULT_STORAGE_KEY = 'hub_optimus.operator.oauth.pending.v1';
const DEFAULT_MAX_TRANSACTION_AGE_MS = 10 * 60 * 1000;
const RANDOM_VALUE_BYTES = 32;

export interface OAuthPkceConfig {
  readonly authorizationEndpoint: string;
  readonly tokenEndpoint: string;
  readonly clientId: string;
  readonly redirectUri: string;
  readonly scope?: string;
  readonly requiredScope?: string;
  readonly storageKey?: string;
  readonly maxTransactionAgeMs?: number;
}

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export interface CryptoLike {
  getRandomValues(array: Uint8Array): Uint8Array;
  readonly subtle: {
    digest(algorithm: string, data: Uint8Array): Promise<ArrayBuffer>;
  };
}

export interface OAuthFetchResponse {
  readonly ok: boolean;
  readonly status: number;
  json(): Promise<unknown>;
}

export interface OAuthFetchInit {
  readonly method: 'POST';
  readonly headers: Readonly<Record<string, string>>;
  readonly body: string;
  readonly credentials: 'omit';
  readonly redirect: 'error';
}

export type OAuthFetch = (url: string, init: OAuthFetchInit) => Promise<OAuthFetchResponse>;

export interface OAuthPkceDependencies {
  readonly crypto: CryptoLike;
  readonly storage: StorageLike;
  readonly fetch: OAuthFetch;
  readonly now?: () => number;
}

export interface OAuthTokenSet {
  /** Send only this token to the intake API as a Bearer token. */
  readonly accessToken: string;
  /** Kept in memory for the caller's current UI session only. */
  readonly idToken: string;
  readonly tokenType: 'Bearer';
  readonly expiresIn?: number;
}

export type OAuthPkceErrorCode =
  | 'invalid_configuration'
  | 'authorization_transaction_missing'
  | 'authorization_transaction_invalid'
  | 'authorization_transaction_expired'
  | 'callback_redirect_mismatch'
  | 'callback_parameters_invalid'
  | 'callback_state_mismatch'
  | 'authorization_server_error'
  | 'token_exchange_failed'
  | 'token_response_invalid'
  | 'jwt_invalid'
  | 'id_token_nonce_mismatch'
  | 'id_token_audience_mismatch'
  | 'access_token_use_invalid'
  | 'access_token_client_mismatch'
  | 'access_token_scope_missing';

export class OAuthPkceError extends Error {
  public constructor(
    public readonly code: OAuthPkceErrorCode,
    message: string,
  ) {
    super(message);
    this.name = 'OAuthPkceError';
  }
}

export interface OAuthPkceClient {
  /** Creates and stores a new single-use transaction and returns the authorize URL. */
  createAuthorizationUrl(): Promise<string>;

  /**
   * Validates and consumes the callback transaction, exchanges the code and
   * returns validated tokens in memory. The tokens are not persisted.
   */
  handleAuthorizationCallback(callbackUrl: string): Promise<OAuthTokenSet>;

  /** Removes an abandoned verifier/state/nonce transaction. */
  clearPendingAuthorization(): void;
}

interface PendingAuthorization {
  readonly version: 1;
  readonly clientId: string;
  readonly redirectUri: string;
  readonly verifier: string;
  readonly state: string;
  readonly nonce: string;
  readonly createdAt: number;
}

interface NormalizedConfig {
  readonly authorizationEndpoint: string;
  readonly tokenEndpoint: string;
  readonly clientId: string;
  readonly redirectUri: string;
  readonly scope: string;
  readonly requiredScope: string;
  readonly storageKey: string;
  readonly maxTransactionAgeMs: number;
}

function configurationError(message: string): never {
  throw new OAuthPkceError('invalid_configuration', message);
}

function validatedHttpsEndpoint(value: string, label: string): string {
  let endpoint: URL;
  try {
    endpoint = new URL(value);
  } catch {
    return configurationError(`${label} must be an absolute URL.`);
  }

  if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password || endpoint.hash) {
    return configurationError(`${label} must be a credential-free HTTPS URL without a fragment.`);
  }
  return endpoint.href;
}

function normalizeConfig(config: OAuthPkceConfig): NormalizedConfig {
  const clientId = config.clientId.trim();
  if (!clientId) {
    return configurationError('clientId is required.');
  }

  const redirectUri = validatedHttpsEndpoint(config.redirectUri, 'redirectUri');
  const redirect = new URL(redirectUri);
  if (redirect.search) {
    return configurationError('redirectUri must not contain query parameters.');
  }

  const requiredScope = (config.requiredScope ?? OPERATOR_INTAKE_SCOPE).trim();
  const scope = (config.scope ?? DEFAULT_SCOPE).trim().split(/\s+/u).filter(Boolean).join(' ');
  const requestedScopes = new Set(scope.split(' '));
  if (!requiredScope || !requestedScopes.has('openid') || !requestedScopes.has(requiredScope)) {
    return configurationError('scope must include openid and the required intake scope.');
  }

  const storageKey = (config.storageKey ?? DEFAULT_STORAGE_KEY).trim();
  if (!storageKey) {
    return configurationError('storageKey must not be empty.');
  }

  const maxTransactionAgeMs = config.maxTransactionAgeMs ?? DEFAULT_MAX_TRANSACTION_AGE_MS;
  if (!Number.isSafeInteger(maxTransactionAgeMs) || maxTransactionAgeMs <= 0) {
    return configurationError('maxTransactionAgeMs must be a positive safe integer.');
  }

  return {
    authorizationEndpoint: validatedHttpsEndpoint(config.authorizationEndpoint, 'authorizationEndpoint'),
    tokenEndpoint: validatedHttpsEndpoint(config.tokenEndpoint, 'tokenEndpoint'),
    clientId,
    redirectUri,
    scope,
    requiredScope,
    storageKey,
    maxTransactionAgeMs,
  };
}

function encodeBase64Url(bytes: Uint8Array): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
  let encoded = '';
  for (let index = 0; index < bytes.length; index += 3) {
    const first = bytes[index];
    const second = index + 1 < bytes.length ? bytes[index + 1] : 0;
    const third = index + 2 < bytes.length ? bytes[index + 2] : 0;
    const value = (first << 16) | (second << 8) | third;
    encoded += alphabet[(value >>> 18) & 63];
    encoded += alphabet[(value >>> 12) & 63];
    if (index + 1 < bytes.length) {
      encoded += alphabet[(value >>> 6) & 63];
    }
    if (index + 2 < bytes.length) {
      encoded += alphabet[value & 63];
    }
  }
  return encoded;
}

function decodeBase64Url(value: string): Uint8Array {
  if (!value || !/^[A-Za-z0-9_-]+$/u.test(value) || value.length % 4 === 1) {
    throw new OAuthPkceError('jwt_invalid', 'JWT payload is not valid base64url.');
  }

  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
  const outputLength = Math.floor((value.length * 6) / 8);
  const output = new Uint8Array(outputLength);
  let accumulator = 0;
  let bitCount = 0;
  let outputIndex = 0;

  for (const character of value) {
    const digit = alphabet.indexOf(character);
    if (digit < 0) {
      throw new OAuthPkceError('jwt_invalid', 'JWT payload is not valid base64url.');
    }
    accumulator = (accumulator << 6) | digit;
    bitCount += 6;
    if (bitCount >= 8) {
      bitCount -= 8;
      output[outputIndex] = (accumulator >>> bitCount) & 255;
      outputIndex += 1;
    }
  }
  return output;
}

function randomBase64Url(crypto: CryptoLike): string {
  const bytes = new Uint8Array(RANDOM_VALUE_BYTES);
  crypto.getRandomValues(bytes);
  return encodeBase64Url(bytes);
}

async function createCodeChallenge(crypto: CryptoLike, verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return encodeBase64Url(new Uint8Array(digest));
}

function constantTimeEqual(left: string, right: string): boolean {
  const maximumLength = Math.max(left.length, right.length);
  let difference = left.length ^ right.length;
  for (let index = 0; index < maximumLength; index += 1) {
    difference |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  }
  return difference === 0;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parsePending(raw: string): PendingAuthorization {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new OAuthPkceError('authorization_transaction_invalid', 'Stored authorization transaction is malformed.');
  }

  if (!isRecord(parsed)
    || parsed.version !== 1
    || typeof parsed.clientId !== 'string'
    || typeof parsed.redirectUri !== 'string'
    || typeof parsed.verifier !== 'string'
    || typeof parsed.state !== 'string'
    || typeof parsed.nonce !== 'string'
    || typeof parsed.createdAt !== 'number'
    || !Number.isFinite(parsed.createdAt)
    || parsed.verifier.length < 43
    || parsed.verifier.length > 128
    || !/^[A-Za-z0-9_-]+$/u.test(parsed.verifier)
    || !/^[A-Za-z0-9_-]{43,}$/u.test(parsed.state)
    || !/^[A-Za-z0-9_-]{43,}$/u.test(parsed.nonce)) {
    throw new OAuthPkceError('authorization_transaction_invalid', 'Stored authorization transaction is invalid.');
  }

  return parsed as unknown as PendingAuthorization;
}

function exactlyOneParameter(parameters: URLSearchParams, name: string): string {
  const values = parameters.getAll(name);
  if (values.length !== 1 || !values[0]) {
    throw new OAuthPkceError('callback_parameters_invalid', `Callback must contain exactly one ${name} parameter.`);
  }
  return values[0];
}

function parseJwtPayload(token: string): Record<string, unknown> {
  const segments = token.split('.');
  if (segments.length !== 3 || segments.some((segment) => !segment)) {
    throw new OAuthPkceError('jwt_invalid', 'Token is not a compact JWT.');
  }

  try {
    const text = new TextDecoder('utf-8', { fatal: true }).decode(decodeBase64Url(segments[1]));
    const payload: unknown = JSON.parse(text);
    if (!isRecord(payload)) {
      throw new Error('JWT payload is not an object.');
    }
    return payload;
  } catch (error) {
    if (error instanceof OAuthPkceError) {
      throw error;
    }
    throw new OAuthPkceError('jwt_invalid', 'JWT payload is malformed.');
  }
}

function requireString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== 'string' || !value) {
    throw new OAuthPkceError('token_response_invalid', `Token response is missing ${key}.`);
  }
  return value;
}

function validateTokenClaims(
  idToken: string,
  accessToken: string,
  expectedNonce: string,
  config: NormalizedConfig,
): void {
  const idClaims = parseJwtPayload(idToken);
  const accessClaims = parseJwtPayload(accessToken);

  if (idClaims.token_use !== 'id') {
    throw new OAuthPkceError('jwt_invalid', 'ID token has an unexpected token_use claim.');
  }
  if (typeof idClaims.nonce !== 'string' || !constantTimeEqual(idClaims.nonce, expectedNonce)) {
    throw new OAuthPkceError('id_token_nonce_mismatch', 'ID token nonce does not match the authorization transaction.');
  }
  if (typeof idClaims.aud !== 'string' || !constantTimeEqual(idClaims.aud, config.clientId)) {
    throw new OAuthPkceError('id_token_audience_mismatch', 'ID token audience does not match this client.');
  }

  if (accessClaims.token_use !== 'access') {
    throw new OAuthPkceError('access_token_use_invalid', 'Access token token_use must be access.');
  }
  if (typeof accessClaims.client_id !== 'string' || !constantTimeEqual(accessClaims.client_id, config.clientId)) {
    throw new OAuthPkceError('access_token_client_mismatch', 'Access token client_id does not match this client.');
  }
  if (typeof accessClaims.scope !== 'string'
    || !new Set(accessClaims.scope.split(/\s+/u).filter(Boolean)).has(config.requiredScope)) {
    throw new OAuthPkceError('access_token_scope_missing', 'Access token lacks the required intake scope.');
  }
}

export function createOAuthPkceClient(
  suppliedConfig: OAuthPkceConfig,
  dependencies: OAuthPkceDependencies,
): OAuthPkceClient {
  const config = normalizeConfig(suppliedConfig);
  const now = dependencies.now ?? (() => Date.now());

  function clearPendingAuthorization(): void {
    dependencies.storage.removeItem(config.storageKey);
  }

  async function createAuthorizationUrl(): Promise<string> {
    const verifier = randomBase64Url(dependencies.crypto);
    const state = randomBase64Url(dependencies.crypto);
    const nonce = randomBase64Url(dependencies.crypto);
    const challenge = await createCodeChallenge(dependencies.crypto, verifier);

    const pending: PendingAuthorization = {
      version: 1,
      clientId: config.clientId,
      redirectUri: config.redirectUri,
      verifier,
      state,
      nonce,
      createdAt: now(),
    };
    dependencies.storage.setItem(config.storageKey, JSON.stringify(pending));

    const authorizeUrl = new URL(config.authorizationEndpoint);
    authorizeUrl.searchParams.set('response_type', 'code');
    authorizeUrl.searchParams.set('client_id', config.clientId);
    authorizeUrl.searchParams.set('redirect_uri', config.redirectUri);
    authorizeUrl.searchParams.set('scope', config.scope);
    authorizeUrl.searchParams.set('state', state);
    authorizeUrl.searchParams.set('nonce', nonce);
    authorizeUrl.searchParams.set('code_challenge', challenge);
    authorizeUrl.searchParams.set('code_challenge_method', 'S256');
    return authorizeUrl.href;
  }

  async function handleAuthorizationCallback(callbackUrlValue: string): Promise<OAuthTokenSet> {
    let callbackUrl: URL;
    try {
      callbackUrl = new URL(callbackUrlValue);
    } catch {
      throw new OAuthPkceError('callback_parameters_invalid', 'Callback URL is invalid.');
    }

    const expectedRedirect = new URL(config.redirectUri);
    if (callbackUrl.origin !== expectedRedirect.origin
      || callbackUrl.pathname !== expectedRedirect.pathname
      || callbackUrl.hash) {
      throw new OAuthPkceError('callback_redirect_mismatch', 'Callback URL does not match the configured redirect URI.');
    }

    const state = exactlyOneParameter(callbackUrl.searchParams, 'state');
    const rawPending = dependencies.storage.getItem(config.storageKey);
    if (rawPending === null) {
      throw new OAuthPkceError('authorization_transaction_missing', 'No pending authorization transaction exists.');
    }

    let pending: PendingAuthorization;
    try {
      pending = parsePending(rawPending);
    } catch (error) {
      clearPendingAuthorization();
      throw error;
    }

    if (pending.clientId !== config.clientId || pending.redirectUri !== config.redirectUri) {
      clearPendingAuthorization();
      throw new OAuthPkceError('authorization_transaction_invalid', 'Authorization transaction belongs to another client.');
    }

    const age = now() - pending.createdAt;
    if (age < 0 || age > config.maxTransactionAgeMs) {
      clearPendingAuthorization();
      throw new OAuthPkceError('authorization_transaction_expired', 'Authorization transaction has expired.');
    }

    if (!constantTimeEqual(state, pending.state)) {
      throw new OAuthPkceError('callback_state_mismatch', 'Callback state does not match the authorization transaction.');
    }

    // Consume the state before handling an OAuth error or sending the code so
    // neither the callback nor its authorization code can be replayed.
    clearPendingAuthorization();

    const oauthErrors = callbackUrl.searchParams.getAll('error');
    if (oauthErrors.length > 0) {
      if (oauthErrors.length !== 1 || !oauthErrors[0]) {
        throw new OAuthPkceError('callback_parameters_invalid', 'Callback contains invalid OAuth error parameters.');
      }
      throw new OAuthPkceError('authorization_server_error', `Authorization server returned ${oauthErrors[0]}.`);
    }

    const code = exactlyOneParameter(callbackUrl.searchParams, 'code');
    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: config.clientId,
      code,
      redirect_uri: config.redirectUri,
      code_verifier: pending.verifier,
    }).toString();

    let response: OAuthFetchResponse;
    try {
      response = await dependencies.fetch(config.tokenEndpoint, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body,
        credentials: 'omit',
        redirect: 'error',
      });
    } catch {
      throw new OAuthPkceError('token_exchange_failed', 'Token endpoint request failed.');
    }

    if (!response.ok) {
      throw new OAuthPkceError('token_exchange_failed', `Token endpoint returned HTTP ${response.status}.`);
    }

    let tokenResponse: unknown;
    try {
      tokenResponse = await response.json();
    } catch {
      throw new OAuthPkceError('token_response_invalid', 'Token endpoint did not return valid JSON.');
    }
    if (!isRecord(tokenResponse)) {
      throw new OAuthPkceError('token_response_invalid', 'Token response must be an object.');
    }

    const accessToken = requireString(tokenResponse, 'access_token');
    const idToken = requireString(tokenResponse, 'id_token');
    if (tokenResponse.token_type !== 'Bearer') {
      throw new OAuthPkceError('token_response_invalid', 'Token response token_type must be Bearer.');
    }
    if (tokenResponse.expires_in !== undefined
      && (typeof tokenResponse.expires_in !== 'number'
        || !Number.isSafeInteger(tokenResponse.expires_in)
        || tokenResponse.expires_in <= 0)) {
      throw new OAuthPkceError('token_response_invalid', 'Token response expires_in is invalid.');
    }

    validateTokenClaims(idToken, accessToken, pending.nonce, config);

    const result: OAuthTokenSet = {
      accessToken,
      idToken,
      tokenType: 'Bearer',
      ...(typeof tokenResponse.expires_in === 'number' ? { expiresIn: tokenResponse.expires_in } : {}),
    };
    return Object.freeze(result);
  }

  return Object.freeze({
    createAuthorizationUrl,
    handleAuthorizationCallback,
    clearPendingAuthorization,
  });
}
