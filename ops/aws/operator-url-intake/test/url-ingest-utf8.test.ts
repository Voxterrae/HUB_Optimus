import { EventEmitter } from 'node:events';
import { promises as dns } from 'node:dns';
import * as https from 'node:https';
import type { IncomingMessage } from 'node:http';
import { fetchPublicText } from '../lambda/url-ingest-handler';

jest.mock('node:https', () => ({ ...jest.requireActual('node:https'), request: jest.fn() }));
jest.mock('node:dns', () => ({
  ...jest.requireActual('node:dns'),
  promises: { ...jest.requireActual('node:dns').promises, lookup: jest.fn() },
}));

const MAX = 1_000_000;
const ADDRESS = '93.184.216.34';
const priorLimits = [process.env.MAX_CONTENT_BYTES, process.env.MAX_EXTRACTED_TEXT_CHARS];

beforeEach(() => {
  jest.clearAllMocks();
  process.env.MAX_CONTENT_BYTES = String(MAX);
  process.env.MAX_EXTRACTED_TEXT_CHARS = '24000';
  (dns.lookup as unknown as jest.Mock).mockResolvedValue([{ address: ADDRESS, family: 4 }]);
});

afterAll(() => {
  for (const [index, key] of ['MAX_CONTENT_BYTES', 'MAX_EXTRACTED_TEXT_CHARS'].entries()) {
    if (priorLimits[index] === undefined) delete process.env[key];
    else process.env[key] = priorLimits[index];
  }
});

function serve(body: Buffer): void {
  (https.request as unknown as jest.Mock).mockImplementation((
    _options: unknown, callback: (response: IncomingMessage) => void,
  ) => {
    const response = Object.assign(new EventEmitter(), {
      statusCode: 200,
      rawHeaders: ['Content-Type', 'text/plain; charset=utf-8', 'Content-Length', String(body.length)],
      destroy: jest.fn(),
    });
    const request = Object.assign(new EventEmitter(), {
      end: () => {
        const socket = Object.assign(new EventEmitter(), { remoteAddress: ADDRESS });
        request.emit('socket', socket);
        socket.emit('connect');
        callback(response as unknown as IncomingMessage);
        response.emit('data', body);
        response.emit('end');
        request.emit('close');
      },
      destroy: (error: Error) => {
        request.emit('error', error);
        request.emit('close');
      },
    });
    return request;
  });
}

test.each(['é', '€', '😀'])('accepts deliberate byte-cap truncation inside %s', async (character) => {
  serve(Buffer.concat([Buffer.alloc(MAX - 1, 'a'), Buffer.from(character + 'a')]));
  const result = await fetchPublicText(new URL('https://example.org/article'));
  expect(result.truncated).toBe(true);
  expect(result.bytes_read).toBe(MAX);
  expect(result.text).toBe('a'.repeat(24_000) + '…');
  expect(result.verification_status).toBe('unreviewed');
});

test.each([
  Buffer.from([0xc3, 0x28]),
  Buffer.from([0x61, 0xc3]),
  Buffer.concat([Buffer.from([0xc3, 0x28]), Buffer.alloc(MAX, 'a')]),
])('rejects malformed retained bytes or incomplete complete responses', async (body) => {
  serve(body);
  await expect(fetchPublicText(new URL('https://example.org/article')))
    .rejects.toMatchObject({ code: 'unsupported_content_type', statusCode: 415 });
});

test('retains complete valid multibyte text', async () => {
  serve(Buffer.from('Readable é € 😀 text'));
  const result = await fetchPublicText(new URL('https://example.org/article'));
  expect(result.text).toBe('Readable é € 😀 text');
  expect(result.truncated).toBe(false);
});
