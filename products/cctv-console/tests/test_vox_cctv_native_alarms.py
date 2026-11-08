"""Offline framed-transport regressions for alarm subscription startup."""
import json
import struct
import unittest
from unittest.mock import patch

import vox_cctv_native as native


def packet(message, body, sequence=1):
    payload = json.dumps(body).encode('utf-8') + b'\n\0'
    return struct.pack('<BB2xII2xHI', 255, 0, 1, sequence, message, len(payload)) + payload


class RecorderSocket:
    def __init__(self, subscription_packets):
        self.wire = bytearray(
            packet(1001, {'Ret': 100, 'SessionID': '0x00000001', 'AliveInterval': 20}) +
            packet(1021, {'Ret': 100, 'SystemInfo': {'SerialNo': 'unit-test-recorder'}}) +
            subscription_packets)
        self.sent = []
        self.closed = False

    def setsockopt(self, *args):
        pass

    def settimeout(self, timeout):
        pass

    def sendall(self, data):
        self.sent.append((struct.unpack_from('<H', data, 14)[0],
                          struct.unpack_from('<I', data, 8)[0],
                          json.loads(data[20:].rstrip(b'\n\0'))))

    def recv(self, count):
        chunk = bytes(self.wire[:min(count, 7)])
        del self.wire[:len(chunk)]
        return chunk

    def shutdown(self, mode):
        pass

    def close(self):
        self.closed = True


class AlarmSubscriptionTests(unittest.TestCase):
    def test_successful_subscription_delivers_every_report_in_maximum_pre_ack_burst(self):
        # A 25-entry pending queue loses the first 38 already-acknowledged
        # reports; 63 reports plus the subscription ACK fit the handshake.
        expected = [
            {'Channel': index % 7, 'Event': 'HumanDetect',
             'Status': 'Start' if index % 2 == 0 else 'Stop',
             'StartTime': f'2026-10-26 13:{index // 60:02d}:{index % 60:02d}'}
            for index in range(63)
        ]
        reports = b''.join(packet(1504, {'Name': 'AlarmInfo', 'SessionID': '0x00000001',
                                       'AlarmInfo': event}, sequence=100 + index)
                           for index, event in enumerate(expected))
        wire = RecorderSocket(reports + packet(1501, {'Ret': 100}))
        with patch.object(native.socket, 'create_connection', return_value=wire), \
                patch.object(native.select, 'select', return_value=([], [], [])):
            client = native.NativeAlarmClient('synthetic-hash')
            try:
                received = [event for _ in range(63) for event in client.poll()]
                self.assertEqual(len(received), 63,
                                 'Every acknowledged startup alarm must reach the consumer')
                self.assertEqual(received, expected)
                self.assertEqual(client.poll(), [])
                client.send(1006, {'Name': 'KeepAlive', 'SessionID': '0x00000001'})
            finally:
                client.close()

        acknowledgements = [(sequence, body) for message, sequence, body in wire.sent
                            if message == 1505]
        self.assertEqual(acknowledgements,
                         [(sequence, {'SessionID': '0x00000001', 'Ret': 100})
                          for sequence in range(100, 163)])
        self.assertEqual(wire.sent[-1][:2], (1006, 3))

    def test_subscription_still_fails_and_closes_after_64_packets_without_ack(self):
        event = {'Channel': 0, 'Event': 'HumanDetect', 'Status': 'Start',
                 'StartTime': '2026-10-26 13:00:00'}
        report = {'Name': 'AlarmInfo', 'SessionID': '0x00000001', 'AlarmInfo': event}
        reports = b''.join(packet(1504, report, sequence=100 + index) for index in range(64))
        wire = RecorderSocket(reports + packet(1501, {'Ret': 100}))
        with patch.object(native.socket, 'create_connection', return_value=wire):
            with self.assertRaisesRegex(native.ProtocolError,
                                        'Alarm subscription acknowledgement is missing'):
                native.NativeAlarmClient('synthetic-hash')
        self.assertTrue(wire.closed)
        self.assertEqual(bytes(wire.wire), packet(1501, {'Ret': 100}))


if __name__ == '__main__':
    unittest.main()
