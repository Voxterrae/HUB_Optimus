import { createHash } from 'node:crypto';
import {
  SafeIngestError,
  canaryWindowStatus,
  createHandler,
  canaryQuotaWindow,
  isAllowedContentType,
  isAllowedCanarySubject,
  isPublicIp,
  parseBoundedPositiveInteger,
  pinnedRequestOptions,
  resolvePublicAddresses,
  resolveRedirectTarget,
  sameIpAddress,
  validateResponseMetadata,
  validateTargetUrl,
} from '../lambda/url-ingest-handler';
import { OPERATOR_INTAKE_SCOPE } from '../frontend/pkce-client';
import { canarySecurityBinding } from '../lib/canary-security-binding';

const TEST_CLIENT_ID = 'operator-public-client';
const TEST_REQUIRED_SCOPE = OPERATOR_INTAKE_SCOPE;
const ORIGINAL_EXPECTED_CLIENT_ID = process.env.EXPECTED_CLIENT_ID;
const ORIGINAL_REQUIRED_SCOPE = process.env.REQUIRED_SCOPE;
const ORIGINAL_CANARY_STARTED_AT = process.env.CANARY_STARTED_AT;
const ORIGINAL_CANARY_EXPIRES_AT = process.env.CANARY_EXPIRES_AT;
const ORIGINAL_CANARY_ALLOWED_SUBJECT_SHA256 = process.env.CANARY_ALLOWED_SUBJECT_SHA256;
const ORIGINAL_CANARY_SECURITY_BINDING_SHA256 = process.env.CANARY_SECURITY_BINDING_SHA256;
const ALLOWED_SUBJECT = 'subject-1';

function authenticatedClaims(subject: string): Record<string, string> {
  return {
    sub: subject,
    token_use: 'access',
    client_id: TEST_CLIENT_ID,
    scope: `openid ${TEST_REQUIRED_SCOPE} profile`,
  };
}

beforeAll(() => {
  process.env.EXPECTED_CLIENT_ID = TEST_CLIENT_ID;
  process.env.REQUIRED_SCOPE = TEST_REQUIRED_SCOPE;
  process.env.CANARY_ALLOWED_SUBJECT_SHA256 = createHash('sha256')
    .update(ALLOWED_SUBJECT)
    .digest('hex');
  const startMs = Math.floor((Date.now() - 60_000) / 1_000) * 1_000;
  process.env.CANARY_STARTED_AT = new Date(startMs).toISOString().replace('.000Z', 'Z');
  process.env.CANARY_EXPIRES_AT = new Date(startMs + 60 * 60 * 1_000)
    .toISOString()
    .replace('.000Z', 'Z');
  process.env.CANARY_SECURITY_BINDING_SHA256 = canarySecurityBinding(
    process.env.CANARY_ALLOWED_SUBJECT_SHA256,
    process.env.CANARY_STARTED_AT,
    process.env.CANARY_EXPIRES_AT,
  );
});

afterAll(() => {
  if (ORIGINAL_EXPECTED_CLIENT_ID === undefined) {
    delete process.env.EXPECTED_CLIENT_ID;
  } else {
    process.env.EXPECTED_CLIENT_ID = ORIGINAL_EXPECTED_CLIENT_ID;
  }
  if (ORIGINAL_REQUIRED_SCOPE === undefined) {
    delete process.env.REQUIRED_SCOPE;
  } else {
    process.env.REQUIRED_SCOPE = ORIGINAL_REQUIRED_SCOPE;
  }
  if (ORIGINAL_CANARY_STARTED_AT === undefined) {
    delete process.env.CANARY_STARTED_AT;
  } else {
    process.env.CANARY_STARTED_AT = ORIGINAL_CANARY_STARTED_AT;
  }
  if (ORIGINAL_CANARY_EXPIRES_AT === undefined) {
    delete process.env.CANARY_EXPIRES_AT;
  } else {
    process.env.CANARY_EXPIRES_AT = ORIGINAL_CANARY_EXPIRES_AT;
  }
  if (ORIGINAL_CANARY_ALLOWED_SUBJECT_SHA256 === undefined) {
    delete process.env.CANARY_ALLOWED_SUBJECT_SHA256;
  } else {
    process.env.CANARY_ALLOWED_SUBJECT_SHA256 = ORIGINAL_CANARY_ALLOWED_SUBJECT_SHA256;
  }
  if (ORIGINAL_CANARY_SECURITY_BINDING_SHA256 === undefined) {
    delete process.env.CANARY_SECURITY_BINDING_SHA256;
  } else {
    process.env.CANARY_SECURITY_BINDING_SHA256 = ORIGINAL_CANARY_SECURITY_BINDING_SHA256;
  }
});

describe('URL validation', () => {
  test.each([
    'ftp://example.com/file',
    'file:///etc/passwd',
    'http://user:secret@example.com/',
    'http://localhost/',
    'http://service.internal/',
    'http://metadata.google.internal/',
    'http://127.0.0.1/',
    'http://2130706433/',
    'http://169.254.169.254/latest/meta-data/',
    'http://[::1]/',
    'https://example.com:8443/',
  ])('blocks unsafe target %s', (target) => {
    expect(() => validateTargetUrl(target)).toThrow(SafeIngestError);
  });

  test.each(['http://example.com/path', 'https://8.8.8.8/resource'])('allows a syntactically public target %s', (target) => {
    expect(validateTargetUrl(target).href).toBe(target);
  });

  test('rejects raw Unicode IRIs and URLs longer than 2048 characters', () => {
    expect(() => validateTargetUrl('https://example.com/niño')).toThrow(
      expect.objectContaining({ code: 'unsupported_url_iri' }),
    );
    expect(() => validateTargetUrl(`https://example.com/${'a'.repeat(2030)}`)).toThrow(
      expect.objectContaining({ code: 'url_too_long' }),
    );
  });
});

describe('network and response policy', () => {
  test('enforces one valid private canary window of at most two hours', () => {
    const start = '2026-08-26T12:00:00Z';
    expect(canaryWindowStatus(start, '2026-08-26T14:00:00Z', Date.parse(start)))
      .toEqual({ active: true, code: 'active' });
    expect(canaryWindowStatus(start, '2026-08-26T14:00:01Z', Date.parse(start)))
      .toEqual({ active: false, code: 'invalid' });
    expect(canaryWindowStatus(start, '2026-08-26T14:00:00Z', Date.parse(start) - 1))
      .toEqual({ active: false, code: 'not_started' });
    expect(canaryWindowStatus(start, '2026-08-26T14:00:00Z', Date.parse('2026-08-26T14:00:00Z')))
      .toEqual({ active: false, code: 'expired' });
    expect(canaryWindowStatus(undefined, undefined, Date.parse(start)))
      .toEqual({ active: false, code: 'invalid' });
  });

  test('uses one three-attempt quota key even when the canary crosses UTC midnight', () => {
    const window = canaryQuotaWindow(
      '2026-08-24T23:30:00Z',
      '2026-08-25T01:30:00Z',
    );

    expect(window.key).toMatch(/^canary:[0-9a-f]{64}$/);
    expect(window.expiresAt).toBe(Date.parse('2026-08-26T01:30:00Z') / 1_000);
    expect(() => canaryQuotaWindow(
      '2026-08-24T23:30:00Z',
      '2026-08-25T01:30:01Z',
    )).toThrow('invalid_canary_quota_window');
  });

  test('allows only the one subject whose SHA-256 was approved', () => {
    const approvedHash = createHash('sha256')
      .update(ALLOWED_SUBJECT)
      .digest('hex');
    expect(isAllowedCanarySubject(ALLOWED_SUBJECT, approvedHash)).toBe(true);
    expect(isAllowedCanarySubject('subject-other', approvedHash)).toBe(false);
    expect(isAllowedCanarySubject(ALLOWED_SUBJECT, undefined)).toBe(false);
  });

  test.each([
    '0.0.0.0',
    '10.0.0.1',
    '100.64.0.1',
    '127.0.0.1',
    '169.254.170.2',
    '172.16.0.1',
    '192.168.1.1',
    '224.0.0.1',
    '::1',
    '::ffff:127.0.0.1',
    'fc00::1',
    'fe80::1',
    'ff02::1',
    '2001::1',
    '2001:1::4',
    '2001:2::1',
    '2001:10::1',
    '2001:db8::1',
    '2002:0808:0808::1',
    '3fff::1',
    '5f00::1',
  ])('rejects non-public IP %s', (address) => {
    expect(isPublicIp(address)).toBe(false);
  });

  test.each([
    '8.8.8.8',
    '1.1.1.1',
    '2001:1::1',
    '2001:3::1',
    '2001:4:112::1',
    '2001:20::1',
    '2001:30::1',
    '2606:4700:4700::1111',
    '2620:4f:8000::1',
  ])('accepts public IP %s', (address) => {
    expect(isPublicIp(address)).toBe(true);
  });

  test('rejects a hostname if any DNS answer is private', async () => {
    await expect(resolvePublicAddresses('example.com', async () => [
      { address: '93.184.216.34', family: 4 },
      { address: '127.0.0.1', family: 4 },
    ])).rejects.toMatchObject({ code: 'blocked_url_host' });
  });

  test('caps the number of distinct DNS answers', async () => {
    await expect(resolvePublicAddresses('example.com', async () => Array.from(
      { length: 17 },
      (_value, index) => ({ address: `8.8.8.${index + 1}`, family: 4 }),
    ))).rejects.toMatchObject({ code: 'unresolvable_url_host' });
  });

  test('permits at most three validated redirects and blocks an SSRF redirect target', () => {
    const from = new URL('https://example.com/start');
    expect(resolveRedirectTarget(from, '/next', 0).href).toBe('https://example.com/next');
    expect(() => resolveRedirectTarget(from, 'http://169.254.169.254/latest', 0))
      .toThrow(expect.objectContaining({ code: 'blocked_url_host' }));
    expect(() => resolveRedirectTarget(from, 'http://example.com/downgrade', 0))
      .toThrow(expect.objectContaining({ code: 'url_fetch_failed' }));
    expect(() => resolveRedirectTarget(from, '/fourth', 3))
      .toThrow(expect.objectContaining({ code: 'too_many_redirects' }));
  });

  test('pins Host and TLS SNI to a fresh socket and checks canonical peers', () => {
    const options = pinnedRequestOptions(
      new URL('https://example.com/report?q=1'),
      { address: '93.184.216.34', family: 4 },
    );
    expect(options).toMatchObject({
      agent: false,
      family: 4,
      hostname: '93.184.216.34',
      path: '/report?q=1',
      port: 443,
      protocol: 'https:',
      servername: 'example.com',
      headers: expect.objectContaining({ host: 'example.com' }),
    });
    expect(sameIpAddress('93.184.216.34', '93.184.216.34')).toBe(true);
    expect(sameIpAddress('::ffff:93.184.216.34', '93.184.216.34')).toBe(true);
    expect(sameIpAddress('93.184.216.35', '93.184.216.34')).toBe(false);
  });

  test('falls back instead of accepting configuration above hard maxima', () => {
    expect(parseBoundedPositiveInteger('3', 1, 3)).toBe(3);
    expect(parseBoundedPositiveInteger('4', 1, 3)).toBe(1);
    expect(parseBoundedPositiveInteger('999999999999999999999', 8_000, 10_000)).toBe(8_000);
  });

  test('enforces content type and declared response size', () => {
    expect(isAllowedContentType('text/html; charset=utf-8')).toBe(true);
    expect(isAllowedContentType('application/pdf')).toBe(false);
    expect(() => validateResponseMetadata(200, { 'content-type': 'application/pdf' }))
      .toThrow(expect.objectContaining({ code: 'unsupported_content_type' }));
    expect(() => validateResponseMetadata(200, {
      'content-type': 'text/plain',
      'content-encoding': 'gzip',
    })).toThrow(expect.objectContaining({ code: 'unsupported_content_encoding' }));
  });
});

describe('HTTP API handler privacy', () => {
  test('blocks authenticated work outside the approved canary window before quota or fetch', async () => {
    const fetcher = jest.fn();
    const quota = { consume: jest.fn().mockResolvedValue(true) };
    const handler = createHandler(
      fetcher,
      quota,
      { info: jest.fn(), warn: jest.fn() },
      { now: () => Date.parse('2026-08-26T14:00:00Z') },
    );
    const previousStart = process.env.CANARY_STARTED_AT;
    const previousExpiry = process.env.CANARY_EXPIRES_AT;
    const previousBinding = process.env.CANARY_SECURITY_BINDING_SHA256;
    process.env.CANARY_STARTED_AT = '2026-08-26T12:00:00Z';
    process.env.CANARY_EXPIRES_AT = '2026-08-26T14:00:00Z';
    process.env.CANARY_SECURITY_BINDING_SHA256 = canarySecurityBinding(
      process.env.CANARY_ALLOWED_SUBJECT_SHA256 ?? '',
      process.env.CANARY_STARTED_AT,
      process.env.CANARY_EXPIRES_AT,
    );
    try {
      const response = await handler({
        body: JSON.stringify({ url: 'https://example.com/' }),
        requestContext: {
          requestId: 'request-expired-canary',
          authorizer: { jwt: { claims: authenticatedClaims(ALLOWED_SUBJECT) } },
        },
      });
      expect(response.statusCode).toBe(503);
      expect(JSON.parse(response.body)).toEqual({ message: 'Private canary is not active' });
      expect(quota.consume).not.toHaveBeenCalled();
      expect(fetcher).not.toHaveBeenCalled();
    } finally {
      if (previousStart === undefined) {
        delete process.env.CANARY_STARTED_AT;
      } else {
        process.env.CANARY_STARTED_AT = previousStart;
      }
      if (previousExpiry === undefined) {
        delete process.env.CANARY_EXPIRES_AT;
      } else {
        process.env.CANARY_EXPIRES_AT = previousExpiry;
      }
      if (previousBinding === undefined) {
        delete process.env.CANARY_SECURITY_BINDING_SHA256;
      } else {
        process.env.CANARY_SECURITY_BINDING_SHA256 = previousBinding;
      }
    }
  });

  test('fails closed before quota or fetch when the subject/window binding differs', async () => {
    const fetcher = jest.fn();
    const quota = { consume: jest.fn().mockResolvedValue(true) };
    const handler = createHandler(fetcher, quota, { info: jest.fn(), warn: jest.fn() });
    const previousBinding = process.env.CANARY_SECURITY_BINDING_SHA256;
    process.env.CANARY_SECURITY_BINDING_SHA256 = 'f'.repeat(64);
    try {
      const response = await handler({
        body: JSON.stringify({ url: 'https://example.com/' }),
        requestContext: {
          requestId: 'request-invalid-binding',
          authorizer: { jwt: { claims: authenticatedClaims(ALLOWED_SUBJECT) } },
        },
      });
      expect(response.statusCode).toBe(503);
      expect(quota.consume).not.toHaveBeenCalled();
      expect(fetcher).not.toHaveBeenCalled();
    } finally {
      if (previousBinding === undefined) {
        delete process.env.CANARY_SECURITY_BINDING_SHA256;
      } else {
        process.env.CANARY_SECURITY_BINDING_SHA256 = previousBinding;
      }
    }
  });

  test('returns the canonical intake schema but never logs content or the complete URL', async () => {
    const messages: string[] = [];
    const logger = {
      info: (entry: unknown) => messages.push(JSON.stringify(entry)),
      warn: (entry: unknown) => messages.push(JSON.stringify(entry)),
    };
    const quota = { consume: jest.fn().mockResolvedValue(true) };
    const handler = createHandler(async (target) => ({
      status: 'ok',
      intake_type: 'controlled_url',
      url: target.href,
      final_url: target.href,
      source_domain: target.hostname,
      retrieved_at_utc: '2026-08-24T00:00:00.000Z',
      title: null,
      text: 'PRIVATE PAGE CONTENT',
      content_type: 'text/plain',
      bytes_read: 20,
      truncated: false,
      redirects: [],
      verification_status: 'unreviewed',
      learning_status: 'candidate-source-not-verified',
      extraction_notes: ['Controlled fetch.'],
    }), quota, logger);

    const response = await handler({
      body: JSON.stringify({ url: 'https://example.com/private/path?token=secret' }),
      isBase64Encoded: false,
      requestContext: {
        requestId: 'request-1',
        authorizer: { jwt: { claims: authenticatedClaims(ALLOWED_SUBJECT) } },
      },
    });

    expect(response.statusCode).toBe(200);
    expect(JSON.parse(response.body)).toMatchObject({
      status: 'ok',
      intake_type: 'controlled_url',
      text: 'PRIVATE PAGE CONTENT',
      bytes_read: 20,
      verification_status: 'unreviewed',
    });
    expect(messages.join('\n')).not.toContain('PRIVATE PAGE CONTENT');
    expect(messages.join('\n')).not.toContain('https://example.com/private/path?token=secret');
    expect(messages.join('\n')).not.toContain('subject-1');
    expect(messages.join('\n')).not.toContain(TEST_CLIENT_ID);
    expect(messages.join('\n')).not.toContain(TEST_REQUIRED_SCOPE);
    expect(messages.join('\n')).toContain('urlFingerprint');
    expect(quota.consume).toHaveBeenCalledTimes(1);
  });

  test.each([
    ['missing claims', undefined],
    ['missing subject', { ...authenticatedClaims('subject'), sub: '' }],
    ['ID token', { ...authenticatedClaims('subject'), token_use: 'id' }],
    ['wrong client', { ...authenticatedClaims('subject'), client_id: `${TEST_CLIENT_ID}-other` }],
    ['missing required scope', { ...authenticatedClaims('subject'), scope: 'openid profile' }],
    ['scope prefix collision', { ...authenticatedClaims('subject'), scope: `${TEST_REQUIRED_SCOPE}.admin` }],
    ['scope suffix collision', { ...authenticatedClaims('subject'), scope: `extra.${TEST_REQUIRED_SCOPE}` }],
    ['non-string scope', { ...authenticatedClaims('subject'), scope: [TEST_REQUIRED_SCOPE] }],
  ])('fails closed for %s', async (_label, claims) => {
    const fetcher = jest.fn();
    const quota = { consume: jest.fn().mockResolvedValue(true) };
    const handler = createHandler(fetcher, quota, { info: jest.fn(), warn: jest.fn() });

    const response = await handler({
      body: JSON.stringify({ url: 'https://example.com/' }),
      requestContext: {
        requestId: 'request-unauthorized-claims',
        authorizer: claims === undefined ? undefined : { jwt: { claims } },
      },
    });

    expect(response.statusCode).toBe(401);
    expect(quota.consume).not.toHaveBeenCalled();
    expect(fetcher).not.toHaveBeenCalled();
  });

  test('rejects a valid token from every subject except the one approved for the canary', async () => {
    const fetcher = jest.fn();
    const quota = { consume: jest.fn().mockResolvedValue(true) };
    const handler = createHandler(fetcher, quota, { info: jest.fn(), warn: jest.fn() });

    const response = await handler({
      body: JSON.stringify({ url: 'https://example.com/' }),
      requestContext: {
        requestId: 'request-wrong-canary-user',
        authorizer: { jwt: { claims: authenticatedClaims('subject-other') } },
      },
    });

    expect(response.statusCode).toBe(401);
    expect(quota.consume).not.toHaveBeenCalled();
    expect(fetcher).not.toHaveBeenCalled();
  });

  test('fails closed when the expected client or required scope configuration is absent', async () => {
    const fetcher = jest.fn();
    const quota = { consume: jest.fn().mockResolvedValue(true) };
    const handler = createHandler(fetcher, quota, { info: jest.fn(), warn: jest.fn() });

    let withoutClient;
    let withoutScope;
    try {
      delete process.env.EXPECTED_CLIENT_ID;
      withoutClient = await handler({
        body: JSON.stringify({ url: 'https://example.com/' }),
        requestContext: {
          requestId: 'request-no-client-config',
          authorizer: { jwt: { claims: authenticatedClaims('subject-no-client') } },
        },
      });
      process.env.EXPECTED_CLIENT_ID = TEST_CLIENT_ID;

      delete process.env.REQUIRED_SCOPE;
      withoutScope = await handler({
        body: JSON.stringify({ url: 'https://example.com/' }),
        requestContext: {
          requestId: 'request-no-scope-config',
          authorizer: { jwt: { claims: authenticatedClaims('subject-no-scope') } },
        },
      });
    } finally {
      process.env.EXPECTED_CLIENT_ID = TEST_CLIENT_ID;
      process.env.REQUIRED_SCOPE = TEST_REQUIRED_SCOPE;
    }

    expect(withoutClient?.statusCode).toBe(401);
    expect(withoutScope?.statusCode).toBe(401);
    expect(quota.consume).not.toHaveBeenCalled();
    expect(fetcher).not.toHaveBeenCalled();
  });

  test('enforces the global canary quota after validating all access-token claims', async () => {
    const fetcher = jest.fn();
    const deniedQuota = { consume: jest.fn().mockResolvedValue(false) };
    const logger = { info: jest.fn(), warn: jest.fn() };
    const handler = createHandler(fetcher, deniedQuota, logger);

    const rateLimited = await handler({
      body: JSON.stringify({ url: 'https://example.com/' }),
      requestContext: {
        requestId: 'request-limited',
        authorizer: { jwt: { claims: authenticatedClaims(ALLOWED_SUBJECT) } },
      },
    });
    expect(rateLimited.statusCode).toBe(429);
    expect(deniedQuota.consume).toHaveBeenCalledTimes(1);
    expect(fetcher).not.toHaveBeenCalled();
  });

  test('rejects an oversized request before fetching', async () => {
    const fetcher = jest.fn();
    const quota = { consume: jest.fn().mockResolvedValue(true) };
    const handler = createHandler(fetcher, quota, { info: jest.fn(), warn: jest.fn() }, {
      maxRequestBytes: 32,
    });

    const response = await handler({
      body: JSON.stringify({ url: `https://example.com/${'a'.repeat(64)}` }),
      isBase64Encoded: false,
      requestContext: {
        requestId: 'request-2',
        authorizer: { jwt: { claims: authenticatedClaims(ALLOWED_SUBJECT) } },
      },
    });

    expect(response.statusCode).toBe(413);
    expect(quota.consume).toHaveBeenCalledTimes(1);
    expect(fetcher).not.toHaveBeenCalled();
  });

  test('charges malformed JSON against the same global canary ceiling', async () => {
    const fetcher = jest.fn();
    const quota = { consume: jest.fn().mockResolvedValue(true) };
    const handler = createHandler(fetcher, quota, { info: jest.fn(), warn: jest.fn() });

    const response = await handler({
      body: '{not-json',
      requestContext: {
        requestId: 'request-invalid-json',
        authorizer: { jwt: { claims: authenticatedClaims(ALLOWED_SUBJECT) } },
      },
    });

    expect(response.statusCode).toBe(400);
    expect(quota.consume).toHaveBeenCalledTimes(1);
    expect(fetcher).not.toHaveBeenCalled();
  });

  test('rejects additional request fields instead of turning them into intake context', async () => {
    const fetcher = jest.fn();
    const handler = createHandler(
      fetcher,
      { consume: jest.fn().mockResolvedValue(true) },
      { info: jest.fn(), warn: jest.fn() },
    );

    const response = await handler({
      body: JSON.stringify({ url: 'https://example.com/', context: 'must-not-pass' }),
      requestContext: {
        requestId: 'request-extra-field',
        authorizer: { jwt: { claims: authenticatedClaims(ALLOWED_SUBJECT) } },
      },
    });

    expect(response.statusCode).toBe(400);
    expect(JSON.parse(response.body)).toMatchObject({ status: 'error', error: 'invalid_url' });
    expect(fetcher).not.toHaveBeenCalled();
  });
});
