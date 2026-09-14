from pathlib import Path

from optimus_admin_gateway.catalog import OperationCatalog


def test_catalog_has_no_unapproved_mutations() -> None:
    catalog = OperationCatalog.load(Path(__file__).parents[1] / "config" / "operations.catalog.json")
    mutations = [item for item in catalog.list() if item.mutation]
    assert mutations
    assert all(item.approval_required for item in mutations)


def test_catalog_does_not_expose_arbitrary_execution() -> None:
    catalog = OperationCatalog.load(Path(__file__).parents[1] / "config" / "operations.catalog.json")
    forbidden = {"command", "script", "script_path", "module", "shell"}
    for operation in catalog.list():
        assert operation.operation_id not in forbidden
        assert "arbitrary" not in operation.description.lower()
