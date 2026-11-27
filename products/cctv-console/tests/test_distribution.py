"""Distribution boundaries: no live data and no unconfigured credential I/O."""
import os
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent

class DistributionTests(unittest.TestCase):
    def test_partial_default_binding_does_not_open_a_socket(self):
        env = {key:value for key,value in os.environ.items() if not key.startswith('HUB_OPTIMUS_CCTV_')}
        env.update(PYTHONPATH=str(ROOT/'src'),HUB_OPTIMUS_CCTV_HOST='10.20.30.40',HUB_OPTIMUS_CCTV_SERIAL='synthetic')
        code = '''from unittest.mock import patch
import vox_cctv_native as native
with patch('socket.create_connection') as socket_call:
    try:
        native.NativeClient('synthetic-hash',0,'Main')
    except native.SourceError:
        pass
    else:
        raise AssertionError('Partial installation binding opened a socket')
    socket_call.assert_not_called()
'''
        result = subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_unconfigured_native_paths_stop_before_io(self):
        env = {key:value for key,value in os.environ.items() if not key.startswith('HUB_OPTIMUS_CCTV_')}
        env['PYTHONPATH'] = str(ROOT/'src')
        code = '''from unittest.mock import patch
import vox_cctv_native as native
with patch('socket.create_connection') as socket_call, patch.object(native.ctypes, 'WinDLL', create=True) as vault:
    try:
        native.owner_hash()
    except ValueError as error:
        assert str(error) == 'installation_configuration_required'
    else:
        raise AssertionError('Unconfigured credential lookup allowed')
    try:
        native.NativeClient('synthetic-hash',0,'Main')
    except native.SourceError:
        pass
    else:
        raise AssertionError('Unconfigured network path allowed')
    socket_call.assert_not_called()
    vault.assert_not_called()
'''
        result = subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_distribution_contains_no_installation_assets(self):
        spec = importlib.util.spec_from_file_location('distribution_manifest',ROOT/'scripts/build-package-manifest.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        for path in builder.distribution_files():
            self.assertNotIn(path.suffix,('.gz','.jpg','.jpeg','.ppm','.hevc','.h264','.sqlite3','.lnk'))
            if path.suffix in ('.py','.json','.md','.toml'):
                text = path.read_text(encoding='utf-8')
                self.assertNotRegex(text,r"192\.168\.1\.\d+")
                self.assertNotRegex(text,r"Voxterrae/CCTV/[a-f0-9]+/admin")
                self.assertNotRegex(text,r"C:\\\\Users\\\\Admin")

if __name__ == '__main__':unittest.main()
