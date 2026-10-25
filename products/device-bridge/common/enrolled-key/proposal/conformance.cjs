'use strict';
// TEST ONLY: decoded fictional values, public software keys, no runtime exports.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const read = name => JSON.parse(fs.readFileSync(path.join(__dirname, name), 'utf8'));
const corpus = read('vectors/resolution_policy.v0_1.json');
const protocol = read('../../native-protocol/vectors/native_signature.v0_1.json');
const results = read('../../native-result/proposal/vectors/native_result_signature.v0_1.json');
const clone = value => structuredClone(value);
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
// Fixed ASCII request shape only. No general JCS/raw JSON parser claims.
const requestCanonical = q => '{' + Object.keys(protocol.request.payload).sort()
  .map(k => JSON.stringify(k) + ':' + JSON.stringify(q[k])).join(',') + '}';
const requestBytes = q => Buffer.from('HUB-RELAY-REQUEST-v0.1\0' + requestCanonical(q));
function publicKey(hex) {
  const sec1 = Buffer.from(hex, 'hex');
  assert.equal(sec1.length, 65); assert.equal(sec1[0], 4);
  crypto.ECDH.convertKey(sec1, 'prime256v1', undefined, undefined, 'uncompressed');
  return crypto.createPublicKey({format: 'jwk', key: {kty: 'EC', crv: 'P-256',
    x: sec1.subarray(1, 33).toString('base64url'), y: sec1.subarray(33).toString('base64url')}});
}
const pin = hex => sha(publicKey(hex).export({format: 'der', type: 'spki'}));
function testKey(scalar) {
  const d = Buffer.from(scalar.toString(16).padStart(64, '0'), 'hex');
  const ec = crypto.createECDH('prime256v1'); ec.setPrivateKey(d);
  const sec1 = ec.getPublicKey(undefined, 'uncompressed');
  const privateKey = crypto.createPrivateKey({format: 'jwk', key: {kty: 'EC', crv: 'P-256',
    d: d.toString('base64url'), x: sec1.subarray(1, 33).toString('base64url'),
    y: sec1.subarray(33).toString('base64url')}});
  return {sec1: sec1.toString('hex'), privateKey};
}
const transport = testKey(3), unknown = testKey(4), offCurve = '04' + '00'.repeat(64);
const base = corpus.baseline, record = base.snapshot.records[0];
const outcome = code => ({status: code ? 'denied' : 'candidate-consistent', code, operationalAuthority: 'absent'});

// Lexical decoded-scenario model only; never an enrolled-key producer or API.
function evaluate(s) {
  const {local:l, pending:p, snapshot:v, presented:u} = s;
  if (v.storeState !== 'available' || [v.epochBefore,v.epochSnapshot,v.epochAfter].includes(null))
    return outcome('StoreUnavailable');
  if (v.epochBefore !== v.epochSnapshot) return outcome('StoreChanged');
  const policy = v.policy;
  if (!policy || policy.validFromTick >= policy.validUntilTick || l.nowTick < policy.validFromTick || l.nowTick >= policy.validUntilTick)
    return outcome('PolicyUnavailable');
  if (policy.policyRef !== l.policyRef || policy.policyDigest !== l.policyDigest) return outcome('PolicyMismatch');
  const selected = v.records.filter(r => ['namespaceRef','accountRef','targetId','profileId'].every(k=>r[k]===l[k]));
  if (selected.length === 0) return outcome('NoRecord');
  if (selected.length !== 1) return outcome('AmbiguousRecord');
  const r = selected[0], q = p.request;
  if (r.authorizerRef !== l.authorizerRef) return outcome('BindingMismatch');
  if (r.policyRef !== l.policyRef) return outcome('PolicyMismatch');
  if (r.lifecycle === 'revoked') return outcome('Revoked');
  if (q.targetId !== l.targetId || q.profileId !== l.profileId) return outcome('BindingMismatch');
  if (q.enrollmentGeneration !== r.enrollmentGeneration || q.brokerStartGeneration !== l.brokerStartGeneration)
    return outcome('GenerationMismatch');
  try {
    for (const hex of [r.brokerSec1Hex,r.approverSec1Hex,u.brokerSec1Hex,u.approverSec1Hex,u.transportSec1Hex]) publicKey(hex);
  } catch { return outcome('KeyMismatch'); }
  const brokerId = sha(Buffer.from(r.brokerSec1Hex,'hex'));
  if (r.brokerKeyId !== brokerId || q.brokerKeyId !== brokerId) return outcome('KeyMismatch');
  const brokerPin = pin(r.brokerSec1Hex), approverPin = pin(r.approverSec1Hex);
  if (r.brokerSec1Hex === r.approverSec1Hex || [brokerPin,approverPin].includes(r.transportSpkiPin)) return outcome('RoleMismatch');
  // Classify all six cross-role substitutions before ordinary key equality checks.
  if (u.brokerSec1Hex === r.approverSec1Hex || pin(u.brokerSec1Hex) === r.transportSpkiPin ||
      u.approverSec1Hex === r.brokerSec1Hex || pin(u.approverSec1Hex) === r.transportSpkiPin ||
      [r.brokerSec1Hex,r.approverSec1Hex].includes(u.transportSec1Hex)) return outcome('RoleMismatch');
  if (u.brokerSec1Hex !== r.brokerSec1Hex || u.approverSec1Hex !== r.approverSec1Hex || pin(u.transportSec1Hex) !== r.transportSpkiPin)
    return outcome('KeyMismatch');
  const pendingBytes = requestBytes(q);
  if (sha(pendingBytes) !== p.requestDigest || !pendingBytes.equals(requestBytes(u.request))) return outcome('PendingMismatch');
  // A changed fixture observation models interleaving; this is not a native transaction.
  if (v.epochAfter !== v.epochBefore) return outcome('StoreChanged');
  return outcome(null);
}

// Fixed recipes with explicit changed-path declarations, never fixture code execution.
const recipes = new Map();
function add(id, changes) { recipes.set(id, changes); }
const R = 'snapshot.records.0.';
add('baseline', []);
add('company-control', [['local.namespaceRef', 'fictional:company'], ['local.accountRef', 'fictional:account-b'],
  ['local.authorizerRef', 'fictional:authorizer-b'], [R+'namespaceRef', 'fictional:company'],
  [R+'accountRef', 'fictional:account-b'], [R+'authorizerRef', 'fictional:authorizer-b']]);
for (const state of ['missing', 'inaccessible', 'corrupt']) add('store-'+state, [['snapshot.storeState', state]]);
for (const field of ['epochBefore', 'epochSnapshot', 'epochAfter']) add('null-'+field.toLowerCase(), [['snapshot.'+field, null]]);
add('epoch-snapshot-changed', [['snapshot.epochSnapshot', '8'.repeat(32)]]);
add('epoch-after-changed', [['snapshot.epochAfter', '8'.repeat(32)]]);
add('epoch-after-old', [['snapshot.epochAfter', '1'.repeat(32)]]);
add('policy-null', [['snapshot.policy', null]]);
add('policy-empty', [['snapshot.policy.validUntilTick', 90]]);
add('policy-reversed', [['snapshot.policy.validUntilTick', 89]]);
for (const [id, tick] of [['before-start',89], ['exact-start',90], ['before-expiry',109], ['exact-expiry',110], ['after-expiry',111]])
  add('policy-'+id, [['local.nowTick', tick]]);
add('policy-ref', [['snapshot.policy.policyRef', 'fictional:policy-b']]);
add('policy-digest', [['snapshot.policy.policyDigest', 'b'.repeat(64)]]);
add('no-records', [['snapshot.records', []]]);
add('duplicate-record', [['snapshot.records', [record, record]]]);
const alternatives = {namespaceRef:'fictional:company', accountRef:'fictional:account-b', targetId:'a'.repeat(32), profileId:'b'.repeat(32)};
for (const [field, value] of Object.entries(alternatives)) {
  add('record-selection-'+field.toLowerCase(), [[R+field, value]]);
  add('local-selection-'+field.toLowerCase(), [['local.'+field, value]]);
  // Presented metadata cannot repair a missing local registration; schema forbids realm fields.
  if (field === 'targetId' || field === 'profileId')
    add('presented-cannot-repair-'+field.toLowerCase(), [['local.'+field, value], ['presented.request.'+field, value]]);
}
const company = {...record, namespaceRef:'fictional:company', accountRef:'fictional:account-b', authorizerRef:'fictional:authorizer-b'};
add('unrelated-company', [['snapshot.records', [record, company]]]);
add('company-cannot-grant-personal', [['snapshot.records', [company]]]);
add('authorizer-binding', [[R+'authorizerRef', 'fictional:authorizer-b']]);
add('record-policy', [[R+'policyRef', 'fictional:policy-b']]);
add('revoked', [[R+'lifecycle', 'revoked']]);
add('revoked-after-lookup', [['snapshot.epochAfter', '9'.repeat(32)]]);
for (const field of ['targetId', 'profileId']) add('pending-binding-'+field.toLowerCase(), [['pending.request.'+field, 'a'.repeat(32)]]);
add('record-generation', [[R+'enrollmentGeneration', 'a'.repeat(32)]]);
add('local-start', [['local.brokerStartGeneration', 'a'.repeat(32)]]);
for (const field of ['enrollmentGeneration', 'brokerStartGeneration']) add('pending-generation-'+field.toLowerCase(), [['pending.request.'+field, 'a'.repeat(32)]]);
const restarted = {...base.pending.request, brokerStartGeneration:'a'.repeat(32)};
add('valid-broker-restart', [['local.brokerStartGeneration', restarted.brokerStartGeneration],
  ['pending.request.brokerStartGeneration', restarted.brokerStartGeneration], ['pending.requestDigest', sha(requestBytes(restarted))],
  ['presented.request.brokerStartGeneration', restarted.brokerStartGeneration]]);
add('record-key-id', [[R+'brokerKeyId', 'a'.repeat(64)]]);
add('pending-key-id', [['pending.request.brokerKeyId', 'a'.repeat(64)]]);
add('pending-digest', [['pending.requestDigest', 'b'.repeat(64)]]);
add('duplicate-signing-role', [[R+'approverSec1Hex', record.brokerSec1Hex]]);
for (const role of ['broker', 'approver']) add('pin-is-'+role, [[R+'transportSpkiPin', pin(record[role+'Sec1Hex'])]]);
const roleKeys = {broker:record.brokerSec1Hex, approver:record.approverSec1Hex, transport:transport.sec1};
for (const to of Object.keys(roleKeys)) for (const from of Object.keys(roleKeys))
  if (to !== from) add('role-'+from+'-into-'+to, [['presented.'+to+'Sec1Hex', roleKeys[from]]]);
for (const role of Object.keys(roleKeys)) add('unknown-'+role, [['presented.'+role+'Sec1Hex', unknown.sec1]]);
for (const role of ['broker', 'approver']) add('changed-record-'+role, [[R+role+'Sec1Hex', unknown.sec1]]);
add('changed-record-pin', [[R+'transportSpkiPin', 'b'.repeat(64)]]);
for (const where of [R+'brokerSec1Hex', R+'approverSec1Hex', ...Object.keys(roleKeys).map(r=>'presented.'+r+'Sec1Hex')])
  add('offcurve-'+where.replaceAll('.', '-').toLowerCase(), [[where, offCurve]]);
for (const field of ['requestId', 'nonce', 'targetId', 'profileId', 'enrollmentGeneration', 'brokerStartGeneration', 'brokerKeyId'])
  add('presented-request-'+field.toLowerCase(), [['presented.request.'+field, 'a'.repeat(base.pending.request[field].length)]]);
const pair = (id, changes) => add('precedence-'+id, changes);
pair('null-before-change', [['snapshot.epochAfter',null], ['snapshot.epochSnapshot','8'.repeat(32)]]);
pair('change-before-policy', [['snapshot.epochSnapshot','8'.repeat(32)], ['snapshot.policy',null]]);
pair('expiry-before-policy-binding', [['local.nowTick',110], ['snapshot.policy.policyRef','fictional:policy-b']]);
pair('policy-before-selection', [['snapshot.policy.policyRef','fictional:policy-b'], ['snapshot.records',[]]]);
pair('no-record-before-pending', [['snapshot.records',[]], ['pending.request.targetId','a'.repeat(32)]]);
pair('ambiguous-before-authorizer', [['snapshot.records',[{...record,authorizerRef:'fictional:authorizer-b'}, {...record,authorizerRef:'fictional:authorizer-b'}]]]);
pair('authorizer-before-record-policy', [[R+'authorizerRef','fictional:authorizer-b'], [R+'policyRef','fictional:policy-b']]);
pair('record-policy-before-revoked', [[R+'policyRef','fictional:policy-b'], [R+'lifecycle','revoked']]);
pair('revoked-before-pending-binding', [[R+'lifecycle','revoked'], ['pending.request.targetId','a'.repeat(32)]]);
pair('pending-binding-before-generation', [['pending.request.targetId','a'.repeat(32)], ['pending.request.enrollmentGeneration','a'.repeat(32)]]);
pair('generation-before-key', [[R+'enrollmentGeneration','a'.repeat(32)], ['presented.transportSec1Hex',offCurve]]);
pair('key-id-before-role', [[R+'brokerKeyId','a'.repeat(64)], ['presented.brokerSec1Hex',record.approverSec1Hex]]);
pair('role-before-key-equality', [['presented.brokerSec1Hex',record.approverSec1Hex], ['presented.transportSec1Hex',unknown.sec1]]);
pair('key-equality-before-pending', [['presented.transportSec1Hex',unknown.sec1], ['presented.request.nonce','a'.repeat(64)]]);
pair('pending-before-final-epoch', [['presented.request.nonce','a'.repeat(64)], ['snapshot.epochAfter','8'.repeat(32)]]);

// Test-only assignment, no JSON-patch language or executable fixture strings.
function scenario(changes) {
  const value = clone(base);
  for (const [name, replacement] of changes) {
    const parts = name.split('.'), leaf = parts.pop();
    let target = value;
    for (const member of parts) target = target[member];
    target[leaf] = clone(replacement);
  }
  // Restore each declared dimension and prove no unrelated input changed.
  const restored = clone(value);
  for (const [name] of changes) {
    const parts = name.split('.'), leaf = parts.pop();
    let target = restored, original = base;
    for (const member of parts) { target = target[member]; original = original[member]; }
    assert.notDeepEqual(target[leaf], original[leaf], name+' must actually change');
    target[leaf] = clone(original[leaf]);
  }
  assert.deepEqual(restored, base, 'exact declared changed-path set');
  return value;
}
test('closed case registry and deterministic public transport fixture', () => {
  assert.equal(new Set(corpus.cases.map(row=>row.id)).size, corpus.cases.length);
  assert.deepEqual(corpus.cases.map(row=>row.id).sort(), [...recipes.keys()].sort());
  assert.equal(base.presented.transportSec1Hex, transport.sec1);
  assert.equal(record.transportSpkiPin, pin(transport.sec1));
  assert.notEqual(record.transportSpkiPin, sha(Buffer.from(transport.sec1,'hex')));
  assert.deepEqual(base.pending.request, protocol.request.payload);
  assert.equal(base.pending.requestDigest, protocol.request.digestSha256Hex);
});
for (const row of corpus.cases) test(row.id, () => {
  assert(recipes.has(row.id), 'live fixed recipe');
  const value = scenario(recipes.get(row.id)), actual = evaluate(value);
  assert.deepEqual(actual, row.expected);
  assert.deepEqual(Object.keys(actual).sort(), ['code','operationalAuthority','status']);
  assert.equal(actual.operationalAuthority, 'absent');
  if (row.id === 'valid-broker-restart') assert.deepEqual(value.snapshot.records, base.snapshot.records);
});
test('public attacker-selected frozen pair passes real math without enrollment', () => {
  const attackerRequest = clone(protocol.request.payload), attackerKey = protocol.keys.broker.publicSec1Hex;
  assert.equal(requestCanonical(attackerRequest), protocol.request.canonicalPayload);
  assert.equal(requestBytes(attackerRequest).toString('hex'), protocol.request.signingBytesHex);
  assert.equal(sha(requestBytes(attackerRequest)), protocol.request.digestSha256Hex);
  assert.equal(sha(Buffer.from(attackerKey,'hex')), attackerRequest.brokerKeyId);
  const result = results.results[0];
  assert.deepEqual(JSON.parse(result.canonicalPayload), result.payload);
  const resultBytes = Buffer.from('HUB-RELAY-RESULT-v0.1\0' + result.canonicalPayload);
  assert.equal(resultBytes.toString('hex'), result.signingBytesHex);
  assert.equal(sha(resultBytes), result.digestSha256Hex);
  assert.equal(result.payload.targetId, attackerRequest.targetId);
  assert.equal(result.payload.profileId, attackerRequest.profileId);
  assert.equal(result.payload.requestDigest, sha(requestBytes(attackerRequest)));
  for (const signature of ['signatureLowSDerHex','signatureHighSDerHex']) {
    assert(crypto.verify('sha256', requestBytes(attackerRequest), publicKey(attackerKey), Buffer.from(protocol.request[signature],'hex')));
    assert(crypto.verify('sha256', resultBytes, publicKey(attackerKey), Buffer.from(result[signature],'hex')));
    for (const wrong of [record.approverSec1Hex, transport.sec1])
      assert.equal(crypto.verify('sha256', requestBytes(attackerRequest), publicKey(wrong), Buffer.from(protocol.request[signature],'hex')), false);
    const approval = protocol.approval;
    assert.deepEqual(approval.payload.request, attackerRequest);
    const approvalBytes = Buffer.from('HUB-RELAY-APPROVAL-v0.1\0' + '{"request":'+requestCanonical(attackerRequest)+',"version":"relay.native-approval.v0.1"}');
    assert.equal(approvalBytes.toString('hex'), approval.signingBytesHex);
    assert.equal(sha(approvalBytes), approval.digestSha256Hex);
    assert(crypto.verify('sha256', approvalBytes, publicKey(record.approverSec1Hex), Buffer.from(approval[signature],'hex')));
    for (const wrong of [attackerKey, transport.sec1])
      assert.equal(crypto.verify('sha256', Buffer.from(approval.signingBytesHex,'hex'), publicKey(wrong), Buffer.from(approval[signature],'hex')), false);
  }
  assert.deepEqual(evaluate({...clone(base), presented:{...clone(base.presented),request:attackerRequest,brokerSec1Hex:attackerKey}}), outcome(null));
  const other = results.counterexamples.otherKey;
  assert.deepEqual(JSON.parse(other.canonicalPayload), other.payload);
  assert.equal(Buffer.from('HUB-RELAY-RESULT-v0.1\0'+other.canonicalPayload).toString('hex'), other.signingBytesHex);
  assert.equal(other.payload.requestDigest, protocol.request.digestSha256Hex);
  for (const signature of ['signatureLowSDerHex','signatureHighSDerHex'])
    assert(crypto.verify('sha256', Buffer.from(other.signingBytesHex,'hex'), publicKey(protocol.keys.approver.publicSec1Hex), Buffer.from(other[signature],'hex')));
  assert.notEqual(sha(Buffer.from(protocol.keys.approver.publicSec1Hex,'hex')), attackerRequest.brokerKeyId);
  assert.equal(crypto.verify('sha256', Buffer.from(other.signingBytesHex,'hex'), publicKey(attackerKey), Buffer.from(other.signatureLowSDerHex,'hex')), false);
});
for (const field of ['nonce','requestId','brokerStartGeneration']) test('signed-changed-'+field, () => {
  const value = scenario([['presented.request.'+field, 'a'.repeat(base.pending.request[field].length)]]);
  const bytes = requestBytes(value.presented.request), signer = testKey(1);
  const signature = crypto.sign('sha256', bytes, signer.privateKey); // Public scalar; kept in memory only.
  assert(crypto.verify('sha256', bytes, publicKey(signer.sec1), signature));
  assert.deepEqual(evaluate(value), outcome('PendingMismatch'));
});
