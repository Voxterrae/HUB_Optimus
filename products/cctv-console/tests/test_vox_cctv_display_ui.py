"""Real Tk detail, zone and original-evidence integration (offline workers)."""
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


class DetailUIContracts(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Needs an interactive Tk display')
    def test_detail_controls_and_zone_labels_keep_event_photo_original(self):
        import tkinter as tk
        import vox_cctv_viewer as viewer

        class OfflineWorker:
            def __init__(self, *args):
                self.stop_event = threading.Event()
                self.stream_type = args[3] if len(args) == 4 else 'Extra1'
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
            app = viewer.Viewer(root, 'unused')
            try:
                original = b'P6\n2 1\n255\n' + bytes([16, 32, 48, 255, 0, 64])
                app.select_camera('C1 · Zona 1')
                root.update_idletasks()
                self.assertEqual(app.detail, 0)
                self.assertEqual(app.camera_choice.get(), 'C1 · Zona 1')
                self.assertIn('sin verificar en esta instalación', app.detail_info.cget('text'))
                for state in app.states.values():
                    state.publish(original, 1920, 1080)
                app.refresh_view()
                self.assertEqual(app.photos[0].get(0, 0), (16, 32, 48))
                self.assertIn('C1 · Zona 1', app.headers[0].cget('text'))
                other_photo = app.photos[1]
                app.display_mode.set('Sombras fuertes')
                app.display_changed()
                app.refresh_view()
                self.assertEqual(app.photos[0].get(0, 0), (37, 60, 79))
                self.assertIs(app.photos[1], other_photo)
                self.assertIn('Vista realzada', app.detail_notice.cget('text'))
                app.alarm_state.add({'Channel': 0, 'Event': 'HumanDetect', 'Status': 'Start',
                                     'StartTime': '2026-10-03 22:00:00'})
                app.refresh_view()
                self.assertIn('C1 · Zona 1', app.alarm_events.get(0))
                self.assertIs(app.states[0].capture_snapshot()['ppm'], original)
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    root.update()
                    rows = app.evidence.list_entries()
                    if rows and app.evidence.read_image(rows[0]['id']):
                        break
                    time.sleep(.01)
                self.assertEqual(app.evidence.read_image(rows[0]['id']), original)
                app.open_gallery((1, 'HumanDetect'))
                root.update_idletasks()
                self.assertIn('C1 · Zona 1', app.gallery_list.get(0))
                self.assertIn('C1 · Zona 1', app.gallery_details.cget('text'))
                self.assertEqual(app.gallery_photo.get(0, 0), (16, 32, 48))
                app.show_mosaic()
                root.update_idletasks()
                self.assertEqual(app.display_mode.get(), 'Original')
                self.assertFalse(app.detail_controls.winfo_manager())
                self.assertIsNone(app.display._derived)
                self.assertIsNone(app.last_ui_error)
            finally:
                app.close()


if __name__ == '__main__':
    unittest.main()
