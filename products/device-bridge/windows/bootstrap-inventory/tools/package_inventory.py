"""Deterministic diagnostic bundle and strict on-disk artifact integrity check.

Hashes compare bundle files to an unauthenticated manifest. They establish no
authorship, approved policy, secure launch, loaded module set or running image.
No host receipt or host-derived digest is accepted as a bundle member.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import struct
import sys
import zipfile
from pathlib import Path

EXE_NAME = "hub-relay-bootstrap-inventory.exe"
TARGET = "x86_64-pc-windows-msvc"
PAYLOAD_FILES = frozenset((EXE_NAME, "LICENSE", "THIRD_PARTY_NOTICES.txt", "README.md",
    "activation-plan.template.json", "scripts/Build-RelayInventory.ps1", "scripts/Run-RelayInventory.ps1",
    "tools/verify_inventory.py", "tools/package_inventory.py"))
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_BUNDLE_BYTES = 256 * 1024 * 1024
# Reviewed Windows platform imports for Rust/MSVC and this fixed Windows adapter.
# Exact names only; a prefix is not permission to load another library.
ALLOWED_DLLS = frozenset(("advapi32.dll", "bcrypt.dll", "crypt32.dll", "dbghelp.dll", "kernel32.dll",
    "ntdll.dll", "ole32.dll", "oleaut32.dll", "secur32.dll", "shell32.dll", "user32.dll",
    "userenv.dll", "ucrtbase.dll", "vcruntime140.dll", "vcruntime140_1.dll", "ws2_32.dll",
    "api-ms-win-core-synch-l1-2-0.dll", "api-ms-win-core-winrt-l1-1-0.dll"))
_MANIFEST_KEYS = frozenset(("schema", "product", "target", "activation", "loaded_image_provenance",
    "build_metadata_authority", "integrity_scope", "source_commit", "policy_sha256", "toolchain",
    "dependencies", "pe_imports", "files"))
_DEPENDENCIES = [dict(name="windows-link", version="0.2.1", license="MIT OR Apache-2.0"),
                 dict(name="windows-sys", version="0.61.2", license="MIT OR Apache-2.0")]


class PackageError(ValueError):
    def __init__(self): super().__init__("Invalid diagnostic package")


class _ClosedParser(argparse.ArgumentParser):
    def error(self,message): self.exit(2,"Invalid diagnostic package arguments.\n")


def _reject(*_unused): raise PackageError() from None


def _unique(pairs):
    result={}
    for key, value in pairs:
        if key in result: _reject()
        result[key]=value
    return result


def _json(raw):
    if len(raw) > 1024 * 1024 or raw.startswith(b"\xef\xbb\xbf"): _reject()
    return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_unique,
                      parse_float=_reject, parse_constant=_reject)


def _canonical(value): return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def _hex(value, length):
    if type(value) is not str or not re.fullmatch("[0-9a-f]{" + str(length) + "}", value): _reject()


def _version(value):
    if type(value) is not str or not 1 <= len(value) <= 256 or any(ord(c) < 32 or ord(c) > 126 for c in value): _reject()


def _safe_node(path):
    info=path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400: _reject()
    return info


def _inventory(root, expected):
    # Check all supplied path ancestors before resolve; resolving would hide links.
    root=Path(os.path.abspath(root))
    for node in (root, *root.parents):
        if not stat.S_ISDIR(_safe_node(node).st_mode): _reject()
    found={}; directories=set(); folded=set(); total=0
    def walk(directory):
        nonlocal total
        for entry in sorted(directory.iterdir(), key=lambda item:item.name):
            relative=entry.relative_to(root).as_posix()
            if ("\\" in relative or ":" in relative or any(part in ("", ".", "..") for part in relative.split("/"))
                    or relative.casefold() in folded): _reject()
            folded.add(relative.casefold()); info=_safe_node(entry)
            if stat.S_ISDIR(info.st_mode):
                directories.add(relative); walk(entry)
            elif stat.S_ISREG(info.st_mode):
                if relative not in expected or info.st_nlink != 1 or not 0 < info.st_size <= MAX_FILE_BYTES: _reject()
                total += info.st_size
                if total > MAX_BUNDLE_BYTES: _reject()
                # Open without following a final symlink, and compare opened identity.
                flags=os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
                descriptor=os.open(entry, flags)
                with os.fdopen(descriptor, "rb") as stream:
                    opened=os.fstat(stream.fileno())
                    if (opened.st_dev, opened.st_ino, opened.st_size) != (info.st_dev, info.st_ino, info.st_size): _reject()
                    data=stream.read(MAX_FILE_BYTES + 1)
                    final=os.fstat(stream.fileno())
                if len(data) != info.st_size or (final.st_size, final.st_mtime_ns) != (opened.st_size, opened.st_mtime_ns): _reject()
                found[relative]=data
            else: _reject()
    walk(root)
    required_directories={part.rsplit("/", 1)[0] for part in expected if "/" in part}
    if found.keys() != expected or directories != required_directories: _reject()
    return found


def pe_imports(data):
    """Parse bounded PE32+ AMD64 import names, including delay imports.

    This records static import tables only; it does not observe runtime loading,
    DLL resolution, signatures, transitive dependencies or dynamic LoadLibrary.
    """
    if len(data) < 256 or data[:2] != b"MZ": _reject()
    pe=struct.unpack_from("<I", data, 0x3C)[0]
    if pe < 64 or pe + 24 > len(data) or data[pe:pe+4] != b"PE\0\0": _reject()
    machine, count, _, _, _, optional_size, characteristics=struct.unpack_from("<HHIIIHH", data, pe+4)
    optional=pe+24
    if (machine != 0x8664 or not 1 <= count <= 96 or optional_size < 240 or optional+optional_size+count*40 > len(data)
            or not characteristics & 2 or characteristics & 0x2000 or struct.unpack_from("<H", data, optional)[0] != 0x20B): _reject()
    number=struct.unpack_from("<I",data,optional+108)[0]
    if number < 14 or number > 16: _reject()
    headers=struct.unpack_from("<I",data,optional+60)[0]
    if not optional+optional_size+count*40 <= headers <= len(data): _reject()
    image_base=struct.unpack_from("<Q",data,optional+24)[0]
    sections=[]
    for index in range(count):
        section=optional+optional_size+index*40
        virtual_size, virtual, raw_size, raw=struct.unpack_from("<IIII",data,section+8)
        if raw_size and (raw < headers or raw+raw_size > len(data)): _reject()
        span=max(virtual_size, raw_size)
        if virtual+span > 0x100000000: _reject()
        if any(virtual < end and start < virtual+span for start,end,_,_ in sections): _reject()
        sections.append((virtual,virtual+span,raw,raw_size))
    def offset(rva, size):
        if not 0 <= rva <= 0xFFFFFFFF or size < 0: _reject()
        if rva < headers and rva+size <= headers: return rva
        matches=[(start,raw,raw_size) for start,end,raw,raw_size in sections if start <= rva and rva+size <= end]
        if len(matches) != 1: _reject()
        start,raw,raw_size=matches[0]
        if rva-start+size > raw_size: _reject()
        return raw+rva-start
    def dll_name(rva):
        result=bytearray()
        for index in range(257):
            byte=data[offset(rva+index,1)]
            if byte == 0:
                if not result: _reject()
                value=result.decode("ascii", "strict").lower()
                if value not in ALLOWED_DLLS: _reject()
                return value
            if not 33 <= byte <= 126 or byte in (47, 58, 92): _reject()
            result.append(byte)
        _reject()
    imports=set()
    for table_index, entry_size in ((1,20), (13,32)):
        rva,size=struct.unpack_from("<II",data,optional+112+8*table_index)
        if not rva and not size: continue
        if not rva or size < entry_size or size > 1024*1024 or size % entry_size: _reject()
        terminated=False
        for index in range(size//entry_size):
            entry=data[offset(rva+index*entry_size,entry_size):][:entry_size]
            if not any(entry): terminated=True; break
            fields=struct.unpack("<"+"I"*(entry_size//4),entry)
            if table_index == 1: name_rva=fields[3]
            else:
                attributes,name_rva=fields[:2]
                if attributes != 1: _reject()  # RVA-form delay descriptors only.
            imports.add(dll_name(name_rva))
        if not terminated: _reject()
    return sorted(imports)


def _manifest(files, source_commit, policy_sha256, rustc_version, cargo_version, linker_version, sdk_version):
    _hex(source_commit,40); _hex(policy_sha256,64)
    for version in (rustc_version,cargo_version,linker_version,sdk_version): _version(version)
    for product,version in (("rustc",rustc_version),("cargo",cargo_version)):
        if not re.fullmatch(product+r" 1\.99\.0(?: \([0-9a-f]{7,40} [0-9]{4}-[0-9]{2}-[0-9]{2}\))?",version): _reject()
    plan=_json(files["activation-plan.template.json"])
    if type(plan) is not dict or plan.get("activation") != "blocked" or plan.get("loaded_image_provenance") != "not_established": _reject()
    return dict(schema="hub_relay.bootstrap_package.v0.1", product="hub-relay-bootstrap-inventory", target=TARGET,
        activation="blocked", loaded_image_provenance="not_established", build_metadata_authority="unverified_claims",
        integrity_scope="exact_packaged_file_bytes_only", source_commit=source_commit, policy_sha256=policy_sha256,
        toolchain=dict(rustc=rustc_version,cargo=cargo_version,linker=linker_version,sdk=sdk_version),
        dependencies=_DEPENDENCIES, pe_imports=pe_imports(files[EXE_NAME]),
        files={name:dict(byte_length=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in sorted(files.items())})


def create_package(stage, output, *, source_commit, policy_sha256, rustc_version, cargo_version, linker_version, sdk_version):
    """Write a new deterministic ZIP; refuse unlisted input or existing output."""
    output=Path(os.path.abspath(output))
    try:
        for node in (output.parent,*output.parent.parents):
            if not stat.S_ISDIR(_safe_node(node).st_mode): _reject()
        files=_inventory(stage,PAYLOAD_FILES)
        manifest=_manifest(files,source_commit,policy_sha256,rustc_version,cargo_version,linker_version,sdk_version)
        members={**files,"manifest.json":_canonical(manifest)}
        # Exclusive creation, fixed metadata and STORE avoid compressor-version drift.
        with output.open("xb") as stream:
            with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_STORED,allowZip64=False) as archive:
                for name,data in sorted(members.items()):
                    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
                    info.create_system=3; info.external_attr=(stat.S_IFREG|0o644)<<16
                    info.compress_type=zipfile.ZIP_STORED; archive.writestr(info,data)
        return manifest
    except Exception:
        pass
    raise PackageError() from None


def verify_package(root):
    """Compare every extracted bundle file with the manifest; no trust adoption."""
    try:
        files=_inventory(root, PAYLOAD_FILES | {"manifest.json"})
        manifest=_json(files.pop("manifest.json"))
        if type(manifest) is not dict or manifest.keys() != _MANIFEST_KEYS: _reject()
        toolchain=manifest["toolchain"]
        if type(toolchain) is not dict or toolchain.keys() != {"rustc","cargo","linker","sdk"}: _reject()
        expected=_manifest(files,manifest["source_commit"],manifest["policy_sha256"],
            toolchain["rustc"],toolchain["cargo"],toolchain["linker"],toolchain["sdk"])
        # Strict types: Python's True == 1 must not make forged metadata match.
        if _canonical(manifest) != _canonical(expected): _reject()
        return expected
    except Exception:
        pass
    raise PackageError() from None


def main(argv=None):
    parser=_ClosedParser(description="Diagnostic artifact integrity only; activation blocked.")
    parser.add_argument("--verify", metavar="EXTRACTED_DIRECTORY")
    parser.add_argument("--stage"); parser.add_argument("--output")
    for name in ("source-commit","policy-sha256","rustc-version","cargo-version","linker-version","sdk-version"):
        parser.add_argument("--"+name)
    args=parser.parse_args(argv)
    try:
        if args.verify:
            if args.stage or args.output or any(getattr(args,name) for name in ("source_commit","policy_sha256","rustc_version","cargo_version","linker_version","sdk_version")): _reject()
            verify_package(args.verify)
        else:
            if not args.stage or not args.output: _reject()
            create_package(args.stage,args.output,**{name:getattr(args,name) for name in
                ("source_commit","policy_sha256","rustc_version","cargo_version","linker_version","sdk_version")})
        print("Packaged file integrity validated; origin and loaded image not established; activation blocked.")
        return 0
    except Exception:
        print("Diagnostic package validation failed; no authority established.",file=sys.stderr)
        return 1


if __name__ == "__main__": sys.exit(main())
