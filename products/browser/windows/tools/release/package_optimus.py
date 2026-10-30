#!/usr/bin/env python3
"""Deterministic, fail-closed packaging for the private Optimus Windows alpha."""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import urlsplit

VERSION = '0.3.1_alpha'
ROOT = f'Optimus_Browser_{VERSION}'
ARCHIVE = f'Optimus_Browser_Windows_{VERSION}.zip'
EXCLUDED = {'.git', '.superpowers', 'bin', 'obj', 'artifacts', 'tooling', '__pycache__', '.pytest_cache', 'qa', 'testresults'}
PRIVATE_DIRS = {'userdata', 'user-data', 'user_data', 'browserdata', 'browser-data', 'profiles', 'profile', 'logs', 'secrets', '.ssh', '.aws', '.azure'}
RESERVED = {'source', 'leeme.txt', 'validacion.md', 'decisiones.md', 'sha256sums.txt'}
SECRET_EXT = {'.pfx', '.p12', '.key', '.pem', '.keystore', '.jks'}
# Official microsoft.aspnetcore.app.runtime.win-x64/10.0.14 NuGet payloads,
# runtimes/win-x64/lib/net10.0; only these publication-relative paths qualify.
# A runtime update must review and repin bytes, never broaden secret patterns.
OFFICIAL_RUNTIME_FILES = {
    'search/microsoft.aspnetcore.authentication.bearertoken.dll':
        '8610b42bb97e9df002694aafe2364ecd21810bc2d0652cb0cbf267628d06ce7d',
    'search/microsoft.extensions.configuration.usersecrets.dll':
        '9b8e836f6fe0db69b4c5b7bbfab5445e886560099000e625078dfa9ac271f0f1',
}
KEY_PATTERNS = [
    re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}'),
    re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})'),
    re.compile(rb'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(rb'\bAIza[0-9A-Za-z_-]{30,}'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'(?i)(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)\s*[=:]\s*[\"\']?([A-Za-z0-9_+/=-]{20,})'),
]
LEEME = '''OPTIMUS BROWSER — 0.3.1 alpha privada para Windows x64

Alpha sin firma digital. La ejecución de esta 0.3 en Windows y sus aceptaciones
de accesibilidad, privacidad y seguridad siguen pendientes; las comprobaciones
Linux y las cabeceras PE no las sustituyen.

USO
1. Descomprime todo el ZIP en una carpeta propia.
2. Ejecuta Optimus.exe desde esa carpeta, conservando el subdirectorio Search/.
3. Comprueba el origen y SHA256SUMS.txt. Si SmartScreen bloquea una alpha sin
   firma, sigue la política del equipo y mantén las protecciones de Windows.
No hay instalación automática ni cambio del navegador predeterminado.
Los runtimes .NET, Windows Desktop y ASP.NET Core están incluidos.
Microsoft Edge WebView2 Evergreen Runtime se instala por separado en Windows.

BÚSQUEDA
Web usa el servicio local Optimus y un SearXNG controlado por el operador.
Sin configurar ese proveedor, Web informa la falta de configuración.
Índice Optimus busca solo el catálogo importado explícitamente y funciona offline.
Wikipedia es una opción explícita; no hay sustitución silenciosa de fuentes.
No es un índice mundial ni un rastreador. No incluye IA generativa conectada.
Consulta GUIA_0_3_1.md y Source/Windows/docs/GUIA_0_3_1.md.
El modo privado no da anonimato ni protección adicional ante malware.
Nunca copies el perfil de usuario ni service.token a esta carpeta de entrega.

CONTENIDO Y VALIDACIÓN
Search/ contiene Optimus.SearchHost.exe y su runtime autocontenido.
Source/Windows y Source/Search contienen las fuentes Git seleccionadas.
VALIDACION.md registra las evidencias declaradas y sus límites.
DECISIONES.md registra decisiones. third-party/ conserva los avisos de terceros.
SHA256SUMS.txt cubre todos los demás archivos; el hash externo cubre el ZIP.
El componente acompañante externo se identifica en VALIDACION.md; no se copia.
'''

class PackagingError(ValueError):
    pass


def safe_path(name):
    path = PurePosixPath(name)
    if (not name or name.startswith('/') or '\\' in name or ':' in name
            or any(p in ('', '.', '..') for p in name.split('/'))
            or any(ord(c) < 32 or c in '<>\"|?*' for c in name)
            or any(re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', p) for p in path.parts)
            or any(p.endswith((' ', '.')) for p in path.parts)):
        raise PackagingError('Unsafe archive path')
    return path


def check_name(name, *, publication_sha256=None):
    parts = [p.lower() for p in safe_path(name).parts]
    leaf = parts[-1]
    if any(p in PRIVATE_DIRS for p in parts):
        raise PackagingError(f'Private data directory refused: {name}')
    if (PurePosixPath(leaf).suffix in SECRET_EXT
            or (leaf.startswith('.env') and leaf != '.env.example')
            or re.search(r'(?:credentials?|secrets?|tokens?|passwords?)(?:[._-]|$)', leaf)
            or leaf in {'id_rsa', 'id_ed25519', 'cookies', 'login data', 'history', 'web data'}):
        if (publication_sha256 is None
                or OFFICIAL_RUNTIME_FILES.get(name.casefold()) != publication_sha256):
            raise PackagingError(f'Suspicious secret filename refused: {name}')


def check_text(data, name):
    # UTF-8 and UTF-16 sources/configuration are scanned; opaque binary payloads
    # still undergo path checks. Do not expose matching credentials in errors.
    candidates = [data]
    for encoding in ('utf-16-le', 'utf-16-be'):
        if b'\x00' in data:
            try:
                candidates.append(data.decode(encoding).encode('utf-8'))
            except UnicodeError:
                pass
    if any(pattern.search(candidate) for pattern in KEY_PATTERNS for candidate in candidates):
        raise PackagingError(f'Potential credential content refused: {name}')


def read_file(base, name):
    path = base.joinpath(*safe_path(name).parts)
    # Reject symlinks at any component, including tracked directory symlinks.
    current = base
    for part in safe_path(name).parts:
        current = current / part
        if current.is_symlink():
            raise PackagingError(f'Symlink refused: {name}')
    if not path.is_file() or not path.resolve().is_relative_to(base):
        raise PackagingError(f'Not a regular file within declared root: {name}')
    data = path.read_bytes()
    if not data:
        raise PackagingError(f'Zero-length file refused: {name}')
    check_text(data, name)
    return data


def load_metadata(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    for field in ('source_commit', 'search_source_commit', 'search_tests', 'native_tests', 'companion_tests', 'companion_url', 'plugin_id', 'validation', 'decisions'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise PackagingError(f'Metadata field must be nonempty text: {field}')
        check_text(data[field].encode(), f'metadata.{field}')
    for field in ('source_commit', 'search_source_commit'):
        if not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', data[field]):
            raise PackagingError(f'{field} must be a full git object ID')
    if not re.fullmatch(r'https://[^\s<>]+', data['companion_url']):
        raise PackagingError('companion_url must be an HTTPS URL')
    return data


def validate_bundled_index(data):
    # This is release acceptance, not a replacement for the host's real import.
    # A nonempty default corpus is promised by this alpha's frozen layout.
    try:
        if len(data) > 16 * 1024 * 1024:
            raise ValueError()
        catalog = json.loads(data.decode('utf-8'))
        if (not isinstance(catalog, dict) or type(catalog.get('schemaVersion')) is not int
                or catalog['schemaVersion'] != 1 or not isinstance(catalog.get('documents'), list)
                or not 1 <= len(catalog['documents']) <= 1000):
            raise ValueError()
        for document in catalog['documents']:
            if (not isinstance(document, dict)
                    or any(not isinstance(document.get(field), str)
                           for field in ('url', 'title', 'content', 'source', 'updatedUtc'))):
                raise ValueError()
            url = document['url']
            parsed = urlsplit(url)
            if (len(url.encode('utf-16-le')) // 2 > 2048 or not parsed.hostname
                    or parsed.scheme not in ('http', 'https') or parsed.username is not None
                    or parsed.password is not None or '\\' in url
                    or any(ord(c) < 32 or ord(c) == 127 for c in url)):
                raise ValueError()
            parsed.port  # Validate the optional port without using it.
            if (not document['title'].strip() or len(document['title'].encode('utf-16-le')) // 2 > 240
                    or len(document['content'].encode('utf-8')) > 64 * 1024):
                raise ValueError()
            stamp = datetime.fromisoformat(document['updatedUtc'].replace('Z', '+00:00'))
            if stamp.utcoffset() != timedelta(0):
                raise ValueError()
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise PackagingError('Search/index.json must contain a valid nonempty schemaVersion 1 catalog within documented limits') from None


def validate_binary(files):
    required = ['Microsoft.Web.WebView2.Core.dll', 'PresentationFramework.dll', 'GUIA_0_3_1.md', 'Search/index.json',
                'Search/README.md', 'Search/docs/PROTOCOL.md', 'Search/docs/VALIDATION.md', 'Search/docs/AI_GOVERNANCE_REVIEW.md']
    for prefix, assembly in (('', 'Optimus'), ('Search/', 'Optimus.SearchHost')):
        required.extend(prefix + assembly + suffix for suffix in ('.exe', '.dll', '.deps.json', '.runtimeconfig.json'))
        required.extend(prefix + name for name in ('coreclr.dll', 'hostpolicy.dll', 'System.Private.CoreLib.dll'))
    required.extend('Search/' + name for name in ('Microsoft.AspNetCore.dll', 'Microsoft.AspNetCore.Server.Kestrel.Core.dll'))
    required.extend('third-party/' + name for name in (
        'NETCore.LICENSE.txt', 'NETCore.THIRD-PARTY-NOTICES.txt', 'WindowsDesktop.LICENSE.txt',
        'Microsoft-WebView2-LICENSE.txt', 'Microsoft-WebView2-NOTICE.txt',
        'ASPNetCore.LICENSE.txt', 'ASPNetCore.THIRD-PARTY-NOTICES.txt'))
    for name in required:
        if name not in files:
            raise PackagingError(f'Required publication file missing: {name}')
    validate_bundled_index(files['Search/index.json'])
    for prefix, assembly, framework in (('', 'Optimus', 'Microsoft.WindowsDesktop.App'),
                                         ('Search/', 'Optimus.SearchHost', 'Microsoft.AspNetCore.App')):
        name = prefix + assembly + '.exe'
        pe = files[name]
        if len(pe) < 64 or pe[:2] != b'MZ':
            raise PackagingError(f'{name} is not a PE apphost')
        offset = struct.unpack_from('<I', pe, 60)[0]
        if offset + 6 > len(pe) or pe[offset:offset+4] != b'PE\x00\x00' or struct.unpack_from('<H', pe, offset+4)[0] != 0x8664:
            raise PackagingError(f'{name} must have PE machine AMD64 (x64)')
        name = prefix + assembly + '.runtimeconfig.json'
        options = json.loads(files[name]).get('runtimeOptions', {})
        frameworks = options.get('includedFrameworks')
        if (options.get('framework') or options.get('frameworks')
                or not isinstance(options.get('tfm'), str) or not re.fullmatch(r'net10\.0(?:-windows.*)?', options['tfm'])
                or not isinstance(frameworks, list)
                or any(not any(isinstance(f, dict) and f.get('name') == expected
                               and isinstance(f.get('version'), str) and re.fullmatch(r'10\.0\.\d+', f['version'])
                               and (expected != 'Microsoft.AspNetCore.App' or f['version'] == '10.0.14')
                               for f in frameworks) for expected in ('Microsoft.NETCore.App', framework))):
            raise PackagingError(f'{name} must declare includedFrameworks for self-contained .NET 10 and {framework}')


def collect_source(files, source, prefix):
    result = subprocess.run(['git', '-C', str(source), 'ls-files', '-z', '--cached'], check=True, capture_output=True)
    source_names = result.stdout.decode('utf-8').split('\x00')
    selected = 0
    for name in sorted(set(filter(None, source_names))):
        parts = safe_path(name).parts
        if any(p.lower() in EXCLUDED for p in parts):
            continue
        check_name(name)
        if any('gateway' in p.lower() for p in parts[:-1]):
            raise PackagingError(f'Gateway source directory refused: {name}')
        files[prefix+name] = read_file(source, name)
        selected += 1
    if not selected:
        raise PackagingError(f'No tracked source files found: {prefix}')


def collect_binary(binary):
    files = {}
    for path in sorted(binary.rglob('*')):
        name = path.relative_to(binary).as_posix()
        if path.is_symlink():
            raise PackagingError(f'Symlink refused: {name}')
        if path.is_dir():
            check_name(name)
            continue
        if safe_path(name).parts[0].lower() in RESERVED:
            raise PackagingError(f'Reserved package path collision: {name}')
        if any(p.lower() in EXCLUDED for p in safe_path(name).parts):
            raise PackagingError(f'Build/source directory in binary publication: {name}')
        data = read_file(binary, name)
        check_name(name, publication_sha256=hashlib.sha256(data).hexdigest()
                   if name.casefold() in OFFICIAL_RUNTIME_FILES else None)
        files[name] = data
    validate_binary(files)
    normalized = [name.casefold() for name in files]
    if len(set(normalized)) != len(normalized):
        raise PackagingError('Case-insensitive publication path collision')
    return files


def collect(source, search_source, binary, metadata):
    files = collect_binary(binary)
    collect_source(files, source, 'Source/Windows/')
    collect_source(files, search_source, 'Source/Search/')
    files['LEEME.txt'] = LEEME.encode('utf-8')
    files['VALIDACION.md'] = (f"# Validación declarada — {VERSION}\n\n"
        f"Commit nativo: `{metadata['source_commit']}`\n\n"
        f"Commit servicio: `{metadata['search_source_commit']}`\n\n"
        f"## Pruebas del servicio\n\n{metadata['search_tests']}\n\n"
        f"## Pruebas nativas\n\n{metadata['native_tests']}\n\n"
        f"## Componente acompañante\n\n{metadata['companion_tests']}\n\n"
        f"Repositorio: {metadata['companion_url']}\n\nPlugin: `{metadata['plugin_id']}`\n\n"
        f"## Evidencia y límites\n\n{metadata['validation']}\n\n"
        "Ejecución real en Windows y aceptaciones de accesibilidad y seguridad pendientes.\n"
        "El empaquetador comprueba estructura, apphost PE x64, declaración .NET autocontenida, "
        "rutas, contenido sospechoso, CRC e integridad SHA-256; no ejecuta el producto.\n").encode()
    files['DECISIONES.md'] = (f"# Decisiones — {VERSION}\n\n{metadata['decisions']}\n").encode()
    normalized = set()
    for name in files:
        # Windows treats names case-insensitively. Refuse aliases before writing.
        folded = name.casefold()
        if folded in normalized:
            raise PackagingError(f'Case-insensitive archive path collision: {name}')
        normalized.add(folded)
    files['SHA256SUMS.txt'] = ''.join(f'{hashlib.sha256(files[n]).hexdigest()}  {n}\n' for n in sorted(files)).encode()
    return files


def verify_zip(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if names != sorted(names) or len(set(n.casefold() for n in names)) != len(names):
            raise PackagingError('Archive ordering or duplicate paths invalid')
        for name in names:
            safe_path(name)
            if not name.startswith(ROOT+'/'):
                raise PackagingError('Archive entry outside product directory')
        if archive.testzip() is not None:
            raise PackagingError('Archive CRC validation failed')
        manifest_name = ROOT+'/SHA256SUMS.txt'
        manifest = archive.read(manifest_name).decode('utf-8').splitlines()
        covered = set()
        for line in manifest:
            digest, name = line.split('  ', 1)
            safe_path(name)
            full = ROOT+'/'+name
            if full in covered or not re.fullmatch('[0-9a-f]{64}', digest):
                raise PackagingError('Malformed or duplicate manifest entry')
            if hashlib.sha256(archive.read(full)).hexdigest() != digest:
                raise PackagingError(f'Manifest mismatch: {name}')
            covered.add(full)
        if covered != set(names)-{manifest_name}:
            raise PackagingError('Manifest coverage mismatch')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-publication', type=Path, help='Validate an existing publish tree without execution')
    for arg in ('source-root', 'search-source-root', 'binary-root', 'output-dir', 'metadata'):
        parser.add_argument('--'+arg, type=Path)
    args = parser.parse_args(argv)
    if args.verify_publication is None:
        for name in ('source_root', 'search_source_root', 'binary_root', 'output_dir', 'metadata'):
            if getattr(args, name) is None:
                parser.error('--'+name.replace('_', '-')+' is required for packaging')
    elif any(getattr(args, name) is not None for name in ('source_root', 'search_source_root', 'binary_root', 'output_dir', 'metadata')):
        parser.error('--verify-publication cannot be combined with packaging arguments')
    try:
        if args.verify_publication is not None:
            binary = args.verify_publication.resolve()
            if not binary.is_dir():
                raise PackagingError('Binary root must exist')
            files = collect_binary(binary)
            print(f'Verified publication ({len(files)} files); no executable was run')
            return 0
        source, search_source, binary, output = (p.resolve() for p in (args.source_root, args.search_source_root, args.binary_root, args.output_dir))
        if not all(p.is_dir() for p in (source, search_source, binary)):
            raise PackagingError('Source and binary roots must exist')
        if any(output.is_relative_to(p) for p in (source, search_source, binary)):
            raise PackagingError('Output must be outside the input roots')
        files = collect(source, search_source, binary, load_metadata(args.metadata))
        output.mkdir(parents=True, exist_ok=True)
        target = output/ARCHIVE
        with tempfile.TemporaryDirectory(prefix='.optimus-package-', dir=output) as stage:
            candidate = Path(stage)/ARCHIVE
            with zipfile.ZipFile(candidate, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for name in sorted(files):
                    entry = zipfile.ZipInfo(ROOT+'/'+name, date_time=(1980,1,1,0,0,0))
                    entry.create_system = 3
                    entry.external_attr = 0o100644 << 16
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, files[name], compresslevel=9)
            verify_zip(candidate)
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            checksum = Path(stage)/(ARCHIVE+'.sha256')
            checksum.write_text(f'{digest}  {ARCHIVE}\n', encoding='ascii')
            os.replace(candidate, target)
            os.replace(checksum, output/(ARCHIVE+'.sha256'))
        print(f'Created and verified {target.name} ({len(files)} files)')
        return 0
    except (PackagingError, OSError, ValueError, KeyError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        # Credential matches never include the matching content.
        print(f'Packaging failed: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
