function language(value) {
  try { return typeof value === 'string' ? Intl.getCanonicalLocales(value)[0] ?? null : null; }
  catch { return null; }
}

function permissionDenied(error) {
  return error?.name === 'NotAllowedError' || error?.name === 'SecurityError' ||
    error?.error === 'not-allowed' || error?.error === 'service-not-allowed';
}

/** Optional, explicit browser speech. Unsupported local capabilities fail closed. */
export class VoiceController {
  constructor({ synthesis = globalThis.speechSynthesis, Recognition = globalThis.SpeechRecognition ?? globalThis.webkitSpeechRecognition,
    createUtterance = globalThis.SpeechSynthesisUtterance ? text => new globalThis.SpeechSynthesisUtterance(text) : null,
    setTimer = (fn, ms) => globalThis.setTimeout(fn, ms), clearTimer = id => globalThis.clearTimeout(id) } = {}) {
    Object.assign(this, { synthesis, Recognition, createUtterance, setTimer, clearTimer });
    this.generation = 0;
    this.active = null;
    this.disposed = false;
  }

  getLocalVoices(lang) {
    const wanted = language(lang);
    if (!wanted) return [];
    try {
      return Array.from(this.synthesis?.getVoices() ?? []).filter(voice => {
        const locale = language(voice.lang);
        return voice.localService === true && locale?.split('-')[0] === wanted.split('-')[0];
      }).sort((a, b) => Number(language(b.lang) === wanted) - Number(language(a.lang) === wanted));
    } catch { return []; }
  }

  _current(token, session) {
    return !this.disposed && token === this.generation &&
      (session === undefined || session === this.active);
  }

  _emit(callback, state) {
    if (!this.disposed && typeof callback === 'function') callback(state);
  }

  _release(active) {
    if (!active) return;
    if (active.timer !== undefined) this.clearTimer(active.timer);
    for (const name of ['onstart', 'onend', 'onerror', 'onresult']) active.resource[name] = null;
  }

  _finish(token, active, state, abort = false) {
    if (!this._current(token, active)) return;
    this.active = null;
    const finished = ++this.generation;
    this._release(active);
    if (abort) this._abort(active);
    if (this._current(finished)) this._emit(active.onState, state);
  }

  _abort(active) {
    try {
      if (active?.kind === 'recognition') active.resource.abort();
    } catch { /* A browser may already have ended recognition. */ }
  }

  stop() {
    // Keep the generation reserved before callbacks: a reentrant operation wins.
    const token = ++this.generation;
    const active = this.active;
    this.active = null;
    this._release(active);
    this._abort(active);
    if (active?.kind === 'speech') {
      try { this.synthesis.cancel(); } catch { /* Best effort browser cleanup. */ }
    }
    if (this._current(token)) this._emit(active?.onState, 'idle');
    return token;
  }

  dispose() {
    this.disposed = true;
    this.stop();
  }

  _prepareRecognition(lang) {
    if (!language(lang)) return { reason: 'unavailable' };
    if (typeof this.Recognition !== 'function' || typeof this.Recognition.available !== 'function') {
      return { reason: 'unsupported' };
    }
    try {
      const recognition = new this.Recognition();
      if (!('processLocally' in recognition) || typeof recognition.start !== 'function' ||
          typeof recognition.abort !== 'function') return { reason: 'unsupported' };
      recognition.processLocally = true;
      if (recognition.processLocally !== true) return { reason: 'unsupported' };
      recognition.lang = language(lang);
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      return { recognition };
    } catch (error) { return { reason: permissionDenied(error) ? 'permission-denied' : 'unsupported' }; }
  }

  async _checkAvailability(lang) {
    try {
      const status = await this.Recognition.available({ langs: [language(lang)], processLocally: true });
      if (status === 'available') return 'available';
      if (status === 'downloadable' || status === 'downloading') return 'download-required';
      return 'unavailable';
    } catch (error) { return permissionDenied(error) ? 'permission-denied' : 'error'; }
  }

  async availability(lang) {
    const token = this.stop();
    if (this.disposed) return 'unavailable';
    if (!this._current(token)) return 'unavailable';
    const prepared = this._prepareRecognition(lang);
    if (!this._current(token)) return 'unavailable';
    const status = prepared.reason ?? await this._checkAvailability(lang);
    if (!this._current(token)) return 'unavailable';
    return ['available', 'unsupported', 'unavailable', 'download-required'].includes(status) ? status : 'unavailable';
  }

  speak(text, { lang, rate = 1, onState } = {}) {
    const token = this.stop();
    if (this.disposed) return { started: false, reason: 'disposed' };
    if (!this._current(token)) return { started: false, reason: 'cancelled' };
    if (typeof text !== 'string' || !text.trim()) return { started: false, reason: 'empty' };
    if (typeof this.createUtterance !== 'function' || typeof this.synthesis?.speak !== 'function' ||
        typeof this.synthesis?.cancel !== 'function') {
      return { started: false, reason: 'unsupported' };
    }
    const voice = this.getLocalVoices(lang)[0];
    if (!this._current(token)) return { started: false, reason: 'cancelled' };
    if (!voice) return { started: false, reason: 'unavailable' };
    let session;
    try {
      const utterance = this.createUtterance(text);
      utterance.voice = voice;
      utterance.lang = language(lang);
      utterance.rate = Number.isFinite(rate) ? Math.min(2, Math.max(0.5, rate)) : 1;
      if (!this._current(token)) return { started: false, reason: 'cancelled' };
      session = { kind: 'speech', resource: utterance, onState };
      utterance.onstart = () => { if (this._current(token, session)) this._emit(onState, 'speaking'); };
      utterance.onend = () => this._finish(token, session, 'idle');
      utterance.onerror = () => this._finish(token, session, 'error');
      this.active = session;
      this.synthesis.speak(utterance);
      if (!this._current(token, session)) return { started: false, reason: 'cancelled' };
      return { started: true, reason: 'available' };
    } catch {
      if (!this._current(token, session)) return { started: false, reason: 'cancelled' };
      if (session) this._finish(token, session, 'error');
      else this._emit(onState, 'error');
      return { started: false, reason: 'error' };
    }
  }

  async dictate({ lang, onText, onState } = {}) {
    const token = this.stop();
    if (this.disposed) return { started: false, reason: 'disposed' };
    if (!this._current(token)) return { started: false, reason: 'cancelled' };
    const { recognition, reason } = this._prepareRecognition(lang);
    if (!this._current(token)) return { started: false, reason: 'cancelled' };
    if (reason) {
      if (reason === 'permission-denied') this._emit(onState, reason);
      return { started: false, reason };
    }
    const session = { kind: 'pending', resource: recognition, onState };
    this.active = session;
    const status = await this._checkAvailability(lang);
    if (!this._current(token, session)) return { started: false, reason: 'cancelled' };
    if (status !== 'available') {
      this._finish(token, session, status === 'permission-denied' || status === 'error' ? status : 'idle');
      return { started: false, reason: status };
    }
    try {
      session.kind = 'recognition';
      recognition.onstart = () => { if (this._current(token, session)) this._emit(onState, 'listening'); };
      recognition.onend = () => this._finish(token, session, 'idle');
      recognition.onerror = error => this._finish(token, session, permissionDenied(error) ? 'permission-denied' : 'error', true);
      recognition.onresult = event => {
        if (!this._current(token, session)) return;
        let text = '';
        for (let i = event.resultIndex ?? 0; i < (event.results?.length ?? 0); i++) {
          const result = event.results[i];
          if (result?.isFinal && typeof result[0]?.transcript === 'string') text += result[0].transcript;
        }
        if (text && typeof onText === 'function') onText(text);
      };
      const timer = this.setTimer(() => {
        if (this._current(token, session)) this.stop();
      }, 30_000);
      if (!this._current(token, session)) {
        this.clearTimer(timer);
        return { started: false, reason: 'cancelled' };
      }
      session.timer = timer;
      recognition.start();
      if (!this._current(token, session)) return { started: false, reason: 'cancelled' };
      return { started: true, reason: 'available' };
    } catch (error) {
      if (!this._current(token, session)) return { started: false, reason: 'cancelled' };
      const reason = permissionDenied(error) ? 'permission-denied' : 'error';
      this._finish(token, session, reason, true);
      return { started: false, reason };
    }
  }
}
