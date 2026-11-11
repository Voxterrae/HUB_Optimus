import tempfile
import threading
import gzip
import random
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import vox_cctv_viewer as viewer
from vox_cctv_evidence import EvidenceStore

def ppm(width, height):
    return f'P6\n{width} {height}\n255\n'.encode() + b'\x30\x60\x90' * (width * height)

class CaptureFixContracts(unittest.TestCase):
    def test_failed_old_image_delete_does_not_exceed_physical_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EvidenceStore(directory, max_bytes=5000, min_free_bytes=0)
            pixels = random.Random(7).randbytes(3000)
            capture = dict(ppm=b'P6\n100 10\n255\n'+pixels,width=100,height=10,
                source_width=100,source_height=10,stream='Main',frame_age_seconds=0)
            event = dict(channel=1,event='HumanDetect',status='Start')
            self.assertTrue(store.add(event,capture))
            store.close()
            store = EvidenceStore(directory, max_bytes=5000, min_free_bytes=0)
            original_unlink=Path.unlink
            old_file=next(Path(directory).glob('*.ppm.gz'))
            def locked(path,*args,**kwargs):
                if path==old_file: raise PermissionError('locked')
                return original_unlink(path,*args,**kwargs)
            with patch.object(Path,'unlink',locked):
                self.assertTrue(store.add(event,capture))
                store.close()
            physical=sum(path.stat().st_size for path in Path(directory).iterdir() if path.is_file())
            self.assertLessEqual(physical,5000)

    def test_restart_orphan_is_accounted_and_cleaned(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/('b'*32+'.ppm.gz')
            path.write_bytes(gzip.compress(ppm(100,10)))
            foreign=Path(directory)/'my-private.txt';foreign.write_text('preserve')
            store=EvidenceStore(directory,min_free_bytes=0)
            store.close()
            self.assertFalse(path.exists())
            self.assertEqual(foreign.read_text(),'preserve')

    def test_mosaic_resizing_never_replaces_source_evidence(self):
        state = viewer.CameraState(0)
        original, thumbnail = ppm(704, 480), ppm(220, 150)
        state.publish_original(original, 704, 480, now=10)
        state.publish(thumbnail, 704, 480, now=10)
        self.assertEqual(state.image()[0], thumbnail)
        capture = state.capture_snapshot(now=11)
        self.assertEqual(capture['ppm'], original)
        self.assertEqual((capture['width'], capture['height']), (704, 480))
        state.reset('Reconectando')
        self.assertIsNone(state.capture_snapshot(now=11))

    def test_camera1440p_has_no1080p_evidence_limit(self):
        state = viewer.CameraState(0)
        state.set_mode('Main')
        original = ppm(2560, 1440)
        state.publish_original(original, 2560, 1440, now=10)
        state.publish(ppm(220, 124), 2560, 1440, now=10)
        self.assertEqual(state.capture_snapshot(now=11)['ppm'], original)

    def test_sequence_age_is_explicit_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EvidenceStore(directory, min_free_bytes=0)
            capture = dict(ppm=ppm(4, 3),width=4,height=3,source_width=4,source_height=3,
                stream='Main',frame_age_seconds=26,sequence_id='a'*32,
                sequence_offset_seconds=-9.3,selection='rostro_detectado',bbox=[1,1,2,2])
            event = dict(channel=1,event='HumanDetect',status='Start',time=None)
            self.assertTrue(store.add(event, capture))
            store.close()
            row = store.list_entries()[0]
            self.assertEqual(store.read_image(row['id']), capture['ppm'])
            self.assertEqual(row['frame_age_seconds'], 26)
            self.assertEqual(row['sequence_offset_seconds'], -9.3)
            self.assertEqual(row['bbox'], [1,1,2,2])
            restored = EvidenceStore(directory, min_free_bytes=0)
            try:
                self.assertEqual(restored.read_image(row['id']), capture['ppm'])
                self.assertEqual(restored.list_entries()[0]['selection'], 'rostro_detectado')
            finally: restored.close()

    def test_production_quota_can_save1440p_original(self):
        with tempfile.TemporaryDirectory() as directory:
            store = EvidenceStore(directory, max_bytes=128*1024*1024,min_free_bytes=0)
            original=ppm(2560,1440)
            self.assertTrue(store.add(dict(channel=1,event='HumanDetect',status='Start'),
                dict(ppm=original,width=2560,height=1440,source_width=2560,
                     source_height=1440,stream='Main',frame_age_seconds=0)))
            store.close()
            row=store.list_entries()[0]
            self.assertEqual(store.read_image(row['id']),original)

if __name__ == '__main__': unittest.main()
