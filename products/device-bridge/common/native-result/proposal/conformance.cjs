'use strict';
// TEST ONLY. Public software scalars, no runtime exports, input boundary or authority.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const vectorPath = path.join(__dirname, 'vectors/native_result_signature.v0_1.json');
const prior = JSON.parse(fs.readFileSync(path.join(__dirname,
  '../../native-protocol/vectors/native_signature.v0_1.json'), 'utf8'));
const fixtureDir = path.join(__dirname, '../../../windows/offline-prototype');
const DOMAIN = 'HUB-RELAY-RESULT-v0.1';
const ORDER = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551n;
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));
const hex32 = value => value.toString(16).padStart(64, '0');

// Closed result profile and existing fixed request ONLY, not universal JCS certification.
// Callers here pass synthetic decoded values; JSON.parse cannot detect duplicate names.
function canonical(value) {
  if (typeof value === 'string') {
    for (const scalar of value) {
      const code = scalar.codePointAt(0);
      assert(code < 0xd800 || code > 0xdfff, 'lone surrogate');
    }
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(k => canonical(k) + ':' + canonical(value[k])).join(',') + '}';
  }
  assert(value === null || (Number.isSafeInteger(value) && value === 60000), 'outside test profile');
  return JSON.stringify(value);
}
const message = (payload, domain = DOMAIN) => Buffer.concat([
  Buffer.from(domain, 'utf8'), Buffer.from([0]), Buffer.from(canonical(payload), 'utf8')]);
const requestDigest = request => sha(message(request, 'HUB-RELAY-REQUEST-v0.1'));

function key(scalar) {
  const d = Buffer.from(hex32(BigInt(scalar)), 'hex');
  const ec = crypto.createECDH('prime256v1');
  ec.setPrivateKey(d);
  const sec1 = ec.getPublicKey(undefined, 'uncompressed');
  const privateKey = crypto.createPrivateKey({format: 'jwk', key: {
    kty: 'EC', crv: 'P-256', d: d.toString('base64url'),
    x: sec1.subarray(1, 33).toString('base64url'), y: sec1.subarray(33).toString('base64url')}});
  return {privateKey, publicKey: crypto.createPublicKey(privateKey), sec1};
}
const broker = key(1), other = key(2);
function publicKey(sec1) {
  assert.equal(sec1.length, 65, 'SEC1 length');
  assert.equal(sec1[0], 4, 'SEC1 uncompressed');
  // OpenSSL curve-point validation; this is synthetic test tooling, not an enrolled-key type.
  crypto.ECDH.convertKey(sec1, 'prime256v1', undefined, undefined, 'uncompressed');
  return crypto.createPublicKey({format: 'jwk', key: {kty: 'EC', crv: 'P-256',
    x: sec1.subarray(1, 33).toString('base64url'), y: sec1.subarray(33).toString('base64url')}});
}
function integer(value) {
  let hex = value.toString(16);
  if (hex.length % 2) hex = '0' + hex;
  let bytes = Buffer.from(hex, 'hex');
  if (bytes[0] & 128) bytes = Buffer.concat([Buffer.from([0]), bytes]);
  return Buffer.concat([Buffer.from([2, bytes.length]), bytes]);
}
function sequence(...parts) {
  const body = Buffer.concat(parts);
  return Buffer.concat([Buffer.from([0x30, body.length]), body]);
}
const der = (r, s) => sequence(integer(r), integer(s));
// Minimal DER inspection for the synthetic math corpus; no raw JSON parser is supplied.
function derParts(bytes) {
  assert(bytes.length >= 8 && bytes.length <= 72);
  assert.equal(bytes[0], 0x30);
  assert.equal(bytes[1], bytes.length - 2);
  let offset = 2;
  const parts = [];
  for (let i = 0; i < 2; i++) {
    assert.equal(bytes[offset++], 2);
    const length = bytes[offset++];
    assert(length >= 1 && length <= 33 && offset + length <= bytes.length);
    const raw = bytes.subarray(offset, offset + length);
    assert(!(raw[0] & 128));
    assert(raw[0] !== 0 || (length > 1 && (raw[1] & 128)));
    const value = BigInt('0x' + raw.toString('hex'));
    assert(value > 0n && value < ORDER);
    parts.push(value);
    offset += length;
  }
  assert.equal(offset, bytes.length);
  return parts;
}
function signed(payload, signer = broker, domain = DOMAIN, bytes = message(payload, domain)) {
  const original = crypto.sign('sha256', bytes, signer.privateKey);
  const [r, s] = derParts(original);
  const low = s > ORDER / 2n ? ORDER - s : s;
  return {payload, canonicalPayload: canonical(payload),
    canonicalUtf8Hex: Buffer.from(canonical(payload), 'utf8').toString('hex'), domain,
    signingBytesHex: bytes.toString('hex'), digestSha256Hex: sha(bytes),
    signatureLowSDerHex: der(r, low).toString('hex'), signatureHighSDerHex: der(r, ORDER - low).toString('hex')};
}
const rawMath = (record, sec1 = broker.sec1, bytes = message(record.payload)) =>
  crypto.verify('sha256', bytes, publicKey(sec1), Buffer.from(record.signatureLowSDerHex, 'hex'));
// A test assertion of independent binding checks, deliberately not exported as product API.
function assertBound(record, expected, sec1 = broker.sec1) {
  const pub = publicKey(sec1);
  assert.equal(sha(sec1), expected.brokerKeyId, 'key binding');
  assert.equal(record.payload.requestDigest, requestDigest(expected), 'request binding');
  assert.equal(record.payload.targetId, expected.targetId, 'target binding');
  assert.equal(record.payload.profileId, expected.profileId, 'profile binding');
  const signature = Buffer.from(record.signatureLowSDerHex, 'hex');
  derParts(signature);
  assert(crypto.verify('sha256', message(record.payload), pub, signature), 'signature math');
}
function payload(state = 'completed', errorCode = null) {
  return {version: 'relay.native-result.v0.1', requestDigest: prior.request.digestSha256Hex,
    targetId: prior.request.payload.targetId, profileId: prior.request.payload.profileId,
    state, errorCode, inventory: state === 'completed' ? {
      windows: {state: 'available', version: 'Windows 11 \u00e9 e\u0301 \ud83d\ude80'},
      powershell7: {state: 'missing', version: null}, node: {state: 'unverified', version: null}} : null};
}
function generate() {
  const results = [signed(payload())];
  for (const [state, codes] of Object.entries({
    denied: ['NOT_AUTHORIZED', 'EXPIRED', 'REVOKED', 'REPLAY', 'BINDING_MISMATCH'],
    failed: ['COLLECTOR_FAILED', 'TIMEOUT', 'OVERFLOW', 'INTERRUPTED'], cancelled: ['CANCELLED']})) {
    for (const code of codes) results.push(signed(payload(state, code)));
  }
  const counterexamples = {};
  for (const [name, value] of [['targetId', '7'.repeat(32)], ['profileId', '8'.repeat(32)],
    ['requestDigest', '9'.repeat(64)]]) counterexamples[name] = signed({...payload(), [name]: value});
  counterexamples.otherKey = signed(payload(), other);
  counterexamples.wrongDomain = signed(payload(), broker, 'HUB-RELAY-REQUEST-v0.1');
  const p = payload();
  counterexamples.missingNul = signed(p, broker, DOMAIN, Buffer.from(DOMAIN + canonical(p)));
  counterexamples.extraNul = signed(p, broker, DOMAIN,
    Buffer.concat([Buffer.from(DOMAIN), Buffer.from([0, 0]), Buffer.from(canonical(p))]));
  counterexamples.doubleHash = signed(p, broker, DOMAIN, Buffer.from(sha(message(p)), 'hex'));
  return {status: 'synthetic-test-only; proposed, not adopted',
    authority: 'NONE: public scalars 1/2, untrusted, not enrolled; no hardware or execution evidence',
    generator: {nodeVersion: process.version, opensslVersion: process.versions.openssl,
      command: 'node products/device-bridge/common/native-result/proposal/conformance.cjs --generate-vectors',
      source: 'conformance.cjs in this directory',
      canonicalizationScope: 'Closed result plus existing fixed request only; no universal JCS certification',
      randomness: 'OpenSSL ECDSA randomness; compare bytes/digests/verification, not identical signature bytes'},
    keys: {broker: {publicTestScalarHex: hex32(1n), publicSec1Hex: broker.sec1.toString('hex')},
      other: {publicTestScalarHex: hex32(2n), publicSec1Hex: other.sec1.toString('hex')}},
    expectedRequest: prior.request.payload, expectedRequestDigest: prior.request.digestSha256Hex,
    results, counterexamples};
}
if (process.argv.includes('--generate-vectors')) {
  assert(!process.env.NODE_TEST_CONTEXT, 'generation is an explicit standalone action');
  const generated = generate();
  fs.mkdirSync(path.dirname(vectorPath), {recursive: true});
  fs.writeFileSync(vectorPath, JSON.stringify(generated, null, 2) + '\n');
  console.log(JSON.stringify({generated: vectorPath, node: process.version, openssl: process.versions.openssl}));
} else {
  const vectors = JSON.parse(fs.readFileSync(vectorPath, 'utf8'));
  console.log(JSON.stringify({node: process.version, openssl: process.versions.openssl,
    scope: 'synthetic math/shape separation only; native parser and T5 pending'}));

  test('frozen canonical bytes, domain NUL, request digest and both S forms', () => {
    assert.equal(requestDigest(vectors.expectedRequest), prior.request.digestSha256Hex);
    assert.equal(message(vectors.expectedRequest, 'HUB-RELAY-REQUEST-v0.1').toString('hex'), prior.request.signingBytesHex);
    assert.equal(vectors.expectedRequestDigest, prior.request.digestSha256Hex);
    assert.equal(vectors.keys.broker.publicSec1Hex, prior.keys.broker.publicSec1Hex);
    assert.equal(sha(broker.sec1), vectors.expectedRequest.brokerKeyId);
    assert.equal(vectors.results.length, 11);
    for (const v of vectors.results) {
      assert.equal(v.canonicalPayload, canonical(v.payload));
      assert.equal(v.canonicalUtf8Hex, Buffer.from(canonical(v.payload)).toString('hex'));
      assert.equal(v.domain, DOMAIN);
      assert.equal(v.signingBytesHex, message(v.payload).toString('hex'));
      assert.equal(v.digestSha256Hex, sha(message(v.payload)));
      for (const signature of [v.signatureLowSDerHex, v.signatureHighSDerHex]) {
        const [, s] = derParts(Buffer.from(signature, 'hex'));
        assert.equal(s <= ORDER / 2n, signature === v.signatureLowSDerHex);
        assert(crypto.verify('sha256', message(v.payload), broker.publicKey, Buffer.from(signature, 'hex')));
      }
      assertBound(v, vectors.expectedRequest);
    }
  });

  test('correctly re-signed target/profile/digest/key counterexamples isolate binding', () => {
    for (const field of ['targetId', 'profileId', 'requestDigest']) {
      const v = vectors.counterexamples[field];
      assert(rawMath(v), field + ' has a valid signature');
      assert.throws(() => assertBound(v, vectors.expectedRequest), new RegExp(
        field === 'targetId' ? 'target binding' : field === 'profileId' ? 'profile binding' : 'request binding'));
    }
    const v = vectors.counterexamples.otherKey;
    assert(rawMath(v, other.sec1));
    assert.throws(() => assertBound(v, vectors.expectedRequest, other.sec1), /key binding/);
    assert.equal(rawMath(v), false);
    const attackerRequest = {...vectors.expectedRequest, brokerKeyId: sha(other.sec1)};
    const attackerResult = signed({...payload(), requestDigest: requestDigest(attackerRequest)}, other);
    assertBound(attackerResult, attackerRequest, other.sec1); // math permits attacker-chosen Q/key; no trust claim
  });

  test('independent expected-request mutations reject even unchanged valid result signatures', () => {
    const v = vectors.results[0];
    for (const field of ['requestId', 'nonce', 'targetId', 'profileId', 'enrollmentGeneration', 'brokerStartGeneration', 'brokerKeyId']) {
      const expected = clone(vectors.expectedRequest);
      expected[field] = 'a'.repeat(expected[field].length);
      assert(rawMath(v));
      assert.notEqual(requestDigest(expected), vectors.expectedRequestDigest);
      assert.throws(() => assertBound(v, expected));
    }
  });

  test('wrong domain, omitted/extra NUL and double-hash signatures reject actual result message', () => {
    for (const name of ['wrongDomain', 'missingNul', 'extraNul', 'doubleHash']) {
      const v = vectors.counterexamples[name];
      assert(rawMath(v, broker.sec1, Buffer.from(v.signingBytesHex, 'hex')), name + ' internally signed');
      assert.equal(rawMath(v), false, name);
      assert.throws(() => assertBound(v, vectors.expectedRequest));
    }
  });

  test('strict DER synthetic matrix and altered signature reject', () => {
    const v = vectors.results[0], bytes = Buffer.from(v.signatureLowSDerHex, 'hex');
    const [r, s] = derParts(bytes);
    const rPart = integer(r);
    const malformed = [Buffer.concat([bytes, Buffer.from([0])]), bytes.subarray(0, -1),
      Buffer.from(hex32(r) + hex32(s), 'hex'), der(0n, s), der(r, 0n), der(ORDER, s), der(r, ORDER),
      sequence(Buffer.from([2, 1, 128]), integer(s)),
      sequence(Buffer.concat([Buffer.from([2, rPart[1] + 1, 0]), rPart.subarray(2)]), integer(s)),
      Buffer.concat([Buffer.from([0x30, 0x81, bytes[1]]), bytes.subarray(2)]),
      Buffer.from([0x30, 6, 2, 0, 2, 2, 1, 1]),
      sequence(Buffer.from([3, 1, 1]), integer(s))];
    for (const bad of malformed) {
      assert.throws(() => derParts(bad));
      assert.equal(crypto.verify('sha256', message(v.payload), broker.publicKey, bad), false);
    }
    const maxDer = der(ORDER - 1n, ORDER - 1n);
    assert.equal(maxDer.length, 72);
    derParts(maxDer); // valid encoding does not imply valid signature
    assert.equal(crypto.verify('sha256', message(v.payload), broker.publicKey, maxDer), false);
    const altered = clone(v);
    altered.payload.inventory.windows.version += '!';
    assert.equal(rawMath(altered), false);
  });

  test('SEC1 encoding/point matrix rejects without inferring enrollment', () => {
    const hybrid = Buffer.from(broker.sec1); hybrid[0] = 6;
    const ec = crypto.createECDH('prime256v1'); ec.setPrivateKey(Buffer.from(hex32(1n), 'hex'));
    for (const bad of [ec.getPublicKey(undefined, 'compressed'), hybrid, broker.sec1.subarray(0, 64),
      Buffer.concat([broker.sec1, Buffer.from([0])]), Buffer.alloc(65),
      Buffer.concat([Buffer.from([4]), Buffer.alloc(64)]), Buffer.from([0])]) {
      assert.throws(() => publicKey(bad));
    }
  });

  test('Unicode spellings/order preserve scalar sequences in scoped canonicalization', () => {
    const p = vectors.results[0].payload;
    const reverse = value => value && typeof value === 'object' && !Array.isArray(value)
      ? Object.fromEntries(Object.entries(value).reverse().map(([k, v]) => [k, reverse(v)])) : value;
    assert.equal(canonical(reverse(p)), canonical(p));
    const escaped = JSON.stringify(p).replaceAll('é', '\\u00e9');
    assert.equal(canonical(JSON.parse(escaped)), canonical(p));
    assert.notEqual(canonical({version: 'é'}), canonical({version: 'e\u0301'}));
    assert.equal(canonical('\u0000\n\ufffe'), '"\\u0000\\n\ufffe"');
    assert.throws(() => canonical('\ud800'));
    assert.equal(Array.from('🚀'.repeat(128)).length, 128);
    // Synthetic byte observations, NOT a native size validator or parser.
    const raw = JSON.stringify({payload: p, signatureDerHex: vectors.results[0].signatureHighSDerHex});
    for (const size of [4095, 4096, 4097]) {
      assert.equal(Buffer.byteLength(raw + ' '.repeat(size - Buffer.byteLength(raw))), size);
    }
  });

  test('unchanged fixture JS refuses native result and keeps real execution disabled', () => {
    const context = vm.createContext({TextEncoder}); // VM is not a security sandbox
    for (const file of ['fixtures.v0_1.js', 'contract.v0_1.js']) {
      vm.runInContext(fs.readFileSync(path.join(fixtureDir, file), 'utf8'), context);
    }
    const fixture = context.HUB_DEVICE_BRIDGE_CONTRACT;
    const native = {payload: vectors.results[0].payload, signatureDerHex: vectors.results[0].signatureLowSDerHex};
    assert.equal(fixture.validateResult(native).ok, false);
    assert.equal(fixture.validateResult(native.payload).ok, false);
    assert.deepEqual(JSON.parse(JSON.stringify(fixture.requestRealExecution())),
      {simulated: true, state: 'denied', code: 'EXECUTOR_DISABLED'});
    assert.equal(context.HUB_DEVICE_BRIDGE_FIXTURES.getFixture('approved').request.schemaVersion, 'fixture.v0.1');
  });
}
