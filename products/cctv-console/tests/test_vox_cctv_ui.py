"""Real Tk integration check; substitutes only the external NVR workers."""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


class ViewerUIContracts(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Needs an interactive Tk display')
    def test_event_opens_a_photo_and_preferences_survive_the_window(self):
        import tkinter as tk
        import vox_cctv_viewer as viewer
        from vox_cctv_alarm_policy import AlarmPolicy

        class OfflineWorker:
            def __init__(self, *args):
                self.stop_event = threading.Event()
                self.stream_type = 'Extra1'
            def start(self):
                pass
            def stop(self):
                self.stop_event.set()
            def is_alive(self):
                return False

        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {'LOCALAPPDATA': directory}), \
                patch.object(viewer, 'CameraWorker', OfflineWorker), \
                patch.object(viewer, 'AlarmWorker', OfflineWorker):
            root = tk.Tk()
            root.withdraw()
            app = viewer.Viewer(root, 'unused-network-credential')
            try:
                ppm = b'P6\n64 48\n255\n' + b'\x20\x70\x40' * (64 * 48)
                for state in app.states.values():
                    state.publish(ppm, 704, 480)
                app.alarm_state.add({'Channel': 0, 'Event': 'HumanDetect', 'Status': 'Start',
                                     'StartTime': '2026-10-03 22:00:00'})
                app.refresh_view()
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline:
                    root.update()
                    rows = app.evidence.list_entries()
                    if rows and app.evidence.read_image(rows[0]['id']):
                        break
                    time.sleep(.02)
                self.assertEqual(len(rows), 1)
                self.assertEqual((rows[0]['width'], rows[0]['height']), (64, 48))
                app.open_gallery((1, 'HumanDetect'))
                root.update()
                self.assertIsNotNone(app.gallery_photo, 'An actual Tk photo must open from the event gallery')
                app.select_group('technical')
                app.refresh_view()
                self.assertIn('Todavía', app.alarm_events.get(0), 'An empty group must not retain old detection rows')
                app.sound.set(False)
                app.preferences_changed()
                self.assertFalse(AlarmPolicy.load(app.preferences_path).sound_enabled)
                self.assertTrue(AlarmPolicy.load(app.preferences_path).rain_mode)
                self.assertIsNone(app.last_ui_error)
            finally:
                app.close()


class HomeViewerBridgeContracts(unittest.TestCase):
    def test_production_main_attempts_core_and_explicit_phase0_rollback(self):
        import sys
        import types
        import vox_cctv_viewer as viewer
        root = types.SimpleNamespace(withdraw=lambda: None, deiconify=lambda: None,
                                     mainloop=lambda: None, destroy=lambda: None)
        tk = types.SimpleNamespace(Tk=lambda: root)
        tk.messagebox = types.SimpleNamespace(showinfo=lambda *a, **k: None, showerror=lambda *a, **k: None)
        av = types.SimpleNamespace(logging=types.SimpleNamespace(PANIC=0, set_level=lambda x: None),
                                   CodecContext=types.SimpleNamespace(create=lambda *a: None))
        calls = []
        with patch.dict(sys.modules, {'tkinter': tk, 'av': av}), \
                patch.object(viewer, 'instance_mutex', return_value=None), \
                patch.object(viewer, 'owner_hash', return_value='synthetic'), \
                patch.object(viewer, 'Viewer', side_effect=lambda *a, **kw: calls.append(kw)):
            viewer.main()
            self.assertEqual(calls, [{'use_home_core': True}])
            viewer.main(phase0=True)
        self.assertEqual(calls, [{'use_home_core': True}, {'use_home_core': False}])

    def test_gallery_refusal_never_reads_store_directly(self):
        import vox_cctv_viewer as viewer
        from vox_home.access import AccessDenied
        from unittest.mock import Mock
        app = viewer.Viewer.__new__(viewer.Viewer)
        app.ui_thread = threading.get_ident()
        app.gallery_list = Mock()
        app.gallery_list.curselection.return_value = (0,)
        app.gallery_rows = [{'id': 'synthetic'}]
        app.gallery_image = Mock()
        app.gallery_details = Mock()
        app.evidence = Mock()
        app.evidence.read_image.side_effect = AssertionError('Gallery bypassed core permission checks')
        app.home_facade = Mock()
        app.home_context = object()
        app.home_facade.read_evidence.side_effect = AccessDenied('permission_denied')
        app.show_capture()
        app.evidence.read_image.assert_not_called()
        self.assertIsNone(app.gallery_photo)
        self.assertIn('permission_denied', str(app.gallery_image.configure.call_args))

    @unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Needs an interactive Tk display')
    def test_single_alarm_subscription_keeps_seven_video_workers(self):
        import tkinter as tk
        import vox_cctv_viewer as viewer
        from vox_cctv_evidence import EvidenceStore
        from vox_home.access import AccessContext, AccessService
        from vox_home.contracts import AdapterManifest, Target
        from vox_home.facade import CoreFacade
        from vox_home.registry import Registry
        from cctv_test_fixtures import OfflineHost
        class OfflineVideo:
            def __init__(self, *args):
                self.stream_type = 'Extra1'
            def start(self): pass
            def stop(self): pass
            def is_alive(self): return False
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'LOCALAPPDATA': directory}), \
                patch.object(viewer, 'CameraWorker', OfflineVideo):
            target = Target('s1', 'nvr1', 'offline.invalid', 'synthetic')
            owner = AccessContext('s1', 'owner', None)
            store = EvidenceStore(Path(directory) / 'captures', min_free_bytes=0)
            host = OfflineHost()
            facade = CoreFacade(Registry(Path(directory) / 'meta.sqlite3'),
                                AccessService({'s1': 'owner'}), host, store, target)
            facade.configure_native(AdapterManifest('native.nvr', '1', 1,
                'vox_home.adapters.native:NativeAdapter', ('probe', 'events', 'health'), (target,)), owner)
            facade.registry.close()  # Metadata loss must not stop mosaic/gallery.
            root = tk.Tk()
            root.withdraw()
            app = viewer.Viewer(root, 'unused', home_facade=facade, home_context=owner,
                                home_target=target, evidence_store=store)
            try:
                deadline = time.monotonic()+2
                while time.monotonic() < deadline and not facade.status()['core_active']:
                    root.update()
                    time.sleep(.02)
                self.assertEqual(len(app.workers), 7)
                self.assertEqual(sum(s.subscriptions for s in host.sessions), 1)
                self.assertIs(app.evidence, facade.evidence_store)
                app.write_metrics([])
                status = json.loads(app.status_path.read_text(encoding='utf-8'))['home']
                self.assertTrue(status['core_active'])
                self.assertEqual(status['alarm_subscriptions'], 1)
                self.assertEqual(status['metadata'], 'metadata_unavailable')
                app.open_gallery()
                root.update()
                self.assertTrue(app.gallery.winfo_exists())
                self.assertNotIn('principal', json.dumps(status))
            finally:
                app.close()
            self.assertTrue(host.sessions[0].closed)


if __name__ == '__main__':
    unittest.main()
