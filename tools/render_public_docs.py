"""Render an explicit, immutable public reading collection without network I/O.

Pinned Git blob IDs keep reproduction possible after a squash merge. When the
source commit is present, its path-to-blob association is also checked. Every
source is checksum-verified; working-tree Markdown is never substituted.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import posixpath
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit

from markdown_it import MarkdownIt

REPOSITORY = "https://github.com/Voxterrae/HUB_Optimus"
MANIFEST = "site/data/public-documents.v1.json"
LANGUAGES = {"es": "Español", "en": "English", "de": "Deutsch", "ca": "Català",
             "fr": "Français", "ru": "Русский", "he": "עברית", "zh-Hans": "简体中文"}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
SLUG = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if result.returncode:
        raise ValueError("unavailable pinned Git object: " + " ".join(args[:2]))
    return result.stdout


def load_sources(root: Path, manifest: dict) -> list[dict]:
    ref = manifest.get("source_ref", "")
    if not HEX40.fullmatch(ref):
        raise ValueError("source_ref must be an immutable commit SHA")
    records, ids, paths = [], set(), set()
    commit_available = subprocess.run(["git", "cat-file", "-e", ref + "^{commit}"],
                                      cwd=root, capture_output=True).returncode == 0
    for path, binding in manifest.get("link_targets", {}).items():
        if (PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
                or "\\" in path or binding.get("kind") not in {"blob", "tree"}
                or not HEX40.fullmatch(binding.get("git_oid", ""))):
            raise ValueError("invalid source target binding")
        if commit_available:
            oid = _git(root, "rev-parse", ref + ":" + path).decode().strip()
            kind = _git(root, "cat-file", "-t", oid).decode().strip()
            if oid != binding["git_oid"] or kind != binding["kind"]:
                raise ValueError("source target binding mismatch")
    for entry in manifest.get("documents", []):
        name, path = entry.get("id", ""), entry.get("path", "")
        parts = PurePosixPath(path)
        if not SLUG.fullmatch(name) or name in ids:
            raise ValueError("invalid or duplicate public document ID")
        if (not path or parts.is_absolute() or ".." in parts.parts or "\\" in path
                or parts.suffix != ".md" or path in paths
                or any(p.startswith(".") for p in parts.parts)
                or any(ord(c) < 32 for c in path)):
            raise ValueError("invalid public Markdown path")
        if (entry.get("language") not in LANGUAGES
                or entry.get("metadata_language", "es") not in LANGUAGES):
            raise ValueError("unknown source language")
        blob = entry.get("git_blob_sha", "")
        if not HEX40.fullmatch(blob):
            raise ValueError("source blob must be pinned")
        if commit_available:
            bound = _git(root, "rev-parse", ref + ":" + path).decode().strip()
            if bound != blob:
                raise ValueError("source path-to-blob binding mismatch")
        content = _git(root, "cat-file", "blob", blob)
        if hashlib.sha256(content).hexdigest() != entry.get("sha256"):
            raise ValueError("source checksum mismatch")
        text = content.decode("utf-8", errors="strict")
        records.append({**entry, "bytes": content, "text": text, "source_ref": ref,
                        "link_targets": manifest.get("link_targets", {})})
        ids.add(name)
        paths.add(path)
    if not records:
        raise ValueError("empty public collection")
    for record in records:
        if not set(record.get("variants", {}).values()) <= ids:
            raise ValueError("unknown document variant")
        for language, target in record.get("variants", {}).items():
            actual = next(r for r in records if r["id"] == target)
            if actual["language"] != language:
                raise ValueError("variant language mismatch")
    expected = {"/docs/", *(f'/docs/{r["id"]}/' for r in records)}
    if set(manifest.get("routes", [])) != expected:
        raise ValueError("explicit public routes do not match the collection")
    return records


def _slug(text: str) -> str:
    return re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", text.lower())).strip("-") or "section"


def _headings(tokens: list) -> list[tuple[str, str, str]]:
    counts, used, result = {}, set(), []
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        inline = tokens[index + 1]
        title = "".join(t.content for t in inline.children or [] if t.type in {"text", "code_inline"})
        stem = _slug(title)
        count = counts.get(stem, 0)
        anchor = stem + (f"-{count}" if count else "")
        while anchor in used:
            count += 1
            anchor = stem + f"-{count}"
        counts[stem] = count + 1
        used.add(anchor)
        token.attrSet("id", "doc-" + anchor)
        result.append((anchor, title, token.tag))
    return result


def _parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable("table")


def _heading_ids(record: dict) -> set[str]:
    return {x[0] for x in _headings(_parser().parse(record["text"]))}


def _safe_link(href: str, record: dict, records: list[dict], root: Path) -> str | None:
    if any(ord(c) < 32 for c in href):
        return None
    try:
        url = urlsplit(href)
    except ValueError:
        return None
    if url.scheme:
        return href if url.scheme.lower() in {"https", "http"} and url.netloc else None
    if url.netloc or href.startswith("//"):
        return None
    path = unquote(url.path)
    fragment = unquote(url.fragment)
    if not path:
        if fragment in _heading_ids(record):
            return "#doc-" + fragment
        return None
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(record["path"]), path))
    if resolved.startswith("../") or resolved.startswith("/") or "\\" in resolved:
        return None
    target = next((r for r in records if r["path"] == resolved), None)
    if target and (not fragment or fragment in _heading_ids(target)):
        return f'../{target["id"]}/index.html' + ("#doc-" + fragment if fragment else "")
    binding = record.get("link_targets", {}).get(resolved)
    if binding:
        kind = binding.get("kind")
    else:
        try:
            kind = _git(root, "cat-file", "-t", record["source_ref"] + ":" + resolved).decode().strip()
        except ValueError:
            return None
    if kind not in {"blob", "tree"}:
        return None
    suffix = ("?" + url.query if url.query else "") + ("#" + url.fragment if url.fragment else "")
    return f'{REPOSITORY}/{kind}/{record["source_ref"]}/{quote(resolved, safe="/")}' + suffix


def _rewrite(tokens: list, record: dict, records: list[dict], root: Path) -> None:
    for token in tokens:
        if token.children:
            _rewrite(token.children, record, records, root)
    disabled = []
    for token in tokens:
        if token.type == "link_open":
            safe = _safe_link(token.attrGet("href") or "", record, records, root)
            disabled.append(safe is None)
            if safe is None:
                token.tag = "span"
                token.attrs = {"class": "reader-unavailable", "title": "Referencia no disponible en este corte"}
            else:
                token.attrSet("href", safe)
                token.attrSet("referrerpolicy", "no-referrer")
                if safe.startswith("../") and "/index.html" in safe:
                    token.attrSet("data-reader-document", "")
        elif token.type == "link_close" and disabled:
            if disabled.pop():
                token.tag = "span"


def _language_links(record: dict) -> str:
    links = []
    for language, label in LANGUAGES.items():
        target = record.get("variants", {}).get(language, record["id"])
        actual = language if language in record.get("variants", {}) else record["language"]
        links.append(f'<a href="../{target}/index.html?lang={language}" hreflang="{actual}" '
                     f'data-reader-language="{language}" lang="{language}">{label}</a>')
    return "\n".join(links)


def _shell(title: str, body: str, *, language: str, prefix: str, source_language: str,
           language_links: str, source_id: str = "", source_languages: str = "",
           title_language: str = "es") -> str:
    direction = "rtl" if language == "he" else "ltr"
    e = html.escape
    return f'''<!doctype html>
<html lang="{language}" dir="{direction}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'">
<title lang="{title_language}">{e(title)} · HUB_Optimus</title>
<link rel="stylesheet" href="{prefix}reading.css"><script src="{prefix}reading.js" defer></script></head>
<body data-source-language="{source_language}" data-source-id="{source_id}" data-source-languages="{e(source_languages)}">
<a class="reader-skip" href="#reader-main" data-reader-copy="skip">Ir al documento</a>
<header class="reader-header"><a class="reader-brand" href="{prefix}../">HUB_Optimus</a>
<nav aria-label="Navegación" data-reader-controls><a href="{prefix}index.html" data-reader-home data-reader-copy="collection">Conoce y explora</a>
<a href="{prefix}../operator/?lang=es#product_intake" data-reader-operator data-reader-copy="operator">Probar Operator</a></nav></header>
<div class="reader-language" data-reader-controls><p data-reader-copy="language">Idioma de navegación</p>
<nav aria-label="Idiomas">{language_links}</nav>
<p id="reader-language-notice" role="status">El texto conserva el idioma de su fuente. Las traducciones que falten se indican expresamente.</p></div>
<main id="reader-main" class="reader-main">{body}</main>
<footer class="reader-footer"><p data-reader-copy="boundary">Las explicaciones ayudan a leer; los documentos originales mantienen su autoridad y su estado. La interfaz no certifica traducción ni producción.</p>
<a href="{prefix}index.html" data-reader-home data-reader-copy="collection">Conoce y explora</a></footer></body></html>
'''


def render_document(record: dict, records: list[dict], root: Path) -> str:
    parser = _parser()
    tokens = parser.parse(record["text"])
    headings = _headings(tokens)
    _rewrite(tokens, record, records, root)

    def image(tokens, index, options, env):
        token = tokens[index]
        safe = _safe_link(token.attrGet("src") or "", record, records, root)
        alt = html.escape(token.content)
        return (f'<span class="reader-image">[Imagen: {alt}] '
                + (f'<a href="{html.escape(safe, quote=True)}" referrerpolicy="no-referrer">ver fuente</a>' if safe else "")
                + "</span>")

    parser.renderer.rules["image"] = image
    parser.renderer.rules["table_open"] = lambda *args: '<div class="reader-table" role="region" aria-label="Tabla" tabindex="0"><table>\n'
    parser.renderer.rules["table_close"] = lambda *args: '</table></div>\n'
    article = parser.renderer.render(tokens, parser.options, {})
    toc = "".join(f'<li><a href="#doc-{html.escape(anchor, quote=True)}">{html.escape(title)}</a></li>'
                  for anchor, title, tag in headings if tag in {"h1", "h2", "h3"})
    source = html.escape(f'{REPOSITORY}/blob/{record["source_ref"]}/{quote(record["path"], safe="/")}', quote=True)
    context = record.get("context", "Texto completo de la fuente; conserva sus límites y su estado.")
    metadata_language = record.get("metadata_language", "es")
    source_direction = "rtl" if record["language"] == "he" else "ltr"
    body = f'''<div class="reader-intro"><p class="reader-kicker">HUB_Optimus · lectura con fuente</p>
<h1 lang="{metadata_language}">{html.escape(record["title"])}</h1><p lang="{metadata_language}">{html.escape(context)}</p>
<p class="reader-source">Fuente: <a href="{source}" referrerpolicy="no-referrer">{html.escape(record["path"])}</a><br>
<span>Commit: <bdi>{record["source_ref"]}</bdi></span><br>
<span>SHA-256: <bdi>{record["sha256"]}</bdi></span><br>
<a href="source.md" download data-reader-copy="download">Descargar el Markdown original</a></p></div>
<div class="reader-layout"><aside class="reader-toc"><h2 data-reader-copy="contents">En esta página</h2><ol lang="{record['language']}" dir="{source_direction}">{toc}</ol></aside>
<article class="reader-article" lang="{record["language"]}" dir="{'rtl' if record["language"] == 'he' else 'ltr'}">{article}</article></div>'''
    return _shell(record["title"], body, language="es", prefix="../",
                  source_language=record["language"], language_links=_language_links(record),
                  source_id=record["id"], source_languages=record.get("source_languages", ""),
                  title_language=metadata_language)


def render_index(records: list[dict], manifest: dict) -> str:
    cards = "".join(f'<li><a href="./{r["id"]}/index.html" lang="{r.get("metadata_language", "es")}" data-reader-document>{html.escape(r["title"])}</a>'
                    f'<p lang="{r.get("metadata_language", "es")}">{html.escape(r.get("context", ""))}</p><span class="reader-badge">Fuente {r["language"]}</span></li>' for r in records)
    body = f'''<section class="reader-intro"><p class="reader-kicker">HUB_Optimus · una entrada para cada interés</p>
<h1>Entender, probar y comprobar.</h1><p>Una plataforma creada y dirigida por Benjamin Gerrit Hoff para organizar fuentes, preparar trabajo revisable y mantener la decisión humana.</p>
<div class="reader-actions"><a href="./conoce/index.html" data-reader-document>Conoce HUB_Optimus</a><a href="./operator-piloto/index.html" data-reader-document>Tu primer caso con Operator</a></div>
<p>Empieza por la explicación y un ejemplo. Después puedes explorar capacidades, historia y textos completos de gobierno con su fuente.</p>
<p>La metodología y las herramientas tienen madureces distintas. Una norma, un prototipo y un servicio aceptado representan estados diferentes.</p></section>
<section><h2>Elige tu recorrido</h2><ul class="reader-cards">{cards}</ul></section>
<p class="reader-source">Colección revisada: {html.escape(manifest["reviewed_on"])} · Fuente: <bdi>{manifest["source_ref"]}</bdi>. Contenido versionado; no indica estado vivo de servicios.</p>'''
    language_links = "\n".join(f'<a href="index.html?lang={code}" hreflang="es" lang="{code}" data-reader-language="{code}">{label}</a>' for code, label in LANGUAGES.items())
    return _shell("Conoce y explora", body, language="es", prefix="./", source_language="es", language_links=language_links)


def generate(root: Path, check: bool = False) -> list[Path]:
    root = root.resolve()
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    records = load_sources(root, manifest)
    outputs = {root / "site/docs/index.html": render_index(records, manifest).encode("utf-8")}
    for record in records:
        outputs[root / "site/docs" / record["id"] / "index.html"] = render_document(record, records, root).encode("utf-8")
        outputs[root / "site/docs" / record["id"] / "source.md"] = record["bytes"]
    drift = [str(path.relative_to(root)) for path, content in outputs.items()
             if not path.exists() or path.read_bytes() != content]
    if check and drift:
        raise ValueError("generated artifact drift: " + ", ".join(drift))
    if not check:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_bytes() != content:
                path.write_bytes(content)
    return list(outputs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        paths = generate(args.root, args.check)
    except (ValueError, UnicodeError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(f"{'Checked' if args.check else 'Generated'} {len(paths)} public reading artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
