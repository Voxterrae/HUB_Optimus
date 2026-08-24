import {
  SafeIngestError,
  createHandler,
  dailyQuotaWindow,
  isAllowedContentType,
  isPublicIp,
  resolvePublicAddresses,
  resolveRedirectTarget,
  validateResponseMetadata,
  validateTargetUrl,
} from '../lambda/url-ingest-handler';

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
  test('uses a three-request UTC-day quota window with TTL grace', () => {
    const beforeMidnight = dailyQuotaWindow(Date.parse('2026-08-24T23:59:59.999Z'));
    const afterMidnight = dailyQuotaWindow(Date.parse('2026-08-25T00:00:00.000Z'));

    expect(beforeMidnight.day).toBe('2026-08-24');
    expect(afterMidnight.day).toBe('2026-08-25');
    expect(afterMidnight.expiresAt - beforeMidnight.expiresAt).toBe(86400);
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
    '2001:db8::1',
  ])('rejects non-public IP %s', (address) => {
    expect(isPublicIp(address)).toBe(false);
  });

  test.each(['8.8.8.8', '1.1.1.1', '2606:4700:4700::1111'])('accepts public IP %s', (address) => {
    expect(isPublicIp(address)).toBe(true);
  });

  test('rejects a hostname if any DNS answer is private', async () => {
    await expect(resolvePublicAddresses('example.com', async () => [
      { address: '93.184.216.34', family: 4 },
      { address: '127.0.0.1', family: 4 },
    ])).rejects.toMatchObject({ code: 'blocked_url_host' });
  });

  test('permits at most three validated redirects and blocks an SSRF redirect target', () => {
    const from = new URL('https://example.com/start');
    expect(resolveRedirectTarget(from, '/next', 0).href).toBe('https://example.com/next');
    expect(() => resolveRedirectTarget(from, 'http://169.254.169.254/latest', 0))
      .toThrow(expect.objectContaining({ code: 'blocked_url_host' }));
    expect(() => resolveRedirectTarget(from, '/fourth', 3))
      .toThrow(expect.objectContaining({ code: 'too_many_redirects' }));
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
        authorizer: { jwt: { claims: { sub: 'subject-1' } } },
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
    expect(messages.join('\n')).toContain('urlFingerprint');
    expect(quota.consume).toHaveBeenCalledWith('subject-1');
  });

  test('fails closed without an authenticated subject and enforces per-subject quota', async () => {
    const fetcher = jest.fn();
    const deniedQuota = { consume: jest.fn().mockResolvedValue(false) };
    const logger = { info: jest.fn(), warn: jest.fn() };
    const handler = createHandler(fetcher, deniedQuota, logger);

    const unauthenticated = await handler({
      body: JSON.stringify({ url: 'https://example.com/' }),
      requestContext: { requestId: 'request-unauthenticated' },
    });
    expect(unauthenticated.statusCode).toBe(401);
    expect(deniedQuota.consume).not.toHaveBeenCalled();

    const rateLimited = await handler({
      body: JSON.stringify({ url: 'https://example.com/' }),
      requestContext: {
        requestId: 'request-limited',
        authorizer: { jwt: { claims: { sub: 'subject-2' } } },
      },
    });
    expect(rateLimited.statusCode).toBe(429);
    expect(fetcher).not.toHaveBeenCalled();
  });

  test('rejects an oversized request before fetching', async () => {
    const fetcher = jest.fn();
    const handler = createHandler(fetcher, { consume: jest.fn().mockResolvedValue(true) }, { info: jest.fn(), warn: jest.fn() }, {
      maxRequestBytes: 32,
    });

    const response = await handler({
      body: JSON.stringify({ url: `https://example.com/${'a'.repeat(64)}` }),
      isBase64Encoded: false,
      requestContext: {
        requestId: 'request-2',
        authorizer: { jwt: { claims: { sub: 'subject-3' } } },
      },
    });

    expect(response.statusCode).toBe(413);
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
        authorizer: { jwt: { claims: { sub: 'subject-4' } } },
      },
    });

    expect(response.statusCode).toBe(400);
    expect(JSON.parse(response.body)).toMatchObject({ status: 'error', error: 'invalid_url' });
    expect(fetcher).not.toHaveBeenCalled();
  });
});
