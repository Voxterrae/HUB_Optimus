from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

os.environ.setdefault("OPTIMUS_DEV_MODE", "true")
os.environ.setdefault("OPTIMUS_EXECUTOR_MODE", "disabled")
os.environ.setdefault("OPTIMUS_ENTRA_TENANT_ID", "11111111-1111-4111-8111-111111111111")

# The repository-wide CI installs only the root dependency set. Keep the
# product suite isolated there; the product workflow installs this package and
# executes every API and authentication test with its own dependency contract.
PACKAGE_ROOT = Path(__file__).parents[1]
SRC_ROOT = PACKAGE_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

_REQUIRED_RUNTIME = ("fastapi", "httpx", "httpx2", "pydantic")
collect_ignore: list[str] = []
if any(importlib.util.find_spec(module_name) is None for module_name in _REQUIRED_RUNTIME):
    collect_ignore.extend(["test_api.py", "test_auth.py", "test_catalog.py"])


def pytest_configure(config) -> None:
    """Fail on the TestClient fallback warning when this Starlette exposes it."""
    if importlib.util.find_spec("starlette") is None:
        return
    from starlette import exceptions as starlette_exceptions

    if getattr(starlette_exceptions, "StarletteDeprecationWarning", None) is not None:
        config.addinivalue_line(
            "filterwarnings",
            "error::starlette.exceptions.StarletteDeprecationWarning",
        )
