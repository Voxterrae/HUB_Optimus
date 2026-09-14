import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

SITE = Path(__file__).resolve().parents[1] / "site"

def test_versioned_v11_is_complete_byte_identical_alias():
    stable = SITE / "obsidian-HUB_Optimus"
    alias = SITE / "obsidian-HUB_Optimus-v1.1"
    actual = {p.relative_to(stable).as_posix(): p.read_bytes() for p in stable.rglob("*") if p.is_file()}
    copied = {p.relative_to(alias).as_posix(): p.read_bytes() for p in alias.rglob("*") if p.is_file()}
    assert "app-v11.js" in actual and "system.inventory.json" in actual
    assert copied == actual

def test_frozen_v10_matches_verified_release_manifest():
    manifest = json.loads((SITE / "obsidian-release-channels.v1.json").read_text(encoding="utf-8"))
    frozen = manifest["frozen_v1_0"]
    assert frozen["source_commit"] == "115d100e278f38dffe23ce6493fbd1ac0f296de1"
    directory = SITE / frozen["route"]
    actual = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob("*") if p.is_file()}
    assert len(actual) == 8
    assert actual == frozen["files"]
    assert "app-v11.js" not in actual

def test_all_release_routes_have_local_entry_assets():
    class Assets(HTMLParser):
        def __init__(self):
            super().__init__()
            self.refs = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "script" and attrs.get("src"):
                self.refs.append(attrs["src"])
            if tag == "link" and attrs.get("rel") == "stylesheet":
                self.refs.append(attrs["href"])
    for name in ("obsidian-HUB_Optimus", "obsidian-HUB_Optimus-v1.0", "obsidian-HUB_Optimus-v1.1"):
        directory = SITE / name
        parser = Assets()
        parser.feed((directory / "index.html").read_text(encoding="utf-8"))
        assert parser.refs
        for reference in parser.refs:
            split = urlsplit(reference)
            assert not split.scheme and not split.netloc
            asset = (directory / split.path).resolve()
            assert asset.is_relative_to(directory.resolve())
            assert asset.is_file()
        model = json.loads((directory / "system.json").read_text(encoding="utf-8"))
        for reference in model.get("includes", []):
            assert (directory / reference).is_file()
