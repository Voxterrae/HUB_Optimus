"""Generate or verify deterministic hashes of the source distribution."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'PACKAGE_MANIFEST.json'

def distribution_files():
    paths = [ROOT/name for name in ('README.md','VALIDATION.md','pyproject.toml','.gitignore')]
    for directory in ('src','tests','scripts'):
        paths.extend(path for path in (ROOT/directory).rglob('*.py') if '__pycache__' not in path.parts)
    for path in sorted(paths):
        if not path.is_file():
            raise ValueError('missing_distribution_file')
        if path.is_symlink():
            raise ValueError('linked_package_file')
        yield path

def build():
    files = []
    for path in distribution_files():
        rel = path.relative_to(ROOT)
        raw = path.read_bytes()
        files.append({'path':rel.as_posix(), 'sha256':hashlib.sha256(raw).hexdigest(), 'size':len(raw)})
    return {'package':'optimus-cctv-console','version':'0.1.0','fileCount':len(files),'files':files}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    value = build()
    if args.check:
        if json.loads(MANIFEST.read_text(encoding='utf-8')) != value:
            raise SystemExit('Package manifest differs from source')
        print(f"Verified {value['fileCount']} distribution files")
    else:
        MANIFEST.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        print(f"Wrote {value['fileCount']} distribution files")
