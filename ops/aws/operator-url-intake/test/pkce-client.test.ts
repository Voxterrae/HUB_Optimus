import { createHash } from 'node:crypto';

import {
  CryptoLike,
  OAuthFetch,
  OAuthPkceConfig,
  OAuthPkceError,
  OPERATOR_INTAKE_SCOPE,
  StorageLike,
  createOAuthPkceClient,
} from '../frontend/pkce-client';

const CONFIG: OAuthPkceConfig = {
  authorizationEndpoint: 'https://auth.example.com/oauth2/authorize',
  tokenEndpoint: 'https://auth.example.com/oauth2/token',
  clientId: 'operator-public-client',
  redirectUri: 'https://huboptimus.dev/operator/',
  scope: `openid ${OPERATOR_INTAKE_SCOPE}`,
};

class MemoryStorage implements StorageLike {
  public readonly values = new Map<string, string>();
  public readonly writes: Array<{ key: string; value: string }> = [];
  public readonly removals: string[] = [];

  public getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  public setItem(key: string, value: string): void {
    this.values.set(key, value);
    this.writes.push({ key, value });
  }

  public removeItem(key: string): void {
    this.values.delete(key);
    this.removals.push(key);
  }
}

function deterministicCrypto(): CryptoLike {
  let randomCall = 0;
  return {
    getRandomValues(array) {
      randomCall += 1;
      for (let index = 0; index < array.length; index += 1) {
        array[index] = (randomCall * 53 + index * 17) & 255;
      }
      return array;
    },
    subtle: {
      async digest(algorithm, data) {
        expect(algorithm).toBe('SHA-256');
        const digest = createHash('sha256').update(data).digest();
        const result = new Uint8Array(digest.length);
        result.set(digest);
        return result.buffer;
      },
    },
  };
}

function encodeJwtPart(value: unknown): string {
  return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url');
}

function jwt(payload: Record<string, unknown>): string {
  return `${encodeJwtPart({ alg: 'RS256', typ: 'JWT' })}.${encodeJwtPart(payload)}.test-signature`;
}

interface PendingFixture {
  readonly verifier: string;
  readonly state: string;
  readonly nonce: string;
  readonly createdAt: number;
}

function storedPending(storage: MemoryStorage): PendingFixture {
  expect(storage.values.size).toBe(1);
  return JSON.parse([...storage.values.values()][0]) as PendingFixture;
}

function tokenResponse(
  pending: PendingFixture,
  overrides: {
    id?: Record<string, unknown>;
    access?: Record<string, unknown>;
    response?: Record<string, unknown>;
  } = {},
): Record<string, unknown> {
  const id = {
    token_use: 'id',
    nonce: pending.nonce,
    aud: CONFIG.clientId,
    ...overrides.id,
  };
  const access = {
    token_use: 'access',
    client_id: CONFIG.clientId,
    scope: `openid ${OPERATOR_INTAKE_SCOPE}`,
    ...overrides.access,
  };
  return {
    access_token: jwt(access),
    id_token: jwt(id),
    token_type: 'Bearer',
    expires_in: 900,
    ...overrides.response,
  };
}

function successfulResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => body,
  };
}

function makeHarness(now = Date.parse('2026-08-25T10:00:00.000Z')) {
  const storage = new MemoryStorage();
  let responseBody: unknown = {};
  const fetchMock = jest.fn<ReturnType<OAuthFetch>, Parameters<OAuthFetch>>(
    async () => successfulResponse(responseBody),
  );
  const client = createOAuthPkceClient(CONFIG, {
    crypto: deterministicCrypto(),
    storage,
    fetch: fetchMock,
    now: () => now,
  });
  return {
    client,
    storage,
    fetchMock,
    setResponseBody: (body: unknown) => {
      responseBody = body;
    },
  };
}

async function begin(harness: ReturnType<typeof makeHarness>) {
  const authorizationUrl = new URL(await harness.client.createAuthorizationUrl());
  const pending = storedPending(harness.storage);
  return { authorizationUrl, pending };
}

function callbackUrl(state: string, code = 'one-time-code'): string {
  const callback = new URL(CONFIG.redirectUri);
  callback.searchParams.set('code', code);
  callback.searchParams.set('state', state);
  return callback.href;
}

describe('OAuth authorization request with PKCE S256', () => {
  test('creates strong verifier, challenge, state and nonce and stores only the pending transaction', async () => {
    const harness = makeHarness();
    const { authorizationUrl, pending } = await begin(harness);

    expect(authorizationUrl.origin + authorizationUrl.pathname).toBe(CONFIG.authorizationEndpoint);
    expect(Object.fromEntries(authorizationUrl.searchParams)).toMatchObject({
      response_type: 'code',
      client_id: CONFIG.clientId,
      redirect_uri: CONFIG.redirectUri,
      scope: CONFIG.scope,
      state: pending.state,
      nonce: pending.nonce,
      code_challenge_method: 'S256',
    });
    expect(pending.verifier).toMatch(/^[A-Za-z0-9_-]{43}$/u);
    expect(pending.state).toMatch(/^[A-Za-z0-9_-]{43}$/u);
    expect(pending.nonce).toMatch(/^[A-Za-z0-9_-]{43}$/u);
    expect(new Set([pending.verifier, pending.state, pending.nonce]).size).toBe(3);
    expect(authorizationUrl.searchParams.get('code_challenge')).toBe(
      createHash('sha256').update(pending.verifier).digest('base64url'),
    );
    expect(harness.storage.writes).toHaveLength(1);
    expect(harness.storage.writes[0].value).not.toContain('token');
    expect(harness.fetchMock).not.toHaveBeenCalled();
  });

  test.each([
    [{ ...CONFIG, authorizationEndpoint: 'http://auth.example.com/authorize' }, 'invalid_configuration'],
    [{ ...CONFIG, redirectUri: 'https://huboptimus.dev/callback?unsafe=1' }, 'invalid_configuration'],
    [{ ...CONFIG, scope: OPERATOR_INTAKE_SCOPE }, 'invalid_configuration'],
    [{ ...CONFIG, scope: 'openid profile' }, 'invalid_configuration'],
  ])('rejects unsafe or incomplete configuration', (config, code) => {
    expect(() => createOAuthPkceClient(config, {
      crypto: deterministicCrypto(),
      storage: new MemoryStorage(),
      fetch: jest.fn() as unknown as OAuthFetch,
    })).toThrow(expect.objectContaining({ code }));
  });
});

describe('authorization callback and token exchange', () => {
  test('checks state exactly, exchanges with form encoding and returns validated tokens only in memory', async () => {
    const harness = makeHarness();
    const { pending } = await begin(harness);
    const response = tokenResponse(pending);
    harness.setResponseBody(response);

    const tokens = await harness.client.handleAuthorizationCallback(
      callbackUrl(pending.state, 'code with + and /'),
    );

    expect(tokens).toEqual({
      accessToken: response.access_token,
      idToken: response.id_token,
      tokenType: 'Bearer',
      expiresIn: 900,
    });
    expect(Object.isFrozen(tokens)).toBe(true);
    expect(harness.fetchMock).toHaveBeenCalledTimes(1);
    const [endpoint, request] = harness.fetchMock.mock.calls[0];
    expect(endpoint).toBe(CONFIG.tokenEndpoint);
    expect(request).toMatchObject({
      method: 'POST',
      credentials: 'omit',
      redirect: 'error',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    expect(Object.fromEntries(new URLSearchParams(request.body))).toEqual({
      grant_type: 'authorization_code',
      client_id: CONFIG.clientId,
      code: 'code with + and /',
      redirect_uri: CONFIG.redirectUri,
      code_verifier: pending.verifier,
    });
    expect(request.body).not.toContain('client_secret');
    expect(harness.storage.values.size).toBe(0);
    expect(JSON.stringify(harness.storage.writes)).not.toContain(String(response.access_token));
    expect(JSON.stringify(harness.storage.writes)).not.toContain(String(response.id_token));
  });

  test('rejects a non-exact state before exchange and leaves the valid transaction available', async () => {
    const harness = makeHarness();
    const { pending } = await begin(harness);

    await expect(harness.client.handleAuthorizationCallback(callbackUrl(`${pending.state}x`)))
      .rejects.toMatchObject({ code: 'callback_state_mismatch' });
    expect(harness.fetchMock).not.toHaveBeenCalled();
    expect(harness.storage.values.size).toBe(1);
  });

  test('rejects duplicate callback parameters and a callback on another redirect path', async () => {
    const harness = makeHarness();
    const { pending } = await begin(harness);
    const duplicate = `${callbackUrl(pending.state)}&state=${encodeURIComponent(pending.state)}`;

    await expect(harness.client.handleAuthorizationCallback(duplicate))
      .rejects.toMatchObject({ code: 'callback_parameters_invalid' });
    await expect(harness.client.handleAuthorizationCallback(
      `https://huboptimus.dev/operator/other?code=x&state=${encodeURIComponent(pending.state)}`,
    )).rejects.toMatchObject({ code: 'callback_redirect_mismatch' });
    expect(harness.fetchMock).not.toHaveBeenCalled();
  });

  test('validates state and consumes the transaction before reporting an OAuth error', async () => {
    const harness = makeHarness();
    const { pending } = await begin(harness);
    const callback = new URL(CONFIG.redirectUri);
    callback.searchParams.set('error', 'access_denied');
    callback.searchParams.set('state', pending.state);

    await expect(harness.client.handleAuthorizationCallback(callback.href))
      .rejects.toMatchObject({ code: 'authorization_server_error' });
    expect(harness.storage.values.size).toBe(0);
    expect(harness.fetchMock).not.toHaveBeenCalled();
  });

  test('expires and removes an old transaction', async () => {
    const storage = new MemoryStorage();
    let clock = Date.parse('2026-08-25T10:00:00.000Z');
    const client = createOAuthPkceClient(CONFIG, {
      crypto: deterministicCrypto(),
      storage,
      fetch: jest.fn() as unknown as OAuthFetch,
      now: () => clock,
    });
    const url = new URL(await client.createAuthorizationUrl());
    clock += 10 * 60 * 1000 + 1;

    await expect(client.handleAuthorizationCallback(callbackUrl(url.searchParams.get('state')!)))
      .rejects.toMatchObject({ code: 'authorization_transaction_expired' });
    expect(storage.values.size).toBe(0);
  });

  test('requires a pending transaction and can explicitly clear one', async () => {
    const harness = makeHarness();
    await expect(harness.client.handleAuthorizationCallback(callbackUrl('a'.repeat(43))))
      .rejects.toMatchObject({ code: 'authorization_transaction_missing' });

    await harness.client.createAuthorizationUrl();
    harness.client.clearPendingAuthorization();
    expect(harness.storage.values.size).toBe(0);
  });

  test('consumes state even when the token endpoint fails and does not expose its response', async () => {
    const harness = makeHarness();
    const { pending } = await begin(harness);
    harness.fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: 'invalid_grant', secret_detail: 'do-not-expose' }),
    });

    await expect(harness.client.handleAuthorizationCallback(callbackUrl(pending.state)))
      .rejects.toEqual(expect.objectContaining({
        code: 'token_exchange_failed',
        message: 'Token endpoint returned HTTP 400.',
      }));
    expect(harness.storage.values.size).toBe(0);
  });
});

describe('local JWT claim gates', () => {
  test.each([
    {
      label: 'ID nonce',
      overrides: { id: { nonce: 'wrong-nonce' } },
      code: 'id_token_nonce_mismatch',
    },
    {
      label: 'ID audience',
      overrides: { id: { aud: 'another-client' } },
      code: 'id_token_audience_mismatch',
    },
    {
      label: 'access token use',
      overrides: { access: { token_use: 'id' } },
      code: 'access_token_use_invalid',
    },
    {
      label: 'access token client',
      overrides: { access: { client_id: 'another-client' } },
      code: 'access_token_client_mismatch',
    },
    {
      label: 'intake scope',
      overrides: { access: { scope: 'openid profile operator/intake-extra' } },
      code: 'access_token_scope_missing',
    },
  ])('rejects a token with invalid $label', async ({ overrides, code }) => {
    const harness = makeHarness();
    const { pending } = await begin(harness);
    harness.setResponseBody(tokenResponse(pending, overrides));

    await expect(harness.client.handleAuthorizationCallback(callbackUrl(pending.state)))
      .rejects.toMatchObject({ code });
    expect(harness.storage.values.size).toBe(0);
  });

  test.each([
    {
      label: 'audience array rather than exact client string',
      overrides: { id: { aud: [CONFIG.clientId] } },
      code: 'id_token_audience_mismatch',
    },
    {
      label: 'malformed JWT',
      overrides: { response: { access_token: 'not-a-jwt' } },
      code: 'jwt_invalid',
    },
    {
      label: 'non-Bearer token type',
      overrides: { response: { token_type: 'bearer' } },
      code: 'token_response_invalid',
    },
    {
      label: 'refresh-only response',
      overrides: { response: { access_token: undefined, refresh_token: 'must-not-be-used' } },
      code: 'token_response_invalid',
    },
  ])('rejects $label', async ({ overrides, code }) => {
    const harness = makeHarness();
    const { pending } = await begin(harness);
    harness.setResponseBody(tokenResponse(pending, overrides));

    await expect(harness.client.handleAuthorizationCallback(callbackUrl(pending.state)))
      .rejects.toMatchObject({ code });
  });

  test('rejects malformed token endpoint JSON', async () => {
    const harness = makeHarness();
    const { pending } = await begin(harness);
    harness.fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError('private response body');
      },
    });

    await expect(harness.client.handleAuthorizationCallback(callbackUrl(pending.state)))
      .rejects.toMatchObject({ code: 'token_response_invalid' });
  });

  test('uses typed, non-secret errors', () => {
    const error = new OAuthPkceError('token_exchange_failed', 'safe message');
    expect(error).toBeInstanceOf(Error);
    expect(error).toMatchObject({ name: 'OAuthPkceError', code: 'token_exchange_failed' });
  });
});
