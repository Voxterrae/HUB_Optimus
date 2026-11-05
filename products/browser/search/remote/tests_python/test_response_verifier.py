import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('verify_response', ROOT / 'remote/tools/verify_response.py')


class ResponseVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SPEC.origin or not Path(SPEC.origin).exists():
            return
        cls.module = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(cls.module)

    def fixtures(self):
        catalog = (ROOT / 'catalog/public-pilot-v0.1.json').read_bytes()
        provenance = (ROOT / 'catalog/public-pilot-v0.1.provenance.json').read_bytes()
        documents = json.loads(catalog)['documents']
        entries = json.loads(provenance)['entries']
        envelope = dict(schemaVersion=1, catalogId='optimus-public-pilot-v0.1',
                        catalogSha256=hashlib.sha256(catalog).hexdigest(),
                        provenanceSha256=hashlib.sha256(provenance).hexdigest(),
                        catalogBytesBase64=base64.b64encode(catalog).decode(),
                        provenanceBytesBase64=base64.b64encode(provenance).decode())
        response = {k: envelope[k] for k in ('schemaVersion', 'catalogId', 'catalogSha256', 'provenanceSha256')}
        response['results'] = [{**documents[0], 'provenance': {k: v for k, v in entries[0].items() if k != 'url'}}]
        return envelope, response

    def verify(self, catalog, response):
        self.assertTrue(hasattr(self, 'module'), 'Missing independent response verifier')
        return self.module.verify(catalog, response)

    def test_trusted_summary_and_empty_results(self):
        catalog, response = self.fixtures()
        self.assertEqual(1, self.verify(catalog, response))
        response['results'] = []
        self.assertEqual(0, self.verify(catalog, response))

    def test_mutated_result_fields_rejected(self):
        for field in ('title', 'url', 'content', 'source', 'updatedUtc'):
            with self.subTest(field=field):
                catalog, response = self.fixtures()
                response['results'][0][field] += ' altered'
                with self.assertRaises(ValueError): self.verify(catalog, response)

    def test_mutated_provenance_and_release_rejected(self):
        catalog, response = self.fixtures()
        response['results'][0]['provenance']['summarySha256'] = '0' * 64
        with self.assertRaises(ValueError): self.verify(catalog, response)
        catalog, response = self.fixtures()
        response['catalogSha256'] = '0' * 64
        with self.assertRaises(ValueError): self.verify(catalog, response)

    def test_self_consistent_attacker_catalog_rejected(self):
        catalog, response = self.fixtures()
        raw = base64.b64decode(catalog['catalogBytesBase64']) + b'\n'
        catalog['catalogBytesBase64'] = base64.b64encode(raw).decode()
        catalog['catalogSha256'] = response['catalogSha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError): self.verify(catalog, response)

    def test_duplicates_unknown_fields_and_boolean_schema_rejected(self):
        for mutation in ('duplicate', 'unknown', 'bool'):
            catalog, response = self.fixtures()
            if mutation == 'duplicate': response['results'] *= 2
            if mutation == 'unknown': response['query'] = 'private-looking-value'
            if mutation == 'bool': response['schemaVersion'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.verify(catalog, response)

    def test_bad_base64_rejected(self):
        catalog, response = self.fixtures()
        catalog['catalogBytesBase64'] = 'not base64'
        with self.assertRaises(ValueError): self.verify(catalog, response)


if __name__ == '__main__':
    unittest.main()
