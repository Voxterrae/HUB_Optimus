"""Bounded local event previews, captured only while the live viewer is running.

These are preview frames at receipt of a device event, not NVR recordings or
historical recovery. This module has no Tk calls, network code or dependencies.
"""
from datetime import datetime, timezone
import gzip
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
import zlib

MAX_PPM_BYTES = 32 * 1024 * 1024
MAX_STORE_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
ID_PATTERN = re.compile(r'[0-9a-f]{32}\Z')
OWNED_FILE_PATTERN = re.compile(r'(?:[0-9a-f]{32}\.ppm\.gz(?:\.[0-9a-f]{32}\.tmp)?|manifest\.json\.[0-9a-f]{32}\.tmp)\Z')
PPM_HEADER = re.compile(br'P6\n([1-9][0-9]{0,4}) ([1-9][0-9]{0,4})\n255\n')
EVENTS = frozenset(('HumanDetect', 'appEventHumanDetectAlarm', 'CarShapeDetect',
    'FaceDetection', 'FaceDetect', 'VideoMotion', 'MotionDetect', 'VideoLoss',
    'LossDetect', 'VideoBlind', 'BlindDetect', 'Blind', 'StorageNotExist',
    'StorageLowSpace', 'StorrageLowSpace', 'StorageFailureWrite',
    'StorageFailureRead', 'StorageReadError', 'NetIPConfict', 'NetAbort',
    'IPCAlarm', 'VideoAnalyze', 'VIdeoAnanyze'))
FIELDS = ('id', 'event', 'camera', 'received_at', 'device_time',
    'frame_age_seconds', 'width', 'height', 'source_width', 'source_height', 'stream', 'state',
    'sequence_id', 'sequence_offset_seconds', 'selection', 'bbox')


def _sequence_metadata(value):
    empty = dict(sequence_id=None, sequence_offset_seconds=None, selection=None, bbox=None)
    identifier, offset = value.get('sequence_id'), value.get('sequence_offset_seconds')
    if not isinstance(identifier, str) or ID_PATTERN.fullmatch(identifier) is None:
        return empty
    if type(offset) not in (int, float) or not math.isfinite(offset) or not -120 <= offset <= 120:
        return empty
    selection = value.get('selection')
    if selection not in ('escena', 'cuerpo_detectado', 'rostro_detectado'):
        return empty
    box = value.get('bbox')
    if box is not None:
        if (not isinstance(box, (list, tuple)) or len(box) != 4 or
                any(type(part) is not int for part in box) or
                box[0] < 0 or box[1] < 0 or box[2] < 1 or box[3] < 1 or
                box[0] + box[2] > value.get('width', 0) or
                box[1] + box[3] > value.get('height', 0)):
            box = None
        else:
            box = list(box)
    return dict(sequence_id=identifier, sequence_offset_seconds=float(offset),
                selection=selection, bbox=box)


class _LowSpace(OSError):
    pass


def _linked(path):
    return path.is_symlink() or bool(getattr(path, 'is_junction', lambda: False)())


def _device_time(value):
    if isinstance(value, str) and len(value) == 19:
        try:
            datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            return value
        except ValueError:
            pass
    return None


def _dimension(value, maximum):
    return type(value) is int and 1 <= value <= maximum


def _ppm_dimensions(value):
    if not isinstance(value, bytes) or len(value) > MAX_PPM_BYTES:
        return None
    header = PPM_HEADER.match(value)
    if header is None:
        return None
    width, height = int(header[1]), int(header[2])
    if width > 4096 or height > 4096 or len(value) != header.end() + width * height * 3:
        return None
    return width, height


def _capture(value):
    if not isinstance(value, dict):
        return None
    dimensions = _ppm_dimensions(value.get('ppm'))
    age = value.get('frame_age_seconds')
    if dimensions is None or dimensions != (value.get('width'), value.get('height')):
        return None
    sequence = _sequence_metadata(value)
    if type(age) not in (int, float) or not math.isfinite(age) or not 0 <= age <= (120 if sequence['sequence_id'] else 2):
        return None
    if not _dimension(value.get('source_width'), 8192) or not _dimension(value.get('source_height'), 8192):
        return None
    if value.get('stream') not in ('Extra1', 'Main'):
        return None
    return dict({key: value[key] for key in ('ppm', 'frame_age_seconds', 'width', 'height',
        'source_width', 'source_height', 'stream')}, **sequence)


class EvidenceStore:
    def __init__(self, directory, max_count=25, max_bytes=8 * 1024 * 1024,
            max_age_hours=48, min_free_bytes=128 * 1024 * 1024):
        self.directory = Path(os.path.abspath(os.fspath(directory)))
        self.max_count = max(1, min(25, int(max_count)))
        self.max_bytes = max(1, min(MAX_STORE_BYTES, int(max_bytes)))
        self.max_age_seconds = max(0.001, min(48 * 3600, float(max_age_hours) * 3600))
        self.min_free_bytes = max(0, int(min_free_bytes))
        self._lock = threading.Lock()
        self._entries = []
        self._owned_files = set()
        self._active_id = None
        self._closed = False
        self._dirty = False
        self._generation = 0
        self._queue = queue.Queue(maxsize=2)
        self._stop = threading.Event()
        self._restore()
        self._worker = threading.Thread(target=self._run, name='CCTV-Capturas', daemon=True)
        self._worker.start()

    def add(self, event_sanitised, capture_or_none):
        """Return immediately; False means closed, invalid event or a full queue."""
        if not isinstance(event_sanitised, dict) or event_sanitised.get('event') not in EVENTS:
            return False
        camera = event_sanitised.get('channel', event_sanitised.get('camera'))
        if camera is not None and not _dimension(camera, 7):
            return False
        if event_sanitised.get('status') not in ('Start', 'Stop', 'None'):
            return False
        picture = _capture(capture_or_none) if camera is not None else None
        now = time.time()
        row = {'id': uuid.uuid4().hex, 'event': event_sanitised['event'], 'camera': camera,
            'received_at': datetime.fromtimestamp(now, timezone.utc).isoformat(timespec='milliseconds'),
            'device_time': _device_time(event_sanitised.get('time')),
            'state': 'Pendiente' if picture else 'Sin imagen reciente',
            '_received_epoch': now, '_ppm': picture['ppm'] if picture else None,
            '_file': None, '_disk_bytes': 0}
        for key in ('frame_age_seconds', 'width', 'height', 'source_width', 'source_height', 'stream',
                    'sequence_id', 'sequence_offset_seconds', 'selection', 'bbox'):
            row[key] = picture[key] if picture else None
        with self._lock:
            if self._closed or self._queue.full():
                return False
            self._prune_locked()
            size = len(row['_ppm']) if row['_ppm'] is not None else 0
            if size > self.max_bytes:
                row['_ppm'] = None
                row['state'] = 'Sin imagen: límite de memoria'
                size = 0
            while len(self._entries) >= self.max_count or self._ram_bytes_locked() + size > self.max_bytes:
                candidate = next((old for old in reversed(self._entries) if old['id'] != self._active_id), None)
                if candidate is None:
                    return False
                self._entries.remove(candidate)
                self._changed_locked()
            try:
                self._queue.put_nowait(row['id'])
            except queue.Full:
                return False
            self._entries.insert(0, row)
            self._changed_locked()
        return True

    def list_entries(self):
        with self._lock:
            self._prune_locked()
            cutoff = time.time() - self.max_age_seconds
            return [self._public(row) for row in self._entries if row['_received_epoch'] >= cutoff]

    def read_image(self, identifier):
        if not isinstance(identifier, str) or ID_PATTERN.fullmatch(identifier) is None:
            return None
        with self._lock:
            row = self._find_locked(identifier)
            if row is None or row['_received_epoch'] < time.time() - self.max_age_seconds:
                return None
            if row['_ppm'] is not None:
                return row['_ppm']
            filename, dimensions = row['_file'], (row['width'], row['height'])
        if filename != identifier + '.ppm.gz':
            return None
        try:
            with self._open_regular(filename, self.max_bytes) as handle:
                with gzip.GzipFile(fileobj=handle, mode='rb') as compressed:
                    ppm = compressed.read(MAX_PPM_BYTES + 1)
            if _ppm_dimensions(ppm) != dimensions:
                raise ValueError('Invalid preview')
            return ppm
        except (OSError, EOFError, ValueError, zlib.error):
            with self._lock:
                row = self._find_locked(identifier)
                if row is not None:
                    row['state'] = 'Captura no disponible'
                    self._changed_locked()
            return None

    def close(self):
        """Allow at most one second to drain; a slow disk cannot hold the UI open."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._stop.set()
        if threading.current_thread() is not self._worker:
            self._worker.join(timeout=1)

    @staticmethod
    def _public(row):
        return {key: row[key] for key in FIELDS if key not in
                ('sequence_id', 'sequence_offset_seconds', 'selection', 'bbox') or row.get('sequence_id')}

    def _find_locked(self, identifier):
        return next((row for row in self._entries if row['id'] == identifier), None)

    def _changed_locked(self):
        self._dirty = True
        self._generation += 1

    def _ram_bytes_locked(self):
        return sum(len(row['_ppm']) for row in self._entries if row['_ppm'] is not None)

    def _prune_locked(self):
        cutoff = time.time() - self.max_age_seconds
        kept = [row for row in self._entries if row['_received_epoch'] >= cutoff or row['id'] == self._active_id]
        if len(kept) != len(self._entries):
            self._entries = kept
            self._changed_locked()
        while len(self._entries) > self.max_count:
            row = next((row for row in reversed(self._entries) if row['id'] != self._active_id), None)
            if row is None:
                break
            self._entries.remove(row)
            self._changed_locked()

    def _directory_safe(self):
        try:
            return not any(_linked(path) for path in (self.directory, *self.directory.parents))
        except OSError:
            return False

    def _prepare_directory(self):
        if not self._directory_safe():
            raise OSError('Unsafe gallery directory')
        self.directory.mkdir(parents=True, exist_ok=True)
        if not self.directory.is_dir() or _linked(self.directory / 'manifest.json'):
            raise OSError('Unsafe gallery manifest')

    def _open_regular(self, filename, maximum):
        if filename != 'manifest.json' and re.fullmatch(r'[0-9a-f]{32}\.ppm\.gz', filename) is None:
            raise OSError('Unsafe gallery filename')
        if not self._directory_safe():
            raise OSError('Unsafe gallery directory')
        path = self.directory / filename
        if _linked(path) or path.resolve(strict=True).parent != self.directory.resolve(strict=True):
            raise OSError('Unsafe gallery file')
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        descriptor = os.open(path, flags)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
                raise OSError('Gallery file exceeds limit')
            return os.fdopen(descriptor, 'rb')
        except Exception:
            os.close(descriptor)
            raise

    def _restore(self):
        try:
            if self._directory_safe() and self.directory.is_dir():
                for path in self.directory.iterdir():
                    if OWNED_FILE_PATTERN.fullmatch(path.name) and not _linked(path) and path.is_file():
                        self._owned_files.add(path.name)
        except OSError:
            pass
        try:
            with self._open_regular('manifest.json', MAX_MANIFEST_BYTES) as handle:
                document = json.loads(handle.read(MAX_MANIFEST_BYTES + 1))
            if not isinstance(document, dict) or document.get('version') != 1 or not isinstance(document.get('entries'), list):
                return
            for saved in document['entries'][:25]:
                row = self._restored_row(saved)
                if row is None or any(old['id'] == row['id'] for old in self._entries):
                    continue
                self._entries.append(row)
                if row['_file'] is not None:
                    self._owned_files.add(row['_file'])
            self._entries.sort(key=lambda row: row['_received_epoch'], reverse=True)
            self._prune_locked()
            self._quota_locked()
        except (OSError, ValueError, TypeError, RecursionError):
            pass
        finally:
            self._delete_orphans()

    def _restored_row(self, saved):
        if not isinstance(saved, dict) or not isinstance(saved.get('id'), str) or ID_PATTERN.fullmatch(saved['id']) is None:
            return None
        if saved.get('event') not in EVENTS or (saved.get('camera') is not None and not _dimension(saved.get('camera'), 7)):
            return None
        timestamp = saved.get('received_at')
        if not isinstance(timestamp, str) or len(timestamp) > 40:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp)
            if parsed.tzinfo is None:
                return None
            epoch = parsed.timestamp()
            if not math.isfinite(epoch) or epoch > time.time() + 300:
                return None
        except (ValueError, OverflowError):
            return None
        filename = saved.get('image_file')
        if filename is not None and filename != saved['id'] + '.ppm.gz':
            return None
        row = {key: saved.get(key) for key in FIELDS}
        row.update(_sequence_metadata(saved))
        row['device_time'] = _device_time(saved.get('device_time'))
        row.update(_received_epoch=epoch, _ppm=None, _file=filename, _disk_bytes=0)
        if filename is not None:
            age = row['frame_age_seconds']
            if type(age) not in (int, float) or not math.isfinite(age) or not 0 <= age <= (120 if row['sequence_id'] else 2):
                return None
            if not all(_dimension(row[key], maximum) for key, maximum in
                    (('width', 4096), ('height', 4096), ('source_width', 8192), ('source_height', 8192))) or row['stream'] not in ('Extra1', 'Main'):
                return None
            try:
                with self._open_regular(filename, self.max_bytes) as handle:
                    row['_disk_bytes'] = os.fstat(handle.fileno()).st_size
                row['state'] = 'Guardada'
            except OSError:
                row['_file'] = None
                row['state'] = 'Captura no disponible'
        else:
            row['state'] = 'Sin imagen reciente' if saved.get('state') == 'Sin imagen reciente' else 'Sin imagen guardada'
            for key in ('frame_age_seconds', 'width', 'height', 'source_width', 'source_height', 'stream'):
                row[key] = None
        return row

    def _manifest_locked(self):
        rows = []
        for row in self._entries:
            if row['state'] == 'Pendiente' and not row.get('_persisting'):
                continue
            saved = self._public(row)
            if row.get('_persisting'):
                saved['state'] = 'Guardada'
            saved['image_file'] = row['_file']
            rows.append(saved)
        return json.dumps({'version': 1, 'entries': rows}, ensure_ascii=False,
            separators=(',', ':'), allow_nan=False).encode('utf-8')

    def _quota_locked(self):
        while self._entries:
            size = sum(row['_disk_bytes'] for row in self._entries) + len(self._manifest_locked())
            if size <= self.max_bytes:
                break
            row = next((row for row in reversed(self._entries) if row['id'] != self._active_id), None)
            if row is None:
                break
            self._entries.remove(row)
            self._changed_locked()

    def _delete_orphans(self):
        with self._lock:
            used = {row['_file'] for row in self._entries if row['_file'] is not None}
            unused = self._owned_files - used
        if not self._directory_safe():
            return
        for filename in unused:
            path = self.directory / filename
            try:
                # Never remove foreign files, symlinks, junctions or nonregular files.
                if _linked(path):
                    continue
                metadata = path.stat(follow_symlinks=False)
                if not stat.S_ISREG(metadata.st_mode):
                    continue
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                continue
            with self._lock:
                self._owned_files.discard(filename)

    def _require_space(self, additional):
        if shutil.disk_usage(self.directory).free < self.min_free_bytes + additional:
            raise _LowSpace('Gallery free-space floor reached')

    def _physical_bytes(self):
        """Count owned files left by failed deletions/crashes, not just rows."""
        if not self._directory_safe():
            raise OSError('Unsafe gallery directory')
        size = 0
        for path in self.directory.iterdir():
            if path.name == 'manifest.json' or OWNED_FILE_PATTERN.fullmatch(path.name):
                if _linked(path):
                    raise OSError('Unsafe gallery file')
                metadata = path.stat(follow_symlinks=False)
                if stat.S_ISREG(metadata.st_mode):
                    size += metadata.st_size
        return size

    def _require_physical_quota(self, filename, additional):
        previous = self.directory / filename
        old_bytes = previous.stat(follow_symlinks=False).st_size if previous.exists() and not _linked(previous) else 0
        if self._physical_bytes() - old_bytes + additional > self.max_bytes:
            raise OSError('Gallery physical byte quota reached')

    def _write_atomic(self, filename, payload):
        self._prepare_directory()
        target = self.directory / filename
        if _linked(target) or (target.exists() and not target.is_file()):
            raise OSError('Unsafe gallery destination')
        self._require_physical_quota(filename, len(payload))
        temporary = self.directory / (filename + '.' + uuid.uuid4().hex + '.tmp')
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0)
        try:
            descriptor = os.open(temporary, flags, 0o600)
            with os.fdopen(descriptor, 'wb') as handle:
                handle.write(payload)
            os.replace(temporary, target)
        finally:
            try:
                temporary.unlink()
            except OSError:
                pass

    def _save_manifest(self):
        self._prepare_directory()
        with self._lock:
            self._prune_locked()
            self._quota_locked()
            payload, generation = self._manifest_locked(), self._generation
            size = sum(row['_disk_bytes'] for row in self._entries) + len(payload)
        self._delete_orphans()
        if size > self.max_bytes or len(payload) > MAX_MANIFEST_BYTES:
            raise OSError('Gallery byte quota reached')
        self._require_space(len(payload))
        self._write_atomic('manifest.json', payload)
        with self._lock:
            if generation == self._generation:
                self._dirty = False

    def _process(self, identifier):
        with self._lock:
            row = self._find_locked(identifier)
            if row is None:
                return
            self._active_id = identifier
            ppm = row['_ppm']
        try:
            self._prepare_directory()
            self._require_space(0)
            if ppm is not None:
                compressed = gzip.compress(ppm, compresslevel=1, mtime=0)
                with self._lock:
                    row['_file'] = identifier + '.ppm.gz'
                    row['_disk_bytes'] = len(compressed)
                    row['_persisting'] = True
                    self._changed_locked()
                    self._quota_locked()
                    prospective = sum(old['_disk_bytes'] for old in self._entries) + len(self._manifest_locked())
                    if prospective > self.max_bytes:
                        raise OSError('Preview exceeds gallery quota')
                self._delete_orphans()
                self._require_space(len(compressed) + MAX_MANIFEST_BYTES)
                self._write_atomic(row['_file'], compressed)
                with self._lock:
                    self._owned_files.add(row['_file'])
            self._save_manifest()
            if ppm is not None:
                with self._lock:
                    row['state'] = 'Guardada'
                    row['_ppm'] = None
        except OSError as error:
            with self._lock:
                if ppm is not None:
                    row['state'] = 'En memoria: poco espacio' if isinstance(error, _LowSpace) else 'En memoria: no se pudo guardar'
                    if row['_file'] not in self._owned_files:
                        row['_file'], row['_disk_bytes'] = None, 0
                    self._changed_locked()
        finally:
            with self._lock:
                row.pop('_persisting', None)
                self._active_id = None

    def _run(self):
        while not self._stop.is_set() or not self._queue.empty():
            try:
                identifier = self._queue.get(timeout=0.2)
            except queue.Empty:
                identifier = None
            if identifier is not None:
                try:
                    self._process(identifier)
                except Exception:
                    # A malformed local artifact or failed device cannot affect video.
                    with self._lock:
                        row = self._find_locked(identifier)
                        if row is not None and row['_ppm'] is not None:
                            row['state'] = 'En memoria: no se pudo guardar'
                        self._active_id = None
                finally:
                    self._queue.task_done()
            else:
                with self._lock:
                    self._prune_locked()
                    dirty = self._dirty
                if dirty:
                    try:
                        self._save_manifest()
                    except (OSError, ValueError):
                        pass
        try:
            self._save_manifest()
        except (OSError, ValueError):
            pass
