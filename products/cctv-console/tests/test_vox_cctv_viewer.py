import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.find_spec('vox_cctv_viewer')
viewer = None
if spec:
    import vox_cctv_viewer as viewer


class ViewerContracts(unittest.TestCase):
    def test_capture_time_normalises_offsets_to_the_same_local_clock(self):
        display = getattr(viewer, 'display_received_time', None)
        self.assertTrue(callable(display), 'Gallery timestamps must account for UTC storage')
        self.assertEqual(display('2026-10-03T20:00:00+00:00'),
                         display('2026-10-03T22:00:00+02:00'))
        self.assertEqual(display(None), 'No disponible')

    def test_capture_uses_stored_pixels_and_age_instead_of_source_dimensions(self):
        state = viewer.CameraState(0)
        capture = getattr(state, 'capture_snapshot', None)
        self.assertTrue(callable(capture), 'Event photos need an atomic fresh-frame snapshot')
        ppm = b'P6\n2 1\n255\n' + b'\xff\x00\x00\x00\xff\x00'
        state.publish(ppm, 2560, 1440, now=10)
        photo = capture(now=11)
        self.assertEqual(photo['ppm'], ppm)
        self.assertEqual((photo['width'], photo['height']), (2, 1))
        self.assertEqual((photo['source_width'], photo['source_height']), (2560, 1440))
        self.assertEqual(photo['frame_age_seconds'], 1)
        self.assertEqual(photo['stream'], 'Extra1')

    def test_event_photo_never_uses_a_missing_stale_or_truncated_frame(self):
        state = viewer.CameraState(0)
        capture = getattr(state, 'capture_snapshot', None)
        self.assertTrue(callable(capture), 'Missing evidence must be explicit')
        self.assertIsNone(capture(now=1))
        state.publish(b'P6\n1 1\n255\n\xff\x00\x00', 1, 1, now=10)
        self.assertIsNone(capture(now=12.01))
        state.publish(b'P6\n2 1\n255\n\xff', 2, 1, now=13)
        self.assertIsNone(capture(now=13.1))

    def test_new_event_delivery_is_deduplicated_and_drops_private_fields(self):
        state = viewer.AlarmState()
        drain = getattr(state, 'drain_pending', None)
        self.assertTrue(callable(drain), 'Captures must use new events, not replay old history')
        event = {'Channel': 0, 'Event': 'HumanDetect', 'Status': 'Start',
                 'StartTime': '2026-10-03 22:00:00', 'PassWord': 'private'}
        state.add(event, now=1)
        state.add(event, now=2)
        received = drain()
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['event']['channel'], 1)
        self.assertNotIn('private', json.dumps(received))
        self.assertEqual(drain(), [])

    def test_refresh_keeps_running_after_an_individual_update_failure(self):
        instance = object.__new__(viewer.Viewer)
        instance.ui_thread = threading.get_ident()
        instance.closed = False
        instance.last_ui_error = None
        class Root:
            def __init__(self):
                self.callbacks = []
            def after(self, delay, callback):
                self.callbacks.append(callback)
        instance.root = Root()
        instance.states = {0: object()}
        instance.refresh()
        self.assertEqual(len(instance.root.callbacks), 1,
                         'An update failure must not permanently freeze the live window')
        self.assertIsNotNone(instance.last_ui_error)

    def test_metrics_refresh_existing_telemetry_when_windows_denies_replace(self):
        instance = object.__new__(viewer.Viewer)
        instance.detail = None
        instance.alarm_state = viewer.AlarmState()
        instance.evidence = SimpleNamespace(list_entries=lambda: [])
        instance.last_ui_error = None
        with tempfile.TemporaryDirectory() as directory:
            instance.status_path = Path(directory) / 'viewer_status.json'
            instance.status_path.write_text(json.dumps({
                'checked_at_local': '2000-01-01T00:00:00+0000',
                'channels': [{'channel': 1, 'decoded_frames': 1}],
                'obsolete_padding': 'old telemetry' * 1000,
            }), encoding='utf-8')
            with patch.object(viewer.os, 'replace', side_effect=PermissionError(13, 'Access denied')):
                instance.write_metrics([{'channel': 1, 'decoded_frames': 42}])
            document = json.loads(instance.status_path.read_text(encoding='utf-8'))
            self.assertEqual(document['channels'], [{'channel': 1, 'decoded_frames': 42}],
                             'A denied atomic replacement must not leave frozen telemetry')
            self.assertNotEqual(document['checked_at_local'], '2000-01-01T00:00:00+0000')
            self.assertNotIn('obsolete_padding', document)
            self.assertFalse(instance.status_path.with_suffix('.tmp').exists())

    def require_module(self):
        self.assertIsNotNone(viewer, 'The local CCTV viewer implementation is missing')

    def test_frame_fragmentation_and_multiple_frames_keep_video_payload(self):
        self.require_module()
        # 2560x1440 keyframe: width high bit in T, LE length at offset 12.
        key = b'\x00\x00\x01\xfc\x13\x19\x40\xb4' + b'\0' * 4 + struct.pack('<I', 6) + b'ABCDEF'
        audio = b'\x00\x00\x01\xfa\x0e\x00\x03\x00xyz'
        delta = b'\x00\x00\x01\xfd\x03\x00\x00\x00GHI'
        parser = viewer.MediaBuffer()
        frames = []
        wire = key + audio + delta
        for index in range(0, len(wire), 3):
            frames += parser.feed(wire[index:index + 3])
        video = [f for f in frames if f.kind in (0xfc, 0xfd)]
        self.assertEqual([f.payload for f in video], [b'ABCDEF', b'GHI'])
        self.assertEqual(video[0].codec, 'hevc')
        self.assertEqual((video[0].width, video[0].height, video[0].fps), (2560, 1440, 25))

    def test_invalid_prefix_and_excessive_declared_length_are_rejected(self):
        self.require_module()
        with self.assertRaises(viewer.ProtocolError):
            viewer.MediaBuffer().feed(b'\x11' * 16)
        with self.assertRaises(viewer.ProtocolError):
            viewer.MediaBuffer().feed(b'\x00\x00\x01\xfd' + struct.pack('<I', 128 * 1024 * 1024))

    def test_implausible_wire_fps_is_unknown_instead_of_displaying_72(self):
        self.require_module()
        wire = b'\x00\x00\x01\xfc\x02\x48\xf0\x87' + b'\0' * 4 + struct.pack('<I', 3) + b'KEY'
        frame = viewer.MediaBuffer().feed(wire)[0]
        self.assertIsNone(frame.fps, 'Unverified wire flags must not become a claimed frame rate')

    def test_rgb_padding_is_excluded_from_in_memory_ppm(self):
        self.require_module()
        class Plane:
            line_size = 8
            def __bytes__(self):
                return b'\x01\x02\x03\x04\x05\x06zz\x07\x08\x09\x0a\x0b\x0cyy'
        class Frame:
            width = 2
            height = 2
            planes = [Plane()]
        self.assertEqual(viewer.rgb_to_ppm(Frame()), b'P6\n2 2\n255\n' + bytes(range(1, 13)))

    def test_authentication_failure_is_terminal_without_retries(self):
        self.require_module()
        calls = []
        class RejectClient:
            def __init__(self, *args):
                calls.append(1)
                raise viewer.AuthError('Authentication rejected')
        state = viewer.CameraState(0)
        worker = viewer.CameraWorker(0, state, 'abcdefgh', 'Extra1', client_factory=RejectClient)
        worker.run()
        self.assertEqual(len(calls), 1)
        self.assertEqual(state.snapshot(1)['status'], 'Credencial rechazada')
        self.assertIsNone(worker.auth_hash, 'Stopped workers must release their private authentication value')

    def test_transient_login_error_stays_retryable_but_wrong_password_is_terminal(self):
        self.require_module()
        classify = getattr(viewer.NativeClient, 'require_login', None)
        self.assertTrue(callable(classify), 'Login results need separate transient/authentication handling')
        with self.assertRaises(viewer.ProtocolError):
            classify({'Ret': 108})
        with self.assertRaises(viewer.AuthError):
            classify({'Ret': 203})

    def test_reconnection_uses_new_codec_context_and_waits_for_keyframe(self):
        self.require_module()
        contexts = []
        class Context:
            thread_count = 0
            thread_type = None
            def parse(self, payload):
                return [payload]
            def decode(self, packet):
                return [packet]
        class Av:
            class CodecContext:
                @staticmethod
                def create(codec, mode):
                    contexts.append(Context())
                    return contexts[-1]
        key = viewer.MediaFrame(0xfc, 'hevc', b'KEY', 1920, 1080, 25)
        delta = viewer.MediaFrame(0xfd, None, b'DELTA')
        first = viewer.DecoderSink(Av)
        self.assertEqual(first.decode(delta), [])
        self.assertEqual(first.decode(key), [b'KEY'])
        second = viewer.DecoderSink(Av)
        self.assertEqual(second.decode(delta), [])
        self.assertEqual(second.decode(key), [b'KEY'])
        self.assertIsNot(contexts[0], contexts[1])

    def test_stale_frame_is_not_reported_as_live(self):
        self.require_module()
        state = viewer.CameraState(2)
        state.publish(b'picture', 640, 360, now=10)
        self.assertEqual(state.snapshot(12)['status'], 'En vivo')
        self.assertEqual(state.snapshot(16)['status'], 'Sin señal reciente')
        state.reset('Conectando')
        self.assertIsNone(state.image()[0])

    def test_tk_calls_from_worker_thread_are_rejected(self):
        self.require_module()
        errors = []
        owner = threading.get_ident()
        def check():
            try:
                viewer.require_ui_thread(owner)
            except RuntimeError:
                errors.append(True)
        thread = threading.Thread(target=check)
        thread.start()
        thread.join()
        self.assertEqual(errors, [True])

    def test_wrong_recorder_identity_is_terminal_before_requesting_video(self):
        self.require_module()
        def packet(message, payload):
            return struct.pack('<BB2xII2xHI', 255, 0, 1, 1, message, len(payload)) + payload
        login = b'{"Ret":100,"SessionID":"0x00000001","AliveInterval":20}\n\0'
        wrong = b'{"Ret":100,"SystemInfo":{"SerialNo":"different-recorder"}}\n\0'
        class Socket:
            def __init__(self):
                self.wire = bytearray(packet(1001, login) + packet(1021, wrong))
                self.sent = []
            def setsockopt(self, *args):
                pass
            def settimeout(self, timeout):
                pass
            def sendall(self, data):
                self.sent.append(struct.unpack_from('<H', data, 14)[0])
            def recv(self, count):
                chunk = bytes(self.wire[:min(count, 3)])
                del self.wire[:len(chunk)]
                return chunk
            def shutdown(self, mode):
                pass
            def close(self):
                pass
        wire = Socket()
        source_error = getattr(viewer, 'SourceError', None)
        self.assertIsNotNone(source_error, 'Wrong-recorder identity needs a terminal source error')
        with patch.object(viewer.socket, 'create_connection', return_value=wire):
            with self.assertRaises(source_error):
                viewer.NativeClient('abcdefgh', 0, 'Extra1')
        self.assertEqual(wire.sent, [1000, 1020], 'A wrong recorder must never receive a monitor claim')

    def test_alarm_subscription_checks_source_without_opening_a_video_stream(self):
        self.require_module()
        alarm_client = getattr(viewer, 'NativeAlarmClient', None)
        self.assertIsNotNone(alarm_client, 'A separate bounded alarm receiver is required')
        def packet(message, payload):
            return struct.pack('<BB2xII2xHI', 255, 0, 1, 1, message, len(payload)) + payload
        class Socket:
            def __init__(self):
                self.wire = bytearray(
                    packet(1001, b'{"Ret":100,"SessionID":"0x00000001","AliveInterval":20}\n\0') +
                    packet(1021, b'{"Ret":100,"SystemInfo":{"SerialNo":"unit-test-recorder"}}\n\0') +
                    packet(1501, b'{"Ret":100}\n\0'))
                self.sent = []
            def setsockopt(self, *args):
                pass
            def settimeout(self, timeout):
                pass
            def sendall(self, data):
                self.sent.append((struct.unpack_from('<H', data, 14)[0], json.loads(data[20:].rstrip(b'\n\0'))))
            def recv(self, count):
                chunk = bytes(self.wire[:min(count, 3)])
                del self.wire[:len(chunk)]
                return chunk
            def shutdown(self, mode):
                pass
            def close(self):
                pass
        wire = Socket()
        with patch.object(viewer.socket, 'create_connection', return_value=wire):
            client = alarm_client('abcdefgh')
            client.close()
        self.assertEqual([message for message, _ in wire.sent], [1000, 1020, 1500])
        self.assertEqual(wire.sent[-1][1], {'Name': '', 'SessionID': '0x00000001'})

    def test_alarm_history_drops_private_fields_and_is_bounded_to_25(self):
        self.require_module()
        alarm_state = getattr(viewer, 'AlarmState', None)
        self.assertIsNotNone(alarm_state, 'Alarm history must be bounded and sanitised')
        state = alarm_state()
        for index in range(40):
            state.add({'Channel': 2, 'Event': 'HumanDetect:1', 'Status': 'Start' if index % 2 == 0 else 'Stop',
                'StartTime': '2026-10-03 22:00:00', 'PersonName': 'private', 'SessionID': 'private', 'PassWord': 'private'}, now=index + 1)
        entries = state.snapshot(41)['events']
        self.assertEqual(len(entries), 25)
        self.assertEqual(set(entries[0]), {'channel', 'event', 'status', 'time'})
        self.assertEqual(entries[0]['channel'], 3)
        self.assertEqual(entries[0]['event'], 'HumanDetect')
        self.assertNotIn('private', json.dumps(entries))

    def test_alarm_reports_are_acknowledged_with_their_sequence_only_in_the_verified_session(self):
        self.require_module()
        def packet(message, body, sequence=1, session=1):
            payload = json.dumps(body).encode() + b'\n\0'
            return struct.pack('<BB2xII2xHI', 255, 0, session, sequence, message, len(payload)) + payload
        def report(event, session='0x00000001', name='AlarmInfo'):
            return {'Name': name, 'SessionID': session, 'AlarmInfo': {'Channel': 0,
                'Event': event, 'Status': 'Start', 'StartTime': '2026-10-03 22:00:00'}}
        class Socket:
            def __init__(self):
                self.wire = bytearray(
                    packet(1001, {'Ret': 100, 'SessionID': '0x00000001', 'AliveInterval': 20}) +
                    packet(1021, {'Ret': 100, 'SystemInfo': {'SerialNo': 'unit-test-recorder'}}) +
                    packet(1504, report('HumanDetect'), sequence=77) +
                    packet(1501, {'Ret': 100}) +
                    packet(1504, report('UnknownDeviceEvent'), sequence=78) +
                    packet(1504, report('HumanDetect'), sequence=79, session=2) +
                    packet(1504, report('HumanDetect', session='0x00000002'), sequence=80) +
                    packet(1504, report('HumanDetect', name='Malformed'), sequence=81) +
                    packet(1504, report('VideoLoss'), sequence=82))
                self.sent = []
            def setsockopt(self, *args):
                pass
            def settimeout(self, timeout):
                pass
            def sendall(self, data):
                self.sent.append((struct.unpack_from('<H', data, 14)[0],
                    struct.unpack_from('<I', data, 8)[0], json.loads(data[20:].rstrip(b'\n\0'))))
            def recv(self, count):
                chunk = bytes(self.wire[:min(count, 3)])
                del self.wire[:len(chunk)]
                return chunk
            def shutdown(self, mode):
                pass
            def close(self):
                pass
        wire = Socket()
        with patch.object(viewer.socket, 'create_connection', return_value=wire), \
                patch.object(viewer.select, 'select', return_value=([wire], [], [])):
            client = viewer.NativeAlarmClient('abcdefgh')
            self.assertEqual(client.poll()[0]['Event'], 'HumanDetect')
            for _ in range(4):
                self.assertEqual(client.poll(), [])
            self.assertEqual(client.poll()[0]['Event'], 'VideoLoss')
            client.send(1006, {'Name': 'KeepAlive', 'SessionID': '0x00000001'})
            client.close()
        acknowledgements = [(sequence, body) for message, sequence, body in wire.sent if message == 1505]
        self.assertEqual(acknowledgements, [(sequence, {'SessionID': '0x00000001', 'Ret': 100})
            for sequence in (77, 78, 82)], 'Valid reports need receipt acknowledgements, including ignored unknown events')
        self.assertEqual(wire.sent[-1][:2], (1006, 3), 'Response acknowledgements must preserve the outgoing request counter')
        self.assertNotIn(1506, [message for message, _, _ in wire.sent], 'Receiving alarms must never inject a network alarm')

    def test_alarm_duplicates_mute_and_30_second_sound_throttle(self):
        self.require_module()
        alarm_state = getattr(viewer, 'AlarmState', None)
        self.assertIsNotNone(alarm_state, 'Owner-controlled alarm sounds are required')
        state = alarm_state()
        base = {'Channel': 0, 'Event': 'HumanDetect', 'StartTime': '2026-10-03 22:00:00'}
        self.assertTrue(state.add(dict(base, Status='Start'), now=1))
        self.assertTrue(state.consume_sound(now=1))
        self.assertFalse(state.add(dict(base, Status='Start'), now=2))
        self.assertFalse(state.consume_sound(now=2))
        self.assertTrue(state.add(dict(base, Status='Stop'), now=3))
        self.assertFalse(state.consume_sound(now=3))
        state.add(dict(base, Status='Start'), now=10)
        self.assertFalse(state.consume_sound(now=10))
        state.add(dict(base, Status='Stop'), now=32)
        state.add(dict(base, Status='Start'), now=33)
        self.assertTrue(state.consume_sound(now=33))
        state.set_sound(False)
        state.add(dict(base, Status='Stop'), now=64)
        state.add(dict(base, Status='Start'), now=65)
        self.assertFalse(state.consume_sound(now=65))

    def test_motion_and_face_reports_are_visual_only_and_invalid_channels_are_ignored(self):
        self.require_module()
        alarm_state = getattr(viewer, 'AlarmState', None)
        self.assertIsNotNone(alarm_state)
        state = alarm_state()
        for event in ('VideoMotion', 'FaceDetect', 'FaceDetection'):
            state.add({'Channel': 0, 'Event': event, 'Status': 'Start', 'StartTime': '2026-10-03 22:00:00'}, now=1)
            self.assertFalse(state.consume_sound(now=1))
        before = len(state.snapshot(2)['events'])
        self.assertFalse(state.add({'Channel': 9, 'Event': 'HumanDetect', 'Status': 'Start', 'StartTime': '2026-10-03 22:00:00'}, now=2))
        self.assertEqual(len(state.snapshot(2)['events']), before)

    def test_reconnection_recovers_an_alarm_start_after_a_lost_stop(self):
        self.require_module()
        state = viewer.AlarmState()
        event = {'Channel': 1, 'Event': 'HumanDetect', 'Status': 'Start', 'StartTime': '2026-10-03 22:00:00'}
        state.add(event, now=1)
        self.assertTrue(state.consume_sound(now=1))
        state.reset('Reconectando avisos')
        connected = getattr(state, 'connected', None)
        self.assertTrue(callable(connected), 'A confirmed new subscription must reset stale alarm transitions')
        connected(now=35)
        self.assertTrue(state.add(event, now=36), 'An unreceived Stop must not suppress future starts after reconnection')
        self.assertTrue(state.consume_sound(now=36))
        self.assertEqual(len(state.snapshot(37)['events']), 2, 'History survives reconnection')

    def test_storage_none_is_audible_bounded_and_deduplicated_by_report_time(self):
        self.require_module()
        state = viewer.AlarmState()
        report = {'Channel': -1, 'Event': 'StorageFailureWrite', 'Status': 'None', 'StartTime': '2026-10-03 22:00:00'}
        self.assertTrue(state.add(report, now=1))
        self.assertTrue(state.consume_sound(now=1), 'Documented storage alarms can omit Start/Stop transitions')
        self.assertFalse(state.add(report, now=2))
        self.assertFalse(state.consume_sound(now=2))
        later = dict(report, StartTime='2026-10-03 22:01:00')
        self.assertTrue(state.add(later, now=35))
        self.assertTrue(state.consume_sound(now=35))
        self.assertIsNone(state.snapshot(36)['events'][0]['channel'])
        for event in ('VideoMotion', 'FaceDetect'):
            state.add({'Channel': 1, 'Event': event, 'Status': 'None', 'StartTime': '2026-10-03 22:01:00'}, now=70)
            self.assertFalse(state.consume_sound(now=70))


if __name__ == '__main__':
    unittest.main()
