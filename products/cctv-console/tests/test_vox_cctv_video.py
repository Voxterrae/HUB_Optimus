import unittest
import threading
from types import SimpleNamespace
from unittest.mock import patch

class TimingContracts(unittest.TestCase):
    def player(self):
        from vox_cctv_video import SequenceInspector
        app=SequenceInspector.__new__(SequenceInspector)
        app.identifier='a'*32;app.stop_event=threading.Event();app.pause_event=threading.Event()
        app.lock=threading.Lock();app.target=(2,2);app.latest=None;app.version=0;app.closed=False
        app.error=None;app.done=False
        frame=SimpleNamespace(width=2,height=2,reformat=lambda **kwargs:frame)
        app.manager=SimpleNamespace(playback_frames=lambda *args:iter([(frame,-9.3),(frame,-9.1)]))
        return app

    def test_decoder_uses_receipt_aware_verified_reader(self):
        app=self.player()
        with patch('vox_cctv_video._ppm',return_value=b'pixels'):
            app.decode()
        self.assertEqual(app.latest[0],b'pixels')
        self.assertAlmostEqual(app.latest[1],.2)
        self.assertTrue(app.done)
        self.assertIsNone(app.error)

    def test_close_during_reformat_never_publishes_after_close(self):
        app=self.player()
        def cancelled(frame):
            with app.lock:app.closed=True;app.stop_event.set()
            return b'pixels'
        with patch('vox_cctv_video._ppm',side_effect=cancelled):
            app.decode()
        self.assertIsNone(app.latest)

    def test_recorded_receipt_times_are_relative_to_first_packet(self):
        from vox_cctv_video import playback_times
        self.assertEqual(playback_times({'frames':[{'event_offset_seconds':-9.3},
            {'event_offset_seconds':-9.2},{'event_offset_seconds':2.1}]}),[0,.1,11.4])
        self.assertEqual(playback_times({'frames':[]}),[])

if __name__=='__main__': unittest.main()
