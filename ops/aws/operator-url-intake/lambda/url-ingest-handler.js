"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.handler = exports.SafeIngestError = void 0;
exports.parseBoundedPositiveInteger = parseBoundedPositiveInteger;
exports.dailyQuotaWindow = dailyQuotaWindow;
exports.isPublicIp = isPublicIp;
exports.validateTargetUrl = validateTargetUrl;
exports.resolvePublicAddresses = resolvePublicAddresses;
exports.isAllowedContentType = isAllowedContentType;
exports.validateResponseMetadata = validateResponseMetadata;
exports.resolveRedirectTarget = resolveRedirectTarget;
exports.sameIpAddress = sameIpAddress;
exports.pinnedRequestOptions = pinnedRequestOptions;
exports.fetchPublicText = fetchPublicText;
exports.createHandler = createHandler;
const node_crypto_1 = require("node:crypto");
const node_dns_1 = require("node:dns");
const http = __importStar(require("node:http"));
const https = __importStar(require("node:https"));
const node_net_1 = require("node:net");
const client_dynamodb_1 = require("@aws-sdk/client-dynamodb");
const ALLOWED_CONTENT_TYPES = new Set([
    'application/xhtml+xml',
    'text/html',
    'text/plain',
]);
const BLOCKED_HOST_SUFFIXES = ['.home', '.internal', '.lan', '.local', '.localhost'];
const BLOCKED_HOSTS = new Set([
    'instance-data.ec2.internal',
    'localhost',
    'metadata.azure.internal',
    'metadata.google.internal',
]);
const HIDDEN_HTML_TAGS = new Set(['noscript', 'script', 'style', 'svg', 'template']);
const HTML_BREAK_TAGS = new Set([
    'article', 'aside', 'blockquote', 'br', 'div', 'footer', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'header', 'li', 'main', 'nav', 'p', 'section', 'table',
    'td', 'th', 'tr',
]);
const HTML_VOID_TAGS = new Set([
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta',
    'param', 'source', 'track', 'wbr',
]);
const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);
const DEFAULT_FETCH_TIMEOUT_MS = 8_000;
const DEFAULT_MAX_CONTENT_BYTES = 1_000_000;
const DEFAULT_MAX_EXTRACTED_TEXT_CHARS = 24_000;
const DEFAULT_MAX_REDIRECTS = 3;
const DEFAULT_MAX_REQUEST_BYTES = 4_096;
const DEFAULT_SUBJECT_REQUESTS_PER_DAY = 3;
const MAX_HTML_DEPTH = 256;
const MAX_DNS_ADDRESSES = 16;
const MAX_PRIMARY_REGIONS = 64;
const MAX_URL_CHARACTERS = 2_048;
const USER_AGENT = 'HUB_Optimus-Operator-URL-Intake/0.1 (+https://huboptimus.dev/operator/)';
class SafeIngestError extends Error {
    code;
    statusCode;
    publicMessage;
    constructor(code, statusCode, publicMessage) {
        super(code);
        this.code = code;
        this.statusCode = statusCode;
        this.publicMessage = publicMessage;
        this.name = 'SafeIngestError';
    }
}
exports.SafeIngestError = SafeIngestError;
class CandidateConnectionError extends Error {
    timedOut;
    constructor(timedOut) {
        super(timedOut ? 'candidate_timeout' : 'candidate_failed');
        this.timedOut = timedOut;
    }
}
function parseBoundedPositiveInteger(value, fallback, maximum) {
    if (value === undefined || !/^\d+$/.test(value)) {
        return fallback;
    }
    const parsed = Number(value);
    return Number.isSafeInteger(parsed) && parsed > 0 && parsed <= maximum ? parsed : fallback;
}
function dailyQuotaWindow(nowMs = Date.now()) {
    const dayIndex = Math.floor(nowMs / 86_400_000);
    return {
        day: new Date(dayIndex * 86_400_000).toISOString().slice(0, 10),
        // DynamoDB TTL deletion is asynchronous. Keep one grace day; a new UTC
        // date always uses a different key, so stale items cannot consume quota.
        expiresAt: (dayIndex + 2) * 86_400,
    };
}
function normalizedHostname(url) {
    return url.hostname.replace(/^\[|\]$/g, '').replace(/\.$/, '').toLowerCase();
}
function ipv4Octets(address) {
    return (0, node_net_1.isIP)(address) === 4 ? address.split('.').map(Number) : undefined;
}
function ipv6Bytes(address) {
    if ((0, node_net_1.isIP)(address) !== 6) {
        return undefined;
    }
    let value = address.toLowerCase();
    const embeddedIpv4 = value.match(/(\d+\.\d+\.\d+\.\d+)$/)?.[1];
    if (embeddedIpv4 !== undefined) {
        const octets = ipv4Octets(embeddedIpv4);
        if (octets === undefined) {
            return undefined;
        }
        const high = ((octets[0] << 8) | octets[1]).toString(16);
        const low = ((octets[2] << 8) | octets[3]).toString(16);
        value = `${value.slice(0, -embeddedIpv4.length)}${high}:${low}`;
    }
    const halves = value.split('::');
    if (halves.length > 2) {
        return undefined;
    }
    const left = halves[0] === '' ? [] : halves[0].split(':');
    const right = halves.length === 1 || halves[1] === '' ? [] : halves[1].split(':');
    const missing = 8 - left.length - right.length;
    if ((halves.length === 1 && missing !== 0) || (halves.length === 2 && missing < 1)) {
        return undefined;
    }
    const groups = [...left, ...Array(missing).fill('0'), ...right];
    if (groups.length !== 8) {
        return undefined;
    }
    const bytes = [];
    for (const group of groups) {
        if (!/^[0-9a-f]{1,4}$/.test(group)) {
            return undefined;
        }
        const parsed = Number.parseInt(group, 16);
        bytes.push(parsed >> 8, parsed & 0xff);
    }
    return bytes;
}
function hasIpv6Prefix(addressBytes, prefixAddress, prefixLength) {
    const prefixBytes = ipv6Bytes(prefixAddress);
    if (prefixBytes === undefined || prefixLength < 0 || prefixLength > 128) {
        return false;
    }
    const completeBytes = Math.floor(prefixLength / 8);
    for (let index = 0; index < completeBytes; index += 1) {
        if (addressBytes[index] !== prefixBytes[index]) {
            return false;
        }
    }
    const remainingBits = prefixLength % 8;
    if (remainingBits === 0) {
        return true;
    }
    const mask = (0xff << (8 - remainingBits)) & 0xff;
    return (addressBytes[completeBytes] & mask) === (prefixBytes[completeBytes] & mask);
}
function isPublicIpv4(address) {
    const octets = ipv4Octets(address);
    if (octets === undefined) {
        return false;
    }
    const [a, b, c] = octets;
    return !(a === 0
        || a === 10
        || a === 127
        || a >= 224
        || (a === 100 && b >= 64 && b <= 127)
        || (a === 169 && b === 254)
        || (a === 172 && b >= 16 && b <= 31)
        || (a === 192 && b === 0 && c === 0)
        || (a === 192 && b === 0 && c === 2)
        || (a === 192 && b === 88 && c === 99)
        || (a === 192 && b === 168)
        || (a === 198 && (b === 18 || b === 19))
        || (a === 198 && b === 51 && c === 100)
        || (a === 203 && b === 0 && c === 113));
}
function isPublicIpv6(address) {
    const bytes = ipv6Bytes(address);
    if (bytes === undefined) {
        return false;
    }
    const globallyRoutablePrefix = (bytes[0] & 0xe0) === 0x20;
    const isatapInterface = (bytes[8] === 0x00 || bytes[8] === 0x02)
        && bytes[9] === 0x00
        && bytes[10] === 0x5e
        && bytes[11] === 0xfe;
    if (!globallyRoutablePrefix || isatapInterface) {
        return false;
    }
    // IANA marks 2001::/23 as non-global unless a more-specific allocation
    // explicitly says otherwise. Fail closed for that block and allow only the
    // currently global exceptions that are useful as ordinary destinations.
    if (hasIpv6Prefix(bytes, '2001::', 23)) {
        return hasIpv6Prefix(bytes, '2001:1::1', 128)
            || hasIpv6Prefix(bytes, '2001:1::2', 128)
            || hasIpv6Prefix(bytes, '2001:1::3', 128)
            || hasIpv6Prefix(bytes, '2001:3::', 32)
            || hasIpv6Prefix(bytes, '2001:4:112::', 48)
            || hasIpv6Prefix(bytes, '2001:20::', 28)
            || hasIpv6Prefix(bytes, '2001:30::', 28);
    }
    // IANA special-purpose ranges that are not globally reachable (or whose
    // global reachability is explicitly indeterminate) are not valid fetch
    // targets. This includes benchmarking, documentation, and transition space.
    if (hasIpv6Prefix(bytes, '2001:db8::', 32)
        || hasIpv6Prefix(bytes, '2002::', 16)
        || hasIpv6Prefix(bytes, '3fff::', 20)) {
        return false;
    }
    return true;
}
function isPublicIp(address) {
    const family = (0, node_net_1.isIP)(address);
    return family === 4 ? isPublicIpv4(address) : family === 6 ? isPublicIpv6(address) : false;
}
function intakeError(code, statusCode, publicMessage) {
    return new SafeIngestError(code, statusCode, publicMessage);
}
function validateTargetUrl(rawUrl) {
    if (typeof rawUrl !== 'string' || rawUrl.length === 0) {
        throw intakeError('invalid_url', 400, 'URL is required.');
    }
    if (rawUrl.length > MAX_URL_CHARACTERS) {
        throw intakeError('url_too_long', 414, 'URL exceeds maximum allowed length.');
    }
    if ([...rawUrl].some((character) => {
        const codePoint = character.codePointAt(0) ?? 0;
        return codePoint <= 0x20 || codePoint === 0x7f;
    })) {
        throw intakeError('invalid_url', 400, 'URL must not contain raw spaces or control characters.');
    }
    if (!/^[\x21-\x7e]+$/.test(rawUrl)) {
        throw intakeError('unsupported_url_iri', 400, 'Unicode IRIs are not supported; use an IDNA hostname and percent-encode non-ASCII text.');
    }
    let target;
    try {
        target = new URL(rawUrl);
    }
    catch {
        throw intakeError('invalid_url', 400, 'URL could not be parsed.');
    }
    if (target.protocol !== 'http:' && target.protocol !== 'https:') {
        throw intakeError('unsupported_url_scheme', 400, 'Only http and https URLs are allowed.');
    }
    if (target.username !== '' || target.password !== '') {
        throw intakeError('unsupported_url_credentials', 400, 'URLs with credentials are not allowed.');
    }
    if (target.port !== '') {
        throw intakeError('unsupported_url_port', 400, 'Only default HTTP/HTTPS ports are allowed.');
    }
    const hostname = normalizedHostname(target);
    if (hostname === '' || hostname.includes('%')) {
        throw intakeError('invalid_url_host', 400, 'URL host is missing or malformed.');
    }
    if (BLOCKED_HOSTS.has(hostname)
        || BLOCKED_HOST_SUFFIXES.some((suffix) => hostname.endsWith(suffix))) {
        throw intakeError('blocked_url_host', 400, 'URL host is not public.');
    }
    if ((0, node_net_1.isIP)(hostname) !== 0 && !isPublicIp(hostname)) {
        throw intakeError('blocked_url_host', 400, 'URL host is not public.');
    }
    return target;
}
const systemLookup = async (hostname) => node_dns_1.promises.lookup(hostname, {
    all: true,
    verbatim: true,
});
async function resolvePublicAddresses(hostname, lookup = systemLookup) {
    if ((0, node_net_1.isIP)(hostname) !== 0) {
        if (!isPublicIp(hostname)) {
            throw intakeError('blocked_url_host', 400, 'URL host is not public.');
        }
        return [{ address: hostname, family: (0, node_net_1.isIP)(hostname) }];
    }
    let addresses;
    try {
        addresses = await lookup(hostname);
    }
    catch {
        throw intakeError('unresolvable_url_host', 400, 'URL host could not be resolved.');
    }
    if (addresses.length === 0) {
        throw intakeError('unresolvable_url_host', 400, 'URL host could not be resolved.');
    }
    if (addresses.some(({ address, family }) => (family !== 4 && family !== 6) || !isPublicIp(address))) {
        throw intakeError('blocked_url_host', 400, 'URL host resolves to a non-public address.');
    }
    const unique = new Map(addresses.map((entry) => [`${entry.family}:${entry.address}`, entry]));
    if (unique.size > MAX_DNS_ADDRESSES) {
        throw intakeError('unresolvable_url_host', 400, 'URL host returned too many addresses.');
    }
    return [...unique.values()].sort((left, right) => left.family - right.family
        || left.address.localeCompare(right.address));
}
function isAllowedContentType(value) {
    if (typeof value !== 'string') {
        return false;
    }
    return ALLOWED_CONTENT_TYPES.has(value.split(';', 1)[0].trim().toLowerCase());
}
function headerValues(headers, name) {
    const direct = Object.entries(headers).find(([key]) => key.toLowerCase() === name.toLowerCase())?.[1];
    if (direct === undefined) {
        return [];
    }
    return Array.isArray(direct) ? direct.map(String) : [String(direct)];
}
function rawHeaderValues(response) {
    const result = {};
    for (let index = 0; index < response.rawHeaders.length; index += 2) {
        const name = response.rawHeaders[index].toLowerCase();
        const value = response.rawHeaders[index + 1];
        (result[name] ??= []).push(value);
    }
    return result;
}
function validateResponseMetadata(statusCode, headers) {
    if (statusCode !== 200 || headerValues(headers, 'content-range').length > 0) {
        throw intakeError('url_fetch_failed', 502, 'URL fetch returned an unsupported status.');
    }
    const contentEncodingValues = headerValues(headers, 'content-encoding');
    if (contentEncodingValues.length > 1
        || (contentEncodingValues.length === 1
            && !['', 'identity'].includes(contentEncodingValues[0].trim().toLowerCase()))) {
        throw intakeError('unsupported_content_encoding', 415, 'Unsupported content encoding.');
    }
    const contentTypeValues = headerValues(headers, 'content-type');
    if (contentTypeValues.length !== 1 || !isAllowedContentType(contentTypeValues[0])) {
        throw intakeError('unsupported_content_type', 415, 'Source Content-Type is malformed or unsupported.');
    }
    const contentLengthValues = headerValues(headers, 'content-length');
    const transferEncodingValues = headerValues(headers, 'transfer-encoding');
    if (contentLengthValues.length > 1 || transferEncodingValues.length > 1) {
        throw intakeError('url_fetch_failed', 502, 'URL response framing headers are ambiguous.');
    }
    let declaredLength;
    if (contentLengthValues.length === 1) {
        const rawLength = contentLengthValues[0].trim();
        if (!/^\d{1,20}$/.test(rawLength) || !Number.isSafeInteger(Number(rawLength))) {
            throw intakeError('url_fetch_failed', 502, 'URL response Content-Length is invalid.');
        }
        declaredLength = Number(rawLength);
    }
    if (transferEncodingValues.length === 1
        && (transferEncodingValues[0].trim().toLowerCase() !== 'chunked' || declaredLength !== undefined)) {
        throw intakeError('url_fetch_failed', 502, 'URL response transfer framing is unsupported.');
    }
    return { contentType: contentTypeValues[0], declaredLength };
}
function resolveRedirectTarget(from, location, redirectCount) {
    if (redirectCount >= DEFAULT_MAX_REDIRECTS) {
        throw intakeError('too_many_redirects', 508, 'URL exceeded maximum redirect limit.');
    }
    if (location.trim() === '') {
        throw intakeError('redirect_without_location', 502, 'URL redirect must include one Location header.');
    }
    if (!/^[\x21-\x7e]+$/.test(location)) {
        throw intakeError('unsupported_url_iri', 400, 'Redirect location must be an ASCII URI.');
    }
    let next;
    try {
        next = new URL(location, from);
    }
    catch {
        throw intakeError('invalid_url', 400, 'Redirect URL could not be parsed.');
    }
    const validated = validateTargetUrl(next.href);
    if (from.protocol === 'https:' && validated.protocol !== 'https:') {
        throw intakeError('url_fetch_failed', 502, 'HTTPS sources may not redirect to an unencrypted URL.');
    }
    return validated;
}
function remainingMilliseconds(deadline) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) {
        throw intakeError('url_fetch_timeout', 504, 'URL fetch timed out.');
    }
    return remaining;
}
function withDeadline(promise, deadline) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(intakeError('url_fetch_timeout', 504, 'URL fetch timed out.')), remainingMilliseconds(deadline));
        promise.then((value) => {
            clearTimeout(timer);
            resolve(value);
        }, (error) => {
            clearTimeout(timer);
            reject(error);
        });
    });
}
function sameIpAddress(left, right) {
    if (left === undefined) {
        return false;
    }
    if (left === right) {
        return true;
    }
    const leftBytes = ipv6Bytes(left);
    const rightIpv4 = ipv4Octets(right);
    if (leftBytes !== undefined
        && rightIpv4 !== undefined
        && leftBytes.slice(0, 10).every((value) => value === 0)
        && leftBytes[10] === 0xff
        && leftBytes[11] === 0xff) {
        return leftBytes.slice(12).every((value, index) => value === rightIpv4[index]);
    }
    const rightBytes = ipv6Bytes(right);
    return leftBytes !== undefined
        && rightBytes !== undefined
        && leftBytes.every((value, index) => value === rightBytes[index]);
}
function collectResponse(response, maxContentBytes) {
    return new Promise((resolve, reject) => {
        let metadata;
        try {
            metadata = validateResponseMetadata(response.statusCode ?? 0, rawHeaderValues(response));
        }
        catch (error) {
            response.destroy();
            reject(error);
            return;
        }
        let settled = false;
        let totalBytes = 0;
        const chunks = [];
        const fail = (error) => {
            if (!settled) {
                settled = true;
                reject(error);
            }
        };
        const finish = (truncated) => {
            if (settled) {
                return;
            }
            settled = true;
            resolve({
                body: Buffer.concat(chunks, Math.min(totalBytes, maxContentBytes)).subarray(0, maxContentBytes),
                contentType: metadata.contentType,
                truncated,
            });
        };
        response.on('data', (chunk) => {
            const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
            const remaining = maxContentBytes + 1 - totalBytes;
            if (remaining > 0) {
                chunks.push(buffer.subarray(0, remaining));
            }
            totalBytes += buffer.length;
            if (totalBytes > maxContentBytes) {
                finish(true);
                setImmediate(() => response.destroy());
            }
        });
        response.on('end', () => {
            if (metadata.declaredLength !== undefined && totalBytes !== metadata.declaredLength) {
                fail(intakeError('url_fetch_failed', 502, 'URL response ended before its declared length.'));
                return;
            }
            finish(false);
        });
        response.on('error', (error) => {
            if (!settled) {
                fail(error instanceof SafeIngestError
                    ? error
                    : intakeError('url_fetch_failed', 502, 'URL response could not be read.'));
            }
        });
    });
}
function pinnedRequestOptions(target, address) {
    return {
        // Disable connection pooling so every hop creates a fresh socket and the
        // peer-address check always runs, including after redirects.
        agent: false,
        family: address.family,
        headers: {
            accept: 'text/html, text/plain, application/xhtml+xml;q=0.9',
            'accept-encoding': 'identity',
            host: target.host,
            'user-agent': USER_AGENT,
        },
        hostname: address.address,
        method: 'GET',
        path: `${target.pathname}${target.search}`,
        port: target.protocol === 'https:' ? 443 : 80,
        protocol: target.protocol,
        servername: (0, node_net_1.isIP)(normalizedHostname(target)) === 0 ? normalizedHostname(target) : undefined,
    };
}
function requestPinnedAddress(target, address, timeoutMs, maxContentBytes) {
    const transport = target.protocol === 'https:' ? https : http;
    const options = pinnedRequestOptions(target, address);
    return new Promise((resolve, reject) => {
        let settled = false;
        const finishReject = (error) => {
            if (!settled) {
                settled = true;
                reject(error instanceof SafeIngestError || error instanceof CandidateConnectionError
                    ? error
                    : new CandidateConnectionError(false));
            }
        };
        const request = transport.request(options, (response) => {
            const status = response.statusCode ?? 0;
            const headers = rawHeaderValues(response);
            if (REDIRECT_STATUSES.has(status)) {
                const locations = headerValues(headers, 'location');
                response.destroy();
                if (locations.length !== 1 || locations[0].trim() === '') {
                    finishReject(intakeError('redirect_without_location', 502, 'URL redirect must include exactly one non-empty Location header.'));
                    return;
                }
                if (!settled) {
                    settled = true;
                    resolve({ kind: 'redirect', location: locations[0].trim(), status });
                }
                return;
            }
            collectResponse(response, maxContentBytes).then((document) => {
                if (!settled) {
                    settled = true;
                    resolve({ kind: 'document', document });
                }
            }, finishReject);
        });
        const timer = setTimeout(() => request.destroy(new CandidateConnectionError(true)), timeoutMs);
        request.on('close', () => clearTimeout(timer));
        request.on('socket', (socket) => {
            socket.once('connect', () => {
                if (!sameIpAddress(socket.remoteAddress, address.address)) {
                    request.destroy(new CandidateConnectionError(false));
                }
            });
        });
        request.on('error', finishReject);
        request.end();
    });
}
async function requestValidatedHop(target, deadline, maxContentBytes) {
    const addresses = await withDeadline(resolvePublicAddresses(normalizedHostname(target)), deadline);
    let sawTimeout = false;
    for (let index = 0; index < addresses.length; index += 1) {
        const remaining = remainingMilliseconds(deadline);
        const candidateBudget = Math.max(1, Math.floor(remaining / (addresses.length - index)));
        try {
            return await requestPinnedAddress(target, addresses[index], candidateBudget, maxContentBytes);
        }
        catch (error) {
            if (error instanceof SafeIngestError) {
                throw error;
            }
            sawTimeout ||= error instanceof CandidateConnectionError && error.timedOut;
        }
    }
    if (Date.now() >= deadline || sawTimeout) {
        throw intakeError('url_fetch_timeout', 504, 'URL fetch timed out.');
    }
    throw intakeError('url_fetch_failed', 502, 'URL fetch failed.');
}
function decodeEntities(text) {
    const named = {
        amp: '&', apos: "'", gt: '>', lt: '<', nbsp: ' ', quot: '"',
    };
    return text.replace(/&(#(?:x[0-9a-f]+|\d+)|[a-z]+);/gi, (entity, value) => {
        if (value.startsWith('#')) {
            const hexadecimal = value[1]?.toLowerCase() === 'x';
            const number = Number.parseInt(value.slice(hexadecimal ? 2 : 1), hexadecimal ? 16 : 10);
            return Number.isInteger(number) && number > 0 && number <= 0x10ffff
                && !(number >= 0xd800 && number <= 0xdfff)
                ? String.fromCodePoint(number)
                : entity;
        }
        return named[value.toLowerCase()] ?? entity;
    });
}
function cleanExtractedText(raw, maxCharacters) {
    const lines = [];
    const seen = new Set();
    const normalized = raw.replace(/\u00a0/g, ' ').replace(/[ \t\r\f\v]+/g, ' ');
    for (const rawLine of normalized.split('\n')) {
        const line = rawLine.trim();
        const key = line.toLowerCase();
        if (line !== '' && !seen.has(key)) {
            seen.add(key);
            lines.push(line);
        }
    }
    const fullText = lines.join('\n');
    if (fullText.length <= maxCharacters) {
        return { text: fullText, truncated: false };
    }
    return { text: `${fullText.slice(0, maxCharacters).trimEnd()}…`, truncated: true };
}
function findTagEnd(html, start) {
    let quote;
    for (let index = start; index < html.length; index += 1) {
        const character = html[index];
        if (quote !== undefined) {
            if (character === quote) {
                quote = undefined;
            }
        }
        else if (character === '"' || character === "'") {
            quote = character;
        }
        else if (character === '>') {
            return index;
        }
    }
    return -1;
}
function extractHtmlText(html, maxCharacters) {
    const visible = [];
    const titleParts = [];
    const stack = [];
    let hiddenDepth = 0;
    let primaryRegions = 0;
    let structuralLimit = false;
    let cursor = 0;
    const appendText = (raw) => {
        if (hiddenDepth > 0 || raw === '') {
            return;
        }
        const decoded = decodeEntities(raw);
        visible.push(decoded);
        if (stack.includes('title')) {
            titleParts.push(decoded);
        }
    };
    while (cursor < html.length) {
        const open = html.indexOf('<', cursor);
        if (open < 0) {
            appendText(html.slice(cursor));
            break;
        }
        appendText(html.slice(cursor, open));
        if (html.startsWith('<!--', open)) {
            const endComment = html.indexOf('-->', open + 4);
            cursor = endComment < 0 ? html.length : endComment + 3;
            continue;
        }
        const close = findTagEnd(html, open + 1);
        if (close < 0) {
            structuralLimit = true;
            break;
        }
        const rawTag = html.slice(open + 1, close).trim();
        const closing = rawTag.startsWith('/');
        const name = rawTag.replace(/^\//, '').match(/^([A-Za-z][A-Za-z0-9:-]*)/)?.[1].toLowerCase();
        cursor = close + 1;
        if (name === undefined || rawTag.startsWith('!') || rawTag.startsWith('?')) {
            continue;
        }
        if (HTML_BREAK_TAGS.has(name)) {
            visible.push('\n');
        }
        if (closing) {
            const matchingIndex = stack.lastIndexOf(name);
            if (matchingIndex >= 0) {
                const removed = stack.splice(matchingIndex);
                hiddenDepth -= removed.filter((tag) => HIDDEN_HTML_TAGS.has(tag)).length;
            }
            continue;
        }
        if (name === 'main' || name === 'article') {
            primaryRegions += 1;
            if (primaryRegions > MAX_PRIMARY_REGIONS) {
                structuralLimit = true;
                break;
            }
        }
        if (!HTML_VOID_TAGS.has(name) && !/\/$/.test(rawTag)) {
            stack.push(name);
            if (HIDDEN_HTML_TAGS.has(name)) {
                hiddenDepth += 1;
            }
            if (stack.length > MAX_HTML_DEPTH) {
                structuralLimit = true;
                break;
            }
        }
    }
    const cleaned = cleanExtractedText(visible.join(''), maxCharacters);
    const cleanedTitle = cleanExtractedText(titleParts.join(''), maxCharacters);
    return {
        text: cleaned.text,
        title: cleanedTitle.text === '' ? null : cleanedTitle.text,
        truncated: structuralLimit || cleaned.truncated || cleanedTitle.truncated,
    };
}
function parseContentType(contentType) {
    if ([...contentType].some((character) => {
        const codePoint = character.codePointAt(0) ?? 0;
        return codePoint < 0x20 || codePoint === 0x7f;
    })) {
        throw intakeError('unsupported_content_type', 415, 'Source Content-Type is malformed.');
    }
    const parts = contentType.split(';');
    const mediaType = parts.shift()?.trim().toLowerCase() ?? '';
    if (!ALLOWED_CONTENT_TYPES.has(mediaType)) {
        throw intakeError('unsupported_content_type', 415, 'Source Content-Type is unsupported.');
    }
    const charsetValues = parts
        .map((part) => part.trim().match(/^charset\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s]+))$/i))
        .filter((match) => match !== null)
        .map((match) => (match[1] ?? match[2] ?? match[3]).trim());
    if (charsetValues.length > 1 || charsetValues.some((value) => value === '')) {
        throw intakeError('unsupported_content_type', 415, 'Source Content-Type charset is ambiguous.');
    }
    return { mediaType, charset: charsetValues[0] ?? 'utf-8' };
}
function extractDocument(body, contentType, maxCharacters) {
    const parsed = parseContentType(contentType);
    let decoded;
    try {
        decoded = new TextDecoder(parsed.charset, { fatal: true }).decode(body);
    }
    catch {
        throw intakeError('unsupported_content_type', 415, 'Source bytes are not valid for the declared text encoding.');
    }
    if (parsed.mediaType === 'text/plain') {
        const cleaned = cleanExtractedText(decoded, maxCharacters);
        return { text: cleaned.text, title: null, truncated: cleaned.truncated };
    }
    return extractHtmlText(decoded, maxCharacters);
}
async function fetchPublicText(target, submittedUrl = target.href) {
    const timeoutMs = parseBoundedPositiveInteger(process.env.FETCH_TIMEOUT_MS, DEFAULT_FETCH_TIMEOUT_MS, 10_000);
    const maxContentBytes = parseBoundedPositiveInteger(process.env.MAX_CONTENT_BYTES, DEFAULT_MAX_CONTENT_BYTES, DEFAULT_MAX_CONTENT_BYTES);
    const maxTextCharacters = parseBoundedPositiveInteger(process.env.MAX_EXTRACTED_TEXT_CHARS, DEFAULT_MAX_EXTRACTED_TEXT_CHARS, DEFAULT_MAX_EXTRACTED_TEXT_CHARS);
    const maxRedirects = parseBoundedPositiveInteger(process.env.MAX_REDIRECTS, DEFAULT_MAX_REDIRECTS, DEFAULT_MAX_REDIRECTS);
    const deadline = Date.now() + timeoutMs;
    const redirects = [];
    let current = target;
    while (true) {
        remainingMilliseconds(deadline);
        const hop = await requestValidatedHop(current, deadline, maxContentBytes);
        if (hop.kind === 'redirect') {
            if (redirects.length >= maxRedirects) {
                throw intakeError('too_many_redirects', 508, 'URL exceeded maximum redirect limit.');
            }
            const next = resolveRedirectTarget(current, hop.location, redirects.length);
            redirects.push({ from: current.href, to: next.href, status: hop.status });
            current = next;
            continue;
        }
        const extracted = extractDocument(hop.document.body, hop.document.contentType, maxTextCharacters);
        if (extracted.text === '') {
            throw intakeError('empty_extraction', 422, 'URL was fetched but no readable text was extracted.');
        }
        return {
            status: 'ok',
            intake_type: 'controlled_url',
            url: submittedUrl,
            final_url: current.href,
            source_domain: normalizedHostname(current),
            retrieved_at_utc: new Date().toISOString(),
            title: extracted.title,
            text: extracted.text,
            content_type: hop.document.contentType,
            bytes_read: hop.document.body.length,
            truncated: hop.document.truncated || extracted.truncated,
            redirects,
            verification_status: 'unreviewed',
            learning_status: 'candidate-source-not-verified',
            extraction_notes: [
                'Fetched by controlled URL intake.',
                'No cookies, authentication, browser automation, or paywall bypass were used.',
                'Text extraction is source-bound and does not verify truth.',
            ],
        };
    }
}
class DynamoSubjectQuota {
    client = new client_dynamodb_1.DynamoDBClient({});
    async consume(subject) {
        const tableName = process.env.QUOTA_TABLE_NAME;
        if (tableName === undefined || tableName === '') {
            throw new Error('quota_table_missing');
        }
        const limit = parseBoundedPositiveInteger(process.env.PER_SUBJECT_REQUESTS_PER_DAY, DEFAULT_SUBJECT_REQUESTS_PER_DAY, DEFAULT_SUBJECT_REQUESTS_PER_DAY);
        const window = dailyQuotaWindow();
        const subjectHash = (0, node_crypto_1.createHash)('sha256').update(subject).digest('hex');
        try {
            await this.client.send(new client_dynamodb_1.UpdateItemCommand({
                TableName: tableName,
                Key: { subjectDay: { S: `${subjectHash}:${window.day}` } },
                ConditionExpression: 'attribute_not_exists(#count) OR #count < :limit',
                ExpressionAttributeNames: {
                    '#count': 'requestCount',
                    '#expiresAt': 'expiresAt',
                },
                ExpressionAttributeValues: {
                    ':expiresAt': { N: String(window.expiresAt) },
                    ':limit': { N: String(limit) },
                    ':one': { N: '1' },
                },
                UpdateExpression: 'SET #expiresAt = :expiresAt ADD #count :one',
            }));
            return true;
        }
        catch (error) {
            if (error.name === 'ConditionalCheckFailedException') {
                return false;
            }
            throw error;
        }
    }
}
const consoleLogger = {
    info: (entry) => console.info(entry),
    warn: (entry) => console.warn(entry),
};
function jsonResponse(statusCode, payload) {
    return {
        statusCode,
        headers: {
            'cache-control': 'no-store',
            'content-type': 'application/json; charset=utf-8',
        },
        body: JSON.stringify(payload),
    };
}
function authenticatedSubject(event) {
    const claims = event.requestContext?.authorizer?.jwt?.claims;
    const expectedClientId = process.env.EXPECTED_CLIENT_ID;
    const requiredScope = process.env.REQUIRED_SCOPE;
    if (claims === undefined
        || expectedClientId === undefined
        || expectedClientId === ''
        || /\s/.test(expectedClientId)
        || requiredScope === undefined
        || requiredScope === ''
        || /\s/.test(requiredScope)) {
        return undefined;
    }
    const subject = claims.sub;
    const tokenUse = claims.token_use;
    const clientId = claims.client_id;
    const scope = claims.scope;
    const grantedScopes = typeof scope === 'string'
        ? scope.split(/\s+/).filter((entry) => entry !== '')
        : [];
    return typeof subject === 'string'
        && subject !== ''
        && tokenUse === 'access'
        && clientId === expectedClientId
        && grantedScopes.includes(requiredScope)
        ? subject
        : undefined;
}
function createHandler(fetcher = fetchPublicText, quota = new DynamoSubjectQuota(), logger = consoleLogger, options = {}) {
    const maxRequestBytes = options.maxRequestBytes
        ?? parseBoundedPositiveInteger(process.env.MAX_REQUEST_BYTES, DEFAULT_MAX_REQUEST_BYTES, DEFAULT_MAX_REQUEST_BYTES);
    return async (event) => {
        const requestId = event.requestContext?.requestId ?? 'unknown';
        const subject = authenticatedSubject(event);
        if (subject === undefined) {
            logger.warn({ event: 'intake.rejected', requestId, code: 'unauthorized' });
            return jsonResponse(401, { message: 'Unauthorized' });
        }
        const rawBody = event.body ?? '';
        const bodyBuffer = event.isBase64Encoded
            ? Buffer.from(rawBody, 'base64')
            : Buffer.from(rawBody, 'utf8');
        if (bodyBuffer.length > maxRequestBytes) {
            logger.warn({ event: 'intake.rejected', requestId, code: 'request_too_large' });
            return jsonResponse(413, { message: 'Request body too large' });
        }
        let payload;
        try {
            payload = JSON.parse(bodyBuffer.toString('utf8'));
        }
        catch {
            logger.warn({ event: 'intake.rejected', requestId, code: 'invalid_json' });
            return jsonResponse(400, { message: 'Invalid JSON' });
        }
        if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) {
            return jsonResponse(400, { message: 'JSON body must be an object' });
        }
        const payloadKeys = Object.keys(payload);
        const hasExactUrlShape = payloadKeys.length === 1
            && payloadKeys[0] === 'url'
            && Object.prototype.hasOwnProperty.call(payload, 'url');
        const submittedUrl = Object.prototype.hasOwnProperty.call(payload, 'url')
            ? payload.url
            : '';
        const urlFingerprint = typeof submittedUrl === 'string'
            ? (0, node_crypto_1.createHash)('sha256').update(submittedUrl).digest('hex').slice(0, 16)
            : undefined;
        try {
            const quotaAllowed = await quota.consume(subject);
            if (!quotaAllowed) {
                logger.warn({ event: 'intake.rejected', requestId, urlFingerprint, code: 'rate_limited' });
                return jsonResponse(429, { message: 'Too Many Requests' });
            }
        }
        catch {
            logger.warn({ event: 'intake.rejected', requestId, urlFingerprint, code: 'quota_unavailable' });
            return jsonResponse(503, { message: 'Service Unavailable' });
        }
        try {
            if (!hasExactUrlShape || typeof submittedUrl !== 'string') {
                throw intakeError('invalid_url', 400, 'Request body must contain only one string field named url.');
            }
            const target = validateTargetUrl(submittedUrl);
            const result = await fetcher(target, submittedUrl);
            logger.info({
                event: 'intake.succeeded',
                requestId,
                urlFingerprint,
                bytesRead: result.bytes_read,
                redirects: result.redirects.length,
                truncated: result.truncated,
            });
            return jsonResponse(200, result);
        }
        catch (error) {
            const safeError = error instanceof SafeIngestError
                ? error
                : intakeError('url_fetch_unavailable', 503, 'URL intake is temporarily unavailable.');
            logger.warn({
                event: 'intake.rejected',
                requestId,
                urlFingerprint,
                code: safeError.code,
            });
            return jsonResponse(safeError.statusCode, {
                status: 'error',
                error: safeError.code,
                message: safeError.publicMessage,
                url: submittedUrl,
                verification_status: 'unreviewed',
            });
        }
    };
}
exports.handler = createHandler();
