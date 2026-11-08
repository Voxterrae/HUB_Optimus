#!/usr/bin/env python3
"""Offline portable verification against a reviewed release, never fetches URLs.

stdin: {"catalog": <GET /v1/catalog object>, "response": <POST /v1/search object>}
Success proves content membership/integrity, not ranking, completeness or truth.
"""
import base64
import binascii
import hashlib
import json
import sys

CATALOG_SHA256 = '8294911789f69f2c1262c80153ca0dddd6189e9a198b586f5fbb3beeb0d665ec'
PROVENANCE_SHA256 = '5312f482daea11727c9c90a683bcf95dce587021aa6c63609b9038756eb05aae'
CATALOG_ID = 'optimus-public-pilot-v0.1'
MAX_BYTES = 128 * 1024
RELEASE_FIELDS = {'schemaVersion', 'catalogId', 'catalogSha256', 'provenanceSha256'}


def require(condition):
    if not condition:
        raise ValueError('Unverified response.')


def fields(value, expected):
    require(type(value) is dict and value.keys() == expected)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def decode(raw):
    require(type(raw) is bytes and len(raw) <= MAX_BYTES)
    return json.loads(raw.decode('utf8'), object_pairs_hook=unique_object,
                      parse_constant=lambda _: require(False))


def release(value):
    require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1)
    require(value['catalogId'] == CATALOG_ID)
    require(value['catalogSha256'] == CATALOG_SHA256)
    require(value['provenanceSha256'] == PROVENANCE_SHA256)


def verify(catalog, response):
    try:
        fields(catalog, RELEASE_FIELDS | {'catalogBytesBase64', 'provenanceBytesBase64'})
        fields(response, RELEASE_FIELDS | {'results'})
        release(catalog)
        release(response)
        raw = []
        for field, expected in (('catalogBytesBase64', CATALOG_SHA256),
                                ('provenanceBytesBase64', PROVENANCE_SHA256)):
            encoded = catalog[field]
            require(type(encoded) is str and len(encoded) <= MAX_BYTES)
            data = base64.b64decode(encoded, validate=True)
            require(hashlib.sha256(data).hexdigest() == expected)
            raw.append(decode(data))
        documents = {item['url']: item for item in raw[0]['documents']}
        entries = {item['url']: item for item in raw[1]['entries']}
        results = response['results']
        require(type(results) is list and len(results) <= 8)
        seen = set()
        for result in results:
            fields(result, {'title', 'url', 'content', 'source', 'updatedUtc', 'provenance'})
            url = result['url']
            require(type(url) is str and url not in seen and url in documents)
            seen.add(url)
            expected = documents[url]
            require(all(result[key] == expected[key] for key in expected))
            fields(result['provenance'], {'referenceKind', 'referenceCheckedDate', 'sourceRevision', 'summarySha256'})
            require(result['provenance'] == {k: v for k, v in entries[url].items() if k != 'url'})
            require(hashlib.sha256(result['content'].encode('utf8')).hexdigest() == entries[url]['summarySha256'])
        return len(results)
    except (KeyError, TypeError, UnicodeError, binascii.Error, RecursionError) as error:
        raise ValueError('Unverified response.') from error


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        value = decode(raw)
        fields(value, {'catalog', 'response'})
        count = verify(value['catalog'], value['response'])
        print(f'Verified {count} result(s) against reviewed pilot release.')
        return 0
    except (ValueError, OSError, RecursionError):
        print('Unverified response.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
