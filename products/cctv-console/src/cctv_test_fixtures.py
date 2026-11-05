"""Synthetic deterministic Home data; no household details or credentials."""


def manifest_mapping():
    """Return fresh JSON-shaped input for the local demonstration adapter."""
    return {
        "adapter_id": "demo.local",
        "version": "1.0.0",
        "api_major": 1,
        "entrypoint": "demo.local:DemoAdapter",
        "permissions": ["probe", "health", "events"],
        "allowed_targets": [
            {"site_id": "s1", "device_id": "d1", "host": "fixture.invalid",
             "expected_serial": "SYNTHETIC-001"}
        ],
    }


from vox_home.adapters.native import NativeAdapter
from vox_home.contracts import OperationResult
from vox_cctv_native import AuthError, SourceError
import threading


class BridgeNativeAdapter(NativeAdapter):
    """The real native adapter with offline transport and an explicit test gate."""
    def __init__(self, target, material):
        self._fixture_gate = threading.Event()
        class Probe:
            verified_serial = target.expected_serial
            def close(self):
                pass
        class Alarm:
            verified_serial = target.expected_serial
            def __init__(alarm):
                if target.host == 'reject_auth_setup':
                    raise AuthError('private-fixture-error ref SID')
                if target.host == 'reject_identity_setup':
                    alarm.verified_serial = 'wrong-fixture-serial'
                alarm.polled = False
            def poll(alarm):
                self._fixture_gate.wait()
                if alarm.polled:
                    error = SourceError if target.host == 'active_identity' else AuthError
                    raise error('private-fixture-error ref SID')
                alarm.polled = True
                count = 1000 if target.host == 'flood' else 1
                return [{'Channel': number % 7, 'Event': 'HumanDetect',
                         'Status': 'Start' if number // 7 % 2 == 0 else 'Stop',
                         'StartTime': '2026-10-03 22:00:00'} for number in range(count)]
            def close(alarm):
                pass
        super().__init__(target, material, client_factory=lambda *a, **kw: Probe(),
                         alarm_factory=lambda *a, **kw: Alarm())

    def prepare_action(self, action, parameters):
        # Test-only adapter utility; production NativeAdapter mutations remain
        # unsupported. The gate makes cross-process terminal races deterministic.
        if action == 'release_fixture_stream' and parameters == {}:
            self._fixture_gate.set()
            return OperationResult('ok', None, None)
        return super().prepare_action(action, parameters)


from vox_home.contracts import Capability, DeviceRecord, EventRecord
import time

class OfflineSession:
    def __init__(self, target):
        self.target = target
        self.subscriptions = 0
        self.closed = False
        self.failure = None
        self.record = DeviceRecord(target.site_id, target.device_id, None, None, 'native.nvr',
            (Capability('events', 'verified', 'synthetic acknowledgement', time.time()),), time.time())
        self.queue = [EventRecord('e1', target.site_id, target.device_id, 7, 'HumanDetect',
                                 'Start', '2026-10-03 22:00:00', time.time())]
    def call(self, operation, parameters, now):
        if self.failure:
            return OperationResult(self.failure, None, 'synthetic_failure')
        if operation == 'events':
            self.subscriptions += 1
            return OperationResult('ok', None, None)
        return OperationResult('ok', self.record, None)
    def poll_events(self):
        queue, self.queue = self.queue, []
        return queue
    def close(self):
        self.closed = True


class OfflineHost:
    def __init__(self):
        self.sessions = []
    def start(self, manifest, target, context):
        session = OfflineSession(target)
        self.sessions.append(session)
        return session
