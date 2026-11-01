"""Bundle integrity checks do not establish origin or loaded-image provenance."""
import hashlib
import json
import shutil
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

import package_inventory as package


def pe(machine=0x8664):
    data = bytearray(1024)
    data[:2] = b"MZ"; struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x84, machine, 1, 0, 0, 0, 240, 0x22)
    struct.pack_into("<H", data, 0x98, 0x20B)
    struct.pack_into("<I", data, 0x98+60, 512)
    struct.pack_into("<I", data, 0x98+108, 16)
    section = 0x98 + 240
    data[section:section+8] = b".rdata\0\0"
    struct.pack_into("<IIII", data, section+8, 512, 0x1000, 512, 512)
    return bytes(data)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.stage=self.base/"stage"; self.stage.mkdir()
        for name in package.PAYLOAD_FILES:
            target = self.stage/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(pe() if name.endswith(".exe") else b"synthetic reviewed asset\n")
        (self.stage/"activation-plan.template.json").write_text(json.dumps({"activation":"blocked","loaded_image_provenance":"not_established"}))
        self.meta = dict(source_commit="a"*40, policy_sha256="b"*64, rustc_version="rustc 1.99.0",
                         cargo_version="cargo 1.99.0", linker_version="14.44", sdk_version="10.0.26100.0")

    def build(self, filename="package.zip"):
        output = self.base/filename
        package.create_package(self.stage, output, **self.meta)
        return output

    def test_deterministic_exact_bundle(self):
        first=self.build(); second=self.build("other.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        unpacked=self.base/"unpacked"
        with zipfile.ZipFile(first) as archive: archive.extractall(unpacked)
        manifest = package.verify_package(unpacked)
        self.assertEqual(manifest["activation"], "blocked")
        self.assertEqual(manifest["loaded_image_provenance"], "not_established")
        self.assertEqual(set(manifest["files"]), set(package.PAYLOAD_FILES))

    def test_missing_extra_links_case_collision_and_output_overwrite_refuse(self):
        (self.stage/"foreign.txt").write_text("foreign")
        with self.assertRaises(package.PackageError): self.build()
        (self.stage/"foreign.txt").unlink()
        (self.stage/"README.md").unlink()
        with self.assertRaises(package.PackageError): self.build()
        (self.stage/"README.md").symlink_to(self.stage/"LICENSE")
        with self.assertRaises(package.PackageError): self.build()
        (self.stage/"README.md").unlink(); (self.stage/"README.md").write_text("ok")
        output=self.build()
        with self.assertRaises(package.PackageError): package.create_package(self.stage, output, **self.meta)

    def test_tamper_missing_foreign_and_approved_manifest_refuse(self):
        archive=self.build(); unpacked=self.base/"unpacked"
        with zipfile.ZipFile(archive) as zipped: zipped.extractall(unpacked)
        (unpacked/"README.md").write_text("changed")
        with self.assertRaises(package.PackageError): package.verify_package(unpacked)
        shutil.rmtree(unpacked)
        with zipfile.ZipFile(archive) as zipped: zipped.extractall(unpacked)
        manifest=json.loads((unpacked/"manifest.json").read_text()); manifest["activation"]="approved"
        (unpacked/"manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(package.PackageError): package.verify_package(unpacked)

    def test_wrong_machine_nonpe_and_bad_metadata_refuse(self):
        exe=self.stage/"hub-relay-bootstrap-inventory.exe"
        for data in (pe(0xAA64), b"not a PE", pe()[:200]):
            exe.write_bytes(data)
            with self.assertRaises(package.PackageError): self.build()
        exe.write_bytes(pe()); self.meta["source_commit"]="../foreign"
        with self.assertRaises(package.PackageError): self.build()

    def test_hardlink_and_foreign_directory_refuse(self):
        import os
        original=self.stage/"README.md"; original.unlink()
        os.link(self.stage/"LICENSE",original)
        with self.assertRaises(package.PackageError): self.build()
        original.unlink(); original.write_text("ok")
        (self.stage/"extra").mkdir()
        with self.assertRaises(package.PackageError): self.build()

    def test_foreign_executable_dependency_refuses(self):
        data=bytearray(pe()); struct.pack_into("<II",data,0x98+112+8,0x1000,40)
        struct.pack_into("<IIIII",data,512,0,0,0,0x1040,0)
        data[576:587]=b"foreign.dll"
        (self.stage/"hub-relay-bootstrap-inventory.exe").write_bytes(data)
        with self.assertRaises(package.PackageError): self.build()

    def test_nonpinned_version_prefix_refuses(self):
        self.meta["rustc_version"]="rustc 1.99.01 forged"
        with self.assertRaises(package.PackageError): self.build()

    def test_symlink_output_parent_refuses(self):
        real=self.base/"real"; real.mkdir(); linked=self.base/"linked"; linked.symlink_to(real,target_is_directory=True)
        with self.assertRaises(package.PackageError): package.create_package(self.stage,linked/"package.zip",**self.meta)


if __name__ == "__main__": unittest.main()
