from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

os.environ.setdefault("OPTIMUS_DEV_MODE", "true")
os.environ.setdefault("OPTIMUS_EXECUTOR_MODE", "disabled")

# The repository-wide CI deliberately installs only the root dependency set.
# Keep static product-boundary and script-safety tests visible there, while the
# module-specific workflow installs the Admin Gateway package and runs the full
# API/contract suite. This prevents unrelated root CI from failing merely
# because product-local runtime dependencies are intentionally isolated.
PACKAGE_ROOT = Path(__file__).parents[1]
SRC_ROOT = PACKAGE_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

_REQUIRED_RUNTIME = ("fastapi", "pydantic")
collect_ignore: list[str] = []
if any(importlib.util.find_spec(module_name) is None for module_name in _REQUIRED_RUNTIME):
    collect_ignore.extend(["test_api.py", "test_catalog.py"])
