#!/usr/bin/env python3
"""Deterministic, fail-closed packaging for the private Optimus Windows alpha."""
import argparse
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

VERSION = '0.2.0_alpha'
ROOT = f'Optimus_Browser_{VERSION}'
ARCHIVE = f'Optimus_Browser_Windows_{VERSION}.zip'
EXCLUDED = {'.git', '.superpowers', 'bin', 'obj', 'artifacts', 'tooling', '__pycache__'}
PRIVATE_DIRS = {'userdata', 'user-data', 'user_data', 'browserdata', 'browser-data', 'profiles', 'logs', 'secrets', '.ssh', '.aws', '.azure'}
RESERVED = {'source', 'leeme.txt', 'validacion.md', 'decisiones.md', 'sha256sums.txt'}
SECRET_EXT = {'.pfx', '.p12', '.key', '.pem', '.keystore', '.jks'}
KEY_PATTERNS = [
    re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}'),
    re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})'),
    re.compile(rb'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(rb'\bAIza[0-9A-Za-z_-]{30,}'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'(?i)(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)\s*[=:]\s*[\"\']?([A-Za-z0-9_+/=-]{20,})'),
]
LEEME = '''OPTIMUS BROWSER — 0.2.0 alpha privada para Windows x64

Es una alpha privada compilada y sin firma digital. El usuario confirmó que la
versión 0.1 abre en Windows. La ejecución de esta 0.2 y sus aceptaciones de
accesibilidad, privacidad y seguridad siguen pendientes; los tests y la
compilación en Linux no las sustituyen.

USO
1. Descomprime todo el ZIP en una carpeta propia.
2. Ejecuta Optimus.exe desde esa carpeta.
3. SmartScreen puede mostrar Windows protegió su PC por ser una alpha sin firma.
   Comprueba que procede de esta entrega y que figura Optimus.exe. Para una
   prueba consciente, Más información permite Ejecutar de todas formas si la
   política del equipo lo admite. Mantén activadas las protecciones de Windows.
No hay instalación automática ni cambio automático del navegador predeterminado.
.NET está incluido en esta publicación autocontenida. Se necesita Microsoft Edge
WebView2 Evergreen Runtime instalado por separado en Windows.

ALCANCE
Incluye identidad Optimus, modo privado manual, reglas locales configurables y
búsqueda integrada de Wikipedia y marcadores. Una instancia SearXNG configurada
por el operador amplía la búsqueda web. No incluye un índice mundial propio.
Lee Source/docs/GUIA_0_2.md para límites, configuración y pruebas.
El modo privado no da anonimato ni protección adicional ante malware.
La guía local funciona mediante reglas. La IA generativa nativa todavía no está
conectada. El componente acompañante se identifica en VALIDACION.md; su código
se mantiene en su repositorio externo y no se incluye aquí.

CONTENIDO Y VALIDACIÓN
Source/ contiene archivos versionados seleccionados del proyecto nativo.
VALIDACION.md registra las evidencias declaradas y sus límites.
DECISIONES.md registra las decisiones de esta entrega.
SHA256SUMS.txt permite verificar todos los demás archivos del paquete.
No distribuyas credenciales ni datos personales en esta alpha.
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


def check_name(name):
    parts = [p.lower() for p in safe_path(name).parts]
    leaf = parts[-1]
    if any(p in PRIVATE_DIRS for p in parts):
        raise PackagingError(f'Private data directory refused: {name}')
    if (PurePosixPath(leaf).suffix in SECRET_EXT
            or (leaf.startswith('.env') and leaf != '.env.example')
            or re.search(r'(?:credentials?|secrets?|tokens?|passwords?)(?:[._-]|$)', leaf)
            or leaf in {'id_rsa', 'id_ed25519', 'cookies', 'login data', 'history', 'web data'}):
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
    for field in ('source_commit', 'native_tests', 'companion_tests', 'companion_url', 'plugin_id', 'validation', 'decisions'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise PackagingError(f'Metadata field must be nonempty text: {field}')
        check_text(data[field].encode(), f'metadata.{field}')
    if not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', data['source_commit']):
        raise PackagingError('source_commit must be a full git object ID')
    if not re.fullmatch(r'https://[^\s<>]+', data['companion_url']):
        raise PackagingError('companion_url must be an HTTPS URL')
    return data


def validate_binary(files):
    for name in ('Optimus.exe', 'Optimus.dll', 'Optimus.runtimeconfig.json', 'Microsoft.Web.WebView2.Core.dll'):
        if name not in files:
            raise PackagingError(f'Required publication file missing: {name}')
    pe = files['Optimus.exe']
    if len(pe) < 64 or pe[:2] != b'MZ':
        raise PackagingError('Optimus.exe is not a PE apphost')
    offset = struct.unpack_from('<I', pe, 60)[0]
    if offset + 6 > len(pe) or pe[offset:offset+4] != b'PE\x00\x00' or struct.unpack_from('<H', pe, offset+4)[0] != 0x8664:
        raise PackagingError('Optimus.exe must have PE machine AMD64 (x64)')
    options = json.loads(files['Optimus.runtimeconfig.json']).get('runtimeOptions', {})
    frameworks = options.get('includedFrameworks')
    if (options.get('framework') or options.get('frameworks') or not isinstance(frameworks, list)
            or not any(isinstance(f, dict) and f.get('name') == 'Microsoft.NETCore.App' and f.get('version') for f in frameworks)):
        raise PackagingError('runtimeconfig must declare includedFrameworks for self-contained .NET')


def collect(source, binary, metadata):
    files = {}
    for path in sorted(binary.rglob('*')):
        name = path.relative_to(binary).as_posix()
        if path.is_symlink():
            raise PackagingError(f'Symlink refused: {name}')
        check_name(name)
        if path.is_dir():
            continue
        if safe_path(name).parts[0].lower() in RESERVED:
            raise PackagingError(f'Reserved package path collision: {name}')
        if any(p.lower() in EXCLUDED for p in safe_path(name).parts):
            raise PackagingError(f'Build/source directory in binary publication: {name}')
        files[name] = read_file(binary, name)
    validate_binary(files)
    result = subprocess.run(['git', '-C', str(source), 'ls-files', '-z', '--cached'], check=True, capture_output=True)
    source_names = result.stdout.decode('utf-8').split('\x00')
    for name in sorted(set(filter(None, source_names))):
        parts = safe_path(name).parts
        if any(p.lower() in EXCLUDED for p in parts):
            continue
        check_name(name)
        # Gateway code is externally git-backed and must not be vendored here.
        if any('gateway' in p.lower() for p in parts[:-1]):
            raise PackagingError(f'Gateway source directory refused: {name}')
        files['Source/'+name] = read_file(source, name)
    if not any(n.startswith('Source/') for n in files):
        raise PackagingError('No tracked source files found')
    files['LEEME.txt'] = LEEME.encode('utf-8')
    files['VALIDACION.md'] = (f"# Validación declarada — {VERSION}\n\n"
        f"Commit nativo: `{metadata['source_commit']}`\n\n"
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
    for arg in ('source-root', 'binary-root', 'output-dir', 'metadata'):
        parser.add_argument('--'+arg, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        source, binary, output = (p.resolve() for p in (args.source_root, args.binary_root, args.output_dir))
        if not source.is_dir() or not binary.is_dir():
            raise PackagingError('Source and binary roots must exist')
        if output.is_relative_to(source) or output.is_relative_to(binary):
            raise PackagingError('Output must be outside the input roots')
        files = collect(source, binary, load_metadata(args.metadata))
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
