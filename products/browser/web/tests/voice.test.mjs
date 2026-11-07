import test from 'node:test';
import assert from 'node:assert/strict';

import { VoiceController } from '../dist/voice.mjs';

function fixture(options = {}) {
  const states = [], texts = [], utterances = [], recognitions = [], checks = [], timers = new Map();
  let nextTimer = 0;
  class Recognition {
    constructor() { this.processLocally = false; this.starts = 0; this.aborts = 0; recognitions.push(this); }
    start() { this.starts++; }
    abort() { this.aborts++; }
    static async available(options) { checks.push(options); return 'available'; }
  }
  const synthesis = {
    voices: [{ name: 'English local', lang: 'en-US', localService: true }],
    getVoices() { return this.voices; },
    speak(utterance) { utterances.push(utterance); },
    cancel() { this.cancelled = (this.cancelled ?? 0) + 1; }
  };
  const voice = new VoiceController({
    synthesis, Recognition, createUtterance: text => ({ text }),
    setTimer: (fn, ms) => { const id = ++nextTimer; timers.set(id, { fn, ms }); return id; },
    clearTimer: id => timers.delete(id), ...options
  });
  return { voice, synthesis, Recognition, states, texts, utterances, recognitions, checks, timers,
    dictation: (lang = 'en-US') => voice.dictate({ lang, onState: state => states.push(state), onText: text => texts.push(text) }),
    speech: (lang = 'en-US', rate = 1) => voice.speak('Safe help', { lang, rate, onState: state => states.push(state) }) };
}

// Break caught: assuming browser globals exist or offering remote-only/other-language voices.
test('imports without browser globals and leaves absent APIs unavailable', async () => {
  assert.equal(typeof VoiceController, 'function');
  const f = fixture({ synthesis: null, Recognition: null, createUtterance: null });
  assert.deepEqual(f.voice.getLocalVoices('en-US'), []);
  assert.equal(await f.voice.availability('en-US'), 'unsupported');
  assert.deepEqual(f.speech(), { started: false, reason: 'unsupported' });
  assert.deepEqual(await f.dictation(), { started: false, reason: 'unsupported' });
});

test('selects only explicitly local matching language voices with exact locale first', () => {
  const f = fixture();
  f.synthesis.voices = [
    { name: 'Remote', lang: 'en-US', localService: false },
    { name: 'Unknown service', lang: 'en-US' },
    { name: 'Spanish', lang: 'es-ES', localService: true },
    { name: 'UK local', lang: 'en-GB', localService: true },
    { name: 'US local', lang: 'en-US', localService: true }
  ];
  assert.deepEqual(f.voice.getLocalVoices('en-US').map(v => v.name), ['US local', 'UK local']);
  assert.deepEqual(f.voice.getLocalVoices('fr-FR'), []);
  assert.deepEqual(f.voice.getLocalVoices('not a language'), []);
  assert.deepEqual(f.speech('fr-FR'), { started: false, reason: 'unavailable' });
  assert.equal(f.utterances.length, 0);
});

// Break caught: default voice/network fallback, unsafe rate, or old utterance callbacks changing new state.
test('speaks using chosen local voice and clamps the supported rate', () => {
  const f = fixture();
  assert.deepEqual(f.speech('en-US', 99), { started: true, reason: 'available' });
  const utterance = f.utterances[0];
  assert.equal(utterance.text, 'Safe help');
  assert.equal(utterance.voice.localService, true);
  assert.equal(utterance.lang, 'en-US');
  assert.equal(utterance.rate, 2);
  utterance.onstart();
  utterance.onend();
  assert.deepEqual(f.states, ['speaking', 'idle']);
  f.speech('en-US', -1);
  assert.equal(f.utterances[1].rate, 0.5);
  f.speech('en-US', NaN);
  assert.equal(f.utterances[2].rate, 1);
});

test('new speech and stop invalidate callbacks from previous utterances', () => {
  const f = fixture();
  f.speech();
  const old = { ...f.utterances[0] };
  old.onstart();
  f.speech();
  const current = { ...f.utterances[1] };
  current.onstart();
  const before = [...f.states];
  old.onend(); old.onerror(); old.onstart();
  assert.deepEqual(f.states, before);
  f.voice.stop();
  assert.equal(f.synthesis.cancelled, 2);
  assert.equal(f.states.at(-1), 'idle');
  const stopped = [...f.states];
  current.onend(); current.onerror(); current.onstart();
  assert.deepEqual(f.states, stopped);
});

test('speech failures return error and disposal suppresses every late callback', async () => {
  const f = fixture();
  f.speech();
  const old = { ...f.utterances[0] };
  f.voice.dispose();
  const before = [...f.states];
  old.onstart(); old.onend(); old.onerror();
  f.voice.stop();
  assert.deepEqual(f.states, before);
  assert.deepEqual(f.speech(), { started: false, reason: 'disposed' });
  assert.deepEqual(await f.dictation(), { started: false, reason: 'disposed' });
  assert.equal(await f.voice.availability('en-US'), 'unavailable');
  const failed = fixture();
  failed.synthesis.speak = () => { throw new Error('speaker unavailable'); };
  assert.deepEqual(failed.speech(), { started: false, reason: 'error' });
  assert.deepEqual(failed.states, ['error']);
});

test('empty speech never invokes browser synthesis', () => {
  const f = fixture();
  assert.deepEqual(f.voice.speak('  ', { lang: 'en-US' }), { started: false, reason: 'empty' });
  assert.equal(f.utterances.length, 0);
});

// Break caught: opening a microphone through an engine that cannot guarantee local processing.
test('requires both processLocally capability and static availability before starting', async () => {
  class LegacyRecognition {
    start() { assert.fail('must not start legacy recognition'); }
    abort() {}
  }
  const missingProperty = fixture({ Recognition: LegacyRecognition });
  LegacyRecognition.available = async () => { assert.fail('must not query unsupported recognition'); };
  assert.equal(await missingProperty.voice.availability('en-US'), 'unsupported');
  assert.deepEqual(await missingProperty.dictation(), { started: false, reason: 'unsupported' });
  class NoAvailability {
    constructor() { this.processLocally = false; }
    start() { assert.fail('must not start unchecked recognition'); }
    abort() {}
  }
  assert.equal(await fixture({ Recognition: NoAvailability }).voice.availability('en-US'), 'unsupported');
});

test('maps local availability statuses without installing or starting any recognition', async () => {
  for (const [browserStatus, expected] of [
    ['available', 'available'], ['downloadable', 'download-required'], ['downloading', 'download-required'],
    ['unavailable', 'unavailable'], ['unexpected', 'unavailable']
  ]) {
    const f = fixture();
    f.Recognition.available = async options => { f.checks.push(options); return browserStatus; };
    f.Recognition.install = () => assert.fail('model installation forbidden');
    assert.equal(await f.voice.availability('en-US'), expected);
    assert.deepEqual(f.checks, [{ langs: ['en-US'], processLocally: true }]);
    assert.equal(f.recognitions[0].starts, 0);
    if (browserStatus !== 'available') {
      assert.deepEqual(await f.dictation(), { started: false, reason: expected });
      assert.equal(f.recognitions.every(rec => rec.starts === 0), true);
    }
  }
});

test('starts only explicitly local finite dictation after actual available result', async () => {
  const f = fixture();
  assert.deepEqual(await f.dictation(), { started: true, reason: 'available' });
  const rec = f.recognitions[0];
  assert.equal(rec.processLocally, true);
  assert.equal(rec.lang, 'en-US');
  assert.equal(rec.continuous, false);
  assert.equal(rec.interimResults, false);
  assert.equal(rec.maxAlternatives, 1);
  assert.equal(rec.starts, 1);
  assert.deepEqual(f.checks, [{ langs: ['en-US'], processLocally: true }]);
  rec.onstart();
  rec.onend();
  assert.deepEqual(f.states, ['listening', 'idle']);
  assert.equal(f.timers.size, 0);
});

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

// Break caught: a non-cooperative availability promise resurrecting a stopped or replaced session.
test('stop cancels pending availability before the microphone can start', async () => {
  const f = fixture(), pending = deferred();
  f.Recognition.available = () => pending.promise;
  const result = f.dictation();
  f.voice.stop();
  const before = [...f.states];
  pending.resolve('available');
  assert.deepEqual(await result, { started: false, reason: 'cancelled' });
  assert.equal(f.recognitions[0].starts, 0);
  assert.deepEqual(f.states, before);
});

test('a language availability check invalidates pending dictation and stale public checks', async () => {
  const f = fixture(), pending = deferred();
  f.Recognition.available = () => pending.promise;
  const dictation = f.dictation();
  const availability = f.voice.availability('es-ES');
  pending.resolve('available');
  assert.deepEqual(await dictation, { started: false, reason: 'cancelled' });
  assert.equal(await availability, 'available');
  assert.equal(f.recognitions.every(rec => rec.starts === 0), true);
  const second = deferred();
  f.Recognition.available = () => second.promise;
  const stale = f.voice.availability('en-US');
  f.voice.stop();
  second.resolve('available');
  assert.equal(await stale, 'unavailable');
});

test('distinguishes permission denial from ordinary availability and startup errors', async () => {
  const denied = fixture();
  denied.Recognition.available = async () => { throw new DOMException('blocked', 'NotAllowedError'); };
  assert.deepEqual(await denied.dictation(), { started: false, reason: 'permission-denied' });
  assert.deepEqual(denied.states, ['permission-denied']);
  const failed = fixture();
  failed.Recognition.prototype.start = () => { throw new Error('device failed'); };
  assert.deepEqual(await failed.dictation(), { started: false, reason: 'error' });
  assert.deepEqual(failed.states, ['error']);
  assert.equal(failed.timers.size, 0);
});

function resultEvent(...results) {
  return { resultIndex: 0, results: results.map(([text, isFinal]) => Object.assign([
    { transcript: text, confidence: 0.9 }
  ], { isFinal })) };
}

// Break caught: interim speech or stale events reaching editable text or executing a command.
test('delivers only final transcript as editable text and never submits a command', async () => {
  const f = fixture();
  await f.dictation();
  const rec = f.recognitions[0];
  rec.onresult(resultEvent(['not final', false]));
  assert.deepEqual(f.texts, []);
  rec.onresult(resultEvent(['open settings', true]));
  assert.deepEqual(f.texts, ['open settings']);
  assert.deepEqual(f.states, []);
  rec.onend();
  assert.deepEqual(f.states, ['idle']);
});

test('stopping dictation aborts hardware and makes captured old handlers inert', async () => {
  const f = fixture();
  await f.dictation();
  const rec = f.recognitions[0], old = { ...rec };
  rec.onstart();
  f.voice.stop();
  assert.equal(rec.aborts, 1);
  assert.equal(f.timers.size, 0);
  const before = [...f.states];
  old.onresult(resultEvent(['must be ignored', true]));
  old.onstart(); old.onerror({ error: 'not-allowed' }); old.onend();
  assert.deepEqual(f.texts, []);
  assert.deepEqual(f.states, before);
});

test('dictation timeout aborts at 30 seconds even if browser never fires start', async () => {
  const f = fixture();
  await f.dictation();
  const timer = [...f.timers.values()][0];
  assert.equal(timer.ms, 30_000);
  timer.fn();
  assert.equal(f.recognitions[0].aborts, 1);
  assert.equal(f.timers.size, 0);
  assert.deepEqual(f.states, ['idle']);
});

test('recognition errors release timers and permission errors have a distinct state', async () => {
  for (const [error, state] of [['not-allowed', 'permission-denied'], ['service-not-allowed', 'permission-denied'], ['audio-capture', 'error']]) {
    const f = fixture();
    await f.dictation();
    const rec = f.recognitions[0], oldEnd = rec.onend;
    rec.onerror({ error });
    oldEnd();
    assert.deepEqual(f.states, [state]);
    assert.equal(f.timers.size, 0);
    assert.equal(rec.aborts, 1);
  }
});

test('dispose invalidates active and pending recognition without later callbacks', async () => {
  const f = fixture();
  await f.dictation();
  const rec = f.recognitions[0], old = { ...rec };
  f.voice.dispose();
  old.onresult(resultEvent(['ignored', true])); old.onstart(); old.onerror({ error: 'not-allowed' }); old.onend();
  assert.deepEqual(f.states, []);
  assert.deepEqual(f.texts, []);
  assert.equal(rec.aborts, 1);
  assert.equal(f.timers.size, 0);
  const pending = fixture(), gate = deferred();
  pending.Recognition.available = () => gate.promise;
  const result = pending.dictation();
  pending.voice.dispose();
  gate.resolve('available');
  assert.deepEqual(await result, { started: false, reason: 'cancelled' });
  assert.equal(pending.recognitions[0].starts, 0);
  assert.deepEqual(pending.states, []);
});

// Break caught: starting audio that this browser cannot explicitly cancel.
test('unavailable synthesis stop control prevents speech startup', () => {
  const f = fixture();
  delete f.synthesis.cancel;
  assert.deepEqual(f.speech(), { started: false, reason: 'unsupported' });
  assert.equal(f.utterances.length, 0);
});

// Break caught: replacement captures a nested operation's generation and loses its hardware resource.
for (const cancellation of ['stop', 'dispose', 'timeout']) {
  test(`reentrant idle dictation retains its resource through speech replacement and ${cancellation}`, async () => {
    const f = fixture();
    let nested;
    f.voice.speak('Original help', { lang: 'en-US', onState: state => {
      if (state === 'idle' && !nested) nested = f.dictation();
    } });
    const replacement = f.speech();
    assert.deepEqual(await nested, { started: true, reason: 'available' });
    const recognition = f.recognitions[0], old = { ...recognition };
    recognition.onstart();
    if (cancellation === 'timeout') [...f.timers.values()][0].fn();
    else f.voice[cancellation]();
    for (const started of f.recognitions.filter(resource => resource.starts > 0)) {
      assert.equal(started.aborts, 1, 'every started recognizer must be aborted');
    }
    assert.deepEqual(replacement, { started: false, reason: 'cancelled' });
    const before = [...f.states];
    old.onresult(resultEvent(['stale transcript', true]));
    old.onstart(); old.onerror({ error: 'not-allowed' }); old.onend();
    assert.deepEqual(f.texts, []);
    assert.deepEqual(f.states, before);
    assert.equal(f.timers.size, 0);
  });
}

test('replacement dictation yields to speech started reentrantly by the prior idle callback', async () => {
  const f = fixture();
  let nested;
  f.voice.speak('Original help', { lang: 'en-US', onState: state => {
    if (state === 'idle' && !nested) nested = f.speech();
  } });
  const replacement = await f.dictation();
  f.voice.stop();
  assert.equal(f.synthesis.cancelled, 2, 'both the original and replacement speech must remain stoppable');
  assert.deepEqual(nested, { started: true, reason: 'available' });
  assert.deepEqual(replacement, { started: false, reason: 'cancelled' });
  assert.equal(f.recognitions.every(resource => resource.starts === 0), true);
});

test('start returns cancelled when a listening callback replaces its recognition session', async () => {
  const f = fixture();
  let nested;
  f.Recognition.prototype.start = function () { this.starts++; this.onstart(); };
  const original = await f.voice.dictate({ lang: 'en-US', onState: state => {
    if (state === 'listening' && !nested) nested = f.dictation();
  } });
  await nested;
  f.voice.stop();
  assert.deepEqual(original, { started: false, reason: 'cancelled' });
  for (const started of f.recognitions.filter(resource => resource.starts > 0)) {
    assert.equal(started.aborts, 1);
  }
});
