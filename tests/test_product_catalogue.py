"""Keep the repository entry catalogue aligned with reviewed capability records."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_product_catalogue_reports_each_registry_entry_without_status_drift():
    registry = json.loads(
        (ROOT / "site/data/capability-registry.v1.json").read_text(encoding="utf-8")
    )
    catalogue = (ROOT / "products/README.md").read_text(encoding="utf-8")
    rows = {}
    for line in catalogue.splitlines():
        match = re.match(r"^\| `([a-z0-9-]+)` \|", line)
        if match:
            component_id = match.group(1)
            assert component_id not in rows, component_id
            rows[component_id] = line

    assert set(rows) == {component["id"] for component in registry["components"]}
    for component in registry["components"]:
        row = rows[component["id"]]
        assert f'`{component["source_status"]}`' in row
        assert f'`{component["lifecycle_state"]}`' in row
        assert component["evidence"][0]["url"] in row


def test_root_entry_points_link_the_catalogue_and_its_runtime_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    catalogue = (ROOT / "products/README.md").read_text(encoding="utf-8")

    assert "[product catalogue](products/README.md)" in readme
    for marker in (
        "Source integration",
        "static web pilot",
        "Windows",
        "Linux",
        "SearXNG",
        "Wikipedia",
        "activation remains blocked",
        "production writes",
        "IP_NOTICE.md",
    ):
        assert marker in catalogue, marker
