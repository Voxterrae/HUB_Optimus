"""Acceptance for a finite public data artifact; never query a Web provider."""

import hashlib
import importlib.util
import io
import json
import re
import zipfile

import pytest


from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "products/browser/search/tools/build_public_pilot.py"


def test_cli_builds_reproducible_public_data(tmp_path):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    for output in (first, second):
        completed = subprocess.run(
            [sys.executable, str(BUILDER), "--output", str(output)],
            cwd=tmp_path, capture_output=True, text=True, check=False,
        )
        assert completed.returncode == 0, completed.stderr
    assert first.read_bytes() == second.read_bytes()


SPEC = importlib.util.spec_from_file_location("optimus_public_pilot", BUILDER)
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)
BASE = "d77ede8f834fb1e4b078923866a55506e8f64e2d"
URLS = (
    f"https://github.com/Voxterrae/HUB_Optimus/blob/{BASE}/products/browser/search/README.md",
    f"https://github.com/Voxterrae/HUB_Optimus/blob/{BASE}/products/browser/search/docs/PROTOCOL.md",
    "https://support.microsoft.com/en-us/accessibility/windows/change-color-contrast-in-windows",
    "https://support.microsoft.com/es-es/accessibility/windows/keyboard-shortcuts-in-windows",
    "https://learn.microsoft.com/en-us/azure/container-apps/overview",
    "https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction",
    "https://learn.microsoft.com/en-us/entra/identity-platform/authentication-vs-authorization",
    "https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets",
)
SOURCE = "Optimus — resúmenes propios de referencias públicas"


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def rebind(catalog, provenance):
    provenance["catalogCanonicalSha256"] = hashlib.sha256(canonical(catalog)).hexdigest()
    for document, entry in zip(catalog["documents"], provenance["entries"]):
        entry["url"] = document["url"]
        entry["summarySha256"] = hashlib.sha256(document["content"].encode("utf-8")).hexdigest()


@pytest.fixture
def public_data():
    stamp = "2026-11-03T19:30:00Z"
    catalog = {"schemaVersion": 1, "documents": [
        {"url": url, "title": f"Referencia pública {index}",
         "content": f"Resumen propio público número {index}.", "source": SOURCE,
         "updatedUtc": stamp} for index, url in enumerate(URLS)
    ]}
    provenance = {
        "schemaVersion": 1, "catalogId": "optimus-public-pilot-v0.1", "language": "es",
        "contentKind": "optimus-authored-summaries",
        "classification": "public-reviewed-reference-summaries", "generalWebCoverage": False,
        "snapshotUtc": stamp, "catalogCanonicalSha256": "",
        "entries": [{"url": url, "referenceKind": "github-immutable" if i < 2 else "microsoft-live",
                     "sourceRevision": BASE if i < 2 else None, "summarySha256": "",
                     "referenceCheckedDate": "2026-11-03"} for i, url in enumerate(URLS)],
    }
    rebind(catalog, provenance)
    return catalog, provenance


def archive_for(pair):
    return pilot.assemble(*(canonical(value) for value in pair))


def test_archive_members_checksums_and_format_are_portable(public_data):
    catalog, provenance = public_data
    data = archive_for(public_data)
    assert data == pilot.assemble(canonical(catalog).replace(b"\n", b"\r\n"),
                                  canonical(provenance).replace(b"\n", b"\r\n"))
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.namelist() == ["catalog.json", "provenance.json", "README.txt", "SHA256SUMS.txt"]
        assert archive.testzip() is None
        assert archive.read("catalog.json") == canonical(catalog)
        assert archive.read("provenance.json") == canonical(provenance)
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.create_system == 3
            assert info.external_attr == 0o100644 << 16
        checks = archive.read("SHA256SUMS.txt").decode("ascii").splitlines()
        assert len(checks) == 3
        for line, name in zip(checks, archive.namelist()[:3]):
            assert line == hashlib.sha256(archive.read(name)).hexdigest() + "  " + name
        assert "not general Web" in archive.read("README.txt").decode("utf-8")


@pytest.mark.parametrize("mutation", [
    "version_bool", "extra_catalog_field", "extra_document_field", "extra_provenance_field",
    "extra_entry_field", "duplicate_url", "missing_document", "unapproved_https", "private_http",
    "credentials", "query", "fragment", "live_github_branch", "non_utc", "invalid_date",
    "date_mismatch", "wrong_review_date", "future_review_date", "bad_revision", "wrong_kind",
    "unicode_year", "coverage_claim", "wrong_language", "wrong_classification", "wrong_source", "empty_summary",
    "oversized_summary", "control_title", "oversized_title", "hash_mismatch", "summary_hash_mismatch",
])
def test_rejects_unreviewed_or_inconsistent_data(public_data, mutation):
    catalog, provenance = public_data
    document = catalog["documents"][0]
    if mutation == "version_bool":
        catalog["schemaVersion"] = True
    elif mutation == "extra_catalog_field":
        catalog["profile"] = "PRIVATE_SENTINEL"
    elif mutation == "extra_document_field":
        document["token"] = "PRIVATE_SENTINEL"
    elif mutation == "extra_provenance_field":
        provenance["extra"] = "PRIVATE_SENTINEL"
    elif mutation == "extra_entry_field":
        provenance["entries"][0]["extra"] = "PRIVATE_SENTINEL"
    elif mutation == "duplicate_url":
        catalog["documents"][1]["url"] = document["url"]
    elif mutation == "missing_document":
        catalog["documents"].pop()
    elif mutation in {"unapproved_https", "private_http", "credentials", "query", "fragment", "live_github_branch"}:
        document["url"] = {
            "unapproved_https": "https://private.example/PRIVATE_SENTINEL",
            "private_http": "http://127.0.0.1/PRIVATE_SENTINEL",
            "credentials": URLS[0].replace("https://", "https://PRIVATE_SENTINEL@"),
            "query": URLS[0] + "?token=PRIVATE_SENTINEL",
            "fragment": URLS[0] + "#PRIVATE_SENTINEL",
            "live_github_branch": URLS[0].replace(BASE, "main"),
        }[mutation]
    elif mutation == "unicode_year":
        document["updatedUtc"] = "٢٠٢٦-11-03T19:30:00Z"
    elif mutation == "non_utc":
        document["updatedUtc"] = "2026-11-03T20:30:00+01:00"
    elif mutation == "invalid_date":
        provenance["snapshotUtc"] = "2026-02-30T00:00:00Z"
    elif mutation == "date_mismatch":
        document["updatedUtc"] = "2026-11-02T19:30:00Z"
    elif mutation == "wrong_review_date":
        provenance["entries"][0]["referenceCheckedDate"] = "2026-02-30"
    elif mutation == "future_review_date":
        provenance["entries"][0]["referenceCheckedDate"] = "2026-11-04"
    elif mutation == "bad_revision":
        provenance["entries"][0]["sourceRevision"] = "main"
    elif mutation == "wrong_kind":
        provenance["entries"][0]["referenceKind"] = "microsoft-live"
    elif mutation == "coverage_claim":
        provenance["generalWebCoverage"] = True
    elif mutation == "wrong_language":
        provenance["language"] = "en"
    elif mutation == "wrong_classification":
        provenance["classification"] = "automatic-dlp-certified"
    elif mutation == "wrong_source":
        document["source"] = "Microsoft official endorsement"
    elif mutation == "empty_summary":
        document["content"] = "   "
    elif mutation == "oversized_summary":
        document["content"] = "á" * 32769
    elif mutation == "control_title":
        document["title"] = "PRIVATE\nSENTINEL"
    elif mutation == "oversized_title":
        document["title"] = "😀" * 121
    rebind(catalog, provenance)
    if mutation == "hash_mismatch":
        provenance["catalogCanonicalSha256"] = "0" * 64
    elif mutation == "summary_hash_mismatch":
        provenance["entries"][0]["summarySha256"] = "0" * 64
    with pytest.raises(pilot.PilotError):
        archive_for(public_data)


@pytest.mark.parametrize("which", [0, 1])
def test_duplicate_json_keys_are_rejected(public_data, which):
    raw = [canonical(value) for value in public_data]
    raw[which] = raw[which].replace(b'{', b'{"schemaVersion":1,', 1)
    with pytest.raises(pilot.PilotError):
        pilot.assemble(*raw)


@pytest.mark.parametrize("raw", [b"{}" * 150000, b'{"schemaVersion":NaN}', b'\xff', b'[]'])
def test_bad_or_oversized_json_is_rejected(public_data, raw):
    with pytest.raises(pilot.PilotError):
        pilot.assemble(raw, canonical(public_data[1]))


def test_fixed_sources_ignore_private_cwd_and_unknown_input(tmp_path):
    private = tmp_path / "private-profile.json"
    sentinel = "PRIVATE_PROFILE_SENTINEL_NOT_FOR_ARTIFACT"
    private.write_text(sentinel, encoding="utf-8")
    output = tmp_path / "public.zip"
    result = subprocess.run([sys.executable, str(BUILDER), "--output", str(output)],
                            cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert sentinel.encode() not in output.read_bytes()
    assert sentinel not in result.stdout + result.stderr
    bad_output = tmp_path / "must-not-exist.zip"
    rejected = subprocess.run([sys.executable, str(BUILDER), "--input", str(private),
                               "--output", str(bad_output)], cwd=tmp_path,
                              capture_output=True, text=True, check=False)
    assert rejected.returncode == 2
    assert str(private) not in rejected.stdout + rejected.stderr
    assert not bad_output.exists()


def invoke(output):
    return pilot.main(["--output", str(output)])


def test_existing_output_is_preserved_and_errors_are_generic(tmp_path, capsys):
    output = tmp_path / "PRIVATE_SENTINEL.zip"
    output.write_bytes(b"prior-data")
    assert invoke(output) == 2
    assert output.read_bytes() == b"prior-data"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PRIVATE_SENTINEL" not in captured.err


def test_relative_output_is_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert invoke(Path("relative.zip")) == 2
    assert not (tmp_path / "relative.zip").exists()


@pytest.mark.parametrize("link_kind", ["output", "parent", "source"])
def test_symbolic_links_are_rejected(tmp_path, monkeypatch, public_data, link_kind):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    target = real_dir / "prior.zip"
    target.write_bytes(b"prior-data")
    output = tmp_path / "new.zip"
    link = tmp_path / "link"
    try:
        if link_kind == "output":
            link.symlink_to(target)
            output = link
        elif link_kind == "parent":
            link.symlink_to(real_dir, target_is_directory=True)
            output = link / "new.zip"
        else:
            target = real_dir / "catalog.json"
            target.write_bytes(canonical(public_data[0]))
            link.symlink_to(target)
            monkeypatch.setattr(pilot, "CATALOG_PATH", link)
    except OSError:
        pytest.skip("Platform does not permit test-local symlinks")
    assert invoke(output) == 2
    assert (real_dir / "prior.zip").read_bytes() == b"prior-data"
    assert not (real_dir / "new.zip").exists()
    if link_kind == "source":
        assert not output.exists()


def test_invalid_fixed_source_creates_no_output(tmp_path, monkeypatch, capsys):
    invalid = tmp_path / "PRIVATE_SENTINEL.json"
    invalid.write_text('{"PRIVATE_SENTINEL":true}', encoding="utf-8")
    monkeypatch.setattr(pilot, "CATALOG_PATH", invalid)
    output = tmp_path / "output.zip"
    assert invoke(output) == 2
    assert not output.exists()
    assert "PRIVATE_SENTINEL" not in capsys.readouterr().err


@pytest.mark.parametrize("damage", ["checksum", "extra_member", "external_digest", None])
def test_documented_verification_survives_python_optimization(tmp_path, public_data, damage):
    artifact = tmp_path / "reviewed.zip"
    good = archive_for(public_data)
    if damage in {"checksum", "extra_member"}:
        with zipfile.ZipFile(io.BytesIO(good)) as original, zipfile.ZipFile(artifact, "w") as changed:
            for name in original.namelist():
                data = original.read(name)
                if damage == "checksum" and name == "catalog.json":
                    data += b" "
                changed.writestr(name, data)
            if damage == "extra_member":
                changed.writestr("unreviewed.txt", "unreviewed")
    else:
        artifact.write_bytes(good)
    digest = "0" * 64 if damage == "external_digest" else hashlib.sha256(artifact.read_bytes()).hexdigest()
    docs = (ROOT / "products/browser/search/docs/PUBLIC_PILOT.md").read_text(encoding="utf-8")
    snippet = re.search(r"```python\n(.*?)```", docs, flags=re.S).group(1)
    snippet = snippet.replace("'/ruta/absoluta/public-pilot-v0.1.zip'", repr(str(artifact)))
    snippet = snippet.replace("SHA256_DE_LA_ENTREGA_REVISADA", digest)
    result = subprocess.run([sys.executable, "-O", "-c", snippet], cwd=tmp_path,
                            capture_output=True, text=True, check=False)
    if damage is None:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0, "Optimized verification accepted damaged/unreviewed artifact"
