"""Delivery wiring uses receipt freshness and never logs local pairing data."""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from test_vox_cctv_usability import app_fixture, report


class PhoneWiring(unittest.TestCase):
    def test_metrics_contains_mobile_state_without_pairing_link_or_token(self):
        app = app_fixture()
        app.last_ui_error = None
        app.phone_notifier = SimpleNamespace(snapshot=lambda: {'state':'Móvil sin conectar',
            'connected':False, 'sent':0, 'queued':0, 'ambiguous':0, 'dropped':0,
            'in_flight':False, 'token':'PRIVATE_TOKEN', 'url':'PRIVATE_PAIRING_LINK'})
        with tempfile.TemporaryDirectory() as directory:
            app.status_path = Path(directory) / 'status.json'
            app.write_metrics([])
            raw = app.status_path.read_text(encoding='utf-8')
        document = json.loads(raw)
        self.assertEqual(document.get('phone', {}).get('state'), 'Móvil sin conectar')
        self.assertNotIn('PRIVATE_TOKEN', raw)
        self.assertNotIn('PRIVATE_PAIRING_LINK', raw)

    def test_fresh_start_reaches_phone_once_before_capture_cooldown(self):
        app = app_fixture()
        received = []
        app.phone_notifier = SimpleNamespace(submit=lambda event: received.append(dict(event)))
        app.states[4].capture_snapshot = lambda **kwargs: None
        app.evidence.add = lambda *args: False
        app.alarm_state.add(report('HumanDetect'), now=100)
        app.receive_captures(101)
        app.receive_captures(102)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['event'], 'HumanDetect')
        self.assertEqual(received[0]['status'], 'Start')

    def test_expired_receipt_never_reaches_phone(self):
        app = app_fixture()
        received = []
        app.phone_notifier = SimpleNamespace(submit=lambda event: received.append(event))
        app.evidence.add = lambda *args: False
        app.alarm_state.add(report('HumanDetect'), now=100)
        app.receive_captures(131)
        self.assertEqual(received, [])

    def test_stop_motion_and_technical_do_not_reach_phone(self):
        app = app_fixture()
        received = []
        app.phone_notifier = SimpleNamespace(submit=lambda event: received.append(event))
        app.evidence.add = lambda *args: False
        for kind, status in [('HumanDetect','Stop'),('VideoBlind','Start'),('VideoMotion','Start')]:
            app.alarm_state.add(report(kind, status), now=100)
        app.receive_captures(101)
        self.assertEqual(received, [])

    def test_mobile_failure_does_not_interrupt_local_capture(self):
        app = app_fixture()
        def unavailable(event): raise OSError('local notifier unavailable')
        app.phone_notifier = SimpleNamespace(submit=unavailable)
        app.states[4].capture_snapshot = lambda **kwargs: None
        saved = []
        app.evidence.add = lambda event, capture: saved.append(event) or False
        app.alarm_state.add(report('HumanDetect'), now=100)
        app.receive_captures(101)
        self.assertEqual(len(saved), 1)


if __name__ == '__main__':
    unittest.main()
