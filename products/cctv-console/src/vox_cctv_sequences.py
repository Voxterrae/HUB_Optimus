"""Bounded, original Main-stream event sequences; importing opens no connection.

The encoded ring is never decoded while idle. Its memory budget includes active
episodes and finalization jobs, not just the live ring. All image selection and
disk work run on the finalizer, and all event timestamps describe local receipt,
because the recorder's MediaFrame does not supply a video capture timestamp.
Raw Annex B export preserves encoded bytes without reencoding. It requires a
player that supports the indicated elementary codec; the JSON supplies timing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import copy
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import stat
import threading
import time
import uuid

from vox_cctv_native import AuthError, CHANNELS, MediaFrame, NativeClient, SourceError


DETECTION_EVENTS = frozenset(('HumanDetect', 'appEventHumanDetectAlarm',
    'CarShapeDetect', 'FaceDetection', 'FaceDetect', 'VideoMotion', 'MotionDetect',
    'IPCAlarm', 'VideoAnalyze', 'VIdeoAnanyze'))
MAX_METADATA_BYTES = 1024 * 1024
MAX_RECORDS_PER_CAMERA = 6000
MAX_PPM_BYTES = 12 * 1024 * 1024
SAFE_ID = re.compile(r'[0-9a-f]{32}\Z')
OWNED_FILENAME = re.compile(r'[0-9a-f]{32}\.(?:json|h264|hevc)(?:\.[0-9a-f]{32}\.tmp)?\Z')
METADATA_FIELDS = frozenset(('version', 'id', 'camera', 'event', 'device_time',
    'received_at', 'received_epoch', 'stream', 'codec', 'format', 'player_support',
    'timing_source', 'embedded_timestamps', 'continuity_verified',
    'gap_detection_threshold_seconds', 'requested_pre_seconds', 'requested_post_seconds',
    'requested_end_offset_seconds', 'latest_activity_offset_seconds',
    'pre_coverage_seconds', 'post_coverage_seconds', 'trigger_count', 'gaps',
    'clipped_reasons', 'status', 'original_sha256', 'encoded_bytes', 'video_file',
    'metadata_file', 'source_width', 'source_height', 'frames', 'decode_error_kind',
    'image_selection', 'selector_status', 'image_status'))


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _linked(path):
    return path.is_symlink() or bool(getattr(path, 'is_junction', lambda: False)())


def _sanitised_event(event):
    if not isinstance(event, dict) or event.get('event') not in DETECTION_EVENTS:
        return None
    camera = event.get('channel', event.get('camera'))
    if type(camera) is not int or camera not in range(1, 8):
        return None
    if event.get('status') not in ('Start', 'Stop', 'None'):
        return None
    result = {'event': event['event'], 'channel': camera, 'status': event['status']}
    device_time = event.get('time')
    if isinstance(device_time, str) and len(device_time) == 19:
        try:
            datetime.strptime(device_time, '%Y-%m-%d %H:%M:%S')
            result['time'] = device_time
        except ValueError:
            pass
    return result


@dataclass(frozen=True)
class _Record:
    payload: bytes
    codec: str
    key: bool
    received: float
    width: int
    height: int
    fps: int | None
    session: int


@dataclass(eq=False)
class _Gop:
    records: list = field(default_factory=list)


@dataclass
class _Episode:
    identifier: str
    channel: int
    event: dict
    event_received: float
    received_epoch: float
    deadline: float
    cap: float
    latest_activity: float
    gops: list
    trigger_count: int = 1
    gaps: list = field(default_factory=list)
    clipped_reasons: set = field(default_factory=set)


@dataclass(frozen=True)
class _Job:
    identifier: str
    channel: int
    event: dict
    event_received: float
    received_epoch: float
    deadline: float
    latest_activity: float
    trigger_count: int
    records: tuple
    gaps: tuple
    clipped_reasons: frozenset


@dataclass
class _Camera:
    ring: list = field(default_factory=list)
    active: _Episode | None = None
    codec: str | None = None
    width: int = 0
    height: int = 0
    fps: int | None = None
    session: int = 0
    last_received: float | None = None
    awaiting_keyframe: bool = True
    status: str = 'not_started'
    last_error_kind: str | None = None
    reconnects: int = 0
    gaps: list = field(default_factory=list)
    frames_received: int = 0


def _decode_records(records, stop_event):
    """Lazy single-thread PyAV decoder with receipt timestamps attached to packets.

    The native payload is an access unit, but the parser may delay its output.
    Encoded byte spans associate parsed packets with input receipt times; decoded
    presentation timestamps follow through the codec's reordering. This is a receipt-time
    association, never a claim about the device's capture clock.
    """
    import av
    context = None
    pending = []
    timestamp_by_pts = {}
    codec = None

    def packet_stamp(packet, fallback):
        timestamp = pending[0][1] if pending else fallback
        length = getattr(packet, 'size', None)
        if type(length) is int and length > 0:
            while pending and length:
                take = min(length, pending[0][0])
                pending[0][0] -= take
                length -= take
                if not pending[0][0]:
                    pending.pop(0)
        elif pending:
            pending.pop(0)
        return timestamp

    def decoded_stamp(frame, fallback):
        # Some PyAV codec outputs expose pts but omit time_base.
        if frame.pts in timestamp_by_pts:
            return timestamp_by_pts[frame.pts]
        if frame.pts is not None and frame.time_base:
            return float(frame.pts * frame.time_base)
        return fallback

    for record in records:
        if stop_event.is_set():
            return
        if record.codec != codec:
            codec = record.codec
            context = av.CodecContext.create(codec, 'r')
            context.thread_count = 1
            context.thread_type = 'SLICE'
            pending = []
            timestamp_by_pts = {}
        pending.append([len(record.payload), record.received])
        for packet in context.parse(record.payload):
            stamp = packet_stamp(packet, record.received)
            packet.pts = round(stamp * 1_000_000)
            timestamp_by_pts[packet.pts] = stamp
            packet.dts = None  # Reception order is not presentation order for B pictures.
            packet.time_base = Fraction(1, 1_000_000)
            for frame in context.decode(packet):
                if stop_event.is_set():
                    return
                yield frame, decoded_stamp(frame, stamp)
    if context is None or stop_event.is_set():
        return
    for packet in context.parse(b''):
        stamp = packet_stamp(packet, records[-1].received)
        packet.pts = round(stamp * 1_000_000)
        timestamp_by_pts[packet.pts] = stamp
        packet.dts = None
        packet.time_base = Fraction(1, 1_000_000)
        for frame in context.decode(packet):
            yield frame, decoded_stamp(frame, stamp)
    for frame in context.decode(None):
        if stop_event.is_set():
            return
        yield frame, decoded_stamp(frame, records[-1].received)


def _frame_quality(frame):
    """A small gray sample scores general scene sharpness and usable exposure."""
    sample = frame.reformat(width=64, height=48, format='gray')
    plane = sample.planes[0]
    raw, stride = bytes(plane), plane.line_size
    if stride < 64 or len(raw) < stride * 48:
        raise ValueError('Invalid gray sample')
    sharpness = total = clipped = count = 0
    for y in range(1, 47):
        for x in range(1, 63):
            offset = y * stride + x
            pixel = raw[offset]
            laplace = 4 * pixel - raw[offset - 1] - raw[offset + 1] - raw[offset - stride] - raw[offset + stride]
            sharpness += laplace * laplace
            total += pixel
            clipped += pixel < 8 or pixel > 247
            count += 1
    exposure = max(0.1, 1.0 - abs(total / count - 127.5) / 127.5)
    usable = max(0.05, 1.0 - clipped / count)
    return sharpness / count * exposure * usable


def _original_ppm(frame):
    width, height = frame.width, frame.height
    if type(width) is not int or type(height) is not int or not 0 < width <= 8192 or not 0 < height <= 8192:
        raise ValueError('Invalid original dimensions')
    header = f'P6\n{width} {height}\n255\n'.encode('ascii')
    if len(header) + width * height * 3 > MAX_PPM_BYTES:
        raise ValueError('Original image exceeds preview bound')
    rgb = frame.reformat(format='rgb24')
    plane = rgb.planes[0]
    raw, stride = bytes(plane), plane.line_size
    row_bytes = width * 3
    if stride < row_bytes or len(raw) < stride * height:
        raise ValueError('Invalid original RGB plane')
    if stride == row_bytes:
        return header + raw[:row_bytes * height]
    return header + b''.join(raw[y * stride:y * stride + row_bytes] for y in range(height))


class _MainWorker(threading.Thread):
    def __init__(self, manager, channel, auth_hash):
        super().__init__(name=f'CCTV-Main-sequence-{channel + 1}', daemon=True)
        self.manager, self.channel, self.auth_hash = manager, channel, auth_hash
        self.client = None
        self.client_lock = threading.Lock()

    def cancel(self):
        with self.client_lock:
            if self.client is not None:
                self.client.close()

    def run(self):
        failures, backoff = 0, 1.0
        manager = self.manager
        try:
            while not manager._stop.is_set():
                client = None
                try:
                    manager._status(self.channel, 'connecting')
                    client = manager.client_factory(self.auth_hash, self.channel, 'Main', manager._stop)
                    with self.client_lock:
                        self.client = client
                    if manager._stop.is_set():
                        return
                    manager._status(self.channel, 'buffering')
                    for frame in client.frames():
                        if manager._stop.is_set():
                            return
                        if manager._ingest(self.channel, frame, manager._clock()):
                            failures, backoff = 0, 1.0
                    if not manager._stop.is_set():
                        raise EOFError('Stream ended')
                except (AuthError, SourceError) as error:
                    manager._status(self.channel, 'terminal_failure', type(error).__name__)
                    manager._reset_channel(self.channel, type(error).__name__, manager._clock())
                    return
                except Exception as error:
                    if manager._stop.is_set():
                        return
                    failures += 1
                    manager._reset_channel(self.channel, 'connection_lost', manager._clock())
                    manager._status(self.channel, 'retrying' if failures <= manager.max_retries else 'retry_limit', type(error).__name__)
                    with manager._lock:
                        manager._cameras[self.channel].reconnects += 1
                    if failures > manager.max_retries:
                        return
                finally:
                    if client is not None:
                        client.close()
                    with self.client_lock:
                        self.client = None
                if manager._stop.wait(backoff):
                    return
                backoff = min(10.0, backoff * 2)
        finally:
            self.auth_hash = None


class SequenceManager:
    def __init__(self, auth_hash, directory, on_capture, client_factory=NativeClient,
            pre_seconds=10, post_seconds=15, *, max_duration_seconds=60,
            max_ring_bytes=32 * 1024 * 1024, max_total_bytes=192 * 1024 * 1024,
            max_storage_bytes=256 * 1024 * 1024, max_episodes=25,
            max_age_hours=48, min_free_bytes=128 * 1024 * 1024, max_retries=5,
            frame_selector_factory=None, clock=time.monotonic, wall_clock=time.time):
        if not callable(on_capture) or not callable(client_factory):
            raise ValueError('Sequence callbacks must be callable')
        for value in (pre_seconds, post_seconds, max_duration_seconds, max_age_hours):
            if not _finite(value) or value <= 0:
                raise ValueError('Sequence durations must be positive and finite')
        self.directory = Path(os.path.abspath(os.fspath(directory)))
        self.on_capture, self.client_factory = on_capture, client_factory
        self.pre_seconds = min(10.0, float(pre_seconds))
        self.post_seconds = min(15.0, float(post_seconds))
        self.max_duration_seconds = max(self.post_seconds, min(60.0, float(max_duration_seconds)))
        self.max_ring_bytes = max(1, min(64 * 1024 * 1024, int(max_ring_bytes)))
        self.max_total_bytes = max(1, min(256 * 1024 * 1024, int(max_total_bytes)))
        self.max_storage_bytes = max(1, min(256 * 1024 * 1024, int(max_storage_bytes)))
        self.max_episodes = max(1, min(25, int(max_episodes)))
        self.max_age_seconds = min(48 * 3600.0, float(max_age_hours) * 3600)
        self.min_free_bytes = max(0, int(min_free_bytes))
        self.max_retries = max(0, min(10, int(max_retries)))
        self.frame_selector_factory = frame_selector_factory
        self._clock, self._wall_clock = clock, wall_clock
        self._auth_hash = auth_hash
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._closed = False
        self._workers = {}
        self._cameras = {channel: _Camera() for channel in CHANNELS}
        self._jobs = queue.Queue(maxsize=7)
        self._inflight = {}
        self._clips = []
        self._orphans = {}
        self._loaded = False
        self._finalizer = None
        self._last_error_kind = None
        self._dropped_jobs = 0

    def _ensure_finalizer(self):
        with self._lock:
            if self._closed or self._finalizer is not None:
                return
            self._finalizer = threading.Thread(target=self._run_finalizer, name='CCTV-Sequence-finalizer', daemon=True)
            self._finalizer.start()

    def start_channel(self, channel):
        """Start one zero-based Main receiver, allowing caller-paced startup."""
        if type(channel) is not int or channel not in CHANNELS:
            raise ValueError('Invalid sequence camera')
        self._ensure_finalizer()
        with self._lock:
            if self._closed or channel in self._workers:
                return False
            worker = _MainWorker(self, channel, self._auth_hash)
            self._workers[channel] = worker
            worker.start()
            return True

    def start(self):
        """Convenience startup; GUI callers can pace start_channel instead."""
        for channel in CHANNELS:
            self.start_channel(channel)

    def trigger(self, event, received_monotonic):
        """Only bounded memory/queue operations; no socket, disk, decoder or Tk."""
        event = _sanitised_event(event)
        if event is None or not _finite(received_monotonic):
            return False
        stamp = float(received_monotonic)
        channel = event['channel'] - 1
        with self._lock:
            if self._closed:
                return False
            camera = self._cameras[channel]
            if camera.active is not None and stamp >= camera.active.deadline:
                self._queue_episode_locked(camera)
            if camera.active is None:
                if event['status'] == 'Stop':
                    return False
                cutoff = stamp - self.pre_seconds
                gops = []
                if camera.ring and camera.ring[-1].records[-1].received >= cutoff:
                    # Keep the last keyframe at/before the requested boundary.
                    # Its final delta may land just before cutoff; filtering by
                    # GOP end would lose that valid decoder prefix and pre-roll.
                    preceding = [index for index, gop in enumerate(camera.ring)
                        if gop.records[0].received <= cutoff]
                    start = preceding[-1] if preceding else 0
                    gops = list(camera.ring[start:])
                camera.active = _Episode(uuid.uuid4().hex, channel, event, stamp,
                    self._wall_clock(), stamp + self.post_seconds, stamp + self.max_duration_seconds,
                    stamp, gops, gaps=[dict(gap) for gap in camera.gaps if gap['to_received'] >= stamp - self.pre_seconds])
            else:
                episode = camera.active
                if stamp < episode.event_received:
                    return False
                episode.latest_activity = max(episode.latest_activity, stamp)
                episode.deadline = min(episode.cap, max(episode.deadline, stamp + self.post_seconds))
                episode.trigger_count = min(1000000, episode.trigger_count + 1)
            self._wake.set()
            return True

    def _status(self, channel, status, error=None):
        with self._lock:
            camera = self._cameras[channel]
            camera.status = status
            camera.last_error_kind = error

    def _reset_channel(self, channel, reason, stamp):
        with self._lock:
            camera = self._cameras[channel]
            if camera.active is not None:
                camera.active.clipped_reasons.add(reason)
                if camera.last_received is not None:
                    camera.active.gaps.append({'reason': reason, 'from_received': camera.last_received, 'to_received': stamp})
                self._queue_episode_locked(camera)
            camera.ring.clear()
            camera.codec, camera.fps = None, None
            camera.width = camera.height = 0
            camera.last_received = None
            camera.awaiting_keyframe = True
            camera.session += 1
            camera.gaps.clear()

    def _ingest(self, channel, frame, received):
        if channel not in CHANNELS or not _finite(received) or frame.kind not in (0xfc, 0xfd):
            return False
        payload = frame.payload
        if not isinstance(payload, bytes) or not payload.startswith((b'\x00\x00\x01', b'\x00\x00\x00\x01')):
            return False
        prefix = 4 if payload.startswith(b'\x00\x00\x00\x01') else 3
        if len(payload) <= prefix:
            return False
        key = frame.kind == 0xfc
        if key and frame.codec not in ('h264', 'hevc'):
            return False
        stamp = float(received)
        with self._lock:
            if self._closed:
                return False
            camera = self._cameras[channel]
            if camera.last_received is not None and stamp < camera.last_received:
                return False
            if key and camera.codec is not None and (camera.codec != frame.codec or
                    (frame.width, frame.height) != (camera.width, camera.height)):
                self._reset_channel(channel, 'codec_or_dimensions_changed', stamp)
            if camera.active is not None and stamp >= camera.active.deadline:
                self._queue_episode_locked(camera)
            if not key and (camera.awaiting_keyframe or not camera.ring):
                return False
            if key:
                camera.codec = frame.codec
                camera.width, camera.height = frame.width, frame.height
                camera.fps = frame.fps if type(frame.fps) is int and 1 <= frame.fps <= 60 else None
                camera.awaiting_keyframe = False
                camera.ring.append(_Gop())
                if camera.active is not None:
                    camera.active.gops.append(camera.ring[-1])
            if camera.last_received is not None and stamp - camera.last_received > max(2.0, 5 / (camera.fps or 10)):
                gap = {'reason': 'receipt_gap', 'from_received': camera.last_received, 'to_received': stamp}
                camera.gaps = (camera.gaps + [gap])[-64:]
                if camera.active is not None:
                    camera.active.gaps = (camera.active.gaps + [dict(gap)])[-64:]
            record = _Record(payload, camera.codec, key, stamp, camera.width, camera.height, camera.fps, camera.session)
            camera.ring[-1].records.append(record)
            camera.last_received = stamp
            camera.frames_received += 1
            camera.status = 'buffering'
            # Retain the GOP immediately before the requested pre-roll boundary.
            while len(camera.ring) > 1 and camera.ring[1].records[0].received <= stamp - self.pre_seconds:
                camera.ring.pop(0)
            self._trim_memory_locked(channel)
            return any(record is item for gop in camera.ring for item in gop.records)

    def _ring_records(self, channel):
        with self._lock:
            return tuple(record for gop in self._cameras[channel].ring for record in gop.records)

    def _memory_locked(self, channel=None):
        unique = {}
        for number, camera in self._cameras.items():
            if channel is not None and number != channel:
                continue
            gops = camera.ring + (camera.active.gops if camera.active is not None else [])
            for gop in gops:
                for record in gop.records:
                    unique[id(record)] = len(record.payload)
        for job in self._inflight.values():
            if channel is None or job.channel == channel:
                for record in job.records:
                    unique[id(record)] = len(record.payload)
        return sum(unique.values())

    def _record_count_locked(self, channel):
        camera = self._cameras[channel]
        records = {id(record) for gop in camera.ring +
            (camera.active.gops if camera.active is not None else []) for record in gop.records}
        for job in self._inflight.values():
            if job.channel == channel:
                records.update(id(record) for record in job.records)
        return len(records)

    def _trim_memory_locked(self, channel):
        camera = self._cameras[channel]
        while self._memory_locked(channel) > self.max_ring_bytes or self._memory_locked() > self.max_total_bytes or \
                self._record_count_locked(channel) > MAX_RECORDS_PER_CAMERA:
            candidates = camera.ring + (camera.active.gops if camera.active is not None else [])
            if not candidates:
                break
            oldest = min(candidates, key=lambda gop: gop.records[0].received)
            camera.ring = [gop for gop in camera.ring if gop is not oldest]
            if camera.active is not None and oldest in camera.active.gops:
                camera.active.gops.remove(oldest)
                camera.active.clipped_reasons.add('memory_quota')
                camera.active.gaps = (camera.active.gaps + [{'reason': 'memory_quota',
                    'from_received': oldest.records[0].received,
                    'to_received': oldest.records[-1].received}])[-64:]
            if not camera.ring:
                camera.awaiting_keyframe = True

    def _queue_episode_locked(self, camera):
        episode = camera.active
        if episode is None:
            return
        records = tuple(record for gop in episode.gops for record in gop.records if record.received <= episode.deadline)
        if episode.deadline >= episode.cap and episode.latest_activity + self.post_seconds >= episode.cap:
            episode.clipped_reasons.add('duration_cap')
        job = _Job(episode.identifier, episode.channel, dict(episode.event),
            episode.event_received, episode.received_epoch, episode.deadline,
            episode.latest_activity, episode.trigger_count, records,
            tuple(dict(gap) for gap in episode.gaps), frozenset(episode.clipped_reasons))
        camera.active = None
        try:
            self._inflight[job.identifier] = job
            self._jobs.put_nowait(job)
            self._wake.set()
        except queue.Full:
            self._inflight.pop(job.identifier, None)
            self._dropped_jobs += 1
            self._last_error_kind = 'FinalizationQueueFull'

    def _collect_due(self, now):
        with self._lock:
            if self._closed:
                return
            for camera in self._cameras.values():
                if camera.active is not None and now >= camera.active.deadline:
                    self._queue_episode_locked(camera)

    def _run_finalizer(self):
        self._load_clips()
        pruned_at = self._clock()
        while not self._stop.is_set():
            now = self._clock()
            self._collect_due(now)
            if now - pruned_at >= 60:
                try:
                    self._prune_storage()
                except OSError as error:
                    with self._lock:
                        self._last_error_kind = type(error).__name__
                pruned_at = now
            try:
                job = self._jobs.get_nowait()
            except queue.Empty:
                self._wake.wait(0.1)
                self._wake.clear()
                continue
            try:
                self._process_job(job)
            except Exception as error:
                with self._lock:
                    self._last_error_kind = type(error).__name__
            finally:
                with self._lock:
                    self._inflight.pop(job.identifier, None)
                self._jobs.task_done()

    def _select(self, job):
        best, best_stamp, best_score = None, None, -1.0
        selector, selector_result, selector_error, sampled_at = None, None, None, None
        selector_samples = 0
        selector_interval = max(1.0, (job.records[-1].received - job.records[0].received) / 19)
        selector_target = job.records[0].received
        decode_error = None
        if self.frame_selector_factory is not None:
            try:
                selector = self.frame_selector_factory()
            except Exception as error:
                selector_error = type(error).__name__
        try:
            for frame, stamp in _decode_records(job.records, self._stop):
                if self._stop.is_set():
                    break
                if not _finite(stamp) or not job.records[0].received - 0.01 <= stamp <= job.records[-1].received + 0.01:
                    continue
                if selector is not None and selector_samples < 20 and stamp + 1e-6 >= selector_target:
                    try:
                        selector.consider(frame, stamp)
                        selector_samples += 1
                        selector_target = job.records[0].received + selector_samples * selector_interval
                    except Exception as error:
                        selector_error = type(error).__name__
                        selector = None
                # Decode dependent pictures but sample scene quality at one fps.
                if sampled_at is None or stamp - sampled_at >= 1.0:
                    sampled_at = stamp
                    score = _frame_quality(frame)
                    if score > best_score:
                        best, best_stamp, best_score = frame, stamp, score
        except Exception as error:
            decode_error = type(error).__name__
        capture = None
        if best is not None and not self._stop.is_set():
            age = self._clock() - best_stamp
            if 0 <= age <= 120:
                try:
                    ppm = _original_ppm(best)
                    capture = {'ppm': ppm, 'width': best.width, 'height': best.height,
                        'source_width': best.width, 'source_height': best.height,
                        'stream': 'Main', 'frame_age_seconds': age, 'sequence_id': job.identifier,
                        'event_received_monotonic': job.event_received,
                        'sequence_offset_seconds': best_stamp - job.event_received,
                        'selection': 'escena',
                        'selection_method': 'full_scene_sharpness_exposure'}
                except Exception as error:
                    decode_error = type(error).__name__
        if selector is not None and not self._stop.is_set():
            try:
                selector_result = selector.finalize()
                if capture is not None:
                    capture['selector_result'] = selector_result
            except Exception as error:
                selector_error = type(error).__name__
        status = {'body_status': 'disabled' if self.frame_selector_factory is None else 'unavailable',
            'face_status': 'disabled' if self.frame_selector_factory is None else 'unavailable',
            'detector_status': 'disabled' if self.frame_selector_factory is None else 'unavailable',
            'considered': 0, 'error_kind': selector_error}
        if isinstance(selector_result, dict):
            for key in ('body_status', 'face_status', 'detector_status'):
                value = selector_result.get(key)
                if isinstance(value, str) and len(value) <= 80:
                    status[key] = value
            considered = selector_result.get('considered')
            if type(considered) is int and 0 <= considered <= 1000:
                status['considered'] = considered
        return capture, decode_error, status

    def _metadata(self, job, capture, decode_error):
        records = job.records
        first, last = (records[0].received, records[-1].received) if records else (job.event_received, job.event_received)
        pre = max(0.0, job.event_received - first) if records else 0.0
        post = max(0.0, last - job.event_received) if records else 0.0
        reasons = set(job.clipped_reasons)
        tolerance = 1 / (records[-1].fps or 10) if records else 0
        if pre + tolerance < self.pre_seconds:
            reasons.add('pre_coverage_incomplete')
        if last + tolerance < job.deadline or not records:
            reasons.add('post_coverage_incomplete')
        if job.gaps:
            reasons.add('gaps_recorded')
        offsets, offset, digest = [], 0, hashlib.sha256()
        for record in records:
            offsets.append({'byte_offset': offset, 'bytes': len(record.payload),
                'event_offset_seconds': round(record.received - job.event_received, 6),
                'keyframe_marker': record.key, 'fps': record.fps})
            offset += len(record.payload)
            digest.update(record.payload)
        codec = records[0].codec if records else None
        filename = job.identifier + ('.h264' if codec == 'h264' else '.hevc') if records else None
        metadata = {'version': 1, 'id': job.identifier, 'camera': job.channel + 1,
            'event': job.event['event'], 'device_time': job.event.get('time'),
            'received_at': datetime.fromtimestamp(job.received_epoch, timezone.utc).isoformat(timespec='milliseconds'),
            'received_epoch': job.received_epoch, 'stream': 'Main', 'codec': codec,
            'format': 'annex_b_elementary_stream', 'player_support': 'elementary_stream_codec_required',
            'timing_source': 'local_monotonic_receipt', 'embedded_timestamps': False,
            'continuity_verified': False, 'gap_detection_threshold_seconds': 2.0,
            'requested_pre_seconds': self.pre_seconds, 'requested_post_seconds': self.post_seconds,
            'requested_end_offset_seconds': round(job.deadline - job.event_received, 6),
            'latest_activity_offset_seconds': round(job.latest_activity - job.event_received, 6),
            'pre_coverage_seconds': round(pre, 6), 'post_coverage_seconds': round(post, 6),
            'trigger_count': job.trigger_count, 'gaps': [{'reason': gap['reason'],
                'from_event_offset_seconds': round(gap['from_received'] - job.event_received, 6),
                'to_event_offset_seconds': round(gap['to_received'] - job.event_received, 6)} for gap in job.gaps],
            'clipped_reasons': sorted(reasons), 'status': 'partial' if reasons else 'complete',
            'original_sha256': digest.hexdigest(), 'encoded_bytes': offset,
            'video_file': filename, 'metadata_file': job.identifier + '.json',
            'source_width': records[0].width if records else None,
            'source_height': records[0].height if records else None,
            'frames': offsets, 'decode_error_kind': decode_error, 'image_selection': None}
        if capture is not None:
            metadata['image_selection'] = {key: capture[key] for key in ('selection',
                'sequence_offset_seconds', 'frame_age_seconds', 'width', 'height')}
        return metadata

    def _process_job(self, job):
        if self._stop.is_set():
            return
        # Preserve original compressed bytes before any expensive image analysis.
        metadata = self._metadata(job, None, None)
        metadata['image_status'] = 'selection_pending'
        saved = False
        try:
            self._save_episode(job, metadata)
        except Exception as error:
            with self._lock:
                self._last_error_kind = type(error).__name__
        else:
            saved = True
        if self._stop.is_set():
            return
        capture, decode_error, selector_status = self._select(job) if job.records else (None, None,
            {'body_status': 'unavailable', 'face_status': 'unavailable',
                'detector_status': 'no_video', 'considered': 0, 'error_kind': None})
        metadata = self._metadata(job, capture, decode_error)
        metadata['selector_status'] = selector_status
        metadata['image_status'] = 'selected' if capture is not None else 'unavailable'
        if saved and not self._stop.is_set():
            try:
                self._update_metadata(metadata)
            except Exception as error:
                with self._lock:
                    self._last_error_kind = type(error).__name__
        if capture is not None:
            capture['sequence_storage_status'] = 'saved' if saved else 'not_saved'
        # Age is measured at publication, after potentially slow persistence.
        if capture is not None:
            capture['frame_age_seconds'] = self._clock() - (job.event_received + capture['sequence_offset_seconds'])
            if not 0 <= capture['frame_age_seconds'] <= 120:
                capture = None
        if not self._stop.is_set():
            try:
                self.on_capture(dict(job.event), capture)
            except Exception as error:
                with self._lock:
                    self._last_error_kind = type(error).__name__

    def _safe_directory(self):
        if any(_linked(path) for path in (self.directory, *self.directory.parents)):
            raise OSError('Unsafe sequence directory')
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.directory.is_dir():
            raise OSError('Invalid sequence directory')

    def _safe_path(self, filename):
        if re.fullmatch(r'[0-9a-f]{32}\.(?:json|h264|hevc)', filename) is None:
            raise OSError('Invalid sequence filename')
        self._safe_directory()
        path = self.directory / filename
        if _linked(path) or (path.exists() and not path.is_file()):
            raise OSError('Unsafe sequence file')
        return path

    def _write_atomic(self, filename, chunks):
        target = self._safe_path(filename)
        temporary = self.directory / (filename + '.' + uuid.uuid4().hex + '.tmp')
        descriptor = None
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
            with os.fdopen(descriptor, 'wb') as handle:
                descriptor = None
                for chunk in chunks:
                    if self._stop.is_set():
                        raise InterruptedError('Sequence stopped')
                    handle.write(chunk)
            if self._stop.is_set():
                raise InterruptedError('Sequence stopped')
            os.replace(temporary, target)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                temporary.unlink()
            except OSError:
                pass

    def _delete_episode(self, metadata):
        deleted = True
        for filename in (metadata.get('video_file'), metadata.get('metadata_file')):
            if filename is None:
                continue
            deleted = self._delete_owned_file(filename) and deleted
        return deleted

    def _delete_owned_file(self, filename):
        if not isinstance(filename, str) or OWNED_FILENAME.fullmatch(filename) is None:
            return False
        try:
            self._safe_directory()
            path = self.directory / filename
            if _linked(path):
                return False
            try:
                metadata = path.stat(follow_symlinks=False)
            except FileNotFoundError:
                return True
            if not stat.S_ISREG(metadata.st_mode):
                return False
            path.unlink()
            return True
        except OSError:
            return False

    def _storage_bytes_locked(self):
        return sum(clip['_disk_bytes'] for clip in self._clips) + sum(self._orphans.values())

    def _prune_storage(self, additional=0, new_count=0):
        # Files Windows refuses to unlink remain counted; a reader or antivirus
        # must not let retention silently exceed the configured byte quota.
        with self._lock:
            orphan_names = list(self._orphans)
        for filename in orphan_names:
            if self._delete_owned_file(filename):
                with self._lock:
                    self._orphans.pop(filename, None)
            else:
                with self._lock:
                    self._last_error_kind = 'RetentionDeleteBlocked'
        attempted = set()
        while True:
            with self._lock:
                cutoff = self._wall_clock() - self.max_age_seconds
                obsolete = next((clip for clip in reversed(self._clips) if
                    clip['received_epoch'] < cutoff and clip['id'] not in attempted), None)
                pressure = len(self._clips) + new_count > self.max_episodes or self._storage_bytes_locked() + additional > self.max_storage_bytes
                if obsolete is None and pressure:
                    obsolete = next((clip for clip in reversed(self._clips) if clip['id'] not in attempted), None)
                if obsolete is None:
                    return not pressure
                attempted.add(obsolete['id'])
            if self._delete_episode(obsolete):
                with self._lock:
                    self._clips = [clip for clip in self._clips if clip is not obsolete]
            else:
                with self._lock:
                    self._last_error_kind = 'RetentionDeleteBlocked'

    def _load_clips(self):
        with self._lock:
            if self._loaded:
                return
            self._loaded = True
        try:
            self._safe_directory()
            saved = []
            # Temporary/crash files have an exact UUID naming convention. Only
            # regular files in this dedicated directory can become owned.
            owned = {}
            for path in self.directory.iterdir():
                if self._stop.is_set():
                    return
                if OWNED_FILENAME.fullmatch(path.name) is None or _linked(path):
                    continue
                try:
                    info = path.stat(follow_symlinks=False)
                    if stat.S_ISREG(info.st_mode):
                        owned[path.name] = info.st_size
                except OSError:
                    continue
            for path in self.directory.glob('*.json'):
                if self._stop.is_set():
                    return
                identifier = path.stem
                if SAFE_ID.fullmatch(identifier) is None:
                    continue
                try:
                    safe = self._safe_path(path.name)
                    if safe.stat().st_size > MAX_METADATA_BYTES:
                        continue
                    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
                    descriptor = os.open(safe, flags)
                    with os.fdopen(descriptor, 'rb') as handle:
                        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                            continue
                        clip = json.loads(handle.read(MAX_METADATA_BYTES + 1))
                    if not isinstance(clip, dict) or clip.get('version') != 1 or clip.get('id') != identifier:
                        continue
                    if not self._valid_restored_metadata(clip):
                        continue
                    if clip.get('metadata_file') != identifier + '.json' or not _finite(clip.get('received_epoch')):
                        continue
                    if clip['received_epoch'] > self._wall_clock() + 300:
                        continue
                    filename = clip.get('video_file')
                    size = safe.stat().st_size
                    if filename is not None:
                        if filename not in (identifier + '.h264', identifier + '.hevc'):
                            continue
                        video = self._safe_path(filename)
                        if filename not in owned or not video.exists():
                            continue
                        encoded_size = video.stat().st_size
                        if clip.get('encoded_bytes') != encoded_size:
                            continue
                        size += encoded_size
                    clip = {key: value for key, value in clip.items() if key in METADATA_FIELDS}
                    clip['frames'] = [{key: row[key] for key in ('byte_offset', 'bytes',
                        'event_offset_seconds', 'keyframe_marker', 'fps')} for row in clip['frames']]
                    clip['gaps'] = [{key: row[key] for key in ('reason',
                        'from_event_offset_seconds', 'to_event_offset_seconds')} for row in clip['gaps']]
                    for field_name, field_keys in (('image_selection', ('selection',
                            'sequence_offset_seconds', 'frame_age_seconds', 'width', 'height')),
                            ('selector_status', ('body_status', 'face_status', 'detector_status', 'considered', 'error_kind'))):
                        if isinstance(clip.get(field_name), dict):
                            clip[field_name] = {key: clip[field_name].get(key) for key in field_keys}
                    clip['_disk_bytes'] = size
                    saved.append(clip)
                    saved.sort(key=lambda row: row['received_epoch'], reverse=True)
                    # Bound restored metadata memory while retaining newer clips.
                    if len(saved) > self.max_episodes:
                        saved.pop()
                except (OSError, ValueError, TypeError, RecursionError):
                    continue
            used = {filename for clip in saved for filename in
                (clip.get('video_file'), clip.get('metadata_file')) if filename is not None}
            with self._lock:
                self._clips = saved
                self._orphans = {filename: size for filename, size in owned.items() if filename not in used}
            self._prune_storage()
        except OSError as error:
            with self._lock:
                self._last_error_kind = type(error).__name__

    @staticmethod
    def _valid_restored_metadata(clip):
        if clip.get('event') not in DETECTION_EVENTS or type(clip.get('camera')) is not int or clip['camera'] not in range(1, 8):
            return False
        if clip.get('stream') != 'Main' or clip.get('format') != 'annex_b_elementary_stream':
            return False
        if clip.get('codec') not in (None, 'h264', 'hevc') or clip.get('status') not in ('complete', 'partial'):
            return False
        frames = clip.get('frames')
        if not isinstance(frames, list) or len(frames) > MAX_RECORDS_PER_CAMERA:
            return False
        offset, previous_time = 0, -float('inf')
        for index, row in enumerate(frames):
            if not isinstance(row, dict) or row.get('byte_offset') != offset:
                return False
            length, timestamp = row.get('bytes'), row.get('event_offset_seconds')
            if type(length) is not int or not 0 < length <= 8 * 1024 * 1024 or not _finite(timestamp) or timestamp < previous_time:
                return False
            if type(row.get('keyframe_marker')) is not bool or (index == 0 and not row['keyframe_marker']):
                return False
            if row.get('fps') is not None and (type(row['fps']) is not int or not 1 <= row['fps'] <= 60):
                return False
            offset += length
            previous_time = timestamp
        if type(clip.get('encoded_bytes')) is not int or clip['encoded_bytes'] != offset:
            return False
        if not isinstance(clip.get('original_sha256'), str) or re.fullmatch(r'[0-9a-f]{64}', clip['original_sha256']) is None:
            return False
        gaps, reasons = clip.get('gaps'), clip.get('clipped_reasons')
        if not isinstance(gaps, list) or len(gaps) > 64 or not isinstance(reasons, list) or len(reasons) > 32:
            return False
        for gap in gaps:
            if not isinstance(gap, dict) or not isinstance(gap.get('reason'), str) or len(gap['reason']) > 80 or not all(
                    _finite(gap.get(key)) for key in ('from_event_offset_seconds', 'to_event_offset_seconds')):
                return False
        return all(isinstance(reason, str) and len(reason) <= 80 for reason in reasons)

    def _save_episode(self, job, metadata):
        self._load_clips()
        self._safe_directory()
        payload = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        size = len(payload) + metadata['encoded_bytes']
        if len(payload) > MAX_METADATA_BYTES or size > self.max_storage_bytes:
            raise OSError('Sequence exceeds storage quota')
        if not self._prune_storage(size, 1):
            raise OSError('Sequence retention could not free quota')
        if shutil.disk_usage(self.directory).free < self.min_free_bytes + size:
            raise OSError('Sequence free space floor reached')
        try:
            if metadata['video_file'] is not None:
                self._write_atomic(metadata['video_file'], (record.payload for record in job.records))
            self._write_atomic(metadata['metadata_file'], (payload,))
        except Exception:
            if not self._delete_episode(metadata):
                with self._lock:
                    for filename in (metadata.get('video_file'), metadata.get('metadata_file')):
                        if filename is None:
                            continue
                        try:
                            path = self._safe_path(filename)
                            if path.exists():
                                self._orphans[filename] = path.stat(follow_symlinks=False).st_size
                        except OSError:
                            pass
            raise
        stored = dict(metadata, _disk_bytes=size)
        with self._lock:
            self._clips.insert(0, stored)
            self._clips.sort(key=lambda clip: clip['received_epoch'], reverse=True)

    def _update_metadata(self, metadata):
        payload = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
        if len(payload) > MAX_METADATA_BYTES:
            raise OSError('Sequence metadata exceeds bound')
        size = metadata['encoded_bytes'] + len(payload)
        with self._lock:
            previous = next((clip for clip in self._clips if clip['id'] == metadata['id']), None)
            if previous is None:
                return
            others = sum(clip['_disk_bytes'] for clip in self._clips if clip is not previous) + sum(self._orphans.values())
        if others + size > self.max_storage_bytes:
            raise OSError('Sequence metadata exceeds storage quota')
        self._write_atomic(metadata['metadata_file'], (payload,))
        with self._lock:
            self._clips = [dict(metadata, _disk_bytes=size) if clip is previous else clip for clip in self._clips]

    def list_clips(self):
        """Cached metadata only; no file access or untrusted playback paths."""
        with self._lock:
            cutoff = self._wall_clock() - self.max_age_seconds
            return [copy.deepcopy({key: value for key, value in clip.items() if not key.startswith('_')})
                for clip in self._clips if clip['received_epoch'] >= cutoff]

    def clip_path(self, identifier):
        """Return a verified owned raw clip path for an explicitly selected ID."""
        if not isinstance(identifier, str) or SAFE_ID.fullmatch(identifier) is None:
            return None
        with self._lock:
            clip = next((item for item in self._clips if item['id'] == identifier and
                item['received_epoch'] >= self._wall_clock() - self.max_age_seconds), None)
            filename = clip.get('video_file') if clip is not None else None
        if filename is None:
            return None
        try:
            path = self._safe_path(filename)
            metadata = path.stat(follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > self.max_storage_bytes:
                return None
            return path
        except OSError:
            return None

    def playback_frames(self, identifier, stop_event):
        """Decode one selected, size/digest-verified original clip in a worker.

        Yield ``(original_av_frame, event_offset_seconds)`` through the same
        receipt/PTS association used for image selection. This is a generator;
        callers must advance it on a playback thread, never the Tk thread.
        """
        if not isinstance(identifier, str) or SAFE_ID.fullmatch(identifier) is None:
            raise ValueError('Invalid sequence identifier')
        with self._lock:
            stored = next((clip for clip in self._clips if clip['id'] == identifier and
                clip['received_epoch'] >= self._wall_clock() - self.max_age_seconds), None)
            clip = copy.deepcopy(stored) if stored is not None else None
        if clip is None or clip.get('video_file') is None:
            raise OSError('Sequence is unavailable')
        if not self._valid_restored_metadata(clip):
            raise ValueError('Invalid sequence metadata')
        path = self._safe_path(clip['video_file'])
        if stop_event.is_set():
            return
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size != clip['encoded_bytes'] or info.st_size > self.max_ring_bytes:
                raise OSError('Sequence size exceeds bound')
            payload = handle.read(self.max_ring_bytes + 1)
        if stop_event.is_set():
            return
        if len(payload) != clip['encoded_bytes'] or hashlib.sha256(payload).hexdigest() != clip['original_sha256']:
            raise ValueError('Original sequence integrity failed')
        records = []
        for row in clip['frames']:
            start = row['byte_offset']
            records.append(_Record(payload[start:start + row['bytes']], clip['codec'],
                row['keyframe_marker'], row['event_offset_seconds'],
                clip['source_width'], clip['source_height'], row['fps'], 0))
        # Free the combined read buffer; encoded records retain the camera cap.
        del payload
        yield from _decode_records(tuple(records), stop_event)

    def snapshot(self):
        with self._lock:
            cameras = []
            for channel, camera in self._cameras.items():
                records = [record for gop in camera.ring for record in gop.records]
                cameras.append({'camera': channel + 1, 'stream': 'Main', 'status': camera.status,
                    'compressed_memory_bytes': self._memory_locked(channel),
                    'ring_bytes': sum(len(record.payload) for record in records),
                    'ring_coverage_seconds': round(records[-1].received - records[0].received, 3) if records else 0,
                    'awaiting_keyframe': camera.awaiting_keyframe, 'episode_active': camera.active is not None,
                    'frames_received': camera.frames_received, 'reconnections': camera.reconnects,
                    'last_error_kind': camera.last_error_kind})
            return {'enabled': not self._closed, 'stream': 'Main', 'pre_seconds': self.pre_seconds,
                'post_seconds': self.post_seconds, 'max_duration_seconds': self.max_duration_seconds,
                'compressed_memory_bytes': self._memory_locked(), 'max_compressed_memory_bytes': self.max_total_bytes,
                'queued_episodes': self._jobs.qsize(), 'episode_count': len(self._clips),
                'storage_bytes': self._storage_bytes_locked(), 'owned_orphan_count': len(self._orphans),
                'max_storage_bytes': self.max_storage_bytes, 'dropped_episodes': self._dropped_jobs,
                'last_error_kind': self._last_error_kind, 'cameras': cameras}

    def stop(self):
        """Cancel without draining clips; receiver/finalizer joins share one second."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._auth_hash = None
            self._stop.set()
            self._wake.set()
            workers = list(self._workers.values())
            for camera in self._cameras.values():
                camera.ring.clear()
                camera.active = None
                camera.awaiting_keyframe = True
                camera.status = 'stopped'
            self._inflight.clear()
            while True:
                try:
                    self._jobs.get_nowait()
                    self._jobs.task_done()
                except queue.Empty:
                    break
        for worker in workers:
            worker.cancel()
        deadline = time.monotonic() + 1.0
        for worker in workers + ([self._finalizer] if self._finalizer is not None else []):
            if worker is not threading.current_thread():
                worker.join(timeout=max(0.0, deadline - time.monotonic()))
