"""Integration checks: real git fixtures and CLI; never execute synthetic PE files."""
import hashlib
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPT = Path(__file__).with_name('package_optimus.py')
PREFIX = 'Optimus_Browser_0.3.1_alpha/'
RUNTIME_FIXTURES = {
    'Search/Microsoft.AspNetCore.Authentication.BearerToken.dll': b'synthetic bearer runtime fixture\n',
    'Search/Microsoft.Extensions.Configuration.UserSecrets.dll': b'synthetic user secrets runtime fixture\n',
}

class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / 'source'
        self.bin = self.root / 'publish'
        self.search = self.root / 'search'
        self.search.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.search)], check=True)
        self.track('src/Optimus.Search/Program.cs', '// search source\n', self.search)
        self.src.mkdir(); self.bin.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.src)], check=True)
        self.track('Program.cs', '// synthetic source\n')
        self.track('bin/ignored.txt', 'build output')
        self.track('.env.example', 'API_KEY=\n')
        pe = bytearray(128); pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 64)
        pe[64:68] = b'PE\0\0'; struct.pack_into('<H', pe, 68, 0x8664)
        (self.bin/'Optimus.exe').write_bytes(pe)
        for name in ('Optimus.dll', 'Optimus.deps.json', 'Microsoft.Web.WebView2.Core.dll', 'PresentationFramework.dll', 'coreclr.dll', 'hostpolicy.dll', 'System.Private.CoreLib.dll'):
            (self.bin/name).write_bytes(b'synthetic managed assembly')
        (self.bin/'Optimus.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {'tfm':'net10.0', 'includedFrameworks':[{'name':'Microsoft.NETCore.App','version':'10.0.14'}, {'name':'Microsoft.WindowsDesktop.App','version':'10.0.14'}]}}))
        host = self.bin/'Search'; host.mkdir()
        (host/'Optimus.SearchHost.exe').write_bytes(pe)
        self.catalog = {'schemaVersion':1, 'documents':[{'url':'https://example.org/help/'+part, 'title':'Ayuda '+part, 'content':'Contenido público de ayuda local.', 'source':'Ayuda Optimus', 'updatedUtc':'2026-10-30T00:00:00Z'} for part in ('one','two','three')]}
        (host/'index.json').write_text(json.dumps(self.catalog))
        for name in ('Optimus.SearchHost.dll', 'Optimus.SearchHost.deps.json', 'Microsoft.AspNetCore.dll', 'Microsoft.AspNetCore.Server.Kestrel.Core.dll', 'coreclr.dll', 'hostpolicy.dll', 'System.Private.CoreLib.dll'):
            (host/name).write_bytes(b'synthetic runtime payload')
        (host/'Optimus.SearchHost.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {'tfm':'net10.0', 'includedFrameworks':[{'name':'Microsoft.NETCore.App','version':'10.0.14'}, {'name':'Microsoft.AspNetCore.App','version':'10.0.14'}]}}))
        for name in ('GUIA_0_3_1.md', 'Search/README.md', 'Search/docs/PROTOCOL.md', 'Search/docs/VALIDATION.md', 'Search/docs/AI_GOVERNANCE_REVIEW.md'):
            target = self.bin/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('Synthetic help fixture.')
        notices = self.bin/'third-party'; notices.mkdir()
        for name in ('NETCore.LICENSE.txt', 'NETCore.THIRD-PARTY-NOTICES.txt', 'WindowsDesktop.LICENSE.txt', 'Microsoft-WebView2-LICENSE.txt', 'Microsoft-WebView2-NOTICE.txt', 'ASPNetCore.LICENSE.txt', 'ASPNetCore.THIRD-PARTY-NOTICES.txt'):
            (notices/name).write_text('Synthetic notice fixture; not a vendor license.')
        self.meta = self.root/'meta.json'
        self.meta.write_text(json.dumps({'source_commit':'a'*40,'search_source_commit':'b'*40,'search_tests':'Synthetic host fixture only.','native_tests':'Synthetic test record; Windows not run.','companion_tests':'Synthetic fixture only.','companion_url':'https://example.com/companion','plugin_id':'synthetic-fixture','validation':'Windows execution pending.','decisions':'Private unsigned alpha.'}))
    def track(self, name, text, source=None):
        source = source or self.src
        path = source/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        subprocess.run(['git','-C',str(source),'add','--',name], check=True)
    def run_cli(self, out='out'):
        return subprocess.run([sys.executable,str(SCRIPT),'--source-root',str(self.src),'--search-source-root',str(self.search),'--binary-root',str(self.bin),'--output-dir',str(self.root/out),'--metadata',str(self.meta)], capture_output=True, text=True)
    def test_reproducible_package_and_complete_hashes(self):
        # Catches nondeterminism, untracked/build inclusion, and incomplete manifests.
        (self.src/'untracked.txt').write_text('must not ship')
        result = self.run_cli(); self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli('out2'); self.assertEqual(result.returncode, 0, result.stderr)
        name = 'Optimus_Browser_Windows_0.3.1_alpha.zip'
        archive = self.root/'out'/name
        self.assertEqual(archive.read_bytes(), (self.root/'out2'/name).read_bytes())
        self.assertEqual((archive.with_suffix('.zip.sha256')).read_text().split()[0], hashlib.sha256(archive.read_bytes()).hexdigest())
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            self.assertEqual(names, sorted(names))
            self.assertIn(PREFIX+'Source/Windows/Program.cs', names)
            self.assertIn(PREFIX+'Source/Search/src/Optimus.Search/Program.cs', names)
            self.assertIn(PREFIX+'Search/Optimus.SearchHost.exe', names)
            self.assertEqual(json.loads(z.read(PREFIX+'Search/index.json')), self.catalog)
            self.assertIn(b'Commit servicio', z.read(PREFIX+'VALIDACION.md'))
            self.assertNotIn(PREFIX+'Source/Windows/bin/ignored.txt', names)
            self.assertNotIn(PREFIX+'Source/Windows/untracked.txt', names)
            manifest = z.read(PREFIX+'SHA256SUMS.txt').decode().splitlines()
            self.assertEqual(len(manifest), len(names)-1)
            for line in manifest:
                digest, path = line.split('  ', 1)
                self.assertEqual(hashlib.sha256(z.read(PREFIX+path)).hexdigest(), digest)
    def test_rejects_missing_or_invalid_host_runtime_and_notices(self):
        # Catches a native-only ZIP, wrong-host architecture and stripped runtimes/notices.
        required = ('GUIA_0_3_1.md', 'Search/README.md', 'Search/docs/PROTOCOL.md', 'Search/Optimus.SearchHost.exe', 'Search/Optimus.SearchHost.dll',
                    'Search/Optimus.SearchHost.deps.json', 'Search/coreclr.dll',
                    'Search/Microsoft.AspNetCore.Server.Kestrel.Core.dll',
                    'coreclr.dll', 'PresentationFramework.dll',
                    'third-party/ASPNetCore.LICENSE.txt', 'third-party/ASPNetCore.THIRD-PARTY-NOTICES.txt',
                    'third-party/NETCore.THIRD-PARTY-NOTICES.txt', 'third-party/WindowsDesktop.LICENSE.txt',
                    'third-party/Microsoft-WebView2-NOTICE.txt')
        for name in required:
            with self.subTest(missing=name):
                target = self.bin/name; original = target.read_bytes(); target.unlink()
                try:
                    result = self.run_cli()
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('Required publication file missing', result.stderr)
                finally:
                    target.write_bytes(original)
        target = self.bin/'Search/Optimus.SearchHost.exe'
        data = bytearray(target.read_bytes()); struct.pack_into('<H', data,68,0x14c)
        target.write_bytes(data)
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn('AMD64', result.stderr)

    def test_verifies_publication_without_source_or_metadata(self):
        # Catches a build checker that cannot validate the actual publication independently.
        args = [sys.executable,str(SCRIPT),'--verify-publication',str(self.bin)]
        result = subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Verified publication', result.stdout)
        (self.bin/'Search/Optimus.SearchHost.exe').unlink()
        result = subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('Required publication file missing', result.stderr)

    def runtime_fixture_packager(self):
        # Replace only pinned bytes for portable tests; all real validation runs.
        spec = importlib.util.spec_from_file_location('runtime_packager', SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        fixture_hashes = {name.casefold(): hashlib.sha256(data).hexdigest()
                          for name, data in RUNTIME_FIXTURES.items()}
        patcher = patch.object(module, 'OFFICIAL_RUNTIME_FILES', fixture_hashes, create=True)
        patcher.start(); self.addCleanup(patcher.stop)
        return module

    def test_runtime_digest_pins_match_official_10_0_14_payloads(self):
        # Security pin data is independent of the synthetic bytes used below.
        spec = importlib.util.spec_from_file_location('pinned_packager', SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.assertEqual(module.OFFICIAL_RUNTIME_FILES, {
            'search/microsoft.aspnetcore.authentication.bearertoken.dll':
                '8610b42bb97e9df002694aafe2364ecd21810bc2d0652cb0cbf267628d06ce7d',
            'search/microsoft.extensions.configuration.usersecrets.dll':
                '9b8e836f6fe0db69b4c5b7bbfab5445e886560099000e625078dfa9ac271f0f1',
        })

    def call_packager(self, module, mode='verify'):
        args = ['--verify-publication', str(self.bin)] if mode == 'verify' else [
            '--source-root', str(self.src), '--search-source-root', str(self.search),
            '--binary-root', str(self.bin), '--output-dir', str(self.root/'out'),
            '--metadata', str(self.meta)]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as errors:
            result = module.main(args)
        return result, errors.getvalue()

    def test_accepts_exact_runtime_paths_and_payloads_in_both_cli_modes(self):
        # Catches the actual runtime filename false positives and case-sensitive lookup.
        module = self.runtime_fixture_packager()
        for name, data in RUNTIME_FIXTURES.items():
            (self.bin/name).write_bytes(data)
        for mode in ('verify', 'package'):
            result, errors = self.call_packager(module, mode)
            self.assertEqual(result, 0, errors)
        with zipfile.ZipFile(self.root/'out'/'Optimus_Browser_Windows_0.3.1_alpha.zip') as archive:
            for name, data in RUNTIME_FIXTURES.items():
                self.assertEqual(archive.read(PREFIX+name), data)
        for name in RUNTIME_FIXTURES:
            (self.bin/name).rename(self.bin/name.upper().replace('SEARCH/', 'Search/'))
        result, errors = self.call_packager(module)
        self.assertEqual(result, 0, errors)

    def test_rejects_runtime_wrong_bytes_and_same_basename_elsewhere(self):
        # Catches trusting only the path, only the hash, a basename or a substring.
        module = self.runtime_fixture_packager()
        for name, data in RUNTIME_FIXTURES.items():
            for wrong_name, wrong_data in ((name, data+b'changed'),
                    (Path(name).name, data), ('Search/nested/'+Path(name).name, data),
                    ('OtherSearch/'+Path(name).name, data), ('Source/'+name, data)):
                with self.subTest(name=wrong_name):
                    target = self.bin/wrong_name; target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(wrong_data)
                    try:
                        result, errors = self.call_packager(module)
                        self.assertEqual(result, 1, errors)
                    finally:
                        target.unlink()
                        while target.parent != self.bin and not any(target.parent.iterdir()):
                            target = target.parent; target.rmdir()

    def test_runtime_exception_does_not_apply_to_sources_or_private_files(self):
        # Catches reusing the publication exception in either source/privacy scan.
        module = self.runtime_fixture_packager()
        for source in (self.src, self.search):
            for name, data in RUNTIME_FIXTURES.items():
                with self.subTest(source=source, name=name):
                    self.track(name, data.decode(), source)
                    result, errors = self.call_packager(module, 'package')
                    self.assertEqual(result, 1, errors)
                    self.assertIn('Suspicious secret filename', errors)
                    subprocess.run(['git','-C',str(source),'rm','-q','-f','--',name], check=True)
        for name in ('Search/service.token', 'Search/.env', 'Search/profile/history.db'):
            with self.subTest(private=name):
                target = self.bin/name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(next(iter(RUNTIME_FIXTURES.values())))
                try:
                    result, errors = self.call_packager(module)
                    self.assertEqual(result, 1, errors)
                finally:
                    target.unlink()
                    if target.parent.name == 'profile': target.parent.rmdir()

    def test_runtime_exception_preserves_file_and_content_checks(self):
        # Catches bypassing symlink, empty/regular-file and content scans on exact paths.
        module = self.runtime_fixture_packager()
        name, data = next(iter(RUNTIME_FIXTURES.items()))
        target = self.bin/name
        for kind in ('symlink', 'directory', 'empty', 'credential'):
            with self.subTest(kind=kind):
                content = b'password='+b'A'*32 if kind == 'credential' else b''
                with patch.dict(module.OFFICIAL_RUNTIME_FILES, {name.casefold(): hashlib.sha256(content).hexdigest()}):
                    if kind == 'symlink':
                        outside = self.root/'runtime.dll'; outside.write_bytes(data)
                        target.symlink_to(outside)
                    elif kind == 'directory': target.mkdir()
                    else: target.write_bytes(content)
                    try:
                        result, errors = self.call_packager(module)
                        self.assertEqual(result, 1, errors)
                        if kind == 'credential': self.assertIn('Potential credential content', errors)
                    finally:
                        if target.is_dir() and not target.is_symlink(): target.rmdir()
                        else: target.unlink()

    def test_rejects_missing_bundled_index_before_verifying_or_packaging(self):
        # Catches accepting a release whose default offline corpus was omitted.
        (self.bin/'Search/index.json').unlink()
        for mode in ('verify', 'package'):
            with self.subTest(mode=mode):
                result = self.run_cli() if mode == 'package' else subprocess.run([sys.executable,str(SCRIPT),'--verify-publication',str(self.bin)],capture_output=True,text=True)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('Search/index.json', result.stderr)
                self.assertFalse((self.root/'out'/'Optimus_Browser_Windows_0.3.1_alpha.zip').exists())

    def test_rejects_invalid_bundled_index_before_verifying_or_packaging(self):
        # Catches treating an existing corrupt, empty or out-of-contract corpus as valid.
        document = self.catalog['documents'][0]
        cases = {
            'malformed JSON': '{broken',
            'wrong root': '[]',
            'unsupported schema': json.dumps({'schemaVersion':2,'documents':[document]}),
            'missing documents': '{"schemaVersion":1}',
            'empty corpus': '{"schemaVersion":1,"documents":[]}',
            'invalid document': '{"schemaVersion":1,"documents":[null]}',
            'missing content': json.dumps({'schemaVersion':1,'documents':[{key:value for key,value in document.items() if key != 'content'}]}),
            'unsafe URL': json.dumps({'schemaVersion':1,'documents':[{**document,'url':'javascript:alert(1)'}]}),
            'long title': json.dumps({'schemaVersion':1,'documents':[{**document,'title':'a'*241}]}),
            'large content': json.dumps({'schemaVersion':1,'documents':[{**document,'content':'a'*(64*1024+1)}]}),
            'invalid UTC': json.dumps({'schemaVersion':1,'documents':[{**document,'updatedUtc':'not-a-date'}]}),
            'too many documents': json.dumps({'schemaVersion':1,'documents':[document]*1001}),
            'oversized file': json.dumps(self.catalog)+' '*(16*1024*1024),
        }
        for label, content in cases.items():
            for mode in ('verify', 'package'):
                with self.subTest(case=label, mode=mode):
                    (self.bin/'Search/index.json').write_text(content)
                    result = self.run_cli() if mode == 'package' else subprocess.run([sys.executable,str(SCRIPT),'--verify-publication',str(self.bin)],capture_output=True,text=True)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('Search/index.json', result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertFalse((self.root/'out'/'Optimus_Browser_Windows_0.3.1_alpha.zip').exists())

    def test_rejects_host_framework_dependent_or_wrong_runtime_version(self):
        # Catches a host that requires an installed ASP.NET runtime or the wrong TFM.
        target = self.bin/'Search/Optimus.SearchHost.runtimeconfig.json'
        original = target.read_bytes()
        for config in ({'runtimeOptions':{'tfm':'net10.0','framework':{'name':'Microsoft.AspNetCore.App','version':'10.0.14'}}},
                       {'runtimeOptions':{'tfm':'net8.0','includedFrameworks':[{'name':'Microsoft.NETCore.App','version':'8.0.0'}, {'name':'Microsoft.AspNetCore.App','version':'8.0.0'}]}},
                       {'runtimeOptions':{'tfm':'net10.0','includedFrameworks':[{'name':'Microsoft.NETCore.App','version':'10.0.14'}]}},
                       {'runtimeOptions':{'tfm':'net10.0','includedFrameworks':[{'name':'Microsoft.NETCore.App','version':'10.0.14'}, {'name':'Microsoft.AspNetCore.App','version':'10.0.15'}]}}):
            with self.subTest(config=config):
                target.write_text(json.dumps(config))
                result = self.run_cli()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('runtimeconfig', result.stderr)
        target.write_bytes(original)

    def test_rejects_private_search_sources_and_qa_publication(self):
        # Catches omissions of the second source privacy scan and QA/runtime spill.
        for name, text in [('service.token', 'A'*64), ('profile/history.db','private'), ('Config.cs','// key '+'sk-proj-'+'A'*48)]:
            with self.subTest(source=name):
                self.track(name, text, self.search)
                self.assertEqual(self.run_cli().returncode, 1)
                subprocess.run(['git','-C',str(self.search),'rm','-q','-f','--',name],check=True)
        for name in ('QA/trace.txt', 'Search/artifacts/test.log', 'Search/service.token', 'Search/profiles/data.txt'):
            with self.subTest(binary=name):
                target = self.bin/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_text('private runtime output')
                self.assertEqual(self.run_cli().returncode, 1)
                target.unlink()
                while target.parent != self.bin and not any(target.parent.iterdir()):
                    target = target.parent; target.rmdir()

    def test_requires_search_source_root_and_search_provenance(self):
        # Catches silently packaging no host source or publishing undocumented provenance.
        args = [sys.executable,str(SCRIPT),'--source-root',str(self.src),'--binary-root',str(self.bin),'--output-dir',str(self.root/'out'),'--metadata',str(self.meta)]
        result = subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--search-source-root', result.stderr)
        meta = json.loads(self.meta.read_text()); del meta['search_source_commit']; self.meta.write_text(json.dumps(meta))
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn('search_source_commit', result.stderr)

    def test_rejects_wrong_machine_missing_runtime_or_empty_payload(self):
        # Catches shipping an incompatible apphost, framework-dependent build, or truncation.
        for case in ('machine','runtime','empty','missing'):
            with self.subTest(case=case):
                target = self.bin/'Optimus.exe'; original = target.read_bytes()
                config = self.bin/'Optimus.runtimeconfig.json'; oldconfig = config.read_bytes()
                if case == 'machine':
                    data = bytearray(original); struct.pack_into('<H', data,68,0x14c); target.write_bytes(data)
                if case == 'runtime': config.write_text('{"runtimeOptions":{"framework":{"name":"Microsoft.NETCore.App"}}}')
                if case == 'empty': target.write_bytes(b'')
                if case == 'missing': target.unlink()
                self.assertNotEqual(self.run_cli().returncode,0)
                target.write_bytes(original); config.write_bytes(oldconfig)
    def test_rejects_sensitive_source_binary_symlink_and_unsafe_path(self):
        # Catches secret inclusion and escaping the declared roots.
        for name, content in [('credentials.json','{}'),('.env','KEY=value'),('Config.cs','// token: '+'sk-proj-'+'A'*48)]:
            with self.subTest(name=name):
                self.track(name,content)
                self.assertNotEqual(self.run_cli().returncode,0)
                subprocess.run(['git','-C',str(self.src),'rm','-q','-f','--',name],check=True)
        (self.bin/'userdata').mkdir(); (self.bin/'userdata'/'history.db').write_text('private')
        self.assertNotEqual(self.run_cli().returncode,0)
        (self.bin/'userdata'/'history.db').unlink(); (self.bin/'userdata').rmdir()
        (self.bin/'linked.dll').symlink_to(self.meta)
        self.assertNotEqual(self.run_cli().returncode,0)
    def test_rejects_windows_unsafe_names_and_case_collisions(self):
        for name in ('CON.txt', 'bad?.txt', 'optimus.DLL'):
            with self.subTest(name=name):
                (self.bin/name).write_text('invalid Windows publication entry')
                self.assertNotEqual(self.run_cli().returncode, 0)
                (self.bin/name).unlink()
    def test_zip_verifier_rejects_tampering_and_traversal(self):
        spec = importlib.util.spec_from_file_location('packager', SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        archive = self.root/'bad.zip'
        for entries in ({PREFIX+'a.txt':b'tampered', PREFIX+'SHA256SUMS.txt':('0'*64+'  a.txt\n').encode()},
                        {PREFIX+'../escape.txt':b'bad', PREFIX+'SHA256SUMS.txt':b''}):
            with zipfile.ZipFile(archive,'w') as z:
                for name in sorted(entries): z.writestr(name,entries[name])
            with self.assertRaises(module.PackagingError): module.verify_zip(archive)
    def test_refuses_reserved_binary_document_collision(self):
        (self.bin/'LEEME.txt').write_text('misleading readme')
        self.assertNotEqual(self.run_cli().returncode,0)

if __name__ == '__main__': unittest.main()
