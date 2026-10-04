"""Existing receive-only recorder transport, parser and exact owner credential.

Importing this module opens no socket and reads no credential. Video decoding,
alarm policy, evidence storage and the user interface remain in the viewer.
"""
from __future__ import annotations

import ctypes
from collections import deque
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import select
import socket
import struct
import sys
import time

from vox_cctv_config import RECORDER_IP, CREDENTIAL_TARGET, RECORDER_SERIAL, require_configuration
MAX_PACKET = 4 * 1024 * 1024
MAX_FRAME = 8 * 1024 * 1024
MAX_BUFFER = 12 * 1024 * 1024
CHANNELS = tuple(range(7))


class ProtocolError(Exception):
    pass


class AuthError(Exception):
    pass


class SourceError(Exception):
    pass


class AlarmUnavailable(Exception):
    pass


@dataclass
class MediaFrame:
    kind: int
    codec: str | None
    payload: bytes
    width: int = 0
    height: int = 0
    fps: int | None = None


class MediaBuffer:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, chunk: bytes) -> list[MediaFrame]:
        if len(self.buffer) + len(chunk) > MAX_BUFFER:
            raise ProtocolError('Media buffer exceeds limit')
        self.buffer.extend(chunk)
        frames = []
        while len(self.buffer) >= 8:
            b = self.buffer
            if b[:3] != b'\x00\x00\x01':
                raise ProtocolError('Invalid media prefix')
            kind = b[3]
            width = height = 0
            fps = None
            codec = None
            if kind in (0xfc, 0xfe):
                header = 16
                if len(b) < header:
                    break
                length = struct.unpack_from('<I', b, 12)[0]
                codec = {2: 'h264', 3: 'hevc'}.get(b[4] & 15)
                width = (b[6] | ((b[4] & 0x30) << 4)) * 8
                height = (b[7] | ((b[4] & 0xc0) << 2)) * 8
                # Some older devices return undocumented flags in this byte.
                # Do not infer a bit mask or claim an implausible source rate.
                fps = b[5] if 1 <= b[5] <= 60 else None
            elif kind == 0xfd:
                header = 8
                length = struct.unpack_from('<I', b, 4)[0]
            elif kind in (0xfa, 0xf9):
                header = 8
                length = struct.unpack_from('<H', b, 6)[0]
            else:
                raise ProtocolError('Unsupported media frame type')
            if length > MAX_FRAME:
                raise ProtocolError('Media frame exceeds limit')
            if len(b) < header + length:
                break
            payload = bytes(b[header:header + length])
            del b[:header + length]
            frames.append(MediaFrame(kind, codec, payload, width, height, fps))
        return frames


def sofia_hash(password: str) -> str:
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    digest = hashlib.md5(password.encode('utf-8')).digest()
    return ''.join(alphabet[(digest[i] + digest[i + 1]) % 62] for i in range(0, 16, 2))


def owner_hash() -> str:
    """Reads only the exact recorder credential, never enumerates the vault."""
    require_configuration()
    if sys.platform != 'win32':
        raise OSError('Windows is required for the owner credential')
    class Credential(ctypes.Structure):
        _fields_ = [
            ('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
            ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
            ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
            ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)),
            ('Persist', wintypes.DWORD), ('AttributeCount', wintypes.DWORD),
            ('Attributes', ctypes.c_void_p), ('TargetAlias', wintypes.LPWSTR),
            ('UserName', wintypes.LPWSTR),
        ]
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    pointer = ctypes.POINTER(Credential)()
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(Credential))]
    api.CredReadW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    if not api.CredReadW(CREDENTIAL_TARGET, 1, 0, ctypes.byref(pointer)):
        raise AuthError('Owner credential is unavailable')
    private = None
    try:
        item = pointer.contents
        size = item.CredentialBlobSize
        if not 0 < size <= 2048 or size % 2:
            raise AuthError('Owner credential is invalid')
        private = ctypes.string_at(item.CredentialBlob, size).decode('utf-16-le')
        result = sofia_hash(private)
        ctypes.memset(item.CredentialBlob, 0, size)
        return result
    finally:
        private = None
        api.CredFree(pointer)


class NativeClient:
    """Only connects to the explicitly known local recorder; video is optional."""
    def __init__(self, auth_hash: str, channel: int, stream_type: str, stop_event=None, *,
                 monitor=True, recorder_ip: str = RECORDER_IP,
                 expected_serial: str = RECORDER_SERIAL):
        if channel not in CHANNELS or stream_type not in ('Main', 'Extra1'):
            raise ValueError('Invalid configured channel or stream')
        if recorder_ip == '127.0.0.1' or expected_serial == 'unconfigured':
            raise SourceError('installation_configuration_required')
        self.stop_event = stop_event
        self.sock = socket.create_connection((recorder_ip, 34567), timeout=5)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.session = 0
        self.sequence = 0
        self.channel = channel
        self.stream_type = stream_type
        self.parser = MediaBuffer()
        self.alive_period = 10.0
        try:
            self.send(1000, {'EncryptType': 'MD5', 'LoginType': 'DVRIP-Web', 'UserName': 'admin', 'PassWord': auth_hash})
            header_session, response = self.response(1001)
            self.require_login(response)
            self.session = int(str(response.get('SessionID', hex(header_session))), 16)
            interval = float(response.get('AliveInterval', 20))
            self.alive_period = max(3.0, min(10.0, interval / 2.0))
            self.send(1020, {'Name': 'SystemInfo', 'SessionID': f'0x{self.session:08X}'})
            _, identity = self.response(1021)
            info = identity.get('SystemInfo')
            if identity.get('Ret') != 100 or not isinstance(info, dict) or info.get('SerialNo') != expected_serial:
                raise SourceError('Recorder identity could not be verified')
            self.verified_serial = info['SerialNo']
            if monitor:
                self.send(1413, self.monitor_body('Claim'))
                _, claim = self.response(1414)
                self.require_ok(claim)
                self.send(1410, self.monitor_body('Start'))
            self.next_alive = time.monotonic() + self.alive_period
        except Exception:
            self.close()
            raise

    def monitor_body(self, action):
        return {'Name': 'OPMonitor', 'SessionID': f'0x{self.session:08X}', 'OPMonitor': {
            'Action': action, 'Parameter': {'Channel': self.channel, 'CombinMode': 'NONE',
                'StreamType': self.stream_type, 'TransMode': 'TCP'}}}

    def send(self, message, body, *, response_sequence=None):
        if self.stop_event is not None and self.stop_event.is_set():
            raise InterruptedError('Viewer stopped')
        payload = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8') + b'\n\0'
        sequence = self.sequence if response_sequence is None else response_sequence
        header = struct.pack('<BB2xII2xHI', 255, 0, self.session, sequence, message, len(payload))
        if response_sequence is None:
            self.sequence = (self.sequence + 1) & 0xffffffff
        self.sock.settimeout(5)
        self.sock.sendall(header + payload)

    def read_exact(self, length, deadline):
        result = bytearray()
        while len(result) < length:
            if self.stop_event is not None and self.stop_event.is_set():
                raise InterruptedError('Viewer stopped')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Recorder response timed out')
            self.sock.settimeout(min(5, remaining))
            part = self.sock.recv(length - len(result))
            if not part:
                raise EOFError('Recorder disconnected')
            result.extend(part)
        return bytes(result)

    def receive(self, deadline=None, *, with_sequence=False):
        if deadline is None:
            deadline = time.monotonic() + 12
        header = self.read_exact(20, deadline)
        if header[0] != 255:
            raise ProtocolError('Invalid recorder packet')
        message = struct.unpack_from('<H', header, 14)[0]
        length = struct.unpack_from('<I', header, 16)[0]
        if length > MAX_PACKET:
            raise ProtocolError('Recorder packet exceeds limit')
        session = struct.unpack_from('<I', header, 4)[0]
        payload = self.read_exact(length, deadline)
        if with_sequence:
            return message, session, payload, struct.unpack_from('<I', header, 8)[0]
        return message, session, payload

    @staticmethod
    def parse_response(payload):
        try:
            response = json.loads(payload.rstrip(b'\0\r\n '))
            if not isinstance(response, dict):
                raise ValueError()
            return response
        except (ValueError, UnicodeError):
            raise ProtocolError('Invalid recorder response') from None

    @staticmethod
    def require_ok(response):
        if response.get('Ret') in (106, 113, 203, 204, 205, 206, 207):
            raise AuthError('Authentication or access rejected')
        if response.get('Ret') != 100:
            raise ProtocolError('Monitor request rejected')

    @staticmethod
    def require_login(response):
        if response.get('Ret') in (106, 113, 203, 204, 205, 206, 207):
            raise AuthError('Authentication or access rejected')
        if response.get('Ret') != 100:
            raise ProtocolError('Login could not be completed')

    def response(self, expected):
        deadline = time.monotonic() + 12
        for _ in range(64):
            message, session, payload = self.receive(deadline)
            if message == expected:
                return session, self.parse_response(payload)
        raise ProtocolError('Matching recorder response is missing')

    def frames(self):
        while self.stop_event is None or not self.stop_event.is_set():
            if time.monotonic() >= self.next_alive:
                self.send(1006, {'Name': 'KeepAlive', 'SessionID': f'0x{self.session:08X}'})
                self.next_alive = time.monotonic() + self.alive_period
            message, _, payload = self.receive()
            if message == 1412:
                yield from self.parser.feed(payload)
            elif message in (1411, 1414, 1007):
                self.require_ok(self.parse_response(payload))
            # Other framed packets, including AlarmInfo 1504, are fully consumed.

    def close(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except (OSError, AttributeError):
            pass
        try:
            self.sock.close()
        except (OSError, AttributeError):
            pass


ALARM_LABELS = {
    'HumanDetect': 'Persona detectada',
    'appEventHumanDetectAlarm': 'Persona detectada',
    'CarShapeDetect': 'Vehículo detectado',
    'FaceDetection': 'Cara detectada',
    'FaceDetect': 'Cara detectada',
    'VideoMotion': 'Movimiento detectado',
    'MotionDetect': 'Movimiento detectado',
    'VideoLoss': 'Pérdida de vídeo',
    'LossDetect': 'Pérdida de vídeo',
    'VideoBlind': 'Vídeo obstruido',
    'BlindDetect': 'Vídeo obstruido',
    'Blind': 'Vídeo obstruido',
    'StorageNotExist': 'Almacenamiento no disponible',
    'StorageLowSpace': 'Poco espacio de almacenamiento',
    'StorrageLowSpace': 'Poco espacio de almacenamiento',
    'StorageFailureWrite': 'Fallo de escritura en almacenamiento',
    'StorageFailureRead': 'Fallo de lectura en almacenamiento',
    'StorageReadError': 'Fallo de lectura en almacenamiento',
    'NetIPConfict': 'Conflicto de dirección de red',
    'NetAbort': 'Desconexión de red',
    'IPCAlarm': 'Aviso de cámara',
    'VideoAnalyze': 'Aviso de análisis de vídeo',
    'VIdeoAnanyze': 'Aviso de análisis de vídeo',
}
STORAGE_ALARMS = frozenset(event for event in ALARM_LABELS if event.startswith(('Storage', 'Storrage')))
SOUND_ALARMS = STORAGE_ALARMS | frozenset(('HumanDetect', 'appEventHumanDetectAlarm', 'CarShapeDetect', 'VideoLoss', 'LossDetect'))


def safe_alarm(info):
    """Retain four bounded fields, never face identities or arbitrary payloads."""
    if not isinstance(info, dict):
        return None
    raw_event = info.get('Event')
    if not isinstance(raw_event, str) or len(raw_event) > 96:
        return None
    event = raw_event.split(':', 1)[0]
    if event not in ALARM_LABELS or info.get('Status') not in ('Start', 'Stop', 'None'):
        return None
    channel = info.get('Channel')
    if type(channel) is int and channel in CHANNELS:
        channel += 1
    elif event in STORAGE_ALARMS and channel in (-1, 0xffffffff, None):
        channel = None  # Recorder-wide storage alerts are not attributed to another camera.
    else:
        return None
    timestamp = info.get('StartTime')
    if isinstance(timestamp, str) and len(timestamp) == 19:
        try:
            datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            timestamp = None
    else:
        timestamp = None
    return {'channel': channel, 'event': event, 'status': info['Status'], 'time': timestamp}


class NativeAlarmClient(NativeClient):
    """One additional receive-only subscription; no persistent alarm configuration."""
    def __init__(self, auth_hash, stop_event=None, *, recorder_ip: str = RECORDER_IP,
                 expected_serial: str = RECORDER_SERIAL):
        super().__init__(auth_hash, 0, 'Extra1', stop_event, monitor=False,
                         recorder_ip=recorder_ip, expected_serial=expected_serial)
        self.pending = deque(maxlen=25)
        try:
            self.send(1500, {'Name': '', 'SessionID': f'0x{self.session:08X}'})
            deadline = time.monotonic() + 12
            for _ in range(64):
                message, session, payload, sequence = self.receive(deadline, with_sequence=True)
                if session != self.session:
                    continue
                if message == 1504:
                    event = self.alarm_info(payload, sequence)
                    if event is not None:
                        self.pending.append(event)
                elif message == 1501:
                    response = self.parse_response(payload)
                    if response.get('Ret') in (103, 502, 605, 607):
                        raise AlarmUnavailable('Alarm subscription is unavailable')
                    self.require_ok(response)
                    self.last_reply = time.monotonic()
                    break
            else:
                raise ProtocolError('Alarm subscription acknowledgement is missing')
        except Exception:
            self.close()
            raise

    def alarm_info(self, payload, sequence):
        if len(payload) > 65536:
            raise ProtocolError('Alarm report exceeds limit')
        body = self.parse_response(payload)
        if body.get('Name') != 'AlarmInfo' or not isinstance(body.get('AlarmInfo'), dict):
            return None
        session = body.get('SessionID')
        if not isinstance(session, str) or len(session) > 10:
            return None
        try:
            if int(session, 16) != self.session:
                return None
        except ValueError:
            return None
        # ALARM_REQ 1504 is a recorder-originated request. Acknowledge receipt
        # with ALARM_RSP 1505, even if its event is not in the local UI whitelist.
        # Echo its packet sequence without advancing this client's request counter.
        self.send(1505, {'SessionID': f'0x{self.session:08X}', 'Ret': 100}, response_sequence=sequence)
        info = safe_alarm(body.get('AlarmInfo'))
        if info is None:
            return None
        return {'Channel': info['channel'] - 1 if info['channel'] is not None else -1,
            'Event': info['event'], 'Status': info['status'], 'StartTime': info['time']}

    def poll(self):
        if self.pending:
            return [self.pending.popleft()]
        now = time.monotonic()
        if now - self.last_reply > max(30, self.alive_period * 3):
            raise TimeoutError('Alarm connection has no recent reply')
        if now >= self.next_alive:
            self.send(1006, {'Name': 'KeepAlive', 'SessionID': f'0x{self.session:08X}'})
            self.next_alive = time.monotonic() + self.alive_period
        # A quiet alarm connection is normal. Do not discard a partial packet on idle.
        readable, _, _ = select.select([self.sock], [], [], min(1, max(0, self.next_alive - time.monotonic())))
        if not readable:
            return []
        message, session, payload, sequence = self.receive(with_sequence=True)
        if session != self.session:
            return []
        if message == 1504:
            info = self.alarm_info(payload, sequence)
            self.last_reply = time.monotonic()
            return [info] if info is not None else []
        if message in (1007, 1501):
            self.require_ok(self.parse_response(payload))
            self.last_reply = time.monotonic()
        return []

