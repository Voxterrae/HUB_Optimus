"""The reading layer publishes pinned public text, never an inferred authority."""

import hashlib
import importlib
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def reader():
    return importlib.import_module("tools.render_public_docs")


@pytest.fixture
def source_repo(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q")
    documents = {
        "docs/a.md": "# Original\n\nPREAMBLE MUST SURVIVE\n\n## Same\n\nEvery normative line.\n\n## Same\n\n[Other](b.md#section) [File](extra.txt)\n\nTAIL MUST SURVIVE\n",
        "docs/b.md": "# Other\n\n## Section\n\nBody.\n",
        "docs/extra.txt": "Public supporting file.\n",
    }
    for name, value in documents.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    git("add", ".")
    git("-c", "commit.gpgSign=false", "-c", "user.name=Fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", "Synthetic source")
    source_ref = git("rev-parse", "HEAD")
    records = []
    for name, slug, language in (("docs/a.md", "a", "es"), ("docs/b.md", "b", "en")):
        records.append({
            "id": slug, "path": name, "language": language,
            "title": slug.upper(), "kind": "normative",
            "sha256": hashlib.sha256((tmp_path / name).read_bytes()).hexdigest(),
            "git_blob_sha": git("rev-parse", source_ref + ":" + name),
        })
    records[0]["variants"] = {"en": "b"}
    manifest = {
        "schema_version": "1.0", "source_ref": source_ref,
        "reviewed_on": "2026-11-14", "documents": records,
        "routes": ["/docs/", "/docs/a/", "/docs/b/"],
    }
    path = tmp_path / "site/data/public-documents.v1.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path, manifest


def test_source_is_complete_byte_exact_and_reproducible(reader, source_repo):
    root, manifest = source_repo
    reader.generate(root)
    page = (root / "site/docs/a/index.html").read_text()
    raw = (root / "site/docs/a/source.md").read_bytes()
    assert raw == (root / "docs/a.md").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["documents"][0]["sha256"]
    assert all(text in page for text in ("PREAMBLE MUST SURVIVE", "Every normative line.", "TAIL MUST SURVIVE"))
    assert manifest["source_ref"] in page
    assert 'id="doc-same"' in page and 'id="doc-same-1"' in page
    assert re.search(
        r'<a\b(?=[^>]*href="\.\./b/index\.html#doc-section")'
        r'(?=[^>]*\bdata-reader-document(?:=|\s|>))[^>]*>', page,
    )
    assert manifest["source_ref"] + '/docs/extra.txt' in page
    assert not re.search(
        r'<a\b(?=[^>]*href="https://)(?=[^>]*\bdata-reader-document(?:=|\s|>))[^>]*>', page,
    )
    before = {p: p.read_bytes() for p in (root / "site/docs").rglob("*") if p.is_file()}
    reader.generate(root, check=True)
    assert before == {p: p.read_bytes() for p in before}


def test_check_detects_artifact_drift_without_writing(reader, source_repo):
    root, _ = source_repo
    reader.generate(root)
    path = root / "site/docs/a/index.html"
    path.write_text(path.read_text() + "changed")
    altered = path.read_bytes()
    with pytest.raises(ValueError, match="drift"):
        reader.generate(root, check=True)
    assert path.read_bytes() == altered


def test_heading_ids_reserve_natural_suffixes_and_repeated_names(reader):
    tokens = reader._parser().parse('# Same\n# Same\n# Same-1\n# Same\n# Same-1\n')
    anchors = [anchor for anchor, _, _ in reader._headings(tokens)]
    assert anchors == ['same', 'same-1', 'same-1-1', 'same-2', 'same-1-2']
    assert len(set(anchors)) == len(anchors)


def test_editorial_shell_and_original_language_are_separate(reader, source_repo):
    root, manifest = source_repo
    records = reader.load_sources(root, manifest)
    record = records[1]
    record['metadata_language'] = 'en'
    record['context'] = 'English editorial context.'
    page = reader.render_document(record, records, root)
    assert '<html lang="es" dir="ltr">' in page
    assert '<p lang="en">English editorial context.</p>' in page
    assert '<article class="reader-article" lang="en" dir="ltr">' in page
    assert '<ol lang="en" dir="ltr">' in page


def test_uncommitted_source_edits_never_replace_reviewed_text(reader, source_repo):
    root, manifest = source_repo
    original = (root / "docs/a.md").read_bytes()
    (root / "docs/a.md").write_text("# Unreviewed replacement\n\nWORKING TREE ONLY\n")
    reader.generate(root)
    assert (root / "site/docs/a/source.md").read_bytes() == original
    page = (root / "site/docs/a/index.html").read_text()
    assert "PREAMBLE MUST SURVIVE" in page
    assert "WORKING TREE ONLY" not in page
    assert manifest["documents"][0]["sha256"] == hashlib.sha256(original).hexdigest()


@pytest.mark.parametrize("field,value", [
    ("path", "../private.md"), ("path", ".env"),
    ("id", "../escape"), ("sha256", "0" * 64),
])
def test_unapproved_paths_ids_or_bytes_are_rejected(reader, source_repo, field, value):
    root, manifest = source_repo
    manifest["documents"][0][field] = value
    with pytest.raises(ValueError):
        reader.load_sources(root, manifest)


def test_mutable_ref_and_wrong_path_binding_are_rejected(reader, source_repo):
    root, manifest = source_repo
    manifest["source_ref"] = "main"
    with pytest.raises(ValueError):
        reader.load_sources(root, manifest)
    manifest["source_ref"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    manifest["documents"][0]["path"] = "docs/b.md"
    with pytest.raises(ValueError):
        reader.load_sources(root, manifest)


def test_relative_target_binding_cannot_claim_a_different_blob(reader, source_repo):
    root, manifest = source_repo
    manifest["link_targets"] = {"docs/extra.txt": {
        "kind": "blob", "git_oid": manifest["documents"][0]["git_blob_sha"]
    }}
    with pytest.raises(ValueError, match="target"):
        reader.load_sources(root, manifest)


def test_raw_html_and_dangerous_urls_never_become_active(reader, source_repo):
    root, manifest = source_repo
    record = reader.load_sources(root, manifest)[0]
    record["text"] = '# Safe\n<script>alert(1)</script>\n\n[x](javascript:alert(1)) [x](file:///etc/passwd) ![image](https://example.invalid/track.png)\n'
    html = reader.render_document(record, reader.load_sources(root, manifest), root)
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html
    assert 'href="javascript:' not in html and 'href="file:' not in html
    assert '<img' not in html
    assert 'src="https://example.invalid' not in html


def test_language_choices_keep_real_source_and_explicit_fallback(reader, source_repo):
    root, _ = source_repo
    reader.generate(root)
    html = (root / "site/docs/a/index.html").read_text()
    assert '<html lang="es" dir="ltr">' in html
    assert 'data-source-language="es"' in html
    assert '../b/index.html?lang=en' in html
    assert 'hreflang="en"' in html
    assert 'data-reader-language="he"' in html
    assert 'source.md' in html
    assert 'app.js' not in html
    assert html.count('data-reader-language=') == 8


def test_checked_in_reader_matches_its_explicit_manifest(reader):
    manifest = json.loads((ROOT / "site/data/public-documents.v1.json").read_text())
    reader.generate(ROOT, check=True)
    ids = {r["id"] for r in manifest["documents"]}
    assert len(ids) == len(manifest["documents"]) == 11
    assert set(manifest["routes"]) == {"/docs/", *(f"/docs/{i}/" for i in ids)}
    assert "operator-piloto" in ids
    for record in reader.load_sources(ROOT, manifest):
        assert (ROOT / "site/docs" / record["id"] / "source.md").read_bytes() == record["bytes"]
    assert re.fullmatch(r"[0-9a-f]{40}", manifest["source_ref"])


def test_portfolio_opens_reading_and_states_public_pasted_text_scope():
    source = (ROOT / "site/index.html").read_text(encoding="utf-8")
    assert 'href="./docs/index.html?lang=en"' in source
    assert 'href="./docs/operator-piloto/index.html?lang=en"' in source
    assert 'data-reader-route' in source
    assert 'public Operator does not fetch it' in source
