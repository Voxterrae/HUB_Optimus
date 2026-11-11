"""Trusted local facade. Native events use one worker; media stays in the viewer.

Contexts and bindings are issued by the core, never taken from adapter payloads.
This private baseline is not a sandbox for untrusted extensions.
"""
from collections import deque
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import re
import threading
import time

from .access import AccessContext, AccessDenied, AccessService
from .contracts import AdapterManifest, DeviceRecord, EventRecord, EvidenceRef, Target
from .host import AdapterHost
from .registry import Registry, RegistryUnavailable
from .secrets import SecretBroker, SecretMaterial, SecretRef


class CoreFacade:
    def __init__(self, registry, access, host, evidence_store, evidence_scope: Target):
        self.registry, self.access, self.host = registry, access, host
        self.evidence_store, self.evidence_scope = evidence_store, evidence_scope
        self._lock = threading.RLock()
        self._manifest = self._owner = self._session = None
        self._events = deque(maxlen=128)
        self._closed = False
        self._metadata = 'available' if registry is not None else 'metadata_unavailable'
        self._worker_status = 'idle'
        self._alarm_issue = None
        self._event_loss = False
        self._verified = False
        self._last_record = None

    def _require(self, context, operation, now):
        try:
            if (self._closed or type(context) is not AccessContext
                    or context.site_id != self.evidence_scope.site_id):
                raise AccessDenied()
            self.access.require(context, self.evidence_scope.device_id, operation, now)
            self.access.require(context, self.evidence_scope.device_id, operation, time.time())
        except AccessDenied:
            raise AccessDenied('permission_denied') from None

    def configure_native(self, manifest, owner):
        if (type(manifest) is not AdapterManifest or self.evidence_scope not in manifest.allowed_targets
                or type(owner) is not AccessContext or owner.grant_id is not None):
            raise AccessDenied('permission_denied')
        for operation in ('probe', 'health', 'events'):
            self._require(owner, operation, time.time())
        with self._lock:
            if self._session is not None:
                raise RuntimeError('subscription_active')
            self._manifest, self._owner = manifest, owner

    def devices(self, context: AccessContext, now: float) -> list[DeviceRecord]:
        self._require(context, 'metadata_read', now)
        try:
            if self.registry is None:
                raise RegistryUnavailable('metadata_unavailable')
            record = self.registry.get(self.evidence_scope.site_id, self.evidence_scope.device_id)
        except RegistryUnavailable:
            self._metadata = 'metadata_unavailable'
            return []
        self._require(context, 'metadata_read', now)
        return [record] if record is not None else []

    def events(self, context: AccessContext, now: float) -> list[EventRecord]:
        self._require(context, 'events', now)
        with self._lock:
            result = list(self._events)
        self._require(context, 'events', now)
        return result

    def evidence_entries(self, context, now):
        self._require(context, 'evidence_read', now)
        rows = self.evidence_store.list_entries()
        self._require(context, 'evidence_read', now)
        return rows

    def evidence_refs(self, context, now):
        return [EvidenceRef(row['id'], 'viewer_at_receipt', row['state'])
                for row in self.evidence_entries(context, now)]

    def read_evidence(self, context: AccessContext, asset_id: str, now: float) -> bytes | None:
        self._require(context, 'evidence_read', now)
        if type(asset_id) is not str or re.fullmatch(r'[a-f0-9]{32}', asset_id) is None:
            return None
        # Only an ID currently owned by this installation's shared store.
        if not any(row['id'] == asset_id for row in self.evidence_entries(context, now)):
            return None
        self._require(context, 'evidence_read', now)
        image = self.evidence_store.read_image(asset_id)
        self._require(context, 'evidence_read', now)
        return image

    def _remember(self, result):
        if type(result.value) is DeviceRecord:
            record = result.value
            if (record.site_id, record.device_id) != (self.evidence_scope.site_id, self.evidence_scope.device_id):
                raise RuntimeError('identity_mismatch')
            self._verified = any(c.name == 'events' and c.status == 'verified' for c in record.capabilities)
            if record != self._last_record:
                try:
                    if self.registry is None:
                        raise RegistryUnavailable('metadata_unavailable')
                    self.registry.upsert(record)
                except RegistryUnavailable:
                    self._metadata = 'metadata_unavailable'
                self._last_record = record
        # Telemetry carries fixed codes only, never an arbitrary adapter status
        # or reason. A past loss/terminal cause remains visible across teardown.
        status = result.status if result.status in (
            'ok', 'pending', 'authentication_failed', 'identity_mismatch',
            'event_overflow', 'event_source_ended', 'event_source_failed',
            'unavailable', 'timeout', 'protocol_error', 'worker_closed',
            'message_too_large', 'access_denied', 'permission_denied', 'unsupported') else 'worker_failed'
        with self._lock:
            self._worker_status = status
            if status not in ('ok', 'pending'):
                self._alarm_issue = status
                self._verified = False
            if status == 'event_overflow':
                self._event_loss = True
        return result

    def acquire_alarm(self, context, target):
        # Authorization and the closed gate share the lifecycle lock with
        # startup/teardown: no pre-lock approval can outlive final shutdown.
        with self._lock:
            self._require(context, 'events', time.time())
            if target != self.evidence_scope or self._manifest is None:
                raise AccessDenied('permission_denied')
            if self._session is not None:
                raise RuntimeError('subscription_active')
            session = self.host.start(self._manifest, target, self._owner)
            self._session = session
            self._worker_status = 'starting'
            return session

    def release_alarm(self, session):
        with self._lock:
            if self._session is not session:
                return  # A delayed old client cannot affect its replacement.
            self._verified = False
            self._worker_status = 'closing'
            # Host shutdown is bounded. Keep the occupied slot and lock until
            # termination finishes, so a replacement cannot overlap this worker.
            session.close()
            self._session = None
            self._worker_status = 'closed'

    def status(self):
        with self._lock:
            return {'core_active': self._session is not None and self._verified,
                    'metadata': self._metadata, 'alarm_subscriptions': int(self._session is not None),
                    'worker_status': self._worker_status,
                    'alarm_issue': self._alarm_issue, 'event_loss': self._event_loss}

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._verified = False
            self._worker_status = 'closing'
            if self._session is not None:
                self._session.close()
                self._session = None
            self._worker_status = 'closed'
            self._events.clear()
            try:
                if self.registry is not None:
                    self.registry.close()
            finally:
                self.evidence_store.close()


class CoreAlarmClient:
    """Legacy alarm shape at the viewer boundary; owns only its worker session."""
    def __init__(self, facade, context, target, stop_event):
        self.facade, self.context, self.target = facade, context, target
        self.stop_event, self.last_reply = stop_event, 0.0
        self._session = None
        self._terminal_result = None
        try:
            self._session = facade.acquire_alarm(context, target)
            self._check(self._session.call('probe', {}, time.time()))
            self._check(self._session.call('events', {}, time.time()))
            # events RPC starts an iterator; only health with events proof means ack.
            deadline = time.monotonic() + 5
            while not stop_event.is_set():
                result = self._session.call('health', {}, time.time())
                self._check(result, pending=True)
                if facade.status()['core_active']:
                    self.last_reply = time.monotonic()
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('subscription_timeout')
                stop_event.wait(.1)
        except Exception:
            self.close()
            raise

    def _check(self, result, pending=False):
        from vox_cctv_native import AuthError, SourceError, AlarmUnavailable
        self.facade._remember(result)
        if result.status == 'identity_mismatch':
            raise SourceError('identity_mismatch')
        if result.status == 'authentication_failed':
            raise AuthError('authentication_failed')
        if result.status in ('access_denied', 'permission_denied'):
            raise AccessDenied('permission_denied')
        if result.status == 'unsupported':
            raise AlarmUnavailable('operation_not_approved')
        if result.status != 'ok' and not (pending and result.status == 'pending'):
            raise RuntimeError('alarm_worker_unavailable')

    def poll(self) -> list[dict]:
        if self.stop_event.wait(.1):
            return []
        self.facade._require(self.context, 'events', time.time())
        session = self._session
        if session is None:
            raise RuntimeError('alarm_worker_closed')
        if self._terminal_result is not None:
            self._check(self._terminal_result)
        events = session.poll_events()
        result = session.call('health', {}, time.time())
        # Permission refusal always suppresses data, including a drained batch.
        if result.status in ('access_denied', 'permission_denied'):
            self._check(result)
        self.facade._require(self.context, 'events', time.time())
        bound = [event for event in events if type(event) is EventRecord
                 and (event.site_id, event.device_id) == (self.target.site_id, self.target.device_id)]
        if result.status not in ('ok', 'pending') and bound:
            # The source can stop after enqueueing its last authorized alarms.
            # Deliver that batch once, then preserve its precise stop policy on
            # the next poll. Never reconnect or throw away the batch beforehand.
            self.facade._remember(result)
            self._terminal_result = result
        else:
            self._check(result, pending=True)
        with self.facade._lock:
            self.facade._require(self.context, 'events', time.time())
            self.facade._events.extend(bound)
            if any(event.kind == 'event_overflow' for event in bound):
                self.facade._event_loss = True
                self.facade._alarm_issue = 'event_overflow'
        self.facade._require(self.context, 'events', time.time())
        from vox_cctv_native import ALARM_LABELS
        self.last_reply = time.monotonic()
        return [{'Channel': event.channel - 1 if event.channel is not None else None,
                 'Event': event.kind, 'Status': event.status, 'StartTime': event.device_time or ''}
                for event in bound if event.kind in ALARM_LABELS and
                (event.channel is None or 1 <= event.channel <= 7)]

    def close(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            self.facade.release_alarm(session)


def local_process_identity() -> str:
    """Actual token SID on Windows, actual uid on Linux; no environment identity."""
    if os.name != 'nt':
        return 'uid-' + str(os.getuid())
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                           wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    token, length, sid_text = wintypes.HANDLE(), wintypes.DWORD(), wintypes.LPWSTR()
    class SidAndAttributes(ctypes.Structure):
        _fields_ = [('sid', ctypes.c_void_p), ('attributes', wintypes.DWORD)]
    try:
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            raise AccessDenied('identity_unavailable')
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(length))
        if not length.value:
            raise AccessDenied('identity_unavailable')
        buffer = ctypes.create_string_buffer(length.value)
        if not advapi.GetTokenInformation(token, 1, buffer, length, ctypes.byref(length)):
            raise AccessDenied('identity_unavailable')
        user = ctypes.cast(buffer, ctypes.POINTER(SidAndAttributes)).contents
        if not advapi.ConvertSidToStringSidW(user.sid, ctypes.byref(sid_text)):
            raise AccessDenied('identity_unavailable')
        return sid_text.value
    finally:
        if sid_text:
            kernel.LocalFree(ctypes.cast(sid_text, ctypes.c_void_p))
        if token:
            kernel.CloseHandle(token)


def bootstrap_local_core(data_dir: Path, evidence_store, auth_hash):
    """Bind this owner's process and the existing exact native credential target."""
    from vox_cctv_native import RECORDER_IP, RECORDER_SERIAL, CREDENTIAL_TARGET, owner_hash
    site_id, device_id = 'local-installation', 'local-recorder'
    principal = local_process_identity()
    context = AccessContext(site_id, principal, None)
    access = AccessService({site_id: principal})
    target = Target(site_id, device_id, RECORDER_IP, RECORDER_SERIAL)
    manifest = AdapterManifest('native.nvr', '1.0.0', 1,
        'vox_home.adapters.native:NativeAdapter', ('probe', 'health', 'events', 'credential_use'), (target,))
    ref = SecretRef(site_id, device_id, manifest.adapter_id, CREDENTIAL_TARGET)
    def provider(request):
        if request.provider_key != CREDENTIAL_TARGET:
            raise AccessDenied('secret_not_approved')
        # Read only the exact configured CredReadW target on each worker start.
        # The broker retains no copy of the viewer's private hash after close.
        return SecretMaterial('owner_hash', owner_hash())
    broker = SecretBroker(access, {(site_id, device_id, manifest.adapter_id): ref}, provider)
    host = AdapterHost(access, broker, {manifest.adapter_id: manifest})
    registry = None
    try:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        registry = Registry(Path(data_dir) / 'home_metadata.sqlite3')
    except (RegistryUnavailable, OSError):
        pass  # Metadata alone degrades; never credential/identity/permission checks.
    facade = CoreFacade(registry, access, host, evidence_store, target)
    facade.configure_native(manifest, context)
    return facade, context, target
