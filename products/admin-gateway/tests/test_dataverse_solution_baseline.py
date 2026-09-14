import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
BASELINE_ROOT = PACKAGE_ROOT / "dataverse" / "solutions" / "OptimusAdminGateway"
SCHEMA_PATH = PACKAGE_ROOT / "dataverse" / "schema" / "optimus-admin-gateway.dataverse.json"


def _text(parent: ET.Element, tag: str) -> str:
    node = parent.find(tag)
    assert node is not None, tag
    assert node.text is not None, tag
    return node.text


def test_empty_solution_baseline_matches_the_declared_product_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["solution"]
    verification = json.loads(
        (BASELINE_ROOT / "baseline-verification.json").read_text(encoding="utf-8")
    )
    solution_root = ET.parse(BASELINE_ROOT / "Other" / "Solution.xml").getroot()
    manifest = solution_root.find("SolutionManifest")
    assert manifest is not None
    publisher = manifest.find("Publisher")
    assert publisher is not None

    display_node = manifest.find("LocalizedNames/LocalizedName")
    assert display_node is not None

    assert _text(manifest, "UniqueName") == schema["uniqueName"] == "OptimusAdminGateway"
    assert display_node.attrib["description"] == schema["displayName"] == "Optimus Admin Gateway"
    assert _text(manifest, "Version") == schema["version"] == "0.1.0.0"
    assert _text(manifest, "Managed") == "0"
    assert _text(publisher, "UniqueName") == schema["publisher"] == "HUB_Optimus"
    assert _text(publisher, "CustomizationPrefix") == schema["prefix"] == "opt"
    assert int(_text(publisher, "CustomizationOptionValuePrefix")) == schema["choiceValuePrefix"] == 88483

    root_components = manifest.find("RootComponents")
    missing_dependencies = manifest.find("MissingDependencies")
    assert root_components is not None and len(root_components) == 0
    assert missing_dependencies is not None and len(missing_dependencies) == 0

    assert verification == {
        "SolutionDisplayName": "Optimus Admin Gateway",
        "SolutionUniqueName": "OptimusAdminGateway",
        "Version": "0.1.0.0",
        "ManagedFlag": "0",
        "PublisherUniqueName": "HUB_Optimus",
        "PublisherPrefix": "opt",
        "ChoiceValuePrefix": "88483",
        "RootComponentCount": 0,
        "MissingDependencyCount": 0,
        "CustomizationsRoot": "ImportExportXml",
        "SolutionXmlBytes": 4400,
        "CustomizationsXmlBytes": 531,
        "ExportZipBytes": 1851,
        "ExportZipSHA256": "f39bf91d8e15d723c5b2cedfa803602cb529f241171823ad8c27c28441e928e9",
    }


def test_empty_solution_baseline_has_no_components_or_private_binding() -> None:
    customizations_root = ET.parse(BASELINE_ROOT / "Other" / "Customizations.xml").getroot()
    for section in (
        "Entities",
        "Roles",
        "Workflows",
        "FieldSecurityProfiles",
        "Templates",
        "EntityMaps",
        "EntityRelationships",
        "OrganizationSettings",
        "optionsets",
        "CustomControls",
        "EntityDataProviders",
    ):
        node = customizations_root.find(section)
        assert node is not None and len(node) == 0, section

    assert not list(BASELINE_ROOT.rglob("*.zip"))

    content = "\n".join(
        path.read_text(encoding="utf-8")
        for path in BASELINE_ROOT.rglob("*")
        if path.is_file()
    )
    lowered = content.lower()
    for forbidden in (
        "lacasa-dashaus",
        "bgh@",
        "lcdhos-dev",
        ".dynamics.com",
    ):
        assert forbidden not in lowered

    assert not re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", content, re.IGNORECASE)
    assert not re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", content, re.IGNORECASE)
