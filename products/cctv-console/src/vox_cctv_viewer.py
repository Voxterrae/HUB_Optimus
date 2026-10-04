"""Local, receive-only CCTV viewer with bounded event photos for Voxterrae.

Requires PyAV in this directory's lib folder and the owner's Windows credential.
Protocol: OpenIPC/python-dvr and AlexxIT/go2rtc DVRIP monitor contracts.
"""
from __future__ import annotations

import ctypes
from collections import deque
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import struct
import sys
import threading
import time
from vox_cctv_alarm_policy import AlarmPolicy
from vox_cctv_evidence import EvidenceStore
from vox_cctv_display import DetailDisplay, MODES
from vox_cctv_photos import PhotoInspector, dimensions as photo_dimensions, fit_size, resize_ppm
from vox_home.access import AccessDenied
from vox_home.facade import CoreAlarmClient, bootstrap_local_core
from vox_cctv_metadata import camera_label, capability_info, load_zones

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR / 'lib'))
from vox_cctv_native import (
    RECORDER_IP, CREDENTIAL_TARGET, RECORDER_SERIAL, MAX_PACKET, MAX_FRAME,
    MAX_BUFFER, CHANNELS, ProtocolError, AuthError, SourceError, AlarmUnavailable,
    MediaFrame, MediaBuffer, sofia_hash, owner_hash, NativeClient,
    ALARM_LABELS, STORAGE_ALARMS, SOUND_ALARMS, safe_alarm, NativeAlarmClient,
)


class AlarmState:
    def __init__(self, policy=None):
        self.lock = threading.Lock()
        self.status = 'Conectando avisos'
        self.last_reply = 0.0
        self.last_error_kind = None
        self.reconnections = 0
        self.history = deque(maxlen=25)
        self.transitions = {}
        self.sound_enabled = True
        self.pending_sound = False
        self.last_sound = float('-inf')
        self.version = 0
        self.policy = policy or AlarmPolicy()
        self.sound_enabled = self.policy.sound_enabled
        self.pending_events = deque(maxlen=64)

    def reset(self, status, error_kind=None):
        with self.lock:
            self.status = status
            self.last_reply = 0.0
            self.last_error_kind = error_kind
            self.pending_sound = False

    def touch(self, now=None):
        with self.lock:
            self.status = 'Escuchando avisos'
            self.last_reply = time.monotonic() if now is None else now
            self.last_error_kind = None

    def connected(self, now=None):
        with self.lock:
            # A Stop may have been lost while disconnected. A new confirmed
            # subscription begins a new transition set, preserving history.
            self.transitions.clear()
            self.policy.new_subscription()
            self.status = 'Escuchando avisos'
            self.last_reply = time.monotonic() if now is None else now
            self.last_error_kind = None

    def add(self, info, now=None):
        event = safe_alarm(info)
        if event is None:
            return False
        if now is None:
            now = time.monotonic()
        key = (event['channel'], event['event'])
        transition = (event['status'], event['time']) if event['event'] in STORAGE_ALARMS and event['status'] == 'None' else event['status']
        with self.lock:
            if self.transitions.get(key) == transition:
                return False
            self.transitions[key] = transition
            self.history.appendleft(event)
            self.pending_events.append({'event': dict(event), 'received_monotonic': now})
            self.policy.add(event, now)
            self.version += 1
            audible = self.policy.notify(event, now)
            if self.sound_enabled and audible:
                self.pending_sound = True
        return True

    def drain_pending(self):
        with self.lock:
            events = list(self.pending_events)
            self.pending_events.clear()
            return events

    def grouped(self, group):
        with self.lock:
            return self.policy.grouped(group)

    def preferences(self):
        with self.lock:
            return self.policy.preferences()

    def configure(self, **preferences):
        with self.lock:
            self.policy.configure(**preferences)
            self.sound_enabled = self.policy.sound_enabled
            self.pending_sound = False

    def save_preferences(self, path):
        with self.lock:
            self.policy.save(path)

    def set_sound(self, enabled):
        with self.lock:
            self.sound_enabled = bool(enabled)
            self.policy.configure(sound_enabled=self.sound_enabled)
            if not self.sound_enabled:
                self.pending_sound = False

    def consume_sound(self, now=None):
        if now is None:
            now = time.monotonic()
        with self.lock:
            play = self.pending_sound and self.sound_enabled
            self.pending_sound = False
            if play:
                self.last_sound = now
            return bool(play)

    def snapshot(self, now=None):
        if now is None:
            now = time.monotonic()
        with self.lock:
            age = max(0, now - self.last_reply) if self.last_reply else None
            status = self.status
            if status == 'Escuchando avisos' and (age is None or age > 30):
                status = 'Escucha sin respuesta reciente'
            return {'state': status, 'last_reply_age_seconds': round(age, 2) if age is not None else None,
                'last_error_kind': self.last_error_kind, 'reconnections': self.reconnections,
                'sound_enabled': self.sound_enabled, 'events': [dict(event) for event in self.history]}


class AlarmWorker(threading.Thread):
    def __init__(self, state, auth_hash, client_factory=NativeAlarmClient, *,
                 facade=None, context=None, target=None):
        super().__init__(name='CCTV-Alarmas', daemon=True)
        self.state = state
        self.auth_hash = auth_hash
        self.client_factory = (
            (lambda legacy_hash, stop: CoreAlarmClient(facade, context, target, stop))
            if facade is not None else client_factory)
        self.stop_event = threading.Event()
        self.client_lock = threading.Lock()
        self.client = None

    def stop(self):
        self.stop_event.set()
        with self.client_lock:
            if self.client is not None:
                self.client.close()

    def run(self):
        try:
            self.run_listener()
        finally:
            self.auth_hash = None

    def run_listener(self):
        backoff = 2
        while not self.stop_event.is_set():
            client = None
            try:
                self.state.reset('Conectando avisos')
                client = self.client_factory(self.auth_hash, self.stop_event)
                with self.client_lock:
                    self.client = client
                if self.stop_event.is_set():
                    return
                self.state.connected(client.last_reply)
                observed_reply = client.last_reply
                while not self.stop_event.is_set():
                    reports = client.poll()
                    if client.last_reply != observed_reply:
                        observed_reply = client.last_reply
                        self.state.touch(observed_reply)
                        backoff = 2
                    for report in reports:
                        if self.stop_event.is_set():
                            return
                        self.state.add(report)
            except SourceError:
                self.state.reset('Grabador no verificado', 'SourceError')
                return
            except AuthError:
                self.state.reset('Credencial rechazada', 'AuthError')
                return
            except AccessDenied:
                self.state.reset('permission_denied', 'AccessDenied')
                return
            except AlarmUnavailable:
                self.state.reset('Avisos no disponibles', 'AlarmUnavailable')
                return
            except Exception as error:
                if not self.stop_event.is_set():
                    self.state.reset('Reconectando avisos', type(error).__name__)
                    with self.state.lock:
                        self.state.reconnections += 1
            finally:
                if client is not None:
                    client.close()
                with self.client_lock:
                    self.client = None
            if self.stop_event.wait(backoff):
                break
            backoff = min(10, backoff * 2)


class DecoderSink:
    def __init__(self, av_module=None):
        if av_module is None:
            import av as av_module
        self.av = av_module
        self.context = None
        self.codec = None

    def decode(self, frame: MediaFrame):
        if frame.kind not in (0xfc, 0xfd):
            return []
        if frame.kind == 0xfc:
            if frame.codec not in ('h264', 'hevc'):
                raise ProtocolError('Unsupported video codec')
            if frame.codec != self.codec:
                self.codec = frame.codec
                self.context = self.av.CodecContext.create(self.codec, 'r')
                self.context.thread_count = 1
                self.context.thread_type = 'SLICE'
        if self.context is None:
            return []  # Every new connection waits for an independently decodable keyframe.
        decoded = []
        for packet in self.context.parse(frame.payload):
            decoded.extend(self.context.decode(packet))
        return decoded


def rgb_to_ppm(frame) -> bytes:
    plane = frame.planes[0]
    raw = bytes(plane)
    row_bytes = frame.width * 3
    if plane.line_size < row_bytes or len(raw) < plane.line_size * frame.height:
        raise ProtocolError('Invalid RGB frame dimensions')
    pixels = b''.join(raw[row * plane.line_size:row * plane.line_size + row_bytes] for row in range(frame.height))
    return f'P6\n{frame.width} {frame.height}\n255\n'.encode('ascii') + pixels


class CameraState:
    def __init__(self, channel):
        self.lock = threading.Lock()
        self.channel = channel
        self.stream_type = 'Extra1'
        self.status = 'Conectando'
        self.ppm = None
        self.original_ppm = None
        self.original_frame_time = 0.0
        self.original_dimensions = (0, 0)
        self.original_hash = None
        self.last_frame = 0.0
        self.frames_decoded = 0
        self.frames_displayed = 0
        self.width = self.height = 0
        self.source_fps = None
        self.reconnections = 0
        self.last_error_kind = None
        self.frame_hash = None
        self.render_size = (440, 250)

    def reset(self, status, error_kind=None):
        with self.lock:
            self.status = status
            self.ppm = None
            self.original_ppm = None
            self.original_frame_time = 0.0
            self.original_hash = None
            self.last_frame = 0.0
            self.last_error_kind = error_kind
            self.frame_hash = None

    def set_mode(self, mode):
        with self.lock:
            self.stream_type = mode

    def set_render_size(self, width, height):
        with self.lock:
            self.render_size = (max(32, min(1920, width)), max(32, min(1080, height)))

    def size(self):
        with self.lock:
            return self.render_size

    def decoded(self, frame, source_fps):
        with self.lock:
            self.frames_decoded += 1
            self.width, self.height = frame.width, frame.height
            self.source_fps = source_fps

    def publish(self, ppm, width, height, now=None):
        if now is None:
            now = time.monotonic()
        digest = hashlib.sha256(ppm).hexdigest()
        with self.lock:
            self.ppm = ppm
            self.width, self.height = width, height
            self.frames_displayed += 1
            self.last_frame = now
            self.frame_hash = digest
            self.status = 'En vivo'
            self.last_error_kind = None

    def image(self):
        with self.lock:
            return self.ppm, self.frames_displayed

    def publish_original(self, ppm, width, height, now=None):
        now = time.monotonic() if now is None else now
        digest = hashlib.sha256(ppm).hexdigest()
        with self.lock:
            self.original_ppm = ppm
            self.original_frame_time = now
            self.original_dimensions = (width, height)
            self.original_hash = digest

    def capture_snapshot(self, max_age_seconds=2, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            original = self.original_ppm if self.original_ppm is not None else self.ppm
            stamp = self.original_frame_time if self.original_ppm is not None else self.last_frame
            age = max(0, now - stamp)
            if original is None or not stamp or age > max_age_seconds:
                return None
            try:
                magic, dimensions, maximum, pixels = original.split(b'\n', 3)
                width, height = map(int, dimensions.split())
                if magic != b'P6' or maximum != b'255' or not (0 < width <= 4096 and 0 < height <= 4096) or len(pixels) != width * height * 3 or len(original) > 32 * 1024 * 1024:
                    return None
            except (ValueError, TypeError):
                return None
            return {'ppm': original, 'frame_age_seconds': round(age, 3),
                'width': width, 'height': height, 'source_width': self.width,
                'source_height': self.height, 'stream': self.stream_type,
                'frame_hash_sha256': self.original_hash if self.original_ppm is not None else self.frame_hash}

    def snapshot(self, now=None):
        if now is None:
            now = time.monotonic()
        with self.lock:
            age = max(0.0, now - self.last_frame) if self.last_frame else None
            status = self.status
            if status == 'En vivo' and (age is None or age > 5):
                status = 'Sin señal reciente'
            return {'channel': self.channel + 1, 'stream': self.stream_type,
                'status': status, 'last_frame_age_seconds': round(age, 2) if age is not None else None,
                'frames_decoded': self.frames_decoded, 'frames_displayed': self.frames_displayed,
                'width': self.width, 'height': self.height, 'source_fps': self.source_fps,
                'capture_dimensions': list(self.original_dimensions) if self.original_ppm is not None else None,
                'capture_age_seconds': round(max(0, now - self.original_frame_time), 2) if self.original_ppm is not None else None,
                'reconnections': self.reconnections, 'last_error_kind': self.last_error_kind,
                'frame_hash_sha256': self.frame_hash}


class CameraWorker(threading.Thread):
    def __init__(self, channel, state, auth_hash, stream_type, client_factory=NativeClient):
        super().__init__(name=f'CCTV-{channel + 1}', daemon=True)
        self.channel = channel
        self.state = state
        self.auth_hash = auth_hash
        self.stream_type = stream_type
        self.client_factory = client_factory
        self.stop_event = threading.Event()
        self.client_lock = threading.Lock()
        self.client = None
        self.state.set_mode(stream_type)

    def stop(self):
        self.stop_event.set()
        with self.client_lock:
            if self.client is not None:
                self.client.close()

    def run(self):
        try:
            self.run_streams()
        finally:
            self.auth_hash = None

    def run_streams(self):
        backoff = 2
        while not self.stop_event.is_set():
            client = None
            try:
                self.state.reset('Conectando')
                client = self.client_factory(self.auth_hash, self.channel, self.stream_type, self.stop_event)
                with self.client_lock:
                    self.client = client
                if self.stop_event.is_set():
                    return
                sink = DecoderSink()  # A fresh decoder belongs to each newly established connection.
                rendered_at = 0.0
                original_at = 0.0
                source_fps = None
                for media_frame in client.frames():
                    if self.stop_event.is_set():
                        return
                    if media_frame.kind == 0xfc:
                        source_fps = media_frame.fps
                    for frame in sink.decode(media_frame):
                        self.state.decoded(frame, source_fps)
                        now = time.monotonic()
                        if now - original_at >= 1.0:
                            original = rgb_to_ppm(frame.reformat(format='rgb24'))
                            if self.stop_event.is_set():
                                return
                            self.state.publish_original(original, frame.width, frame.height, now)
                            original_at = now
                        if now - rendered_at < (1 / 15 if self.stream_type == 'Main' else 1 / 10):
                            continue
                        target_width, target_height = self.state.size()
                        ratio = min(target_width / frame.width, target_height / frame.height, 1.0)
                        width = max(1, int(frame.width * ratio))
                        height = max(1, int(frame.height * ratio))
                        rgb = frame.reformat(width=width, height=height, format='rgb24')
                        ppm = rgb_to_ppm(rgb)
                        if self.stop_event.is_set():
                            return
                        self.state.publish(ppm, frame.width, frame.height, now)
                        rendered_at = now
                        backoff = 2
            except SourceError:
                self.state.reset('Grabador no verificado', 'SourceError')
                return  # Never request video from an unverified source.
            except AuthError:
                self.state.reset('Credencial rechazada', 'AuthError')
                return  # Never retry a rejected credential.
            except Exception as error:
                if not self.stop_event.is_set():
                    self.state.reset('Reconectando', type(error).__name__)
                    with self.state.lock:
                        self.state.reconnections += 1
            finally:
                if client is not None:
                    client.close()
                with self.client_lock:
                    self.client = None
            if self.stop_event.wait(backoff):
                break
            backoff = min(10, backoff * 2)


def require_ui_thread(owner):
    if threading.get_ident() != owner:
        raise RuntimeError('Tk must only be updated on its owning thread')


def display_received_time(value):
    try:
        return datetime.fromisoformat(value).astimezone().strftime('%d/%m %H:%M:%S %z')
    except (ValueError, TypeError):
        return 'No disponible'


class Viewer:
    # Optional integration remains absent for phase-0 embedders/headless fixtures.
    home_facade = None
    sequence_manager = None

    def __init__(self, root, auth_hash, *, home_facade=None, home_context=None,
                 home_target=None, evidence_store=None, use_home_core=False):
        import tkinter as tk
        self.tk, self.root = tk, root
        self.ui_thread = threading.get_ident()
        self.auth_hash = auth_hash
        self.closed = False
        self.pending_callbacks = set()
        self.detail = None
        self.zones = load_zones(APP_DIR / 'vox_cctv_zones.json')
        self.display = DetailDisplay()
        self.fullscreen = False
        self.epochs = {channel: 0 for channel in CHANNELS}
        self.states = {channel: CameraState(channel) for channel in CHANNELS}
        self.data_dir = Path(os.environ.get('LOCALAPPDATA', str(APP_DIR))) / 'VoxterraeCCTV'
        self.capture_root = self.data_dir
        if use_home_core:
            try:
                storage = json.loads((APP_DIR / 'capture_storage.json').read_text(encoding='utf-8'))
                candidate = Path(storage['directory'])
                if storage.get('version') == 1 and candidate.is_absolute():
                    self.capture_root = candidate
                    vision = Path(storage.get('vision_directory', ''))
                    if vision.is_absolute() and vision.is_dir():
                        sys.path.insert(0, str(vision))
            except (OSError, KeyError, TypeError, ValueError):
                pass
        self.preferences_path = self.data_dir / 'alarm_preferences.json'
        policy = AlarmPolicy.load(self.preferences_path)
        if not self.preferences_path.exists():
            policy.configure(rain_mode=True)
        self.alarm_state = AlarmState(policy)
        self.home_facade, self.home_context, self.home_target = home_facade, home_context, home_target
        self.evidence = (home_facade.evidence_store if home_facade is not None
                         else evidence_store if evidence_store is not None
                         else EvidenceStore(self.capture_root / 'capturas', max_bytes=128 * 1024 * 1024))
        if home_facade is not None and evidence_store is not None and evidence_store is not self.evidence:
            raise ValueError('shared_evidence_store_required')
        if use_home_core and self.home_facade is None:
            try:
                self.home_facade, self.home_context, self.home_target = bootstrap_local_core(
                    self.data_dir, self.evidence, auth_hash)
            except Exception:
                self.evidence.close()
                raise
        if self.home_facade is not None:
            self.alarm_worker = AlarmWorker(self.alarm_state, auth_hash,
                facade=self.home_facade, context=self.home_context, target=self.home_target)
        else:
            self.alarm_worker = AlarmWorker(self.alarm_state, auth_hash)
        self.last_capture = {}
        self.active_sequence_events = {}
        self.sequence_capture_drops = 0
        self.gallery = None
        self.gallery_photo = None
        self.gallery_rows = []
        self.gallery_filter = None
        self.gallery_original = None
        self.gallery_resize_pending = False
        self.inspectors = []
        self.event_group = 'detections'
        self.visible_events = []
        self.last_ui_error = None
        self.workers = {}
        self.tiles = {}
        self.images = {}
        self.headers = {}
        self.photos = {}
        self.versions = {}
        self.last_metrics = 0.0
        self.status_path = self.capture_root / 'viewer_status.json'
        root.title('Voxterrae · Cámaras en directo')
        root.configure(bg='#101722')
        width = min(1360, max(960, root.winfo_screenwidth() - 32))
        height = min(880, max(660, root.winfo_screenheight() - 80))
        root.geometry(f'{width}x{height}')
        root.minsize(960, 660)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<F11>', self.toggle_fullscreen)
        root.bind('<Escape>', self.escape)
        toolbar = tk.Frame(root, bg='#101722', padx=15, pady=11)
        toolbar.pack(fill='x')
        self.banner = tk.Label(toolbar, text='Conectando las siete cámaras…', bg='#101722', fg='#e4edf6', font=('Segoe UI', 13, 'bold'), width=1, anchor='w')
        tk.Button(toolbar, text='Vista conjunta', command=self.show_mosaic, bg='#26384e', fg='white', relief='flat', padx=15).pack(side='right', padx=8)
        tk.Button(toolbar, text='Capturas', command=self.open_gallery, bg='#26384e', fg='white', relief='flat', padx=12).pack(side='right', padx=4)
        self.rain = tk.BooleanVar(value=policy.rain_mode)
        tk.Checkbutton(toolbar, text='Lluvia', variable=self.rain, command=self.preferences_changed,
            bg='#101722', fg='#dce8f4', selectcolor='#26384e', activebackground='#101722',
            activeforeground='#dce8f4', font=('Segoe UI', 10)).pack(side='right', padx=4)
        self.sound = tk.BooleanVar(value=policy.sound_enabled)
        tk.Checkbutton(toolbar, text='Sonido', variable=self.sound, command=self.sound_changed,
            bg='#101722', fg='#dce8f4', selectcolor='#26384e', activebackground='#101722',
            activeforeground='#dce8f4', font=('Segoe UI', 10)).pack(side='right', padx=5)
        tk.Label(toolbar, text='Doble clic: detalle · F11: completa', bg='#101722', fg='#99aec4', font=('Segoe UI', 9)).pack(side='right', padx=8)
        # Reserve control space before a potentially long alarm description.
        self.banner.pack(side='left', fill='x', expand=True)
        selection = tk.Frame(root, bg='#101722', padx=15)
        selection.pack(fill='x', pady=(0, 5))
        self.camera_choice = tk.StringVar(value='Seleccionar cámara')
        camera_choices = [camera_label(self.zones, channel + 1) for channel in CHANNELS]
        chooser = tk.OptionMenu(selection, self.camera_choice, *camera_choices, command=self.select_camera)
        chooser.configure(bg='#26384e', fg='white', activebackground='#26384e', highlightthickness=0)
        chooser.pack(side='left')
        self.detail_controls = tk.Frame(selection, bg='#101722')
        self.display_mode = tk.StringVar(value='Original')
        adjustment = tk.OptionMenu(self.detail_controls, self.display_mode, *MODES, command=self.display_changed)
        adjustment.configure(bg='#26384e', fg='white', activebackground='#26384e', highlightthickness=0)
        adjustment.pack(side='left', padx=8)
        self.detail_notice = tk.Label(self.detail_controls, text='Original · capturas conservan el original',
            bg='#101722', fg='#ffca73', font=('Segoe UI', 9), anchor='w')
        self.detail_notice.pack(side='left', fill='x', expand=True)
        self.detail_info = tk.Label(root, text='', bg='#101722', fg='#b8c9db', font=('Segoe UI', 9),
            anchor='w', justify='left', padx=15)
        self.grid = tk.Frame(root, bg='#101722')
        self.grid.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        for index in range(3):
            self.grid.grid_rowconfigure(index, weight=1, uniform='rows')
            self.grid.grid_columnconfigure(index, weight=1, uniform='columns')
        for channel in CHANNELS:
            tile = tk.Frame(self.grid, bg='#070c13', highlightthickness=1, highlightbackground='#26384e')
            tile.pack_propagate(False)
            header = tk.Label(tile, text=f'{camera_label(self.zones, channel + 1)} · Conectando', anchor='w', bg='#172333', fg='#dce8f4', font=('Segoe UI', 10, 'bold'), padx=8, pady=5)
            header.pack(fill='x')
            image = tk.Label(tile, text='Esperando señal', bg='#070c13', fg='#8ea5bd', font=('Segoe UI', 13))
            image.pack(fill='both', expand=True)
            image.bind('<Configure>', lambda event, c=channel: self.states[c].set_render_size(event.width - 8, event.height - 8))
            for widget in (tile, header, image):
                widget.bind('<Double-Button-1>', lambda event, c=channel: self.toggle_detail(c))
            self.tiles[channel], self.images[channel], self.headers[channel] = tile, image, header
        self.info = tk.Frame(self.grid, bg='#172333', padx=12, pady=10)
        self.info.pack_propagate(False)
        tk.Label(self.info, text='Detecciones y capturas', bg='#172333', fg='#e4edf6', font=('Segoe UI', 11, 'bold'), anchor='w').pack(fill='x')
        self.alarm_status = tk.Label(self.info, text='Conectando avisos', bg='#172333', fg='#99aec4', font=('Segoe UI', 9), anchor='w', pady=4)
        self.alarm_status.pack(fill='x')
        filters = tk.Frame(self.info, bg='#172333')
        filters.pack(fill='x', pady=3)
        for group, label in (('detections', 'Personas/vehículos'), ('activity', 'Actividad'), ('technical', 'Técnicos')):
            tk.Button(filters, text=label, command=lambda g=group: self.select_group(g),
                bg='#26384e', fg='#e4edf6', relief='flat', padx=4, font=('Segoe UI', 8)).pack(side='left', padx=2)
        self.alarm_events = tk.Listbox(self.info, bg='#172333', fg='#b8c9db',
            font=('Segoe UI', 9), relief='flat', highlightthickness=0, exportselection=False)
        self.alarm_events.pack(fill='both', expand=True)
        self.alarm_events.bind('<Double-Button-1>', self.open_event_capture)
        tk.Label(self.info, text='Doble clic en un aviso: revisar capturas', bg='#172333', fg='#99aec4', font=('Segoe UI', 8), anchor='w').pack(fill='x')
        self.technical = tk.BooleanVar(value=policy.technical_sound)
        tk.Checkbutton(self.info, text='Sonido por pérdida de señal', variable=self.technical,
            command=self.preferences_changed, bg='#172333', fg='#99aec4', selectcolor='#26384e',
            activebackground='#172333', font=('Segoe UI', 8), anchor='w').pack(fill='x')
        self.health = tk.Label(self.grid, text='Comprobando señal…', bg='#172333', fg='#99aec4', font=('Segoe UI', 9), justify='left', padx=12)
        self.health.bind('<Configure>', lambda event: self.health.configure(wraplength=max(120, event.width - 24)))
        self.layout()
        for channel in CHANNELS:
            self.start_worker(channel, 'Extra1')
        self.alarm_worker.start()
        if use_home_core:
            from vox_cctv_sequences import SequenceManager
            from vox_cctv_selection import FrameSelector
            self.sequence_manager = SequenceManager(auth_hash, self.capture_root / 'secuencias',
                self.publish_sequence_capture, frame_selector_factory=FrameSelector,
                max_ring_bytes=64 * 1024 * 1024, max_total_bytes=256 * 1024 * 1024)
            for index, channel in enumerate(CHANNELS):
                self.defer(1500 * index + 500, lambda c=channel: self.start_sequence_channel(c))
        self.defer(80, self.refresh)

    def defer(self, delay, callback):
        if not hasattr(self, 'pending_callbacks'):
            self.pending_callbacks = set()
        token = [None]
        def invoke():
            self.pending_callbacks.discard(token[0])
            if not self.closed:
                callback()
        token[0] = self.root.after(delay, invoke)
        if token[0] is not None:
            self.pending_callbacks.add(token[0])
        return token[0]

    def start_sequence_channel(self, channel):
        if not self.closed and self.sequence_manager is not None:
            self.sequence_manager.start_channel(channel)

    def publish_sequence_capture(self, event, capture):
        if self.closed:
            return
        accepted = False
        for attempt in range(20):
            if self.closed:
                return
            if self.evidence.add(event, capture):
                accepted = True
                break
            time.sleep(.05)
        if not accepted:
            self.sequence_capture_drops += 1
            return
        if capture is None:
            return
        result = capture.get('selector_result') or {}
        received = capture.get('event_received_monotonic')
        if not isinstance(received, (float, int)):
            return
        for candidate in result.get('candidates', [])[:2]:
            picture = dict(candidate)
            stamp = picture.get('timestamp')
            if not isinstance(stamp, (float, int)):
                continue
            picture.update(source_width=picture['width'], source_height=picture['height'],
                stream='Main', sequence_id=capture['sequence_id'],
                sequence_offset_seconds=stamp-received,
                frame_age_seconds=max(0, time.monotonic()-stamp))
            # The small storage queue may be busy committing the scene. Waiting
            # is confined to this finalizer, never the Tk/event receiving thread.
            for attempt in range(20):
                if self.closed or self.evidence.add(event, picture):
                    break
                time.sleep(.05)

    def check_ui(self):
        require_ui_thread(self.ui_thread)

    def sound_changed(self):
        self.check_ui()
        self.preferences_changed()

    def select_camera(self, label):
        self.check_ui()
        for channel in CHANNELS:
            if label == camera_label(self.zones, channel + 1):
                if self.detail != channel:
                    self.toggle_detail(channel)
                return

    def display_changed(self, value=None):
        self.check_ui()
        self.display.select(self.display_mode.get())
        if self.detail is not None:
            self.versions.pop(self.detail, None)

    def reset_display(self):
        self.display.select('Original')
        self.display.reset()
        self.display_mode.set('Original')
        self.detail_notice.configure(text='Original · capturas conservan el original')

    def preferences_changed(self):
        self.check_ui()
        self.alarm_state.configure(sound_enabled=self.sound.get(), rain_mode=self.rain.get(),
                                  technical_sound=self.technical.get())
        try:
            self.alarm_state.save_preferences(self.preferences_path)
        except OSError:
            self.last_ui_error = 'Preferencias no guardadas'

    def select_group(self, group):
        self.check_ui()
        self.event_group = group
        self.visible_events = []
        self.alarm_events.delete(0, 'end')

    def open_event_capture(self, event=None):
        selected = self.alarm_events.curselection()
        if selected and selected[0] < len(self.visible_events):
            item = self.visible_events[selected[0]]
            self.open_gallery((item['channel'], item['event']))

    def receive_captures(self, now):
        for received in self.alarm_state.drain_pending():
            event = received['event']
            if event['event'] not in ('HumanDetect', 'appEventHumanDetectAlarm', 'CarShapeDetect', 'FaceDetect', 'FaceDetection'):
                continue
            channel = event['channel']
            if channel is None:
                continue
            if self.sequence_manager is not None:
                self.sequence_manager.trigger(event, received['received_monotonic'])
                sequence_key = (channel, event['event'])
                if event['status'] == 'Start':
                    self.active_sequence_events[sequence_key] = {
                        'event': dict(event), 'started': received['received_monotonic'], 'next': now + 5}
                elif event['status'] == 'Stop':
                    self.active_sequence_events.pop(sequence_key, None)
            if event['status'] != 'Start':
                continue
            key = (channel, event['event'])
            interval = 120 if self.rain.get() else 30
            if now - self.last_capture.get(key, float('-inf')) < interval:
                continue
            # A delayed UI update must not attach a newer live image to an old report.
            capture = self.states[channel - 1].capture_snapshot(now=now) if now - received['received_monotonic'] <= 2 else None
            if self.evidence.add(event, capture):
                self.last_capture[key] = now
        if self.sequence_manager is not None:
            for key, activity in list(self.active_sequence_events.items()):
                if now - activity['started'] >= 60 or self.alarm_state.snapshot(now)['state'] != 'Escuchando avisos':
                    self.active_sequence_events.pop(key, None)
                elif now >= activity['next']:
                    self.sequence_manager.trigger(activity['event'], now)
                    activity['next'] = now + 5

    def open_gallery(self, filter_by=None):
        self.check_ui()
        self.gallery_filter = filter_by
        if self.gallery is not None and self.gallery.winfo_exists():
            self.gallery.lift()
            self.update_gallery()
            return
        tk = self.tk
        self.gallery = tk.Toplevel(self.root)
        self.gallery.title('Voxterrae · Capturas de avisos')
        self.gallery.geometry('1000x650')
        self.gallery.minsize(700, 450)
        self.gallery.configure(bg='#101722')
        tk.Label(self.gallery, text='Imágenes originales · Doble clic en la imagen para ampliar',
            bg='#101722', fg='#e4edf6', font=('Segoe UI', 12, 'bold'), pady=10).pack(fill='x')
        body = tk.Frame(self.gallery, bg='#101722')
        body.pack(fill='both', expand=True, padx=12, pady=8)
        sidebar = tk.Frame(body, bg='#172333', width=285)
        sidebar.pack(side='left', fill='y', padx=(0, 10))
        self.gallery_list = tk.Listbox(sidebar, width=34, bg='#172333', fg='#e4edf6',
            selectbackground='#286254', relief='flat', exportselection=False, font=('Segoe UI', 10))
        self.gallery_list.pack(fill='both', expand=True)
        self.gallery_list.bind('<<ListboxSelect>>', self.show_capture)
        self.gallery_image = tk.Label(body, text='Selecciona una captura', bg='#070c13', fg='#99aec4')
        self.gallery_image.pack(fill='both', expand=True)
        self.gallery_image.bind('<Double-Button-1>', self.open_capture_detail)
        self.gallery_image.bind('<Configure>', self.gallery_resized)
        self.gallery_details = tk.Label(self.gallery, text='', bg='#101722', fg='#b8c9db',
            font=('Segoe UI', 10), justify='left', anchor='w', padx=12, pady=8, wraplength=970)
        self.gallery_details.pack(fill='x')
        tk.Button(self.gallery, text='Ver todas las capturas', command=lambda: self.open_gallery(),
            bg='#26384e', fg='white', relief='flat', padx=12).pack(side='left', padx=12, pady=8)
        tk.Button(self.gallery, text='Ampliar original', command=self.open_capture_detail,
            bg='#26384e', fg='white', relief='flat', padx=12).pack(side='left', pady=8)
        tk.Button(self.gallery, text='Ver secuencia', command=self.open_capture_sequence,
            bg='#26384e', fg='white', relief='flat', padx=12).pack(side='left', padx=8, pady=8)
        tk.Label(self.gallery, text='25 imágenes · 128 MiB · 48 h', bg='#101722',
            fg='#99aec4', font=('Segoe UI', 9)).pack(side='right', padx=12)
        self.gallery.protocol('WM_DELETE_WINDOW', self.close_gallery)
        self.update_gallery()

    def close_gallery(self):
        self.check_ui()
        if self.gallery is not None:
            self.gallery.destroy()
        self.gallery = None
        self.gallery_photo = None
        self.gallery_original = None
        self.gallery_rows = []

    def update_gallery(self):
        if self.gallery is None or not self.gallery.winfo_exists():
            return
        try:
            rows = (self.home_facade.evidence_entries(self.home_context, time.time())
                    if self.home_facade is not None else self.evidence.list_entries())
        except AccessDenied:
            self.gallery_rows = []
            self.gallery_photo = None
            self.gallery_original = None
            self.gallery_list.delete(0, 'end')
            self.gallery_image.configure(image='', text='permission_denied')
            self.gallery_details.configure(text='permission_denied')
            return
        if self.gallery_filter is not None:
            camera, kind = self.gallery_filter
            rows = [r for r in rows if r.get('camera', r.get('channel')) == camera and r.get('event') == kind]
        if rows == self.gallery_rows:
            return
        selected = self.gallery_list.curselection()
        selected_id = self.gallery_rows[selected[0]]['id'] if selected and selected[0] < len(self.gallery_rows) else None
        self.gallery_rows = rows
        self.gallery_list.delete(0, 'end')
        for row in rows:
            stamp = display_received_time(row.get('received_at'))[:14]
            camera = row.get('camera', row.get('channel'))
            label = ALARM_LABELS.get(row.get('event'), 'Aviso')
            self.gallery_list.insert('end', f'{stamp} · {camera_label(self.zones, camera)} · {label}')
        if rows:
            index = next((i for i, row in enumerate(rows) if row['id'] == selected_id), 0)
            self.gallery_list.selection_set(index)
            self.show_capture()
        else:
            self.gallery_photo = None
            self.gallery_original = None
            self.gallery_image.configure(image='', text='No hay capturas para esta selección.\nLas capturas comienzan al activar esta versión.')
            self.gallery_details.configure(text='Los avisos anteriores no tenían una foto guardada en este visor.')

    def show_capture(self, event=None):
        self.check_ui()
        selected = self.gallery_list.curselection()
        if not selected or selected[0] >= len(self.gallery_rows):
            return
        row = self.gallery_rows[selected[0]]
        try:
            ppm = (self.home_facade.read_evidence(self.home_context, row['id'], time.time())
                   if self.home_facade is not None else self.evidence.read_image(row['id']))
        except AccessDenied:
            self.gallery_photo = None
            self.gallery_original = None
            self.gallery_image.configure(image='', text='permission_denied')
            self.gallery_details.configure(text='permission_denied')
            return
        self.gallery_photo = None
        self.gallery_original = None
        if ppm:
            try:
                self.gallery_original = ppm
                self.render_gallery_photo()
            except (self.tk.TclError, ValueError):
                self.gallery_image.configure(image='', text='No se pudo mostrar esta imagen')
        else:
            self.gallery_image.configure(image='', text=row.get('state', 'Sin imagen disponible'))
        received = display_received_time(row.get('received_at'))
        device_time = row.get('device_time') or 'No disponible'
        dimensions = f"{row['width']} × {row['height']}" if row.get('width') and row.get('height') else 'No disponible'
        age = row.get('frame_age_seconds')
        age_text = f'{age:.2f} s' if isinstance(age, (float, int)) else 'No disponible'
        origin = camera_label(self.zones, row.get('camera', row.get('channel')))
        selection = row.get('selection')
        offset = row.get('sequence_offset_seconds')
        moment = f" · {offset:+.2f} s respecto al aviso" if isinstance(offset, (float, int)) else ''
        explanation = ('Selección desde secuencia · ' + str(selection) + moment + ' · detección sin confirmar.'
                       if row.get('sequence_id') else 'Fotograma recibido del flujo original; las imágenes antiguas conservan su resolución anterior.')
        self.gallery_details.configure(text=f"{origin} · {row.get('state', '')} · Imagen: {dimensions}\nGuardada: {received} · Hora de cámara: {device_time} · Edad al seleccionar: {age_text}\n{explanation}")

    def gallery_resized(self, event=None):
        if not self.gallery_resize_pending and self.gallery is not None:
            self.gallery_resize_pending = True
            self.defer(150, self.render_gallery_photo)

    def render_gallery_photo(self):
        self.gallery_resize_pending = False
        if self.gallery is None or not self.gallery.winfo_exists() or not self.gallery_original:
            return
        row, authorised = self.authorised_selected_photo()
        if row is None or authorised is None:
            self.gallery_original = self.gallery_photo = None
            self.gallery_image.configure(image='', text='Captura no disponible')
            return
        self.gallery_original = authorised
        w, h = photo_dimensions(self.gallery_original)
        available = (max(32, self.gallery_image.winfo_width()-8), max(32, self.gallery_image.winfo_height()-8))
        target = fit_size(w, h, *available)
        rendered = resize_ppm(self.gallery_original, *target)
        self.gallery_photo = self.tk.PhotoImage(data=rendered, format='PPM', master=self.gallery)
        self.gallery_image.configure(image=self.gallery_photo, text='')

    def authorised_selected_photo(self):
        if self.gallery is None:
            return None, None
        selected = self.gallery_list.curselection()
        if not selected or selected[0] >= len(self.gallery_rows):
            return None, None
        row = self.gallery_rows[selected[0]]
        try:
            ppm = (self.home_facade.read_evidence(self.home_context, row['id'], time.time())
                   if self.home_facade is not None else self.evidence.read_image(row['id']))
        except AccessDenied:
            self.gallery_original = self.gallery_photo = None
            self.gallery_image.configure(image='', text='permission_denied')
            return None, None
        return row, ppm

    def open_capture_detail(self, event=None):
        self.check_ui()
        row, ppm = self.authorised_selected_photo()
        if ppm:
            self.close_inspectors()
            self.inspectors.append(PhotoInspector(self.root, ppm, row))

    def open_capture_sequence(self):
        self.check_ui()
        row, ppm = self.authorised_selected_photo()
        if row is None or ppm is None or self.sequence_manager is None:
            return
        identifier = row.get('sequence_id')
        clip = next((item for item in self.sequence_manager.list_clips() if item.get('id') == identifier), None)
        if not clip:
            self.gallery_details.configure(text='Secuencia no disponible para esta imagen; puede haber caducado.')
            return
        from vox_cctv_video import SequenceInspector
        self.close_inspectors()
        try:
            self.inspectors.append(SequenceInspector(self.root, self.sequence_manager, identifier))
        except (ValueError, OSError):
            self.gallery_details.configure(text='La secuencia ya no está disponible.')

    def close_inspectors(self):
        for item in self.inspectors:
            if item.window.winfo_exists():
                item.close()
        self.inspectors = []

    def start_worker(self, channel, mode):
        worker = CameraWorker(channel, self.states[channel], self.auth_hash, mode)
        self.workers[channel] = worker
        worker.start()

    def switch_stream(self, channel, mode):
        self.check_ui()
        old = self.workers[channel]
        if old.stream_type == mode and old.is_alive() and not old.stop_event.is_set():
            return
        self.epochs[channel] += 1
        epoch = self.epochs[channel]
        old.stop()
        if self.detail == channel:
            self.display.reset()
        self.states[channel].reset('Cambiando vista')
        def after_close():
            self.check_ui()
            if self.closed or self.epochs[channel] != epoch:
                return
            if old.is_alive():
                self.defer(80, after_close)
            elif self.workers.get(channel) is old:
                self.start_worker(channel, mode)
        self.defer(80, after_close)

    def toggle_detail(self, channel):
        self.check_ui()
        if self.detail == channel:
            self.show_mosaic()
            return
        self.reset_display()
        if self.detail is not None:
            self.switch_stream(self.detail, 'Extra1')
        self.detail = channel
        self.switch_stream(channel, 'Main')
        self.layout()

    def show_mosaic(self):
        self.check_ui()
        self.reset_display()
        if self.detail is not None:
            self.switch_stream(self.detail, 'Extra1')
            self.detail = None
        self.layout()

    def layout(self):
        self.check_ui()
        for tile in self.tiles.values():
            tile.grid_remove()
        self.info.grid_remove()
        self.health.grid_remove()
        if self.detail is not None:
            self.camera_choice.set(camera_label(self.zones, self.detail + 1))
            self.detail_controls.pack(side='left', fill='x', expand=True)
            self.detail_info.configure(text=capability_info(self.detail + 1))
            self.detail_info.pack(before=self.grid, fill='x', pady=(0, 5))
            self.tiles[self.detail].grid(row=0, column=0, rowspan=3, columnspan=3, sticky='nsew', padx=4, pady=4)
        else:
            self.camera_choice.set('Seleccionar cámara')
            self.detail_controls.pack_forget()
            self.detail_info.pack_forget()
            for channel in CHANNELS:
                self.tiles[channel].grid(row=channel // 3, column=channel % 3, rowspan=1, columnspan=1, sticky='nsew', padx=4, pady=4)
            self.info.grid(row=2, column=1, sticky='nsew', padx=4, pady=4)
            self.health.grid(row=2, column=2, sticky='nsew', padx=4, pady=4)

    def toggle_fullscreen(self, event=None):
        self.check_ui()
        self.fullscreen = not self.fullscreen
        self.root.attributes('-fullscreen', self.fullscreen)

    def escape(self, event=None):
        if self.detail is not None:
            self.show_mosaic()
        elif self.fullscreen:
            self.toggle_fullscreen()

    def write_metrics(self, snapshots):
        document = {'checked_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
            'recorder': RECORDER_IP, 'mode': 'detail' if self.detail is not None else 'mosaic',
            'detail_channel': self.detail + 1 if self.detail is not None else None,
            'channels': snapshots, 'alarms': self.alarm_state.snapshot(),
            'preferences': self.alarm_state.preferences(),
            'capture_count': len(self.evidence.list_entries()),
            'last_ui_error': self.last_ui_error,
            'sequences': self.sequence_manager.snapshot() if self.sequence_manager is not None else {'enabled': False},
            'sequence_image_drops': getattr(self, 'sequence_capture_drops', 0),
            'home': (self.home_facade.status() if self.home_facade is not None else
                     {'core_active': False, 'metadata': 'phase0', 'alarm_subscriptions': 0,
                      'worker_status': 'legacy'})}
        temporary = self.status_path.with_suffix('.tmp')
        try:
            self.status_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(document, ensure_ascii=False, indent=2)
            temporary.write_text(payload, encoding='utf-8')
            try:
                os.replace(temporary, self.status_path)
            except PermissionError:
                # Windows may deny replacing existing telemetry while allowing
                # writes. This fallback is non-atomic: readers must retry a
                # partial JSON read. Evidence files always keep atomic writes.
                with self.status_path.open('r+', encoding='utf-8') as status:
                    status.write(payload)
                    status.truncate()
        except OSError:
            pass  # Status telemetry never interrupts the live picture.
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def refresh(self):
        self.check_ui()
        if self.closed:
            return
        try:
            self.refresh_view()
        except Exception as error:
            # One malformed picture or failed gallery update must not stop
            # all seven pictures. Retain only the error class, never payloads.
            self.last_ui_error = type(error).__name__
        finally:
            if not self.closed:
                self.defer(80, self.refresh)

    def refresh_view(self):
        self.check_ui()
        if self.closed:
            return
        now = time.monotonic()
        snapshots = []
        live = 0
        for channel in CHANNELS:
            state = self.states[channel]
            info = state.snapshot(now)
            snapshots.append(info)
            age = info['last_frame_age_seconds']
            fresh = info['status'] == 'En vivo'
            live += bool(fresh)
            color = '#6de7ad' if fresh and age is not None and age <= 2 else '#ffca73' if fresh else '#ff8989'
            age_text = f' · {age:.1f}s' if age is not None else ''
            detail_text = ' · Detalle' if self.detail == channel else ''
            self.headers[channel].configure(text=f"{camera_label(self.zones, channel + 1)}{detail_text} · {info['status']}{age_text}", fg=color)
            ppm, version = state.image()
            if not fresh:
                if self.detail == channel:
                    self.display.reset()
                    self.detail_notice.configure(text='Original · esperando imagen reciente')
                self.images[channel].configure(image='', text=info['status'])
                self.photos.pop(channel, None)
                self.versions.pop(channel, None)
            elif ppm is not None:
                token = (version, self.display.mode if self.detail == channel else 'Original')
                if self.versions.get(channel) == token:
                    continue
                rendered, effective = self.display.render(channel, ppm, version) if self.detail == channel else (ppm, 'Original')
                try:
                    photo = self.tk.PhotoImage(data=rendered, format='PPM', master=self.root)
                except self.tk.TclError:
                    if effective == 'Original':
                        raise
                    self.display.reset()
                    effective = 'Original'
                    photo = self.tk.PhotoImage(data=ppm, format='PPM', master=self.root)
                self.images[channel].configure(image=photo, text='')
                self.photos[channel] = photo
                self.versions[channel] = token
                if self.detail == channel:
                    notice = f'Vista realzada · {effective} · capturas conservan el original' if effective != 'Original' else 'Original · capturas conservan el original'
                    self.detail_notice.configure(text=notice)
        self.receive_captures(now)
        self.update_gallery()
        alarm = self.alarm_state.snapshot(now)
        alarm_live = alarm['state'] == 'Escuchando avisos'
        home_status = self.home_facade.status() if self.home_facade is not None else {}
        issue_labels = {
            'authentication_failed': 'Credencial rechazada',
            'identity_mismatch': 'Grabador no verificado',
            'event_overflow': 'Pérdida de avisos',
            'event_source_ended': 'Fuente de avisos terminada',
            'event_source_failed': 'Fallo de la fuente de avisos',
            'unavailable': 'Fuente de avisos no disponible',
            'timeout': 'Avisos sin respuesta', 'protocol_error': 'Fallo del proceso de avisos',
            'worker_closed': 'Proceso de avisos detenido',
            'message_too_large': 'Mensaje de avisos rechazado',
            'access_denied': 'Permiso de avisos denegado',
            'permission_denied': 'Permiso de avisos denegado',
            'unsupported': 'Avisos no disponibles', 'worker_failed': 'Fallo de avisos',
        }
        notices = []
        if home_status.get('event_loss'):
            notices.append('Pérdida de avisos (event_overflow)')
        issue = home_status.get('alarm_issue')
        if issue in issue_labels and not (issue == 'event_overflow' and notices):
            notices.append(f'{issue_labels[issue]} ({issue})')
        alarm_text = alarm['state'] + (' · Home: ' + ' · '.join(notices) if notices else '')
        self.alarm_status.configure(text=alarm_text, fg='#6de7ad' if alarm_live and not notices else '#ffca73')
        lines = []
        grouped = self.alarm_state.grouped(self.event_group)
        for event in grouped:
            stamp = event['time'][11:] if event['time'] else 'Hora no disponible'
            origin = camera_label(self.zones, event['channel'])
            transition = {'Start': 'inicio', 'Stop': 'fin', 'None': 'aviso'}[event['status']]
            repetitions = f" · ×{event['count']}" if event['count'] > 1 else ''
            lines.append(f"{stamp} · {origin} · {ALARM_LABELS[event['event']]}{repetitions}")
        if grouped != self.visible_events:
            self.visible_events = grouped
            self.alarm_events.delete(0, 'end')
            for line in lines:
                self.alarm_events.insert('end', line)
        if not grouped and self.alarm_events.size() == 0:
            self.alarm_events.insert('end', 'Todavía no hay avisos en este grupo.')
        banner = f'{live} de 7 cámaras con señal reciente'
        detections = self.alarm_state.grouped('detections')
        if self.detail is not None and detections:
            latest = detections[0]
            origin = camera_label(self.zones, latest['channel'])
            transition = 'inicio' if latest['status'] == 'Start' else 'fin' if latest['status'] == 'Stop' else 'aviso'
            banner += f" · {origin}: {ALARM_LABELS[latest['event']]} ({transition})"
        self.banner.configure(text=banner)
        if self.alarm_state.consume_sound(now):
            self.root.bell()  # Tk is only called from this owning UI thread.
        weather = 'Lluvia: agrupa repeticiones 2 min' if self.rain.get() else 'Avisos: intervalo normal'
        count = len(self.evidence.list_entries())
        sequence_note = ''
        if self.sequence_manager is not None:
            sequence_note = '\nSecuencias: 10 s previos / 15 s posteriores'
        metadata_status = ('\nHome: metadata_unavailable' if home_status.get('metadata') == 'metadata_unavailable' else '')
        self.health.configure(text=f'{live}/7 con señal · {count} capturas\n{weather}{metadata_status}{sequence_note}\nAvisos del detector, sin confirmar.\n{capability_info()}')
        if now - self.last_metrics >= 2:
            self.write_metrics(snapshots)
            self.last_metrics = now

    def close(self):
        self.check_ui()
        self.closed = True
        for callback in self.pending_callbacks:
            try:
                self.root.after_cancel(callback)
            except self.tk.TclError:
                pass
        self.pending_callbacks.clear()
        for worker in self.workers.values():
            worker.stop()
        self.alarm_worker.stop()
        if self.sequence_manager is not None:
            self.sequence_manager.stop()
        self.close_inspectors()
        if self.home_facade is not None:
            self.home_facade.close()
        else:
            self.evidence.close()
        self.close_gallery()
        self.auth_hash = None
        self.display.reset()
        self.photos.clear()
        self.root.destroy()


def instance_mutex():
    if sys.platform != 'win32':
        return None
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateMutexW.restype = wintypes.HANDLE
    handle = api.CreateMutexW(None, False, 'Local\\VoxterraeCCTVLiveViewer')
    if not handle:
        raise OSError('Viewer instance guard is unavailable')
    if ctypes.get_last_error() == 183:
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        api.CloseHandle(handle)
        raise RuntimeError('El visor ya está abierto en Voxterrae.')
    return handle


def main(*, phase0=False):
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    handle = None
    try:
        handle = instance_mutex()
        import av
        av.logging.set_level(av.logging.PANIC)
        # Validate both native codecs before opening any recorder connection.
        av.CodecContext.create('hevc', 'r')
        av.CodecContext.create('h264', 'r')
        private_hash = owner_hash()
        Viewer(root, private_hash, use_home_core=not phase0)
        private_hash = None
        root.deiconify()
        root.mainloop()
    except RuntimeError as error:
        messagebox.showinfo('Cámaras', str(error), parent=root)
        root.destroy()
    except Exception:
        # No traceback, response bodies, sessions, credentials or hashes are logged.
        messagebox.showerror('Cámaras', 'No se pudo abrir el visor local. Comprueba la instalación y la credencial del grabador en Voxterrae.', parent=root)
        root.destroy()
    finally:
        if handle:
            api = ctypes.WinDLL('kernel32', use_last_error=True)
            api.CloseHandle.argtypes = [wintypes.HANDLE]
            api.CloseHandle(handle)


if __name__ == '__main__':
    main(phase0='--phase0' in sys.argv[1:])
