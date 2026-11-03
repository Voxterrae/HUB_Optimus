#!/usr/bin/env python3
"""Build the reviewed public pilot data only; no network or profile inputs."""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
from datetime import date, datetime
import unicodedata
import zipfile

CATALOG_PATH = Path(__file__).resolve().parents[1] / "catalog/public-pilot-v0.1.json"
PROVENANCE_PATH = CATALOG_PATH.with_name("public-pilot-v0.1.provenance.json")
CATALOG_ID = "optimus-public-pilot-v0.1"
SOURCE = "Optimus — resúmenes propios de referencias públicas"
SOURCE_REVISION = "d77ede8f834fb1e4b078923866a55506e8f64e2d"
APPROVED_URLS = (
    f"https://github.com/Voxterrae/HUB_Optimus/blob/{SOURCE_REVISION}/products/browser/search/README.md",
    f"https://github.com/Voxterrae/HUB_Optimus/blob/{SOURCE_REVISION}/products/browser/search/docs/PROTOCOL.md",
    "https://support.microsoft.com/en-us/accessibility/windows/change-color-contrast-in-windows",
    "https://support.microsoft.com/es-es/accessibility/windows/keyboard-shortcuts-in-windows",
    "https://learn.microsoft.com/en-us/azure/container-apps/overview",
    "https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction",
    "https://learn.microsoft.com/en-us/entra/identity-platform/authentication-vs-authorization",
    "https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets",
)
MAX_SOURCE_BYTES = 256 * 1024
README = (
    "Optimus public pilot v0.1 — eight Spanish authored reference summaries.\n"
    "Finite curated coverage; not general Web search or a deployed Azure service.\n"
    "Public classification is a reviewed assertion, not automatic DLP or endorsement.\n"
    "Hashes cover these catalog/summaries, not the remote article bytes.\n"
    "Verify SHA256SUMS.txt against every data member before manual CLI import.\n"
    "See products/browser/search/docs/PUBLIC_PILOT.md at the source revision.\n"
).encode("utf-8")


class PilotError(ValueError):
    """Invalid public data or output request; never expose raw input values."""


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _require(condition):
    if not condition:
        raise PilotError()


def _fields(value, names):
    _require(type(value) is dict and set(value) == set(names.split()))


def _text(value, maximum=None):
    _require(type(value) is str and bool(value.strip()))
    _require(not any(unicodedata.category(char) == "Cc" for char in value))
    if maximum is not None:
        _require(len(value.encode("utf-16-le")) // 2 <= maximum)


def _utc_stamp(value):
    _require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _sha(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value))


def _validate(catalog, provenance):
    _fields(catalog, "schemaVersion documents")
    _require(type(catalog["schemaVersion"]) is int and catalog["schemaVersion"] == 1)
    documents = catalog["documents"]
    _require(type(documents) is list and len(documents) == len(APPROVED_URLS))
    _fields(provenance, "schemaVersion catalogId language contentKind classification "
            "generalWebCoverage snapshotUtc catalogCanonicalSha256 entries")
    _require(type(provenance["schemaVersion"]) is int and provenance["schemaVersion"] == 1)
    _require(provenance["catalogId"] == CATALOG_ID and provenance["language"] == "es")
    _require(provenance["contentKind"] == "optimus-authored-summaries")
    _require(provenance["classification"] == "public-reviewed-reference-summaries")
    _require(provenance["generalWebCoverage"] is False)
    snapshot = _utc_stamp(provenance["snapshotUtc"])
    _sha(provenance["catalogCanonicalSha256"])
    _require(provenance["catalogCanonicalSha256"] == hashlib.sha256(canonical(catalog)).hexdigest())
    entries = provenance["entries"]
    _require(type(entries) is list and len(entries) == len(documents))
    for index, (document, entry) in enumerate(zip(documents, entries)):
        _fields(document, "url title content source updatedUtc")
        _require(document["url"] == APPROVED_URLS[index])
        _text(document["title"], 240)
        _text(document["content"])
        _require(len(document["content"].encode("utf-8")) <= 64 * 1024)
        _require(document["source"] == SOURCE)
        _require(_utc_stamp(document["updatedUtc"]) == snapshot)
        _fields(entry, "url referenceKind sourceRevision summarySha256 referenceCheckedDate")
        _require(entry["url"] == document["url"])
        _require(entry["referenceKind"] == ("github-immutable" if index < 2 else "microsoft-live"))
        _require(entry["sourceRevision"] == (SOURCE_REVISION if index < 2 else None))
        _sha(entry["summarySha256"])
        _require(entry["summarySha256"] == hashlib.sha256(document["content"].encode("utf-8")).hexdigest())
        checked = entry["referenceCheckedDate"]
        _require(type(checked) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", checked))
        _require(date.fromisoformat(checked) <= snapshot.date())
    return catalog, provenance


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _no_constant(_value):
    raise PilotError()


def _decode(raw):
    _require(type(raw) is bytes and len(raw) <= MAX_SOURCE_BYTES)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                      parse_constant=_no_constant)


def assemble(catalog_bytes, provenance_bytes):
    try:
        catalog, provenance = _validate(_decode(catalog_bytes), _decode(provenance_bytes))
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        raise PilotError() from error
    members = {"catalog.json": canonical(catalog),
               "provenance.json": canonical(provenance), "README.txt": README}
    members["SHA256SUMS.txt"] = "".join(
        hashlib.sha256(data).hexdigest() + "  " + name + "\n"
        for name, data in members.items()
    ).encode("ascii")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in members.items():
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return buffer.getvalue()


def _plain_path(path):
    # Reject existing symlinks and Windows reparse points, including parent directories.
    _require(path.is_absolute() and ".." not in path.parts)
    for part in reversed(path.parents):
        info = part.lstat()
        _require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode))
        _require(not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _read_fixed(path):
    _plain_path(path)
    info = path.lstat()
    _require(stat.S_ISREG(info.st_mode))
    _require(not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode))
        _require(os.fstat(stream.fileno()).st_size <= MAX_SOURCE_BYTES)
        raw = stream.read(MAX_SOURCE_BYTES + 1)
        _require(len(raw) <= MAX_SOURCE_BYTES)
        return raw


def _write_new(output, data):
    _plain_path(output)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    # Exclusive creation never truncates an existing file or follows an output symlink.
    with os.fdopen(os.open(output, flags, 0o600), "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 2 or args[0] != "--output":
            raise PilotError()
        output = Path(args[1])
        if not output.is_absolute():
            raise PilotError()
        data = assemble(_read_fixed(CATALOG_PATH), _read_fixed(PROVENANCE_PATH))
        _write_new(output, data)
        print(f"Built {CATALOG_ID}: 8 documents; sha256={hashlib.sha256(data).hexdigest()}")
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        print("Unable to build public pilot. Check reviewed data and a new absolute output path.",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
