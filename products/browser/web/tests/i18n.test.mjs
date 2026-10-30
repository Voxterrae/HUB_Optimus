import test from 'node:test';
import assert from 'node:assert/strict';
import * as api from '../dist/i18n.mjs';

test('unsupported language and region inputs safely resolve to supported UI language', () => {
  assert.equal(typeof api.normalizeLanguage, 'function');
  for (const value of [undefined, null, '', 'xx', {}, '__proto__']) assert.equal(api.normalizeLanguage(value), 'es');
  assert.equal(api.normalizeLanguage('EN-gb'), 'en');
  assert.equal(api.normalizeLanguage(' ca-ES '), 'ca');
  assert.equal(api.t('xx', 'nav.home'), api.t('es', 'nav.home'));
});

test('parameters remain literal text without HTML processing or replacement-string expansion', () => {
  assert.equal(typeof api.t, 'function');
  assert.equal(api.t('en', 'search.resultCount', {count: '<img src=x onerror=alert(1)>$&'}), '<img src=x onerror=alert(1)>$& results');
  assert.equal(api.t('en', 'search.resultCount'), '{count} results');
  assert.equal(api.t('en', 'search.resultCount', {count: 0}), '0 results');
});

test('missing and prototype keys return a safe plain string', () => {
  assert.equal(typeof api.t, 'function');
  assert.equal(api.t('fr', 'missing.key'), 'missing.key');
  assert.equal(api.t('en', '__proto__'), '__proto__');
  assert.equal(api.t('en', 'constructor'), 'constructor');
  assert.equal(api.t('en', null), '');
});

test('six localized dictionaries cover every UI route and have a consistent key and placeholder contract', () => {
  assert.equal(typeof api.validateDictionaries, 'function');
  assert.deepEqual(api.validateDictionaries(), []);
  assert.deepEqual(api.LANGUAGES.map(x => x.code), ['es','ca','en','de','fr','ru']);
  for (const {code, locale, wikiHost} of api.LANGUAGES) {
    assert.equal(wikiHost, `${code}.wikipedia.org`);
    assert.ok(locale.startsWith(code));
    for (const key of ['home.title', 'saved.title', 'guide.title', 'settings.title', 'privacy.search', 'voice.permissionDenied', 'search.error']) {
      assert.equal(typeof api.t(code, key), 'string');
      assert.notEqual(api.t(code, key), key);
    }
  }
});

test('validation reports missing, extra, empty, and mismatched-placeholder translations', () => {
  assert.equal(typeof api.validateDictionaries, 'function');
  const candidate = structuredClone(api.dictionaries);
  delete candidate.ca['nav.home'];
  candidate.fr['unexpected.key'] = 'Extra';
  candidate.de['nav.saved'] = ' ';
  candidate.ru['search.resultCount'] = 'Без параметра';
  const errors = api.validateDictionaries(candidate);
  assert.ok(errors.some(x => x.includes('ca') && x.includes('nav.home') && x.includes('missing')));
  assert.ok(errors.some(x => x.includes('fr') && x.includes('unexpected.key') && x.includes('extra')));
  assert.ok(errors.some(x => x.includes('de') && x.includes('nav.saved') && x.includes('empty')));
  assert.ok(errors.some(x => x.includes('ru') && x.includes('search.resultCount') && x.includes('placeholder')));
});
