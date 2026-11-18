"""Bounded body/face selection contracts with deterministic detector stubs."""
import math
import unittest
from unittest.mock import patch

from vox_cctv_selection import Detection, FrameAnalysis, FrameSelector, crop_ppm


class Plane:
    def __init__(self, raw, line_size):
        self.raw = raw
        self.line_size = line_size

    def __bytes__(self):
        return self.raw


class Frame:
    def __init__(self, width=1280, height=720, value=91):
        self.width, self.height, self.value = width, height, value
        self.reformats = []

    def reformat(self, *, width=None, height=None, format):
        width, height = width or self.width, height or self.height
        self.reformats.append((width, height, format))
        result = Frame(width, height, self.value)
        row = bytes([self.value]) * (width * 3)
        result.planes = [Plane((row + b'xx') * height, width * 3 + 2)]
        return result


class Backend:
    def __init__(self, analyses):
        self.analyses = iter(analyses)
        self.calls = []

    def analyze(self, frame, max_width):
        self.calls.append((frame, max_width))
        return next(self.analyses)


def face(bbox=(100, 60, 50, 50), *, sharpness=100, luminance=120,
         contrast=35, detector='opencv_haar_frontal'):
    return Detection('face', bbox, sharpness, luminance, contrast, detector)


def body(bbox=(80, 20, 100, 250), *, sharpness=100, luminance=120,
         contrast=35):
    return Detection('body', bbox, sharpness, luminance, contrast,
                     'opencv_hog_persona')


class SelectionContracts(unittest.TestCase):
    def test_selection_keeps_original_size_and_separate_best_frame_references(self):
        first, second = Frame(value=41), Frame(value=93)
        backend = Backend([FrameAnalysis(640, 360, [body(), face(sharpness=35)]),
                           FrameAnalysis(640, 360, [face(sharpness=200)])])
        selector = FrameSelector(backend=backend)
        self.assertTrue(selector.consider(first, 10))
        self.assertTrue(selector.consider(second, 11))
        self.assertEqual(first.reformats, [])
        self.assertEqual(second.reformats, [])
        result = selector.finalize()
        by_kind = {row['selection']: row for row in result['candidates']}
        self.assertEqual(len(by_kind), 2)
        self.assertEqual(by_kind['cuerpo_detectado']['timestamp'], 10)
        self.assertEqual(by_kind['rostro_detectado']['timestamp'], 11)
        self.assertEqual(by_kind['cuerpo_detectado']['bbox'], (160, 40, 200, 500))
        self.assertEqual(by_kind['rostro_detectado']['bbox'], (200, 120, 100, 100))
        self.assertEqual(by_kind['rostro_detectado']['width'], 1280)
        self.assertEqual(by_kind['rostro_detectado']['height'], 720)
        self.assertTrue(by_kind['rostro_detectado']['ppm'].startswith(b'P6\n1280 720\n255\n'))
        self.assertEqual(by_kind['rostro_detectado']['ppm'].split(b'\n', 3)[3], bytes([93]) * (1280 * 720 * 3))
        self.assertEqual(second.reformats, [(1280, 720, 'rgb24')])
        self.assertFalse(hasattr(selector, 'frames'))

    def test_coordinates_are_clamped_and_border_body_not_claimed_clear(self):
        backend = Backend([FrameAnalysis(640, 360, [
            body(bbox=(-5, 4, 100, 250)), face(bbox=(-8, 10, 56, 55))])])
        selector = FrameSelector(backend=backend)
        selector.consider(Frame(), 5)
        result = {row['selection']: row for row in selector.finalize()['candidates']}
        self.assertEqual(result['rostro_detectado']['bbox'], (0, 20, 96, 110))
        self.assertFalse(result['cuerpo_detectado']['body_boundary_clear'])
        self.assertNotIn('complete_body', result['cuerpo_detectado'])

    def test_bad_lighting_blur_and_small_faces_produce_no_face(self):
        rejected = [face(luminance=10), face(luminance=247),
                    face(sharpness=12), face(contrast=4),
                    face(bbox=(50, 20, 29, 40)),
                    face(bbox=(50, 20, 15, 40))]
        selector = FrameSelector(backend=Backend([FrameAnalysis(640, 360, rejected)]))
        selector.consider(Frame(), 1)
        result = selector.finalize()
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['face_status'], 'sin_rostro_con_calidad_suficiente')

    def test_minimum_face_size_is_checked_in_original_and_analysis_pixels(self):
        selector = FrameSelector(backend=Backend([FrameAnalysis(640, 360,
            [face(bbox=(50, 20, 20, 35))])]))
        selector.consider(Frame(2560, 1440), 1)
        self.assertEqual(selector.finalize()['candidates'], [])

    def test_no_detections_do_not_become_body_or_face_from_generic_scene(self):
        selector = FrameSelector(backend=Backend([FrameAnalysis(640, 360, [])]))
        selector.consider(Frame(), 1)
        result = selector.finalize()
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['body_status'], 'sin_cuerpo_con_calidad_suficiente')

    def test_sample_interval_and_twenty_candidate_hard_limit(self):
        backend = Backend([FrameAnalysis(640, 360, []) for _ in range(20)])
        selector = FrameSelector(backend=backend, max_candidates=1000,
                                 sample_interval=.01)
        frame = Frame()
        for number in range(100):
            selector.consider(frame, number / 2)
        self.assertEqual(len(backend.calls), 20)
        self.assertTrue(all(width <= 640 for _, width in backend.calls))
        self.assertEqual(selector.finalize()['considered'], 20)

    def test_invalid_boxes_and_nonfinite_quality_are_rejected(self):
        rows = [face(bbox=(math.nan, 2, 100, 100)),
                face(bbox=(5000, 2, 100, 100)),
                face(bbox=(20, 2, -1, 100)),
                face(sharpness=math.inf),
                Detection('face', (100, 60, 50, 50), 100, 120, 35, 'invented_identity')]
        selector = FrameSelector(backend=Backend([FrameAnalysis(640, 360, rows)]))
        selector.consider(Frame(), 1)
        self.assertEqual(selector.finalize()['candidates'], [])

    def test_disabled_and_missing_dependencies_do_not_affect_original_frames(self):
        frame = Frame()
        with patch('vox_cctv_selection._get_backend', side_effect=ImportError('optional dependency')) as loader:
            disabled = FrameSelector(enabled=False)
            self.assertFalse(disabled.consider(frame, 1))
            loader.assert_not_called()
            selector = FrameSelector()
            self.assertFalse(selector.consider(frame, 1))
            self.assertFalse(selector.consider(frame, 2))
            self.assertEqual(loader.call_count, 1)
        self.assertEqual(frame.reformats, [])
        self.assertEqual(selector.finalize()['detector_status'], 'no_disponible')
        self.assertEqual(selector.finalize()['candidates'], [])

    def test_crop_is_only_original_pixels_and_padding_was_excluded(self):
        pixels = bytes(range(1, 19))
        original = b'P6\n3 2\n255\n' + pixels
        self.assertEqual(crop_ppm(original, (1, 0, 2, 2)),
                         b'P6\n2 2\n255\n' + pixels[3:9] + pixels[12:18])
        self.assertEqual(original, b'P6\n3 2\n255\n' + pixels)
        with self.assertRaises(ValueError):
            crop_ppm(original, (-1, 0, 2, 2))
        with self.assertRaises(ValueError):
            crop_ppm(original[:-1], (1, 0, 2, 2))


if __name__ == '__main__':
    unittest.main()
