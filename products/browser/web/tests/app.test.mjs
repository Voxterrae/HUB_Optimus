import test from 'node:test';
import assert from 'node:assert/strict';

// Only browser boundaries are simulated: the real app, translations and voice
// controller create the utterance after the actual select/click handlers run.
function browserFixture() {
  function element(tag) {
    return {
      tagName: tag.toUpperCase(), children: [], listeners: new Map(),
      setAttribute(key, value) { this[key] = value; },
      append(...children) { this.children.push(...children); },
      replaceChildren(...children) { this.children = children; },
      addEventListener(event, listener) { this.listeners.set(event, listener); },
    };
  }
  const app = element('div');
  app.id = 'app';
  const find = (node, id) => node.id === id ? node : node.children.map(child => find(child, id)).find(Boolean);
  const document = {
    documentElement: {style: {}},
    body: {dataset: {}, classList: {toggle() {}}},
    activeElement: null,
    createElement: element,
    getElementById: id => find(app, id),
    addEventListener() {},
  };
  const utterances = [];
  const voices = ['es-ES', 'en-GB'].map(lang => ({
    lang, name: `Fixture ${lang}`, voiceURI: `fixture:${lang}`, localService: true, default: false,
  }));
  return {
    document, utterances,
    globals: {
      document,
      window: {localStorage: {getItem: () => null}, addEventListener() {}},
      location: {hash: ''},
      HTMLInputElement: class {},
      SpeechSynthesisUtterance: class { constructor(text) { this.text = text; } },
      speechSynthesis: {getVoices: () => voices, speak: utterance => utterances.push(utterance), cancel() {}},
    },
  };
}

const cases = [
  {
    ui: 'en', speech: 'es', locale: 'es-ES',
    text: 'Este piloto es una página de inicio y búsqueda para tu navegador. Escribe una consulta y pulsa Buscar o Intro. Los resultados abren páginas de Wikipedia. La lectura y el dictado son opcionales y dependen del soporte local del navegador y del idioma instalado.',
  },
  {
    ui: 'es', speech: 'en', locale: 'en-GB',
    text: 'This pilot is a home and search page for your browser. Type a query and press Search or Enter. Results open Wikipedia pages. Reading aloud and dictation are optional and depend on local browser support and the installed language.',
  },
];

for (const scenario of cases) {
  test(`spoken help follows ${scenario.speech} speech while the interface stays ${scenario.ui}`, async () => {
    const fixture = browserFixture();
    const originals = new Map(Object.keys(fixture.globals).map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
    try {
      for (const [key, value] of Object.entries(fixture.globals)) {
        Object.defineProperty(globalThis, key, {value, writable: true, configurable: true});
      }
      const app = new URL('../dist/app.mjs', import.meta.url);
      app.searchParams.set('spoken-help-test', `${scenario.ui}-${scenario.speech}`);
      await import(app.href);
      const ui = fixture.document.getElementById('top-language');
      ui.value = scenario.ui;
      ui.listeners.get('change')();
      const speech = fixture.document.getElementById('voice-language');
      speech.value = scenario.speech;
      speech.listeners.get('change')();
      fixture.document.getElementById('read-help').listeners.get('click')();

      assert.equal(fixture.utterances.length, 1);
      const utterance = fixture.utterances[0];
      assert.equal(utterance.text, scenario.text);
      assert.equal(utterance.lang, scenario.locale);
      assert.equal(utterance.voice.lang, scenario.locale);
      assert.equal(fixture.document.documentElement.lang, scenario.ui);
    } finally {
      fixture.document.getElementById('stop-voice')?.listeners.get('click')?.();
      for (const [key, descriptor] of originals) {
        if (descriptor) Object.defineProperty(globalThis, key, descriptor);
        else delete globalThis[key];
      }
    }
  });
}
