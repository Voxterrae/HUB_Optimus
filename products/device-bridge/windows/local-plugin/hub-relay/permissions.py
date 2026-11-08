"""Local one-use grants; not biometric or chat-identity authentication.

Provision the private directory separately. The issuer prints a bearer token
once; consumers store no token and commit consumption before any diagnostic.
Processes controlling the same account or an administrator are out of scope.
"""

from contextlib import closing
import hashlib
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import sys
import time


TOOL_NAME = "hub_relay_windows_diagnostics"
DB_FILENAME = "one-use-permissions.sqlite3"
DATA_SUBDIRECTORY = "one-use"
MAX_TTL_SECONDS = 120
TOKEN_PATTERN = r"[A-Za-z0-9_-]{42}[AEIMQUYcgkosw048]"


class PermissionError(ValueError):
    """Deliberately excludes paths, tokens, SQL and operating-system details."""

    code = "PERMISSION_STORE_UNAVAILABLE"

    def __init__(self):
        super().__init__(self.code)


def valid_token(value):
    return type(value) is str and re.fullmatch(TOKEN_PATTERN, value) is not None


def _absolute_directory(value):
    try:
        path = Path(value)
        if (not path.is_absolute() or ".." in path.parts
                or "\x00" in str(path) or len(str(path)) > 4096):
            raise ValueError
        return path
    except (TypeError, ValueError, OSError):
        raise PermissionError() from None


def _number(value):
    return (type(value) in (int, float) and math.isfinite(value)
            and 0 <= value <= 253402300799)


def validate_private_directory(directory):
    """Read Windows ACLs only; never create a directory or change its ACL.

    Accept a local fixed drive, no reparse components, a protected directory
    DACL and only current-user/SYSTEM/Administrators allow entries. Existing
    database and journal files must have the same private principal boundary.
    """
    try:
        if sys.platform != "win32":
            raise PermissionError()
        import ctypes
        from ctypes import wintypes

        path = _absolute_directory(directory)
        if not re.fullmatch(r"[A-Za-z]:\\", path.anchor) or not path.is_dir():
            raise PermissionError()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        security = ctypes.WinDLL("advapi32", use_last_error=True)
        pointer = ctypes.c_void_p

        def bind(library, name, result, arguments):
            function = getattr(library, name)
            function.restype, function.argtypes = result, arguments
            return function

        get_drive = bind(kernel, "GetDriveTypeW", wintypes.UINT, [wintypes.LPCWSTR])
        if get_drive(path.anchor) != 3:  # DRIVE_FIXED
            raise PermissionError()
        for component in (path, *path.parents):
            if component.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise PermissionError()

        local_free = bind(kernel, "LocalFree", pointer, [pointer])
        close_handle = bind(kernel, "CloseHandle", wintypes.BOOL, [wintypes.HANDLE])
        current_process = bind(kernel, "GetCurrentProcess", wintypes.HANDLE, [])
        open_token = bind(security, "OpenProcessToken", wintypes.BOOL,
                          [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)])
        get_token = bind(security, "GetTokenInformation", wintypes.BOOL,
                         [wintypes.HANDLE, ctypes.c_int, pointer, wintypes.DWORD,
                          ctypes.POINTER(wintypes.DWORD)])
        sid_string = bind(security, "ConvertSidToStringSidW", wintypes.BOOL,
                          [pointer, ctypes.POINTER(pointer)])
        get_security = bind(security, "GetNamedSecurityInfoW", wintypes.DWORD,
                            [wintypes.LPCWSTR, ctypes.c_int, wintypes.DWORD,
                             ctypes.POINTER(pointer), pointer, ctypes.POINTER(pointer),
                             pointer, ctypes.POINTER(pointer)])
        get_control = bind(security, "GetSecurityDescriptorControl", wintypes.BOOL,
                           [pointer, ctypes.POINTER(wintypes.WORD),
                            ctypes.POINTER(wintypes.DWORD)])
        valid_acl = bind(security, "IsValidAcl", wintypes.BOOL, [pointer])
        get_ace = bind(security, "GetAce", wintypes.BOOL,
                       [pointer, wintypes.DWORD, ctypes.POINTER(pointer)])

        def sid_text(sid):
            allocated = pointer()
            if not sid or not sid_string(sid, ctypes.byref(allocated)):
                raise PermissionError()
            try:
                return ctypes.wstring_at(allocated)
            finally:
                local_free(allocated)

        token = wintypes.HANDLE()
        if not open_token(current_process(), 0x0008, ctypes.byref(token)):
            raise PermissionError()
        try:
            size = wintypes.DWORD()
            get_token(token, 1, None, 0, ctypes.byref(size))  # TokenUser
            if not 0 < size.value <= 65536:
                raise PermissionError()
            buffer = ctypes.create_string_buffer(size.value)
            if not get_token(token, 1, buffer, size.value, ctypes.byref(size)):
                raise PermissionError()
            current_sid = sid_text(ctypes.cast(buffer, ctypes.POINTER(pointer))[0])
        finally:
            close_handle(token)
        allowed = {current_sid, "S-1-5-18", "S-1-5-32-544"}

        class ACL(ctypes.Structure):
            _fields_ = [("revision", wintypes.BYTE), ("reserved", wintypes.BYTE),
                        ("size", wintypes.WORD), ("count", wintypes.WORD),
                        ("reserved2", wintypes.WORD)]

        def check_acl(target, protected):
            owner, dacl, descriptor = pointer(), pointer(), pointer()
            if get_security(str(target), 1, 0x00000005, ctypes.byref(owner), None,
                            ctypes.byref(dacl), None, ctypes.byref(descriptor)):
                raise PermissionError()
            try:
                control, revision = wintypes.WORD(), wintypes.DWORD()
                if (not dacl or sid_text(owner) not in allowed
                        or not valid_acl(dacl)
                        or not get_control(descriptor, ctypes.byref(control),
                                           ctypes.byref(revision))
                        or not control.value & 0x0004
                        or (protected and not control.value & 0x1000)):
                    raise PermissionError()
                acl = ctypes.cast(dacl, ctypes.POINTER(ACL)).contents
                if not 0 < acl.count <= 64:
                    raise PermissionError()
                for index in range(acl.count):
                    ace = pointer()
                    if not get_ace(dacl, index, ctypes.byref(ace)):
                        raise PermissionError()
                    # ACCESS_ALLOWED_ACE: header(4), mask(4), variable SID.
                    header = (wintypes.BYTE * 4).from_address(ace.value)
                    size = int.from_bytes(bytes(header[2:4]), "little")
                    if (header[0] != 0 or size < 16 or ace.value < dacl.value + 8
                            or ace.value + size > dacl.value + acl.size
                            or sid_text(ace.value + 8) not in allowed):
                        raise PermissionError()
            finally:
                local_free(descriptor)

        check_acl(path, True)
        for suffix in ("", "-journal", "-wal", "-shm"):
            target = path / (DB_FILENAME + suffix)
            try:
                metadata = target.lstat()
            except FileNotFoundError:
                continue
            if (metadata.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
                    or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1):
                raise PermissionError()
            check_acl(target, False)
    except PermissionError:
        raise
    except Exception:
        raise PermissionError() from None


class PermissionStore:
    def __init__(self, data_dir, clock=time.time, directory_guard=None):
        self.data_dir = _absolute_directory(data_dir)
        self.db_path = self.data_dir / DB_FILENAME
        self.clock = clock
        self.directory_guard = (validate_private_directory if directory_guard is None
                                else directory_guard)

    def _connect(self, create):
        self.directory_guard(self.data_dir)
        mode = "rwc" if create else "rw"
        connection = sqlite3.connect(self.db_path.as_uri() + "?mode=" + mode,
                                     uri=True, timeout=0, isolation_level=None)
        try:
            connection.execute("PRAGMA trusted_schema=OFF")
            if connection.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",):
                raise PermissionError()
            connection.execute("PRAGMA synchronous=FULL")
            if connection.execute("PRAGMA quick_check(1)").fetchone() != ("ok",):
                raise PermissionError()
            self.directory_guard(self.data_dir)
            return connection
        except Exception:
            connection.close()
            raise

    def issue(self, ttl_seconds=MAX_TTL_SECONDS):
        """Issue only this diagnostic operation; return the secret exactly once."""
        try:
            now = self.clock()
            if (type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_TTL_SECONDS
                    or not _number(now) or not _number(now + ttl_seconds)):
                raise PermissionError()
            token = secrets.token_urlsafe(32)
            digest = hashlib.sha256(token.encode("ascii")).hexdigest()
            with closing(self._connect(create=True)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("""CREATE TABLE IF NOT EXISTS grants (
                    token_hash TEXT PRIMARY KEY, operation TEXT NOT NULL,
                    issued_at REAL NOT NULL, expires_at REAL NOT NULL,
                    consumed INTEGER NOT NULL DEFAULT 0)""")
                connection.execute("INSERT INTO grants VALUES (?, ?, ?, ?, 0)",
                                   (digest, TOOL_NAME, now, now + ttl_seconds))
                connection.commit()
            return token
        except Exception:
            raise PermissionError() from None

    def consume(self, token):
        """Durably consume before returning True; never create missing storage."""
        if not valid_token(token):
            return False
        try:
            digest = hashlib.sha256(token.encode("ascii")).hexdigest()
            with closing(self._connect(create=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT operation, issued_at, expires_at, consumed FROM grants "
                    "WHERE token_hash = ?", (digest,)).fetchone()
                if (row is None or row[0] != TOOL_NAME or type(row[3]) is not int
                        or row[3] != 0 or not _number(row[1]) or not _number(row[2])
                        or not 0 < row[2] - row[1] <= MAX_TTL_SECONDS):
                    connection.rollback()
                    return False
                now = self.clock()
                if not _number(now):
                    raise PermissionError()
                if not row[1] <= now < row[2]:
                    connection.rollback()
                    return False
                changed = connection.execute(
                    "UPDATE grants SET consumed = 1 WHERE token_hash = ? "
                    "AND operation = ? AND consumed = 0 AND issued_at = ? AND expires_at = ?",
                    (digest, TOOL_NAME, row[1], row[2])).rowcount
                if changed != 1:
                    connection.rollback()
                    return False
                connection.commit()
            return True
        except Exception:
            raise PermissionError() from None


def from_environment():
    """Only the fixed private subdirectory of an absolute PLUGIN_DATA is used."""
    root = os.environ.get("PLUGIN_DATA")
    if not root:
        raise PermissionError()
    return PermissionStore(_absolute_directory(root) / DATA_SUBDIRECTORY)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not (argv == ["issue"] or (len(argv) == 3 and argv[:2] == ["issue", "--data-dir"])):
        sys.stderr.write("Usage: permissions.py issue [--data-dir ABSOLUTE_PRIVATE_DIRECTORY]\n")
        return 2
    try:
        store = PermissionStore(argv[2]) if len(argv) == 3 else from_environment()
        token = store.issue()
        sys.stdout.write(token + "\n")
        sys.stdout.flush()
        return 0
    except Exception:
        sys.stderr.write("PERMISSION_STORE_UNAVAILABLE\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
