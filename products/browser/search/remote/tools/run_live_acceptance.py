#!/usr/bin/env python3
"""Exercise the real CLI on loopback with disposable credentials; no external HTTP."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from verify_response import verify


def main():
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file() or shutil.which('dotnet') is None:
        print('Supply the built remote API DLL and make .NET 10 available on PATH.', file=sys.stderr)
        return 2
    dll = str(Path(sys.argv[1]).resolve())
    # Never send generated credentials to a service left running by someone else.
    try:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 8080))
    except OSError:
        print('Loopback port 8080 is occupied; acceptance was not started.', file=sys.stderr)
        return 2
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with tempfile.TemporaryDirectory(prefix='optimus-remote-live-') as directory:
        credential = secrets.token_urlsafe(32)
        registry = Path(directory) / 'registry.json'
        expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
        registry.write_text(json.dumps({'schemaVersion': 1, 'clients': [{'clientId': 'isolated-acceptance', 'secretSha256': hashlib.sha256(credential.encode('ascii')).hexdigest(), 'expiresUtc': expiry}]}), encoding='utf8')
        os.chmod(registry, 0o600)
        environment = os.environ.copy()
        environment['OPTIMUS_REMOTE_CREDENTIALS_FILE'] = str(registry)
        environment.pop('OPTIMUS_REMOTE_CONTAINER_HTTP', None)
        process = subprocess.Popen(['dotnet', dll], cwd=directory, env=environment,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise ValueError('CLI exited before readiness.')
                try:
                    with opener.open('http://127.0.0.1:8080/healthz', timeout=0.5) as response:
                        if response.read(1024) != b'{"status":"ok"}':
                            raise ValueError('Unexpected readiness response.')
                    break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise ValueError('CLI readiness deadline expired.')
                    time.sleep(0.05)

            def call(path, body=None):
                data = None if body is None else json.dumps(body).encode('utf8')
                request = urllib.request.Request('http://127.0.0.1:8080' + path, data=data,
                          headers={'Authorization': 'Bearer ' + credential, 'Content-Type': 'application/json'})
                with opener.open(request, timeout=3) as response:
                    raw = response.read(65537)
                    if len(raw) > 65536 or response.headers.get('Cache-Control') != 'no-store':
                        raise ValueError('Response bounds or privacy header failed.')
                    return json.loads(raw)

            catalog = call('/v1/catalog')
            for query in ('fuentes', 'token', 'contraste', 'atajos', 'contenedores', 'almacenamiento', 'Entra', 'presupuestos'):
                if verify(catalog, call('/v1/search', {'query': query, 'limit': 8})) == 0:
                    raise ValueError('Expected reviewed topic missing.')
            if verify(catalog, call('/v1/search', {'query': 'zzzzsyntheticunrelatedneedle', 'limit': 8})) != 0:
                raise ValueError('Unrelated query returned results.')
            print('PASS real CLI + HTTP + independent Python verification: 8 topics and empty result.')
        except (ValueError, OSError, urllib.error.URLError, json.JSONDecodeError):
            print('FAIL isolated live acceptance; details suppressed.', file=sys.stderr)
            return 1
        finally:
            process.terminate()
            try:
                output, errors = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                output, errors = process.communicate(timeout=5)
        if output or errors:
            print('FAIL real CLI emitted unexpected diagnostics; details suppressed.', file=sys.stderr)
            return 1
        print('PASS valid CLI lifecycle emits no query, credential, IP or request diagnostics.')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
