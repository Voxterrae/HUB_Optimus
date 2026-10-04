"""Offline integration: real permissions, metadata and capture store; no NVR."""
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from vox_home.access import AccessContext, AccessDenied, AccessService, Grant
from vox_home.contracts import AdapterManifest, Capability, DeviceRecord, EventRecord, OperationResult, Target
from vox_home.registry import Registry
from vox_cctv_evidence import EvidenceStore
try:
    from vox_home.facade import CoreFacade, CoreAlarmClient, bootstrap_local_core, local_process_identity
except ImportError:
    CoreFacade = CoreAlarmClient = bootstrap_local_core = local_process_identity = None


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


class HomeFacadeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(CoreFacade, 'Local Home facade is not implemented')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Target('s1', 'nvr1', 'offline.invalid', 'synthetic')
        self.owner = AccessContext('s1', 'owner', None)
        self.access = AccessService({'s1': 'owner', 's2': 'owner'})
        self.registry = Registry(Path(self.temp.name) / 'metadata.sqlite3')
        self.store = EvidenceStore(Path(self.temp.name) / 'captures', min_free_bytes=0)
        self.host = OfflineHost()
        self.facade = CoreFacade(self.registry, self.access, self.host, self.store, self.target)
        self.addCleanup(self.facade.close)
        self.manifest = AdapterManifest('native.nvr', '1.0.0', 1,
            'vox_home.adapters.native:NativeAdapter', ('probe', 'health', 'events', 'credential_use'), (self.target,))
        self.facade.configure_native(self.manifest, self.owner)
    def test_single_subscription_normalizes_channel_and_retry_releases_session(self):
        client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        reports = client.poll()
        self.assertEqual(reports, [{'Channel': 6, 'Event': 'HumanDetect', 'Status': 'Start',
                                    'StartTime': '2026-10-03 22:00:00'}])
        self.assertEqual(self.host.sessions[0].subscriptions, 1)
        self.assertEqual(self.facade.status()['alarm_subscriptions'], 1)
        client.close()
        self.assertTrue(self.host.sessions[0].closed)
        self.assertEqual(self.facade.status()['alarm_subscriptions'], 0)
        next_client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        self.assertEqual(len(self.host.sessions), 2)
        next_client.close()
        self.assertIsNotNone(self.store.list_entries())
    def test_media_read_is_scoped_and_revocable(self):
        event = {'event': 'HumanDetect', 'channel': 1, 'status': 'Start', 'time': ''}
        ppm = b'P6\n2 2\n255\n' + b'\x20\x70\x40' * 4
        self.assertTrue(self.store.add(event, {'ppm': ppm, 'width': 2, 'height': 2,
            'source_width': 704, 'source_height': 480, 'frame_age_seconds': .2, 'stream': 'Extra1'}))
        asset = self.store.list_entries()[0]['id']
        with patch.object(self.store, 'read_image', wraps=self.store.read_image) as read:
            with self.assertRaises(AccessDenied) as refusal:
                self.facade.read_evidence(AccessContext('s2', 'owner', None), asset, time.time())
            self.assertEqual(refusal.exception.code, 'permission_denied')
            read.assert_not_called()
        grant = Grant('g1', 's1', 'technician', ('nvr1',), ('evidence_read',), time.time()+30, False)
        self.access.issue_grant(self.owner, grant)
        observer = AccessContext('s1', 'technician', 'g1')
        self.assertEqual(self.facade.read_evidence(observer, asset, time.time()), ppm)
        self.assertEqual(self.facade.evidence_refs(observer, time.time())[0].provenance, 'viewer_at_receipt')
        self.access.revoke(self.owner, 'g1')
        with patch.object(self.store, 'read_image', wraps=self.store.read_image) as read:
            with self.assertRaises(AccessDenied) as refusal:
                self.facade.read_evidence(observer, asset, time.time())
            self.assertEqual(refusal.exception.code, 'permission_denied')
            read.assert_not_called()
        self.assertIsNone(self.facade.read_evidence(self.owner, '../outside.ppm', time.time()))
    def test_missing_store_keeps_viewer_and_gallery_status(self):
        self.registry.close()
        client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        client.poll()
        self.assertEqual(self.facade.devices(self.owner, time.time()), [])
        status = self.facade.status()
        self.assertTrue(status['core_active'])
        self.assertEqual(status['metadata'], 'metadata_unavailable')
        self.assertEqual(status['alarm_subscriptions'], 1)
        self.assertEqual(self.facade.evidence_entries(self.owner, time.time()), [])
        client.close()
    def test_metadata_and_events_recheck_revocation(self):
        client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        client.poll()
        self.access.issue_grant(self.owner, Grant('g2', 's1', 'observer', ('nvr1',),
            ('metadata_read', 'events'), time.time()+30, False))
        observer = AccessContext('s1', 'observer', 'g2')
        self.assertEqual(len(self.facade.devices(observer, time.time())), 1)
        self.assertEqual(len(self.facade.events(observer, time.time())), 1)
        self.assertEqual(len(self.host.sessions), 1)
        self.access.revoke(self.owner, 'g2')
        for method in (self.facade.devices, self.facade.events):
            with self.assertRaises(AccessDenied):
                method(observer, time.time())
        client.close()
    def test_refusal_closes_subscription_without_legacy_fallback(self):
        from vox_cctv_native import SourceError
        client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        client.poll()  # With no final batch, a terminal refusal is immediate.
        self.host.sessions[0].failure = 'identity_mismatch'
        with self.assertRaises(SourceError):
            client.poll()
        client.close()
        self.assertTrue(self.host.sessions[0].closed)
        self.assertEqual(len(self.host.sessions), 1)
    def test_bootstrap_preserves_corrupt_metadata_and_shared_store(self):
        path = Path(self.temp.name) / 'home_metadata.sqlite3'
        path.write_bytes(b'preserve-corrupt-store')
        facade, context, target = bootstrap_local_core(Path(self.temp.name), self.store, 'synthetic-hash')
        try:
            self.assertIs(facade.evidence_store, self.store)
            self.assertEqual(facade.status()['metadata'], 'metadata_unavailable')
            self.assertEqual(path.read_bytes(), b'preserve-corrupt-store')
            self.assertEqual(context.principal_id, local_process_identity())
        finally:
            facade.close()
    @unittest.skipUnless(os.name != 'nt', 'Linux uid contract')
    def test_identity_uses_os_uid_not_environment(self):
        with patch.dict(os.environ, {'USERNAME': 'pretend-owner', 'USER': 'pretend-owner'}):
            self.assertEqual(local_process_identity(), 'uid-' + str(os.getuid()))

    def test_active_health_does_not_rewrite_same_metadata_on_each_poll(self):
        with patch.object(self.registry, 'upsert', wraps=self.registry.upsert) as save:
            client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
            client.poll()
            client.poll()
            self.assertEqual(save.call_count, 1)
            client.close()
    def test_duplicate_subscriber_cannot_replace_or_duplicate_worker(self):
        client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        try:
            with self.assertRaisesRegex(RuntimeError, 'subscription_active'):
                CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
            self.assertEqual(len(self.host.sessions), 1)
            self.assertFalse(self.host.sessions[0].closed)
            self.assertEqual(len(client.poll()), 1)
        finally:
            client.close()


class LifecycleBarrierLock:
    """Observe a contender before it enters the real lock; never bypass locking."""
    def __init__(self, lock, thread_name, reached, proceed=None):
        self.lock, self.thread_name = lock, thread_name
        self.reached, self.proceed = reached, proceed
    def __enter__(self):
        if threading.current_thread().name == self.thread_name:
            self.reached.set()
            if self.proceed is not None and not self.proceed.wait(2):
                raise AssertionError('lifecycle barrier was not released')
        return self.lock.__enter__()
    def __exit__(self, *args):
        return self.lock.__exit__(*args)


class HomeLifecycleTests(unittest.TestCase):
    setUp = HomeFacadeTests.setUp
    # Deliberately isolate concurrent lifecycle assertions from worker RPC/network.
    def test_acquisition_paused_before_lock_cannot_start_after_close_returns(self):
        reached, proceed = threading.Event(), threading.Event()
        self.facade._lock = LifecycleBarrierLock(self.facade._lock, 'pending-acquire', reached, proceed)
        results = []
        def acquire():
            try:
                results.append(self.facade.acquire_alarm(self.owner, self.target))
            except Exception as error:
                results.append(error)
        thread = threading.Thread(target=acquire, name='pending-acquire')
        thread.start()
        try:
            self.assertTrue(reached.wait(1), 'Acquisition never reached lifecycle boundary')
            self.facade.close()
        finally:
            proceed.set()
            thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.host.sessions, [], 'Closed facade spawned a worker')
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], AccessDenied)
        self.assertEqual(results[0].code, 'permission_denied')
        self.assertEqual(self.facade.status()['alarm_subscriptions'], 0)

    def test_acquisition_waits_until_old_session_teardown_finishes(self):
        old = self.facade.acquire_alarm(self.owner, self.target)
        entered, permit_close, requested, acquired = (threading.Event() for _ in range(4))
        self.facade._lock = LifecycleBarrierLock(self.facade._lock, 'replacement-acquire', requested)
        original_close = old.close
        results = []
        def close_old():
            entered.set()
            if not permit_close.wait(2):
                raise AssertionError('teardown barrier was not released')
            original_close()
        def acquire():
            try:
                results.append(self.facade.acquire_alarm(self.owner, self.target))
            except Exception as error:
                results.append(error)
            finally:
                acquired.set()
        with patch.object(old, 'close', side_effect=close_old):
            release = threading.Thread(target=self.facade.release_alarm, args=(old,))
            contender = threading.Thread(target=acquire, name='replacement-acquire')
            release.start()
            try:
                self.assertTrue(entered.wait(1), 'Old session did not begin teardown')
                contender.start()
                self.assertTrue(requested.wait(1), 'Replacement did not attempt lifecycle lock')
                self.assertFalse(acquired.wait(.1), 'New worker started during old teardown')
                self.assertEqual(len(self.host.sessions), 1)
            finally:
                permit_close.set()
                release.join(2)
                if contender.ident is not None:
                    contender.join(2)
        self.assertFalse(release.is_alive())
        self.assertFalse(contender.is_alive())
        self.assertTrue(old.closed)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], OfflineSession)
        self.assertIsNot(results[0], old)
        self.assertEqual(len(self.host.sessions), 2)
        self.facade.release_alarm(results[0])

    def test_delayed_stale_release_does_not_repeat_close_or_touch_replacement(self):
        old = self.facade.acquire_alarm(self.owner, self.target)
        stale_waiting, allow_stale = threading.Event(), threading.Event()
        errors = []
        def stale_release():
            stale_waiting.set()
            if not allow_stale.wait(2):
                errors.append('stale release barrier timed out')
                return
            self.facade.release_alarm(old)
        with patch.object(old, 'close', wraps=old.close) as close_old:
            stale = threading.Thread(target=stale_release)
            stale.start()
            try:
                self.assertTrue(stale_waiting.wait(1))
                self.facade.release_alarm(old)
                replacement = self.facade.acquire_alarm(self.owner, self.target)
            finally:
                allow_stale.set()
                stale.join(2)
            self.assertFalse(stale.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(close_old.call_count, 1, 'Stale owner repeated native teardown')
            self.assertFalse(replacement.closed)
            self.assertEqual(self.facade.status()['alarm_subscriptions'], 1)
            self.facade.release_alarm(replacement)


class BridgeBoundaryTests(unittest.TestCase):
    setUp = HomeFacadeTests.setUp

    def real_bridge(self, mode):
        from vox_home.host import AdapterHost
        from vox_home.secrets import SecretBroker, SecretMaterial, SecretRef
        self.target = Target('s1', 'nvr1', mode, 'synthetic')
        self.manifest = AdapterManifest('native.nvr', '1', 1,
            'cctv_test_fixtures:BridgeNativeAdapter',
            ('probe', 'health', 'events', 'credential_use', 'prepare_action'), (self.target,))
        ref = SecretRef('s1', 'nvr1', 'native.nvr', 'fixture-provider-key')
        broker = SecretBroker(self.access, {('s1', 'nvr1', 'native.nvr'): ref},
                              lambda ref: SecretMaterial('owner_hash', 'fixture-material'))
        self.host = AdapterHost(self.access, broker, {'native.nvr': self.manifest})
        self.facade.host, self.facade.evidence_scope = self.host, self.target
        self.facade.configure_native(self.manifest, self.owner)

    @staticmethod
    def release_stream(client):
        client._session.call('prepare_action', {'action': 'release_fixture_stream', 'parameters': {}}, time.time())

    @staticmethod
    def retry_guard():
        class StopAtRetry(threading.Event):
            def __init__(self):
                super().__init__()
                self.retry_waits = 0
            def wait(self, timeout=None):
                if timeout is not None and timeout >= 1:
                    self.retry_waits += 1
                    self.set()
                    return True
                return super().wait(timeout)
        return StopAtRetry()

    def render_viewer_status(self, state):
        # Exercise the real UI refresh consumer without a display server. Only
        # the label/list surfaces and unavailable camera images are substituted.
        import vox_cctv_viewer as viewer
        from types import SimpleNamespace
        class Surface:
            def __init__(self):
                self.text = ''
                self.rows = []
            def configure(self, **values):
                self.text = values.get('text', self.text)
            def delete(self, *args):
                self.rows.clear()
            def insert(self, index, value):
                self.rows.append(value)
            def size(self):
                return len(self.rows)
        app = viewer.Viewer.__new__(viewer.Viewer)
        app.ui_thread, app.closed = threading.get_ident(), False
        app.states = {channel: viewer.CameraState(channel) for channel in viewer.CHANNELS}
        app.headers = {channel: Surface() for channel in viewer.CHANNELS}
        app.images = {channel: Surface() for channel in viewer.CHANNELS}
        app.detail, app.zones, app.photos, app.versions = None, {}, {}, {}
        app.receive_captures, app.update_gallery = lambda now: None, lambda: None
        app.alarm_state, app.alarm_status = state, Surface()
        app.alarm_events, app.banner, app.health = Surface(), Surface(), Surface()
        app.event_group, app.visible_events = 'technical', []
        app.root, app.rain = SimpleNamespace(bell=lambda: None), SimpleNamespace(get=lambda: False)
        app.evidence, app.home_facade = self.store, self.facade
        app.last_metrics = time.monotonic()
        app.refresh_view()
        return app.alarm_status.text

    def test_post_probe_native_rejections_reach_viewer_without_reconnect(self):
        import vox_cctv_viewer as viewer
        for mode, label, status in (
                ('reject_auth_setup', 'Credencial rechazada', 'authentication_failed'),
                ('reject_identity_setup', 'Grabador no verificado', 'identity_mismatch')):
            with self.subTest(mode=mode):
                self.real_bridge(mode)
                state = viewer.AlarmState()
                worker = viewer.AlarmWorker(state, 'unused', facade=self.facade,
                                            context=self.owner, target=self.target)
                worker.stop_event = self.retry_guard()
                worker.run()
                self.assertEqual(state.snapshot()['state'], label)
                self.assertEqual(state.snapshot()['reconnections'], 0)
                self.assertEqual(worker.stop_event.retry_waits, 0)
                self.assertEqual(self.facade.status()['alarm_subscriptions'], 0)
                self.assertEqual(self.facade.status().get('alarm_issue'), status)
                self.assertNotIn('private-fixture', str(self.facade.status()))

    def test_final_native_alarm_is_delivered_before_active_terminal_rejection(self):
        import vox_cctv_viewer as viewer
        for mode, label in (('active_auth', 'Credencial rechazada'),
                            ('active_identity', 'Grabador no verificado')):
            with self.subTest(mode=mode):
                self.real_bridge(mode)
                history_before = len(self.facade.events(self.owner, time.time()))
                state = viewer.AlarmState()
                def factory(legacy_hash, stop):
                    client = CoreAlarmClient(self.facade, self.owner, self.target, stop)
                    self.release_stream(client)
                    # Force the terminal frame and bounded host shutdown to
                    # complete before viewer polling; cached health during an
                    # earlier race cannot accidentally satisfy this regression.
                    deadline = time.monotonic() + 2
                    while client._session.process.poll() is None and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertIsNotNone(client._session.process.poll())
                    return client
                worker = viewer.AlarmWorker(state, 'unused', client_factory=factory)
                worker.stop_event = self.retry_guard()
                worker.run()
                self.assertEqual(state.snapshot()['state'], label)
                self.assertEqual([e['event'] for e in state.snapshot()['events']], ['HumanDetect'])
                self.assertEqual(state.snapshot()['reconnections'], 0)
                self.assertEqual(worker.stop_event.retry_waits, 0)
                self.assertEqual(len(self.facade.events(self.owner, time.time())), history_before + 1)

    def test_real_worker_overflow_reaches_viewer_and_survives_teardown(self):
        import vox_cctv_viewer as viewer
        self.real_bridge('flood')
        state = viewer.AlarmState()
        def factory(legacy_hash, stop):
            client = CoreAlarmClient(self.facade, self.owner, self.target, stop)
            session = client._session
            self.release_stream(client)
            deadline = time.monotonic() + 2
            while session.process.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertIsNotNone(session.process.poll())
            return client
        worker = viewer.AlarmWorker(state, 'unused', client_factory=factory)
        worker.stop_event = self.retry_guard()
        worker.run()
        self.assertTrue(state.snapshot()['events'], 'Viewer discarded the final alarm batch')
        events = self.facade.events(self.owner, time.time())
        self.assertLessEqual(len(events), 128)
        self.assertEqual(events[-1].kind, 'event_overflow')
        status = self.facade.status()
        self.assertEqual(status.get('alarm_issue'), 'event_overflow')
        self.assertTrue(status.get('event_loss'))
        self.assertEqual(status['alarm_subscriptions'], 0)
        visible = self.render_viewer_status(state)
        self.assertIn('event_overflow', visible)
        self.assertIn('Pérdida de avisos', visible)

    def test_final_batch_from_generic_end_is_delivered_once_before_retry(self):
        client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        self.host.sessions[0].failure = 'event_source_ended'
        self.assertEqual([row['Event'] for row in client.poll()], ['HumanDetect'])
        with self.assertRaisesRegex(RuntimeError, 'alarm_worker_unavailable'):
            client.poll()
        client.close()
        self.assertEqual([row.kind for row in self.facade.events(self.owner, time.time())], ['HumanDetect'])
        self.assertEqual(self.facade.status().get('alarm_issue'), 'event_source_ended')

    def test_private_adapter_status_never_enters_diagnostics_or_viewer_copy(self):
        import vox_cctv_viewer as viewer
        client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        self.host.sessions[0].failure = 'private-arbitrary-status ref SID'
        self.assertTrue(client.poll())
        with self.assertRaises(RuntimeError):
            client.poll()
        client.close()
        self.assertEqual(self.facade.status().get('alarm_issue'), 'worker_failed')
        self.assertNotIn('private', str(self.facade.status()))
        self.assertNotIn('private', self.render_viewer_status(viewer.AlarmState()))

    def test_revocation_after_drain_never_delivers_or_remembers_final_batch(self):
        self.access.issue_grant(self.owner, Grant('observer-bridge', 's1', 'observer', ('nvr1',),
            ('events',), time.time() + 30, False))
        observer = AccessContext('s1', 'observer', 'observer-bridge')
        client = CoreAlarmClient(self.facade, observer, self.target, threading.Event())
        session = self.host.sessions[0]
        original_call = session.call
        def revoke_before_health(operation, parameters, now):
            self.access.revoke(self.owner, 'observer-bridge')
            return original_call(operation, parameters, now)
        session.call = revoke_before_health
        with self.assertRaises(AccessDenied):
            client.poll()
        self.assertEqual(self.facade.events(self.owner, time.time()), [])
        client.close()

    def test_permission_denied_terminal_never_delivers_final_batch(self):
        client = CoreAlarmClient(self.facade, self.owner, self.target, threading.Event())
        self.host.sessions[0].failure = 'permission_denied'
        with self.assertRaises(AccessDenied):
            client.poll()
        self.assertEqual(self.facade.events(self.owner, time.time()), [])
        client.close()
