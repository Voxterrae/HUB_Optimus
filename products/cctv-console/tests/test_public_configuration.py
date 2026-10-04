"""Tests for the public distribution's explicit installation configuration."""
import importlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(SRC))

class PublicConfigTests(unittest.TestCase):
    def load(self, values=None):
        with patch.dict(os.environ, values or {}, clear=True):
            sys.modules.pop('vox_cctv_config', None)
            return importlib.import_module('vox_cctv_config')

    def test_import_does_not_contact_network_or_credential_store(self):
        with patch('socket.create_connection', side_effect=AssertionError('network used')):
            config = self.load()
            self.assertEqual(config.RECORDER_IP, '127.0.0.1')
            with self.assertRaisesRegex(ValueError, 'installation_configuration_required'):
                config.require_configuration()

    def test_all_three_explicit_bindings_are_required(self):
        values = {'HUB_OPTIMUS_CCTV_HOST': '10.20.30.40', 'HUB_OPTIMUS_CCTV_SERIAL':'synthetic'}
        with self.assertRaises(ValueError):self.load(values).require_configuration()

    def test_private_ipv4_and_exact_identity_are_accepted(self):
        values = {'HUB_OPTIMUS_CCTV_HOST':'10.20.30.40', 'HUB_OPTIMUS_CCTV_SERIAL':'synthetic',
                  'HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET':'example/testing/recorder'}
        config = self.load(values)
        config.require_configuration()
        self.assertEqual(config.RECORDER_SERIAL, 'synthetic')

    def test_host_must_be_explicit_private_ipv4(self):
        values={'HUB_OPTIMUS_CCTV_SERIAL':'synthetic','HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET':'example'}
        for host in ('example.com','8.8.8.8','127.0.0.1','::1','10.0.0.1:34567','10.0.0.1\n'):
            with self.subTest(host=host),self.assertRaises(ValueError):
                self.load({**values,'HUB_OPTIMUS_CCTV_HOST':host}).require_configuration()

    def test_identifiers_cannot_contain_control_characters(self):
        values={'HUB_OPTIMUS_CCTV_HOST':'10.20.30.40','HUB_OPTIMUS_CCTV_SERIAL':'synthetic',
                'HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET':'example'}
        for key in ('HUB_OPTIMUS_CCTV_SERIAL','HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.load({**values,key:'bad\nvalue'}).require_configuration()

if __name__ == '__main__':unittest.main()
