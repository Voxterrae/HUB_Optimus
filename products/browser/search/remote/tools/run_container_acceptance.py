#!/usr/bin/env python3
"""Exercise a locally built image on loopback; never publish or contact Azure."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from verify_response import decode, verify


REGISTRY_PATH = '/run/optimus-remote/credentials.json'
TOPICS = (
    ('fuentes catálogo', 'README.md'),
    ('token perfil', 'PROTOCOL.md'),
    ('contraste', 'change-color-contrast-in-windows'),
    ('atajos teclado', 'keyboard-shortcuts-in-windows'),
    ('Container Apps', 'container-apps/overview'),
    ('Blob Storage', 'storage-blobs-introduction'),
    ('Entra autenticación', 'authentication-vs-authorization'),
    ('presupuestos coste', 'tutorial-acm-create-budgets'),
)


def require(condition):
    if not condition:
        raise ValueError('Container acceptance failed.')


def docker(*arguments, timeout=30):
    result = subprocess.run(['docker', *arguments], capture_output=True,
                            text=True, timeout=timeout, check=False)
    # Never echo captured container output, inspect data or synthetic credentials.
    require(result.returncode == 0)
    return result


def inspect(container):
    return json.loads(docker('inspect', container).stdout)[0]


def write_registry(path, credential):
    if path.exists():
        os.chmod(path, 0o600)
    expiry = (datetime.datetime.now(datetime.timezone.utc)
              + datetime.timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
    path.write_text(json.dumps({'schemaVersion': 1, 'clients': [{
        'clientId': 'isolated-container',
        'secretSha256': hashlib.sha256(credential.encode('ascii')).hexdigest(),
        'expiresUtc': expiry,
    }]}), encoding='utf8')
    # The private host directory is 0700; only the hash registry is mounted.
    # UID 1654 in the container must read a file owned by the runner's host UID.
    os.chmod(path, 0o444)


def endpoint(container, registry):
    state = inspect(container)
    require(state['Config']['User'] == '1654:1654')
    require(state['State']['Running'])
    host = state['HostConfig']
    require(host['ReadonlyRootfs'] and host['Memory'] == 512 * 1024 * 1024)
    require(host['NanoCpus'] == 250_000_000 and host['PidsLimit'] == 64)
    require('ALL' in host['CapDrop'])
    require(any(value.startswith('no-new-privileges') for value in host['SecurityOpt']))
    mounts = [mount for mount in state['Mounts'] if mount['Destination'] == REGISTRY_PATH]
    require(len(mounts) == 1 and mounts[0]['Type'] == 'bind'
            and mounts[0]['Source'] == str(registry) and mounts[0]['RW'] is False)
    bindings = state['NetworkSettings']['Ports']['8080/tcp']
    require(len(bindings) == 1 and bindings[0]['HostIp'] == '127.0.0.1')
    port = int(bindings[0]['HostPort'])
    require(1 <= port <= 65535)
    return f'http://127.0.0.1:{port}'


def request(opener, base, path, credential=None, body=None, expected=200):
    headers = {'Content-Type': 'application/json'}
    if credential is not None:
        headers['Authorization'] = 'Bearer ' + credential
    data = None if body is None else json.dumps(body).encode('utf8')
    query = urllib.request.Request(base + path, data=data, headers=headers)
    try:
        response = opener.open(query, timeout=2)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        require(response.status == expected)
        require(response.headers.get('Cache-Control') == 'no-store')
        require(response.headers.get('X-Content-Type-Options') == 'nosniff')
        require(response.headers.get('Referrer-Policy') == 'no-referrer')
        require(response.headers.get('Set-Cookie') is None)
        require(response.headers.get('Access-Control-Allow-Origin') is None)
        raw = response.read(65537)
        require(len(raw) <= 65536)
        return decode(raw)


def ready(opener, base):
    deadline = time.monotonic() + 30
    while True:
        try:
            require(request(opener, base, '/healthz') == {'status': 'ok'})
            return
        except (urllib.error.URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise ValueError('Container readiness deadline expired.')
            time.sleep(0.1)


def stop(container, base):
    docker('stop', '--time', '8', container, timeout=15)
    state = inspect(container)['State']
    require(not state['Running'] and state['ExitCode'] == 0)
    address = urllib.parse.urlsplit(base)
    with socket.socket() as probe:
        probe.settimeout(1)
        require(probe.connect_ex(('127.0.0.1', address.port)) != 0)


def accept(image):
    image_config = json.loads(docker('image', 'inspect', image).stdout)[0]
    require(image_config['Config']['User'] == '1654:1654')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with tempfile.TemporaryDirectory(prefix='optimus-container-acceptance-') as directory:
        registry = Path(directory) / 'credentials.json'
        cid_file = Path(directory) / 'container.id'
        credential = secrets.token_urlsafe(32)
        write_registry(registry, credential)
        try:
            docker('create', '--cidfile', str(cid_file),
                   '--publish', '127.0.0.1::8080',
                   '--cpus', '0.25', '--memory', '512m', '--memory-swap', '512m',
                   '--pids-limit', '64', '--read-only',
                   '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777',
                   '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                   '--mount', f'type=bind,src={registry},dst={REGISTRY_PATH},readonly',
                   '--env', 'OPTIMUS_REMOTE_CONTAINER_HTTP=true',
                   '--env', f'OPTIMUS_REMOTE_CREDENTIALS_FILE={REGISTRY_PATH}', image)
            container = cid_file.read_text(encoding='ascii').strip()
            require(re.fullmatch(r'[0-9a-f]{64}', container) is not None)
            docker('start', container)
            base = endpoint(container, registry)
            ready(opener, base)
            processes = docker('top', container, '-eo', 'uid,gid,comm').stdout.splitlines()[1:]
            require(processes and all(line.split()[:2] == ['1654', '1654'] for line in processes))
            require(request(opener, base, '/v1/catalog', expected=401)['error'] == 'unauthorized')
            require(request(opener, base, '/v1/search', body={'query': 'contraste', 'limit': 8}, expected=401)['error'] == 'unauthorized')
            catalog = request(opener, base, '/v1/catalog', credential)
            for query, suffix in TOPICS:
                response = request(opener, base, '/v1/search', credential,
                                   {'query': query, 'limit': 8})
                require(verify(catalog, response) > 0)
                require(response['results'][0]['url'].endswith(suffix))
            empty = request(opener, base, '/v1/search', credential,
                            {'query': 'zzzzsyntheticunrelatedneedle', 'limit': 8})
            require(verify(catalog, empty) == 0)

            stop(container, base)
            replacement = secrets.token_urlsafe(32)
            write_registry(registry, replacement)
            docker('start', container)
            base = endpoint(container, registry)
            ready(opener, base)
            require(request(opener, base, '/v1/catalog', credential, expected=401)['error'] == 'unauthorized')
            rotated_catalog = request(opener, base, '/v1/catalog', replacement)
            require(rotated_catalog == catalog)
            stop(container, base)
            logs = docker('logs', container)
            require(not logs.stdout and not logs.stderr)
        finally:
            if cid_file.exists():
                container = cid_file.read_text(encoding='ascii').strip()
                require(re.fullmatch(r'[0-9a-f]{64}', container) is not None)
                docker('rm', '--force', container, timeout=15)


def main():
    if len(sys.argv) != 2 or re.fullmatch(r'sha256:[0-9a-f]{64}', sys.argv[1]) is None:
        print('Supply the immutable local image ID produced by docker build --iidfile.', file=sys.stderr)
        return 2
    try:
        accept(sys.argv[1])
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError):
        print('FAIL isolated container acceptance; captured details suppressed.', file=sys.stderr)
        return 1
    print('PASS constrained UID1654 container, read-only hash registry, independent verification of 8 topics and empty result, 401/revocation, silent logs and graceful cleanup.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
