"""Optional, bounded body/face frame selection from original decoded video.

Run ``consider`` only in the sequence finalizer, never in the live decoder or
Tk thread. OpenCV/numpy and their bundled models load on the first eligible
sample. HOG and Haar detections can be wrong or absent; they neither establish
identity nor infer intent. No image enhancement or reconstruction occurs.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
import threading


MAX_CANDIDATES = 20
MAX_ANALYSIS_SIDE = 640
MAX_PPM_BYTES = 12 * 1024 * 1024
MAX_DETECTIONS = 32
_HEADER = re.compile(br'P6\n([1-9][0-9]{0,3}) ([1-9][0-9]{0,3})\n255\n')
_DETECTORS = {'body': frozenset(('opencv_hog_persona',)),
              'face': frozenset(('opencv_haar_frontal', 'opencv_haar_perfil'))}


@dataclass(frozen=True, slots=True)
class Detection:
    """One detector box in analysis pixels; quality is measured on that box."""
    kind: str
    bbox: tuple
    sharpness: float
    luminance: float
    contrast: float
    detector: str


@dataclass(frozen=True, slots=True)
class FrameAnalysis:
    width: int
    height: int
    detections: tuple | list


@dataclass(slots=True)
class _Choice:
    frame: object
    timestamp: float
    bbox: tuple
    quality: dict
    detector: str
    boundary_clear: bool
    rank: tuple


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _dimensions(frame):
    width, height = getattr(frame, 'width', None), getattr(frame, 'height', None)
    if (type(width) is not int or type(height) is not int or
            not 1 <= width <= 4096 or not 1 <= height <= 4096 or
            width * height * 3 + 32 > MAX_PPM_BYTES):
        raise ValueError('Original frame exceeds the evidence limit')
    return width, height


def _rgb_pixels(frame):
    width, height = _dimensions(frame)
    plane = frame.planes[0]
    raw, stride = bytes(plane), plane.line_size
    row_bytes = width * 3
    if type(stride) is not int or stride < row_bytes or len(raw) < stride * height:
        raise ValueError('Invalid RGB plane')
    return b''.join(raw[row * stride:row * stride + row_bytes]
                    for row in range(height))


def _original_ppm(frame):
    width, height = _dimensions(frame)
    rgb = frame.reformat(width=width, height=height, format='rgb24')
    if (rgb.width, rgb.height) != (width, height):
        raise ValueError('Original frame size changed')
    return f'P6\n{width} {height}\n255\n'.encode('ascii') + _rgb_pixels(rgb)


def crop_ppm(ppm, bbox):
    """Extract an unscaled RGB pixel rectangle; leave the original untouched."""
    if not isinstance(ppm, bytes) or len(ppm) > MAX_PPM_BYTES:
        raise ValueError('Invalid original PPM')
    header = _HEADER.match(ppm)
    if header is None:
        raise ValueError('Invalid original PPM header')
    width, height = int(header[1]), int(header[2])
    if width > 4096 or height > 4096 or len(ppm) != header.end() + width * height * 3:
        raise ValueError('Invalid original PPM dimensions')
    if not isinstance(bbox, (tuple, list)) or len(bbox) != 4 or any(type(value) is not int for value in bbox):
        raise ValueError('Invalid crop rectangle')
    x, y, box_width, box_height = bbox
    if min(x, y) < 0 or min(box_width, box_height) < 1 or x + box_width > width or y + box_height > height:
        raise ValueError('Crop rectangle is outside the original')
    pixels = memoryview(ppm)[header.end():]
    rows = [pixels[(row * width + x) * 3:(row * width + x + box_width) * 3]
            for row in range(y, y + box_height)]
    return f'P6\n{box_width} {box_height}\n255\n'.encode('ascii') + b''.join(rows)


def _mapped_box(bbox, source_width, source_height, analysis_width, analysis_height):
    if (not isinstance(bbox, (tuple, list)) or len(bbox) != 4 or
            not all(_number(value) for value in bbox)):
        return None
    x, y, width, height = bbox
    if width <= 0 or height <= 0:
        return None
    # Clamp in analysis coordinates before converting, so edge crops cannot
    # address pixels outside the source even when a detector adds padding.
    left, top = max(0, x), max(0, y)
    right, bottom = min(analysis_width, x + width), min(analysis_height, y + height)
    if right <= left or bottom <= top:
        return None
    source_left = max(0, math.floor(left * source_width / analysis_width))
    source_top = max(0, math.floor(top * source_height / analysis_height))
    source_right = min(source_width, math.ceil(right * source_width / analysis_width))
    source_bottom = min(source_height, math.ceil(bottom * source_height / analysis_height))
    return ((source_left, source_top, source_right - source_left, source_bottom - source_top),
            (right - left, bottom - top))


class _OpenCVBackend:
    def __init__(self):
        # Optional packages are deliberately absent from module-level imports.
        import cv2
        import numpy
        cv2.setNumThreads(1)
        self.cv2, self.numpy = cv2, numpy
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        models = Path(cv2.data.haarcascades)
        self.frontal = cv2.CascadeClassifier(str(models / 'haarcascade_frontalface_default.xml'))
        self.profile = cv2.CascadeClassifier(str(models / 'haarcascade_profileface.xml'))
        if self.frontal.empty() or self.profile.empty():
            raise RuntimeError('Bundled face detector is unavailable')
        self._lock = threading.Lock()

    def _detection(self, gray, kind, rectangle, detector):
        x, y, width, height = map(int, rectangle)
        left, top = max(0, x), max(0, y)
        right, bottom = min(gray.shape[1], x + width), min(gray.shape[0], y + height)
        region = gray[top:bottom, left:right]
        if region.size < 4 or right <= left or bottom <= top:
            return None
        sharpness = float(self.cv2.Laplacian(region, self.cv2.CV_32F).var())
        return Detection(kind, (x, y, width, height), sharpness,
                         float(region.mean()), float(region.std()), detector)

    def analyze(self, frame, max_width):
        width, height = _dimensions(frame)
        ratio = min(max_width / width, MAX_ANALYSIS_SIDE / height, 1.0)
        small_width, small_height = max(1, int(width * ratio)), max(1, int(height * ratio))
        rgb = frame.reformat(width=small_width, height=small_height, format='rgb24')
        pixels = self.numpy.frombuffer(_rgb_pixels(rgb), dtype=self.numpy.uint8)
        rgb_array = pixels.reshape(small_height, small_width, 3)
        gray = self.cv2.cvtColor(rgb_array, self.cv2.COLOR_RGB2GRAY)
        detections = []
        # Model instances are shared across episodes. The sequence finalizer
        # normally has one worker; this lock also bounds accidental concurrency.
        with self._lock:
            if small_width >= 64 and small_height >= 128:
                boxes, _weights = self.hog.detectMultiScale(
                    rgb_array, hitThreshold=.6, winStride=(8, 8),
                    padding=(8, 8), scale=1.10)
                for box in sorted(boxes, key=lambda box: int(box[2]) * int(box[3]), reverse=True)[:8]:
                    detection = self._detection(gray, 'body', box, 'opencv_hog_persona')
                    if detection is not None:
                        detections.append(detection)
            for model, label, flipped in ((self.frontal, 'opencv_haar_frontal', False),
                                          (self.profile, 'opencv_haar_perfil', False),
                                          (self.profile, 'opencv_haar_perfil', True)):
                inspected = self.cv2.flip(gray, 1) if flipped else gray
                boxes = model.detectMultiScale(inspected, scaleFactor=1.1,
                                               minNeighbors=5, minSize=(24, 24))
                for box in sorted(boxes, key=lambda box: int(box[2]) * int(box[3]), reverse=True)[:8]:
                    x, y, box_width, box_height = map(int, box)
                    if flipped:
                        x = small_width - x - box_width
                    detection = self._detection(gray, 'face', (x, y, box_width, box_height), label)
                    if detection is not None:
                        detections.append(detection)
        return FrameAnalysis(small_width, small_height, detections)


_BACKEND_LOCK = threading.Lock()
_BACKEND = None
_BACKEND_ERROR = None


def _get_backend():
    global _BACKEND, _BACKEND_ERROR
    with _BACKEND_LOCK:
        if _BACKEND_ERROR is not None:
            raise RuntimeError('Optional detectors are unavailable')
        if _BACKEND is None:
            try:
                _BACKEND = _OpenCVBackend()
            except Exception as error:
                _BACKEND_ERROR = type(error).__name__
                raise
        return _BACKEND


class FrameSelector:
    """Keep at most two original AV-frame references and inspect <=20 samples.

    ``timestamp`` is the monotonic receipt time used by the sequence manager.
    Quality thresholds deliberately leave an unavailable result for dark,
    blurred or too-small detections. Scores rank image usefulness; they are
    neither model confidence nor probabilities of identity or body completeness.
    """
    def __init__(self, *, enabled=True, sample_interval=1.0, max_candidates=20,
                 min_face_pixels=60, backend=None):
        if type(enabled) is not bool:
            raise TypeError('enabled must be boolean')
        self.enabled = enabled
        interval = float(sample_interval)
        self.sample_interval = max(1.0, min(2.0, interval)) if math.isfinite(interval) else 1.0
        self.max_candidates = max(1, min(MAX_CANDIDATES, int(max_candidates)))
        self.min_face_pixels = max(60, min(256, int(min_face_pixels)))
        self._backend = backend
        self._last_sample = None
        self._best = {'body': None, 'face': None}
        self._considered = 0
        self._result = None
        self._status = 'pendiente' if enabled else 'desactivado'
        self._error_kind = None

    def consider(self, av_frame, timestamp):
        if (not self.enabled or self._result is not None or self._status == 'no_disponible' or
                not _number(timestamp) or timestamp < 0 or self._considered >= self.max_candidates or
                (self._last_sample is not None and timestamp - self._last_sample < self.sample_interval)):
            return False
        try:
            width, height = _dimensions(av_frame)
        except (ValueError, TypeError, AttributeError):
            return False
        self._last_sample = timestamp
        self._considered += 1
        try:
            if self._backend is None:
                self._backend = _get_backend()
            analysis = self._backend.analyze(av_frame, MAX_ANALYSIS_SIDE)
            if (type(analysis.width) is not int or type(analysis.height) is not int or
                    not 1 <= analysis.width <= MAX_ANALYSIS_SIDE or
                    not 1 <= analysis.height <= MAX_ANALYSIS_SIDE or
                    not isinstance(analysis.detections, (tuple, list))):
                raise ValueError('Invalid detector analysis')
            self._status = 'disponible'
        except Exception as error:
            self._status, self._error_kind = 'no_disponible', type(error).__name__
            self._backend = None
            return False
        for detection in analysis.detections[:MAX_DETECTIONS]:
            if (not isinstance(detection, Detection) or type(detection.kind) is not str or
                    type(detection.detector) is not str or detection.kind not in _DETECTORS or
                    detection.detector not in _DETECTORS[detection.kind] or
                    not all(_number(value) for value in
                            (detection.sharpness, detection.luminance, detection.contrast))):
                continue
            mapped = _mapped_box(detection.bbox, width, height, analysis.width, analysis.height)
            if mapped is None:
                continue
            bbox, analysis_size = mapped
            sharpness, light, contrast = detection.sharpness, detection.luminance, detection.contrast
            if detection.kind == 'face':
                if (min(bbox[2:]) < self.min_face_pixels or min(analysis_size) < 24 or
                        sharpness < 25 or not 35 <= light <= 225 or contrast < 10):
                    continue
            elif (analysis_size[0] < 32 or analysis_size[1] < 64 or
                  sharpness < 10 or not 20 <= light <= 235 or contrast < 8):
                continue
            x, y, box_width, box_height = bbox
            margin_x, margin_y = max(2, int(width * .02)), max(2, int(height * .02))
            clear = (x >= margin_x and y >= margin_y and
                     x + box_width <= width - margin_x and y + box_height <= height - margin_y)
            area = box_width * box_height / (width * height)
            score = (min(sharpness, 500) / 500 * .50 + min(contrast, 80) / 80 * .20 +
                     max(0.0, 1 - abs(light - 128) / 128) * .15 + math.sqrt(area) * .15)
            rank = (int(clear) if detection.kind == 'body' else 0, score)
            previous = self._best[detection.kind]
            if previous is None or rank > previous.rank:
                quality = {'sharpness': round(sharpness, 3), 'luminance': round(light, 3),
                           'contrast': round(contrast, 3), 'score': round(score, 5)}
                self._best[detection.kind] = _Choice(av_frame, timestamp, bbox, quality,
                                                    detection.detector, clear, rank)
        return True

    def finalize(self):
        """Convert only selected originals to PPM and release AV-frame references."""
        if self._result is not None:
            return self._result
        result = {'candidates': [], 'body_status': 'sin_cuerpo_con_calidad_suficiente',
                  'face_status': 'sin_rostro_con_calidad_suficiente',
                  'detector_status': self._status, 'considered': self._considered}
        if self._error_kind is not None:
            result['detector_error_kind'] = self._error_kind
        originals = {}
        for kind, selection in (('body', 'cuerpo_detectado'), ('face', 'rostro_detectado')):
            choice = self._best[kind]
            if choice is None:
                if self._status in ('desactivado', 'no_disponible', 'pendiente'):
                    result[kind + '_status'] = self._status
                continue
            try:
                frame_key = id(choice.frame)
                if frame_key not in originals:
                    originals[frame_key] = _original_ppm(choice.frame)
                width, height = _dimensions(choice.frame)
                row = {'ppm': originals[frame_key], 'width': width, 'height': height,
                       'timestamp': choice.timestamp, 'selection': selection,
                       'bbox': choice.bbox, 'quality': dict(choice.quality),
                       'detector': choice.detector}
                if kind == 'body':
                    row['body_boundary_clear'] = choice.boundary_clear
                result['candidates'].append(row)
                result[kind + '_status'] = 'disponible'
            except Exception:
                result[kind + '_status'] = 'fotograma_no_disponible'
        self._best = {'body': None, 'face': None}
        self._result = result
        return result
