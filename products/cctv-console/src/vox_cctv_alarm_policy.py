"""Local presentation and sound policy; no image analysis or device changes."""
from collections import deque
from datetime import datetime
import json
import math
import os
from pathlib import Path
import tempfile
import threading


DETECTIONS = frozenset(('HumanDetect', 'appEventHumanDetectAlarm', 'CarShapeDetect'))
ACTIVITY = frozenset(('VideoMotion', 'MotionDetect', 'FaceDetection', 'FaceDetect',
                      'IPCAlarm', 'VideoAnalyze', 'VIdeoAnanyze'))
STORAGE = frozenset(('StorageNotExist', 'StorageLowSpace', 'StorrageLowSpace',
                     'StorageFailureWrite', 'StorageFailureRead', 'StorageReadError'))
LOSS = frozenset(('VideoLoss', 'LossDetect'))
TECHNICAL = STORAGE | LOSS | frozenset(('VideoBlind', 'BlindDetect', 'Blind',
                                       'NetIPConfict', 'NetAbort'))
GROUPS = {'detections': DETECTIONS, 'activity': ACTIVITY, 'technical': TECHNICAL}
PREFERENCE_KEYS = frozenset(('sound_enabled', 'rain_mode', 'technical_sound'))


def _safe(event):
    if not isinstance(event, dict):
        return None
    kind = event.get('event')
    if not isinstance(kind, str) or kind not in DETECTIONS | ACTIVITY | TECHNICAL:
        return None
    channel = event.get('channel')
    if not (type(channel) is int and 1 <= channel <= 7):
        if channel is not None or kind not in TECHNICAL:
            return None
    status = event.get('status')
    if not isinstance(status, str) or status not in ('Start', 'Stop', 'None'):
        return None
    stamp = event.get('time')
    if isinstance(stamp, str) and len(stamp) == 19:
        try:
            datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            stamp = None
    else:
        stamp = None
    return {'channel': channel, 'event': kind, 'status': status, 'time': stamp}


def _valid_now(now):
    return type(now) in (int, float) and math.isfinite(now)


class AlarmPolicy:
    """Bounded episodes and immediate sound decisions on sanitised event fields.

    ``now`` is a monotonic time, independent of the recorder's display timestamp.
    Rain mode only lengthens aggregation and sound intervals; it cannot identify
    rain or decide whether a detector's person/vehicle classification is correct.
    """
    def __init__(self, sound_enabled=True, rain_mode=False, technical_sound=False):
        self._lock = threading.RLock()
        self._history = {group: deque(maxlen=25) for group in GROUPS}
        self._last_sound = {}
        self._last_report = {}
        self.configure(sound_enabled=sound_enabled, rain_mode=rain_mode,
                       technical_sound=technical_sound)

    def configure(self, *, sound_enabled=None, rain_mode=None, technical_sound=None):
        updates = {'sound_enabled': sound_enabled, 'rain_mode': rain_mode,
                   'technical_sound': technical_sound}
        for value in updates.values():
            if value is not None and type(value) is not bool:
                raise TypeError('Alarm preferences must be booleans')
        with self._lock:
            for key, value in updates.items():
                if value is not None:
                    setattr(self, key, value)

    def preferences(self):
        with self._lock:
            return {key: getattr(self, key) for key in sorted(PREFERENCE_KEYS)}

    def new_subscription(self):
        """Forget stale report transitions after a confirmed new subscription.

        A Stop can be lost on disconnect. Histories, preferences and sound
        intervals survive reconnection, so reconnects cannot bypass throttling.
        """
        with self._lock:
            self._last_report.clear()

    def add(self, event, now):
        event = _safe(event)
        if event is None or not _valid_now(now):
            return False
        group = next(group for group, kinds in GROUPS.items() if event['event'] in kinds)
        key = (event['channel'], event['event'])
        with self._lock:
            history = self._history[group]
            existing = next((item for item in history
                             if (item['channel'], item['event']) == key), None)
            interval = 120 if self.rain_mode else 30
            # A delayed Stop closes the latest known episode instead of creating
            # a separate apparent detection. Starts after silence begin anew.
            merge = existing is not None and (event['status'] == 'Stop' or
                                             0 <= now - existing['_seen_at'] < interval)
            if merge:
                history.remove(existing)
                existing.update(status=event['status'], time=event['time'],
                                last_time=event['time'], _seen_at=now)
                if event['status'] != 'Stop':
                    existing['count'] += 1
                history.appendleft(existing)
            else:
                history.appendleft(dict(event, first_time=event['time'],
                                        last_time=event['time'],
                                        count=0 if event['status'] == 'Stop' else 1,
                                        _seen_at=now))
        return True

    def grouped(self, group):
        with self._lock:
            return [{key: value for key, value in item.items() if key != '_seen_at'}
                    for item in self._history[group]]

    def notify(self, event, now):
        """Decide sound immediately; muted events are consumed, never queued."""
        event = _safe(event)
        if event is None or not _valid_now(now):
            return False
        key = (event['channel'], event['event'])
        report = (event['status'], event['time'])
        with self._lock:
            if self._last_report.get(key) == report:
                return False
            self._last_report[key] = report
            audible = ((event['event'] in DETECTIONS and event['status'] == 'Start') or
                       (event['event'] in STORAGE and event['status'] in ('Start', 'None')) or
                       (self.technical_sound and event['event'] in LOSS and
                        event['status'] == 'Start'))
            interval = 120 if self.rain_mode else 30
            if not self.sound_enabled or not audible or now - self._last_sound.get(key, float('-inf')) < interval:
                return False
            self._last_sound[key] = now
            return True

    def save(self, path):
        """Atomically save only three owner preferences; write errors propagate."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                             dir=path.parent, prefix=path.name + '.',
                                             suffix='.tmp', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(self.preferences(), handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, path):
        """Absent, unreadable or malformed preferences use constructor defaults."""
        try:
            with Path(path).open('rb') as handle:
                raw = handle.read(4097)
            if len(raw) > 4096:
                return cls()
            prefs = json.loads(raw.decode('utf-8'))
            if not isinstance(prefs, dict) or set(prefs) != PREFERENCE_KEYS:
                return cls()
            if any(type(value) is not bool for value in prefs.values()):
                return cls()
            return cls(**prefs)
        except (OSError, UnicodeError, ValueError):
            return cls()
