"""Integration checks: real git fixtures and CLI; never execute synthetic PE files."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).with_name('package_optimus.py')
PREFIX = 'Optimus_Browser_0.2.0_alpha/'

class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / 'source'
        self.bin = self.root / 'publish'
        self.src.mkdir(); self.bin.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.src)], check=True)
        self.track('Program.cs', '// synthetic source\n')
        self.track('bin/ignored.txt', 'build output')
        self.track('.env.example', 'API_KEY=\n')
        pe = bytearray(128); pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 64)
        pe[64:68] = b'PE\0\0'; struct.pack_into('<H', pe, 68, 0x8664)
        (self.bin/'Optimus.exe').write_bytes(pe)
        for name in ('Optimus.dll', 'Microsoft.Web.WebView2.Core.dll'):
            (self.bin/name).write_bytes(b'synthetic managed assembly')
        (self.bin/'Optimus.runtimeconfig.json').write_text(json.dumps({'runtimeOptions': {'tfm':'net8.0', 'includedFrameworks':[{'name':'Microsoft.NETCore.App','version':'8.0.0'}]}}))
        self.meta = self.root/'meta.json'
        self.meta.write_text(json.dumps({'source_commit':'a'*40,'native_tests':'Synthetic test record; Windows not run.','companion_tests':'Synthetic fixture only.','companion_url':'https://example.com/companion','plugin_id':'synthetic-fixture','validation':'Windows execution pending.','decisions':'Private unsigned alpha.'}))
    def track(self, name, text):
        path = self.src/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        subprocess.run(['git','-C',str(self.src),'add','--',name], check=True)
    def run_cli(self, out='out'):
        return subprocess.run([sys.executable,str(SCRIPT),'--source-root',str(self.src),'--binary-root',str(self.bin),'--output-dir',str(self.root/out),'--metadata',str(self.meta)], capture_output=True, text=True)
    def test_reproducible_package_and_complete_hashes(self):
        # Catches nondeterminism, untracked/build inclusion, and incomplete manifests.
        (self.src/'untracked.txt').write_text('must not ship')
        result = self.run_cli(); self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli('out2'); self.assertEqual(result.returncode, 0, result.stderr)
        name = 'Optimus_Browser_Windows_0.2.0_alpha.zip'
        archive = self.root/'out'/name
        self.assertEqual(archive.read_bytes(), (self.root/'out2'/name).read_bytes())
        self.assertEqual((archive.with_suffix('.zip.sha256')).read_text().split()[0], hashlib.sha256(archive.read_bytes()).hexdigest())
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            self.assertEqual(names, sorted(names))
            self.assertIn(PREFIX+'Source/Program.cs', names)
            self.assertNotIn(PREFIX+'Source/bin/ignored.txt', names)
            self.assertNotIn(PREFIX+'Source/untracked.txt', names)
            manifest = z.read(PREFIX+'SHA256SUMS.txt').decode().splitlines()
            self.assertEqual(len(manifest), len(names)-1)
            for line in manifest:
                digest, path = line.split('  ', 1)
                self.assertEqual(hashlib.sha256(z.read(PREFIX+path)).hexdigest(), digest)
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
