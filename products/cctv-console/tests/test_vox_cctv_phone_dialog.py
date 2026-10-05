"""Real Tk mobile wizard contracts, using no network or native credentials.

Linux without a display skips these cases. On an interactive Windows desktop
the tests instantiate the production dialog and exercise its actual buttons,
entries and scheduled callbacks with an in-memory notifier.
"""
import os
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import vox_cctv_viewer as viewer
from test_vox_cctv_usability import app_fixture, report


TOKEN = '123456789:' + 'a' * 35
LINK = 'https://t.me/OwnerCCTVBot?start=' + 'n' * 43


class FakeNotifier:
    def __init__(self):
        self.info = {'state': 'Móvil sin conectar'}
        self.pairings = []
        self.revocations = 0
        self.closes = 0

    def start_pairing(self, token):
        self.pairings.append(token)
        self.info = {'state': 'Abra el enlace en su teléfono',
                     'url': LINK, 'expires_seconds': 599}
        return True

    def pairing_info(self):
        return dict(self.info)

    def revoke(self):
        self.revocations += 1
        self.info = {'state': 'Móvil sin conectar'}

    def close(self):
        self.closes += 1


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class PhoneReceiptBoundaryContracts(unittest.TestCase):
    def test_thirty_second_human_and_car_receipts_bypass_capture_cooldown(self):
        for kind in ('HumanDetect', 'appEventHumanDetectAlarm', 'CarShapeDetect'):
            with self.subTest(kind=kind):
                app = app_fixture()
                received = []
                app.phone_notifier = SimpleNamespace(submit=lambda event: received.append(dict(event)))
                app.last_capture[(5, kind)] = 129
                def unexpected_capture(*args):
                    self.fail('capture cooldown must remain active during independent phone delivery')
                app.evidence.add = unexpected_capture
                app.alarm_state.add(report(kind), now=100)
                app.receive_captures(130)
                self.assertEqual(len(received), 1)
                self.assertEqual(received[0]['event'], kind)

    def test_future_and_over_thirty_second_receipts_do_not_reach_phone(self):
        for now in (99, 130.001):
            with self.subTest(now=now):
                app = app_fixture()
                received = []
                app.phone_notifier = SimpleNamespace(submit=lambda event: received.append(event))
                app.evidence.add = lambda *args: False
                app.alarm_state.add(report('CarShapeDetect'), now=100)
                app.receive_captures(now)
                self.assertEqual(received, [])


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'),
                     'Needs an interactive Tk display')
class RealTkPhoneDialogContracts(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.tk = tk
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest('Interactive Tk unavailable: ' + type(error).__name__)
        self.root.withdraw()
        self.tk_errors = []
        self.root.report_callback_exception = lambda kind, value, trace: self.tk_errors.append(kind)
        self.notifier = FakeNotifier()
        self.app = viewer.Viewer.__new__(viewer.Viewer)
        self.app.tk, self.app.root = tk, self.root
        self.app.ui_thread = threading.get_ident()
        self.app.closed = False
        self.app.phone_window = None
        self.app.phone_notifier = self.notifier
        self.app.pending_callbacks = set()
        # Keep production callback registration/cancellation; shorten the dialog
        # poll interval to avoid a one-second delay per interaction.
        self.app.defer = lambda delay, callback: viewer.Viewer.defer(self.app, 5, callback)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for identifier in tuple(self.app.pending_callbacks):
            try:
                self.root.after_cancel(identifier)
            except self.tk.TclError:
                pass
        self.app.pending_callbacks.clear()
        try:
            self.root.destroy()
        except self.tk.TclError:
            pass

    def pump_until(self, condition):
        deadline = time.monotonic() + .5
        while time.monotonic() < deadline:
            self.root.update()
            if condition():
                self.assertEqual(self.tk_errors, [])
                return
            time.sleep(.002)
        self.fail('Tk callback did not settle within the bounded test interval')

    def controls(self):
        widgets = list(descendants(self.app.phone_window))
        tokens = [item for item in widgets if isinstance(item, self.tk.Entry)
                  and item.cget('show') == '*']
        links = [item for item in widgets if isinstance(item, self.tk.Entry)
                 and item.cget('state') == 'readonly']
        buttons = {item.cget('text'): item for item in widgets
                   if isinstance(item, self.tk.Button)}
        self.assertEqual(len(tokens), 1)
        self.assertEqual(len(links), 1)
        return tokens[0], links[0], buttons

    def test_open_is_empty_masked_and_duplicate_keeps_one_dialog(self):
        self.app.open_phone_dialog()
        first = self.app.phone_window
        token, link, _ = self.controls()
        self.assertEqual(token.get(), '')
        self.assertEqual(token.cget('show'), '*')
        self.assertEqual(link.get(), '')
        self.assertEqual(len(self.app.pending_callbacks), 1)
        self.app.open_phone_dialog()
        self.assertIs(self.app.phone_window, first)
        self.assertEqual(len(self.app.pending_callbacks), 1)
        self.assertEqual(self.notifier.pairings, [])

    def test_connect_clears_token_and_requires_explicit_link_action(self):
        with patch('webbrowser.open') as open_browser:
            self.app.open_phone_dialog()
            token, link, buttons = self.controls()
            token.insert(0, '  ' + TOKEN + '  ')
            buttons['Conectar y activar avisos'].invoke()
            self.assertEqual(token.get(), '')
            self.assertEqual(self.notifier.pairings, [TOKEN])
            self.pump_until(lambda: link.get() == LINK)
            open_browser.assert_not_called()
            buttons['Abrir enlace de Telegram'].invoke()
            open_browser.assert_called_once_with(LINK)
            self.notifier.info = {'state': 'Móvil conectado'}
            self.pump_until(lambda: link.get() == '')
            labels = [item.cget('text') for item in descendants(self.app.phone_window)
                      if isinstance(item, self.tk.Label)]
            self.assertIn('Móvil conectado', labels)
            self.assertFalse(any(TOKEN in label for label in labels))
            buttons['Desconectar móvil'].invoke()
            self.pump_until(lambda: self.notifier.revocations == 1 and link.get() == '')

    def test_dialog_close_stops_poll_and_reopen_has_clean_token(self):
        self.app.open_phone_dialog()
        token, _, _ = self.controls()
        token.insert(0, TOKEN)
        previous = self.app.phone_window
        previous.destroy()
        self.pump_until(lambda: not self.app.pending_callbacks)
        self.assertEqual(self.notifier.closes, 0)
        self.assertEqual(self.notifier.revocations, 0)
        self.app.open_phone_dialog()
        self.assertIsNot(self.app.phone_window, previous)
        token, _, _ = self.controls()
        self.assertEqual(token.get(), '')
        self.assertEqual(len(self.app.pending_callbacks), 1)

    def test_viewer_close_closes_notifier_and_cancels_dialog_callbacks(self):
        self.app.open_phone_dialog()
        stopped = []
        self.app.workers = {}
        self.app.alarm_worker = SimpleNamespace(stop=lambda: stopped.append('alarms'))
        self.app.sequence_manager = None
        self.app.inspectors = []
        self.app.home_facade = None
        self.app.evidence = SimpleNamespace(close=lambda: stopped.append('evidence'))
        self.app.gallery = None
        self.app.display = SimpleNamespace(reset=lambda: None)
        self.app.photos = {}
        self.app.close()
        self.assertTrue(self.app.closed)
        self.assertEqual(self.notifier.closes, 1)
        self.assertEqual(stopped, ['alarms', 'evidence'])
        self.assertEqual(self.app.pending_callbacks, set())
        self.assertEqual(self.tk_errors, [])


if __name__ == '__main__':
    unittest.main()
