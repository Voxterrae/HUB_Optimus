"""Small transactional installation matrix; never a permission or asset store.

Only a new path receives a schema. Existing unsupported or damaged stores
remain untouched and raise ``metadata_unavailable`` for a degraded viewer.
One instance serializes its connection across background and UI threads.
"""

from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from threading import RLock

from .contracts import Capability, ContractValidationError, DeviceRecord


SCHEMA_VERSION = 1
_RECORD_FIELDS = {"site_id", "device_id", "model", "firmware", "adapter_id",
                  "capabilities", "checked_at"}
_CAPABILITY_FIELDS = {"name", "status", "proof", "checked_at"}


class RegistryUnavailable(Exception):
    """Safe failure code, without filesystem or database details."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _validated(record: DeviceRecord) -> DeviceRecord:
    if not isinstance(record, DeviceRecord):
        raise ContractValidationError("invalid_type", "record")
    # Revalidate even immutable objects: callers may bypass dataclass guards.
    DeviceRecord.__post_init__(record)
    capabilities = tuple(Capability(item.name, item.status, item.proof, item.checked_at)
                         for item in record.capabilities)
    return DeviceRecord(record.site_id, record.device_id, record.model, record.firmware,
                        record.adapter_id, capabilities, record.checked_at)


def _decode(row: tuple[str, str, str]) -> DeviceRecord:
    try:
        site_id, device_id, payload = row
        mapping = json.loads(payload)
        if not isinstance(mapping, dict) or set(mapping) != _RECORD_FIELDS:
            raise ValueError("invalid record shape")
        capabilities = mapping["capabilities"]
        if not isinstance(capabilities, list) or any(
                not isinstance(item, dict) or set(item) != _CAPABILITY_FIELDS
                for item in capabilities):
            raise ValueError("invalid capability shape")
        mapping["capabilities"] = tuple(Capability(**item) for item in capabilities)
        record = DeviceRecord(**mapping)
        if (record.site_id, record.device_id) != (site_id, device_id):
            raise ValueError("record key mismatch")
        return record
    except (TypeError, ValueError, KeyError, OverflowError):
        raise RegistryUnavailable("metadata_unavailable") from None


class Registry:
    """Persist validated device metadata under a composite installation key."""

    def __init__(self, path: Path):
        self._lock = RLock()
        self._connection = None
        try:
            existing = path.exists()
            if existing and not path.is_file():
                raise RegistryUnavailable("metadata_unavailable")
            # mode=rw avoids rebuilding a store removed between exists and open.
            location = path.resolve().as_uri() + "?mode=rw" if existing else str(path)
            connection = sqlite3.connect(location, uri=existing, timeout=0.1,
                                         check_same_thread=False)
            self._connection = connection
            if existing:
                self._verify_schema()
                # Bad persisted contracts fail closed; no promoted defaults.
                for row in connection.execute("SELECT site_id, device_id, payload FROM devices"):
                    _decode(row)
            else:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        "CREATE TABLE devices (site_id TEXT NOT NULL, device_id TEXT NOT NULL, "
                        "payload TEXT NOT NULL, PRIMARY KEY (site_id, device_id))"
                    )
                    connection.execute("PRAGMA user_version = 1")
        except (sqlite3.Error, OSError, RegistryUnavailable):
            if self._connection is not None:
                self._connection.close()
                self._connection = None
            raise RegistryUnavailable("metadata_unavailable") from None

    def _verify_schema(self) -> None:
        connection = self._require_connection()
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        checks = connection.execute("PRAGMA quick_check").fetchall()
        columns = connection.execute("PRAGMA table_info(devices)").fetchall()
        expected = [("site_id", "TEXT", 1, 1), ("device_id", "TEXT", 1, 2),
                    ("payload", "TEXT", 1, 0)]
        actual = [(column[1], column[2], column[3], column[5]) for column in columns]
        if version != SCHEMA_VERSION or checks != [("ok",)] or actual != expected:
            raise RegistryUnavailable("metadata_unavailable")

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RegistryUnavailable("metadata_unavailable")
        return self._connection

    def upsert(self, record: DeviceRecord) -> None:
        record = _validated(record)
        payload = json.dumps(asdict(record), ensure_ascii=True, allow_nan=False,
                             separators=(",", ":"))
        with self._lock:
            connection = self._require_connection()
            try:
                with connection:
                    connection.execute(
                        "INSERT INTO devices (site_id, device_id, payload) VALUES (?, ?, ?) "
                        "ON CONFLICT(site_id, device_id) DO UPDATE SET payload=excluded.payload",
                        (record.site_id, record.device_id, payload),
                    )
            except (sqlite3.Error, OSError):
                raise RegistryUnavailable("metadata_unavailable") from None

    def get(self, site_id: str, device_id: str) -> DeviceRecord | None:
        with self._lock:
            connection = self._require_connection()
            try:
                row = connection.execute(
                    "SELECT site_id, device_id, payload FROM devices "
                    "WHERE site_id = ? AND device_id = ?", (site_id, device_id),
                ).fetchone()
                return _decode(row) if row is not None else None
            except (sqlite3.Error, OSError):
                raise RegistryUnavailable("metadata_unavailable") from None

    def list_records(self, site_id: str) -> list[DeviceRecord]:
        with self._lock:
            connection = self._require_connection()
            try:
                rows = connection.execute(
                    "SELECT site_id, device_id, payload FROM devices "
                    "WHERE site_id = ? ORDER BY device_id", (site_id,),
                ).fetchall()
                return [_decode(row) for row in rows]
            except (sqlite3.Error, OSError):
                raise RegistryUnavailable("metadata_unavailable") from None

    def export_metadata(self, site_id: str) -> dict:
        return {"schema_version": SCHEMA_VERSION, "site_id": site_id,
                "devices": [asdict(record) for record in self.list_records(site_id)]}

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                try:
                    self._connection.close()
                except sqlite3.Error:
                    raise RegistryUnavailable("metadata_unavailable") from None
                finally:
                    self._connection = None
