from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    dev_mode: bool
    catalog_path: Path
    executor_mode: str
    approval_hmac_secret: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        package_root = Path(__file__).resolve().parents[2]
        default_catalog = package_root / "config" / "operations.catalog.json"
        return cls(
            dev_mode=os.getenv("OPTIMUS_DEV_MODE", "false").lower() == "true",
            catalog_path=Path(os.getenv("OPTIMUS_OPERATION_CATALOG", default_catalog)),
            executor_mode=os.getenv("OPTIMUS_EXECUTOR_MODE", "disabled"),
            approval_hmac_secret=os.getenv("OPTIMUS_APPROVAL_HMAC_SECRET") or None,
        )
