import gzip
import importlib.util
import json
from pathlib import Path
import random
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

if importlib.util.find_spec('vox_cctv_evidence'):
    from vox_cctv_evidence import EvidenceStore
else:
    EvidenceStore = None


def event(camera=1):
    return {'channel': camera, 'event': 'HumanDetect', 'status': 'Start',
        'time': '2026-10-03 22:00:00', 'SessionID': 'must-not-persist', 'PersonName': 'must-not-persist'}


def capture(ppm=b'P6\n2 1\n255\n\x01\x02\x03\x04\x05\x06', width=2, height=1):
    return {'ppm': ppm, 'frame_age_seconds': 0.125, 'width': width, 'height': height,
        'source_width': 1920, 'source_height': 1080, 'stream': 'Extra1'}


def wait_until_saved(store, count=1):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        entries = store.list_entries()
        if len(entries) >= count and all(row['state'] != 'Pendiente' for row in entries):
            return entries
        time.sleep(0.005)
    raise AssertionError('The evidence worker did not finish its bounded queue')


class EvidenceContracts(unittest.TestCase):
    def store(self, directory, **kwargs):
        self.assertIsNotNone(EvidenceStore, 'The bounded evidence store is not implemented')
        result = EvidenceStore(directory, **kwargs)
        self.addCleanup(result.close)
        return result

    def test_photo_survives_restart_with_actual_preview_dimensions_and_safe_metadata(self):
        # A missing image write/restore, or substituting source dimensions, must fail.
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, min_free_bytes=0)
            picture = capture()
            self.assertTrue(store.add(event(), picture))
            store.close()
            entry = store.list_entries()[0]
            self.assertEqual(entry['state'], 'Guardada')
            self.assertEqual((entry['width'], entry['height']), (2, 1))
            self.assertEqual((entry['source_width'], entry['source_height']), (1920, 1080))
            self.assertEqual(entry['frame_age_seconds'], 0.125)
            self.assertEqual(entry['device_time'], '2026-10-03 22:00:00')
            self.assertEqual(set(entry), {'id', 'event', 'camera', 'received_at', 'device_time',
                'frame_age_seconds', 'width', 'height', 'source_width', 'source_height', 'stream', 'state'})
            restored = self.store(directory, min_free_bytes=0)
            self.assertEqual(restored.read_image(entry['id']), b'P6\n2 1\n255\n\x01\x02\x03\x04\x05\x06')
            self.assertEqual(restored.list_entries()[0]['id'], entry['id'])
            manifest = (Path(directory) / 'manifest.json').read_text()
            self.assertNotIn('must-not-persist', manifest)
            self.assertNotIn('ppm', json.dumps(entry))
            copied = restored.list_entries()
            copied[0]['camera'] = 7
            self.assertEqual(restored.list_entries()[0]['camera'], 1)

    def test_event_without_a_fresh_picture_is_visible_without_an_invented_photo(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, min_free_bytes=0)
            self.assertTrue(store.add(event(), None))
            store.close()
            entry = store.list_entries()[0]
            self.assertEqual(entry['state'], 'Sin imagen reciente')
            self.assertIsNone(store.read_image(entry['id']))
            self.assertIsNone(entry['width'])
            restored = self.store(directory, min_free_bytes=0)
            self.assertEqual(restored.list_entries()[0]['state'], 'Sin imagen reciente')

    def test_low_disk_space_keeps_the_image_in_bounded_memory_without_writing(self):
        # A real threshold larger than any local volume exercises the disk branch.
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, min_free_bytes=2 ** 63)
            self.assertTrue(store.add(event(), capture()))
            store.close()
            entry = store.list_entries()[0]
            self.assertEqual(entry['state'], 'En memoria: poco espacio')
            self.assertEqual(store.read_image(entry['id']), b'P6\n2 1\n255\n\x01\x02\x03\x04\x05\x06')
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_count_quota_removes_only_the_oldest_owned_image(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            foreign = folder / 'someone-elses.ppm.gz'
            foreign.write_bytes(b'do not delete')
            store = self.store(directory, max_count=2, min_free_bytes=0)
            self.assertTrue(store.add(event(1), capture()))
            first = wait_until_saved(store)[0]['id']
            self.assertTrue(store.add(event(2), capture()))
            wait_until_saved(store, 2)
            self.assertTrue(store.add(event(3), capture()))
            store.close()
            self.assertEqual([row['camera'] for row in store.list_entries()], [3, 2])
            self.assertFalse((folder / (first + '.ppm.gz')).exists())
            self.assertEqual(foreign.read_bytes(), b'do not delete')
            restored = self.store(directory, max_count=2, min_free_bytes=0)
            self.assertEqual([row['camera'] for row in restored.list_entries()], [3, 2])

    def test_byte_quota_includes_images_and_the_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            pixels = random.Random(31).randbytes(3000)
            picture = capture(b'P6\n100 10\n255\n' + pixels, 100, 10)
            store = self.store(directory, max_bytes=5000, min_free_bytes=0)
            self.assertTrue(store.add(event(1), picture))
            wait_until_saved(store)
            self.assertTrue(store.add(event(2), picture))
            store.close()
            self.assertEqual([row['camera'] for row in store.list_entries()], [2])
            owned = [file for file in Path(directory).iterdir() if file.name == 'manifest.json' or file.suffix == '.gz']
            self.assertLessEqual(sum(file.stat().st_size for file in owned), 5000)

    def test_expired_entries_and_their_owned_images_are_removed_on_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, min_free_bytes=0)
            self.assertTrue(store.add(event(), capture()))
            store.close()
            identifier = store.list_entries()[0]['id']
            manifest_path = Path(directory) / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['entries'][0]['received_at'] = '2000-01-01T00:00:00+00:00'
            manifest_path.write_text(json.dumps(manifest))
            foreign = Path(directory) / 'foreign.txt'
            foreign.write_text('keep')
            restored = self.store(directory, min_free_bytes=0)
            restored.close()
            self.assertEqual(restored.list_entries(), [])
            self.assertFalse((Path(directory) / (identifier + '.ppm.gz')).exists())
            self.assertEqual(foreign.read_text(), 'keep')

    def test_a_failed_directory_write_preserves_the_picture_and_cannot_break_the_caller(self):
        with tempfile.TemporaryDirectory() as directory:
            blocked = Path(directory) / 'a-file-not-a-directory'
            blocked.write_bytes(b'keep')
            store = self.store(blocked, min_free_bytes=0)
            self.assertTrue(store.add(event(), capture()))
            store.close()
            entry = store.list_entries()[0]
            self.assertEqual(entry['state'], 'En memoria: no se pudo guardar')
            self.assertEqual(store.read_image(entry['id']), b'P6\n2 1\n255\n\x01\x02\x03\x04\x05\x06')
            self.assertEqual(blocked.read_bytes(), b'keep')

    def test_unsafe_manifest_paths_and_reader_ids_never_escape_the_gallery(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'gallery'
            store = self.store(folder, min_free_bytes=0)
            self.assertTrue(store.add(event(), capture()))
            store.close()
            outside = Path(directory) / 'outside.ppm.gz'
            foreign_payload = gzip.compress(b'P6\n1 1\n255\n\xff\xff\xff')
            outside.write_bytes(foreign_payload)
            manifest_path = folder / 'manifest.json'
            manifest = json.loads(manifest_path.read_text())
            identifier = manifest['entries'][0]['id']
            manifest['entries'][0]['image_file'] = '../outside.ppm.gz'
            manifest_path.write_text(json.dumps(manifest))
            restored = self.store(folder, min_free_bytes=0)
            self.assertIsNone(restored.read_image(identifier))
            self.assertIsNone(restored.read_image('../outside'))
            self.assertEqual(outside.read_bytes(), foreign_payload)
            self.assertTrue(outside.exists())

    def test_symlink_image_is_not_followed_even_when_its_target_is_valid_ppm(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'gallery'
            store = self.store(folder, min_free_bytes=0)
            self.assertTrue(store.add(event(), capture()))
            store.close()
            identifier = store.list_entries()[0]['id']
            picture_file = folder / (identifier + '.ppm.gz')
            outside = Path(directory) / 'outside.ppm.gz'
            outside.write_bytes(gzip.compress(b'P6\n1 1\n255\n\xff\xff\xff'))
            picture_file.unlink()
            try:
                picture_file.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest('This platform does not permit creating symbolic links')
            self.assertIsNone(store.read_image(identifier))
            self.assertTrue(outside.exists())

    def test_truncated_or_excessively_expanded_gzip_is_never_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, min_free_bytes=0)
            self.assertTrue(store.add(event(), capture()))
            store.close()
            identifier = store.list_entries()[0]['id']
            picture_file = Path(directory) / (identifier + '.ppm.gz')
            picture_file.write_bytes(b'\x1f\x8b\x08\x00')
            self.assertIsNone(store.read_image(identifier))
            picture_file.write_bytes(gzip.compress(b'P6\n4096 4096\n255\n' + b'\0' * (12 * 1024 * 1024 + 1)))
            self.assertIsNone(store.read_image(identifier))

    def test_stale_or_mislabelled_ppm_never_becomes_a_recent_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, min_free_bytes=0)
            stale = dict(capture(), frame_age_seconds=5.1)
            self.assertTrue(store.add(event(1), stale))
            wait_until_saved(store)
            wrong_dimensions = dict(capture(), width=1920, height=1080)
            self.assertTrue(store.add(event(2), wrong_dimensions))
            store.close()
            for row in store.list_entries():
                self.assertIsNone(store.read_image(row['id']))
                self.assertIsNone(row['width'])

    def test_busy_store_never_blocks_or_accepts_an_unbounded_backlog(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, min_free_bytes=0)
            entered, release = threading.Event(), threading.Event()
            original_compress = gzip.compress
            def slow_compress(*args, **kwargs):
                entered.set()
                release.wait(3)
                return original_compress(*args, **kwargs)
            # Hold the expensive compressor only; the thread, queue and disk writes
            # remain real, avoiding a scheduler-dependent producer-speed assertion.
            with patch.object(gzip, 'compress', side_effect=slow_compress):
                try:
                    self.assertTrue(store.add(event(1), capture()))
                    self.assertTrue(entered.wait(1))
                    self.assertTrue(store.add(event(2), capture()))
                    self.assertTrue(store.add(event(3), capture()))
                    started = time.monotonic()
                    self.assertFalse(store.add(event(4), capture()))
                    self.assertLess(time.monotonic() - started, 0.1)
                    started = time.monotonic()
                    store.close()
                    self.assertLess(time.monotonic() - started, 1.3)
                finally:
                    release.set()
                    store.close()
                    # Application close is intentionally bounded. Test teardown
                    # must additionally wait for the real worker's final manifest
                    # before TemporaryDirectory removes its files on Windows.
                    store._worker.join(timeout=5)
                    self.assertFalse(store._worker.is_alive(), 'The released evidence worker must finish before directory cleanup')
                self.assertEqual([row['state'] for row in store.list_entries()], ['Guardada'] * 3)
            self.assertLessEqual(len(store.list_entries()), 25)
            self.assertFalse(store.add(event(), capture()), 'A closed gallery must refuse new work')

    def test_memory_fallback_obeys_the_byte_quota_too(self):
        with tempfile.TemporaryDirectory() as directory:
            pixels = random.Random(61).randbytes(3000)
            picture = capture(b'P6\n100 10\n255\n' + pixels, 100, 10)
            store = self.store(directory, max_bytes=5000, min_free_bytes=2 ** 63)
            self.assertTrue(store.add(event(1), picture))
            first = wait_until_saved(store)[0]['id']
            self.assertTrue(store.add(event(2), picture))
            store.close()
            self.assertEqual([row['camera'] for row in store.list_entries()], [2])
            self.assertIsNone(store.read_image(first))
            retained = [store.read_image(row['id']) for row in store.list_entries()]
            self.assertLessEqual(sum(len(ppm) for ppm in retained if ppm is not None), 5000)

    def test_saved_state_is_not_announced_before_the_image_and_manifest_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, min_free_bytes=0)
            entered, release = threading.Event(), threading.Event()
            original_write = EvidenceStore._write_atomic
            def slow_write(instance, filename, payload):
                if filename.endswith('.ppm.gz'):
                    entered.set()
                    release.wait(2)
                return original_write(instance, filename, payload)
            with patch.object(EvidenceStore, '_write_atomic', new=slow_write):
                try:
                    self.assertTrue(store.add(event(), capture()))
                    self.assertTrue(entered.wait(1))
                    row = store.list_entries()[0]
                    self.assertEqual(row['state'], 'Pendiente', 'A RAM preview must not claim a completed disk write')
                    self.assertEqual(store.read_image(row['id']), b'P6\n2 1\n255\n\x01\x02\x03\x04\x05\x06')
                finally:
                    release.set()
                    store.close()
                saved = wait_until_saved(store)[0]
            self.assertEqual(saved['state'], 'Guardada')
            self.assertTrue((Path(directory) / (saved['id'] + '.ppm.gz')).is_file())
            self.assertTrue((Path(directory) / 'manifest.json').is_file())

    def test_nonfinite_and_negative_frame_ages_cannot_supply_a_recent_photo(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, age in enumerate((-0.1, float('nan'), float('inf'))):
                with self.subTest(age=age):
                    store = self.store(Path(directory) / str(index), min_free_bytes=0)
                    self.assertTrue(store.add(event(), dict(capture(), frame_age_seconds=age)))
                    store.close()
                    self.assertTrue(all(store.read_image(row['id']) is None for row in store.list_entries()))

    def test_expiration_applies_while_the_gallery_remains_open(self):
        with tempfile.TemporaryDirectory() as directory:
            # Only wall time is controlled. Actual disk writes, worker execution
            # and monotonic waits remain real, so slow storage cannot expire the
            # entry before this test observes its successful commit.
            with patch('vox_cctv_evidence.time.time', return_value=1_790_000_000.0) as wall_clock:
                store = self.store(directory, min_free_bytes=0)
                try:
                    self.assertTrue(store.add(event(), capture()))
                    identifier = wait_until_saved(store)[0]['id']
                    wall_clock.return_value = 1_790_000_000.0 + 47 * 3600
                    self.assertEqual(store.list_entries()[0]['id'], identifier)
                    wall_clock.return_value = 1_790_000_000.0 + 49 * 3600
                    self.assertEqual(store.list_entries(), [], 'Retention must not require a restart')
                finally:
                    store.close()
                self.assertFalse((Path(directory) / (identifier + '.ppm.gz')).exists())

    def test_a_symlink_gallery_directory_never_writes_outside_it(self):
        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / 'outside'
            outside.mkdir()
            linked = Path(directory) / 'linked'
            try:
                linked.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('This platform does not permit creating symbolic links')
            store = self.store(linked, min_free_bytes=0)
            self.assertTrue(store.add(event(), capture()))
            store.close()
            self.assertEqual(list(outside.iterdir()), [])
            self.assertIsNotNone(store.read_image(store.list_entries()[0]['id']))

    def test_a_symlink_manifest_is_not_read_or_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'gallery'
            first = self.store(folder, min_free_bytes=0)
            self.assertTrue(first.add(event(), capture()))
            first.close()
            original = (folder / 'manifest.json').read_bytes()
            external = Path(directory) / 'external-manifest.json'
            external.write_bytes(original)
            (folder / 'manifest.json').unlink()
            try:
                (folder / 'manifest.json').symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest('This platform does not permit creating symbolic links')
            restored = self.store(folder, min_free_bytes=0)
            self.assertEqual(restored.list_entries(), [])
            self.assertTrue(restored.add(event(2), capture()))
            restored.close()
            self.assertEqual(external.read_bytes(), original)
            self.assertTrue((folder / 'manifest.json').is_symlink())


if __name__ == '__main__':
    unittest.main()
