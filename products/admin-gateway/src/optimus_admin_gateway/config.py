from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_APPROVAL_MAX_AGE_SECONDS = 900
MIN_APPROVAL_MAX_AGE_SECONDS = 1
MAX_APPROVAL_MAX_AGE_SECONDS = 86_400


def _bounded_approval_age_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    error = f"{name} must be an integer from 1 to {MAX_APPROVAL_MAX_AGE_SECONDS}"
    if not raw_value.isascii() or not raw_value.isdecimal():
        raise ValueError(error)
    value = int(raw_value)
    if not MIN_APPROVAL_MAX_AGE_SECONDS <= value <= MAX_APPROVAL_MAX_AGE_SECONDS:
        raise ValueError(error)
    return value


@dataclass(frozen=True)
class Settings:
    dev_mode: bool
    catalog_path: Path
    executor_mode: str
    approval_hmac_secret: str | None
    entra_tenant_id: str | None
    reader_role: str
    mutator_role: str
    approval_max_age_seconds: int = DEFAULT_APPROVAL_MAX_AGE_SECONDS

    def __post_init__(self) -> None:
        if not self.reader_role or not self.mutator_role:
            raise ValueError("Admin Gateway application roles must be non-empty")
        if self.reader_role == self.mutator_role:
            raise ValueError("Read and mutation application roles must remain separate")
        if type(self.approval_max_age_seconds) is not int or not (
            MIN_APPROVAL_MAX_AGE_SECONDS
            <= self.approval_max_age_seconds
            <= MAX_APPROVAL_MAX_AGE_SECONDS
        ):
            raise ValueError(
                f"Approval maximum age must be an integer from "
                f"{MIN_APPROVAL_MAX_AGE_SECONDS} to {MAX_APPROVAL_MAX_AGE_SECONDS} seconds"
            )

    @classmethod
    def from_env(cls) -> "Settings":
        package_root = Path(__file__).resolve().parents[2]
        default_catalog = package_root / "config" / "operations.catalog.json"
        return cls(
            dev_mode=os.getenv("OPTIMUS_DEV_MODE", "false").lower() == "true",
            catalog_path=Path(os.getenv("OPTIMUS_OPERATION_CATALOG", default_catalog)),
            executor_mode=os.getenv("OPTIMUS_EXECUTOR_MODE", "disabled"),
            approval_hmac_secret=os.getenv("OPTIMUS_APPROVAL_HMAC_SECRET") or None,
            entra_tenant_id=os.getenv("OPTIMUS_ENTRA_TENANT_ID") or None,
            reader_role=os.getenv("OPTIMUS_READER_ROLE", "Optimus.Reader"),
            mutator_role=os.getenv("OPTIMUS_MUTATOR_ROLE", "Optimus.Mutator"),
            approval_max_age_seconds=_bounded_approval_age_env(
                "OPTIMUS_APPROVAL_MAX_AGE_SECONDS",
                DEFAULT_APPROVAL_MAX_AGE_SECONDS,
            ),
        )
