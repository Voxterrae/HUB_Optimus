"""Read-only Home boundary around the existing recorder transport.

Video stays in the viewer's existing workers. This adapter opens a monitor-free
identity probe or one native alarm subscription, and introduces no configuration,
recording, playback or camera-control requests. Original recorder snapshots are
pending; an event photo captured by the viewer has separate provenance.
"""

from collections.abc import Iterator
import threading
import time
import uuid

from vox_cctv_native import (
    AuthError, NativeAlarmClient, NativeClient, SourceError, safe_alarm,
)
from ..contracts import Capability, DeviceRecord, EventRecord, OperationResult, Target
from ..secrets import SecretMaterial


class NativeAdapter:
    """A single approved target and its broker-delivered protocol hash."""

    def __init__(self, target: Target, material: SecretMaterial,
                 client_factory=NativeClient, alarm_factory=NativeAlarmClient):
        if not isinstance(target, Target):
            raise ValueError('invalid_target')
        if not isinstance(material, SecretMaterial) or material.kind != 'owner_hash':
            raise ValueError('invalid_material')
        self.target = target
        self._material = material
        self._client_factory = client_factory
        self._alarm_factory = alarm_factory
        self._lock = threading.Lock()
        self._event_stop = threading.Event()
        self._alarm_client = None
        self._subscribing = False
        self._closed = False
        self._events_verified = False
        self._last_result = OperationResult('pending', None, 'identity_not_checked')

    @staticmethod
    def _failure(error: Exception) -> OperationResult:
        if isinstance(error, SourceError):
            return OperationResult('identity_mismatch', None, 'approved_serial_not_matched')
        if isinstance(error, AuthError):
            return OperationResult('authentication_failed', None, 'native_authentication_rejected')
        return OperationResult('unavailable', None, 'native_transport_unavailable')

    def _identity_matches(self, client) -> bool:
        return (self.target.expected_serial is not None and
                getattr(client, 'verified_serial', None) == self.target.expected_serial)

    def _record(self) -> DeviceRecord:
        now = time.time()
        identity = Capability('identity', 'verified', 'SystemInfo matched approved serial', now)
        events = Capability('events', 'verified', 'Native alarm subscription acknowledged', now) \
            if self._events_verified else Capability('events', 'pending', None, None)
        capabilities = (
            identity, events, Capability('live_video', 'pending', None, None),
            Capability('snapshot', 'pending', None, None),
            Capability('recordings', 'unsupported', None, None),
            Capability('playback', 'unsupported', None, None),
            Capability('control', 'unsupported', None, None),
        )
        return DeviceRecord(self.target.site_id, self.target.device_id, None, None,
                            'native.nvr', capabilities, now)

    def probe(self, target: Target) -> DeviceRecord | OperationResult:
        if target != self.target:
            return OperationResult('target_mismatch', None, 'target_not_approved')
        if self._closed:
            return OperationResult('unavailable', None, 'adapter_closed')
        if self.target.expected_serial is None:
            self._last_result = OperationResult('identity_mismatch', None, 'approved_serial_required')
            return self._last_result
        client = None
        try:
            client = self._client_factory(
                self._material.value, 0, 'Extra1', monitor=False,
                recorder_ip=self.target.host, expected_serial=self.target.expected_serial,
            )
            if not self._identity_matches(client):
                self._last_result = OperationResult('identity_mismatch', None, 'approved_serial_not_matched')
                return self._last_result
            record = self._record()
            self._last_result = OperationResult('ok', record, None)
            return record
        except Exception as error:
            self._last_result = self._failure(error)
            return self._last_result
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

    def health(self) -> OperationResult:
        with self._lock:
            if self._closed:
                return OperationResult('unavailable', None, 'adapter_closed')
            # Reserve setup before the blocking factory call; health must await
            # its acknowledgement without opening another recorder session.
            if self._subscribing and self._alarm_client is None:
                return OperationResult('pending', None, 'alarm_subscription_initializing')
            if self._alarm_client is not None or self._last_result.status in (
                    'identity_mismatch', 'authentication_failed'):
                return self._last_result
            # Keep the decision and standalone probe serialized against alarm
            # startup so subscription cannot begin between this check and login.
            result = self.probe(self.target)
            return OperationResult('ok', result, None) if isinstance(result, DeviceRecord) else result

    def subscribe_events(self) -> Iterator[EventRecord]:
        with self._lock:
            if self._closed or self._subscribing:
                return
            self._subscribing = True
            self._event_stop.clear()
            material = self._material
        client = None
        try:
            if self.target.expected_serial is None:
                with self._lock:
                    self._last_result = OperationResult('identity_mismatch', None, 'approved_serial_required')
                return
            client = self._alarm_factory(
                material.value, stop_event=self._event_stop,
                recorder_ip=self.target.host, expected_serial=self.target.expected_serial,
            )
            with self._lock:
                if self._closed or self._event_stop.is_set():
                    return
                if not self._identity_matches(client):
                    self._last_result = OperationResult('identity_mismatch', None, 'approved_serial_not_matched')
                    return
                self._alarm_client = client
                self._events_verified = True
                self._last_result = OperationResult('ok', self._record(), None)
            while not self._event_stop.is_set():
                for raw in client.poll():
                    event = safe_alarm(raw)
                    if event is not None and not self._event_stop.is_set():
                        yield EventRecord(
                            uuid.uuid4().hex, self.target.site_id, self.target.device_id,
                            event['channel'], event['event'], event['status'], event['time'], time.time(),
                        )
        except Exception as error:
            with self._lock:
                if not self._event_stop.is_set():
                    self._last_result = self._failure(error)
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
            with self._lock:
                self._alarm_client = None
                self._subscribing = False

    def _subscription_terminal_status(self):
        """Worker-only cached stop cause; never probe or export private details."""
        with self._lock:
            status = self._last_result.status
            return status if status in (
                'identity_mismatch', 'authentication_failed', 'unavailable') else None

    def snapshot(self, channel: int) -> OperationResult:
        return OperationResult('pending', None, 'Original recorder snapshot is not verified')

    def list_recordings(self, query: dict) -> OperationResult:
        return OperationResult('unsupported', None, 'Native recording discovery is not implemented')

    def playback(self, reference: str) -> OperationResult:
        return OperationResult('unsupported', None, 'Native playback is not implemented')

    def prepare_action(self, action: str, parameters: dict) -> OperationResult:
        return OperationResult('unsupported', None, 'Native control actions are not implemented')

    def execute_action(self, proposal_id: str) -> OperationResult:
        return OperationResult('unsupported', None, 'Native control actions are not implemented')

    def close(self) -> None:
        """Stop the adapter's alarm stream without touching viewer video workers."""
        with self._lock:
            self._closed = True
            self._event_stop.set()
            client = self._alarm_client
            self._material = None
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
