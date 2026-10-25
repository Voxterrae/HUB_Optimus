import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import uuid
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vox_cctv_native import AuthError, MediaFrame, SourceError
import vox_cctv_sequences as sequences


def video(key=True, size=12, codec='h264', value=7):
    payload = b'\x00\x00\x00\x01' + bytes([0x65 if key else 0x41]) + bytes([value]) * (size - 5)
    return MediaFrame(0xfc if key else 0xfd, codec if key else None, payload, 2 if key else 0, 1 if key else 0, 10 if key else None)


class SceneFrame:
    """Decoded-frame fixture; original RGB conversion keeps exact pixel bytes."""
    width = 2
    height = 1
    def __init__(self, value): self.value = value
    def reformat(self, *, format):
        if format != 'rgb24': raise AssertionError('Only the original RGB is requested')
        class Plane:
            line_size = 8
            def __bytes__(plane): return bytes([self.value]) * 6 + b'xx'
        return SimpleNamespace(planes=[Plane()])


class SequenceContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.now = 100.0
        self.published = []
        self.manager = sequences.SequenceManager('private', self.temporary.name,
            lambda event, capture: self.published.append((event, capture)),
            clock=lambda: self.now, min_free_bytes=0)

    def tearDown(self):
        self.manager.stop()
        self.temporary.cleanup()

    def feed(self, stamp, key=False, size=12):
        self.now = stamp
        return self.manager._ingest(0, video(key, size), stamp)

    def event(self, status='Start', name='HumanDetect'):
        return {'event': name, 'channel': 1, 'status': status, 'time': '2026-10-04 12:00:00', 'PassWord': 'must disappear'}

    def test_ring_waits_for_keyframe_and_trims_complete_gops(self):
        self.assertFalse(self.feed(90))
        for stamp, key in ((90, True), (92, False), (95, True), (97, False), (101, True), (102, False)):
            self.feed(stamp, key)
        records = self.manager._ring_records(0)
        self.assertEqual(records[0].received, 90)
        self.feed(106, True)
        records = self.manager._ring_records(0)
        self.assertEqual(records[0].received, 95)
        self.assertTrue(records[0].key)
        self.assertTrue(all(record.codec == 'h264' for record in records))

    def test_episode_precoverage_extension_and_absolute_duration_cap(self):
        self.feed(90, True)
        self.feed(96, True)
        self.feed(100)
        self.assertTrue(self.manager.trigger(self.event(), 100))
        self.assertTrue(self.manager.trigger(self.event(), 112))
        episode = self.manager._cameras[0].active
        self.assertEqual(episode.deadline, 127)
        self.assertEqual(episode.event_received, 100)
        for stamp in (125, 138, 150, 153):
            self.manager.trigger(self.event(), stamp)
        self.assertEqual(episode.deadline, 160)
        self.assertEqual(episode.trigger_count, 6)
        self.assertNotIn('PassWord', episode.event)

    def test_fractional_pre_boundary_keeps_preceding_keyframe_gop(self):
        # The last delta of the preceding GOP ends0.005s before cutoff90.0.
        # Dropping it by its end loses the original keyframe and full pre-roll.
        for stamp, key in ((89.035, True), (89.955, False), (89.995, False),
                (90.035, True), (99.955, False), (99.995, False)):
            self.feed(stamp, key)
        self.assertEqual(self.manager._ring_records(0)[0].received, 89.035)
        self.assertTrue(self.manager.trigger(self.event(), 100))
        self.assertEqual(self.manager._cameras[0].active.gops[0].records[0].received, 89.035)
        self.manager._collect_due(115)
        job = self.manager._jobs.get_nowait()
        metadata = self.manager._metadata(job, None, None)
        self.assertGreaterEqual(metadata['pre_coverage_seconds'], 10)
        self.assertNotIn('pre_coverage_incomplete', metadata['clipped_reasons'])

    def test_stale_ring_does_not_claim_precoverage_from_an_old_keyframe(self):
        self.feed(70, True)
        self.manager.trigger(self.event(), 100)
        self.assertEqual(self.manager._cameras[0].active.gops, [])

    def test_deltas_audio_unsupported_codec_and_unframed_payload_are_not_exported(self):
        self.assertFalse(self.manager._ingest(0, MediaFrame(0xfa, None, b'audio'), 99))
        self.assertFalse(self.manager._ingest(0, MediaFrame(0xfc, 'mpeg4', b'unsupported'), 99))
        self.assertFalse(self.manager._ingest(0, MediaFrame(0xfc, 'h264', b'no prefix'), 99))
        self.feed(100, True)
        self.assertEqual(len(self.manager._ring_records(0)), 1)

    def test_combined_ring_active_and_inflight_memory_is_bounded(self):
        manager = sequences.SequenceManager('private', self.temporary.name, lambda *args: None,
            max_ring_bytes=48, max_total_bytes=48, clock=lambda: self.now, min_free_bytes=0)
        try:
            for stamp in range(90, 100):
                manager._ingest(0, video(True, 12), stamp)
            manager.trigger(self.event(), 100)
            for stamp in range(100, 110):
                manager._ingest(0, video(True, 12), stamp)
                self.assertLessEqual(manager.snapshot()['compressed_memory_bytes'], 48)
            episode = manager._cameras[0].active
            self.assertIn('memory_quota', episode.clipped_reasons)
            manager._collect_due(126)
            held = manager.snapshot()['compressed_memory_bytes']
            for stamp in range(127, 140):
                manager._ingest(0, video(True, 12), stamp)
                self.assertLessEqual(manager.snapshot()['compressed_memory_bytes'], 48)
            self.assertLessEqual(held, 48)
            self.assertTrue(manager.snapshot()['cameras'][0]['awaiting_keyframe'])
        finally:
            manager.stop()

    def test_oversized_gop_drops_until_the_next_usable_keyframe(self):
        manager = sequences.SequenceManager('private', self.temporary.name, lambda *args: None,
            max_ring_bytes=24, max_total_bytes=24, min_free_bytes=0)
        try:
            manager._ingest(0, video(True, 12), 1)
            manager._ingest(0, video(False, 20), 2)
            self.assertEqual(manager._ring_records(0), ())
            self.assertFalse(manager._ingest(0, video(False), 3))
            self.assertTrue(manager._ingest(0, video(True, 12), 4))
            self.assertTrue(manager._ring_records(0)[0].key)
        finally:
            manager.stop()

    def test_reconnect_finalizes_partial_episode_and_never_splices_sessions(self):
        self.feed(95, True)
        self.manager.trigger(self.event(), 100)
        self.manager._reset_channel(0, 'connection_lost', 103)
        self.assertEqual(self.manager._ring_records(0), ())
        job = self.manager._jobs.get_nowait()
        self.assertIn('connection_lost', job.clipped_reasons)
        self.feed(105, True)
        self.assertEqual(self.manager._ring_records(0)[0].received, 105)
        self.assertNotEqual(job.records[0].session, self.manager._ring_records(0)[0].session)

    def test_silent_camera_finalizes_on_timer_with_honest_coverage(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(115)
        job = self.manager._jobs.get_nowait()
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        clip = self.manager.list_clips()[0]
        self.assertEqual(clip['pre_coverage_seconds'], 1)
        self.assertEqual(clip['post_coverage_seconds'], 0)
        self.assertEqual(clip['status'], 'partial')
        self.assertIn('post_coverage_incomplete', clip['clipped_reasons'])
        self.assertIsNone(self.published[0][1])

    def test_exact_elementary_export_has_offsets_timestamps_and_original_digest(self):
        first, second = video(True, 17), video(False, 13)
        self.manager._ingest(0, first, 99)
        self.manager._ingest(0, second, 100)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        clip = self.manager.list_clips()[0]
        payload = (Path(self.temporary.name) / clip['video_file']).read_bytes()
        self.assertEqual(payload, first.payload + second.payload)
        self.assertEqual(clip['original_sha256'], hashlib.sha256(payload).hexdigest())
        self.assertEqual([row['byte_offset'] for row in clip['frames']], [0, 17])
        self.assertEqual([row['event_offset_seconds'] for row in clip['frames']], [-1, 0])
        self.assertEqual(clip['format'], 'annex_b_elementary_stream')
        self.assertEqual(clip['timing_source'], 'local_monotonic_receipt')
        self.assertNotIn('private', json.dumps(clip))

    def test_quota_deletes_only_owned_episodes_and_keeps_newest(self):
        manager = sequences.SequenceManager('private', self.temporary.name, lambda *args: None,
            max_episodes=1, min_free_bytes=0, clock=lambda: self.now)
        foreign = Path(self.temporary.name) / 'foreign.h264'
        foreign.write_bytes(b'keep')
        try:
            identifiers = []
            for stamp in (100, 120):
                self.now = stamp
                manager._ingest(0, video(True), stamp)
                manager.trigger(self.event(), stamp)
                manager._collect_due(stamp + 16)
                job = manager._jobs.get_nowait()
                identifiers.append(job.identifier)
                with patch.object(sequences, '_decode_records', return_value=iter(())):
                    manager._process_job(job)
            self.assertEqual([clip['id'] for clip in manager.list_clips()], [identifiers[-1]])
            self.assertFalse((Path(self.temporary.name) / (identifiers[0] + '.h264')).exists())
            self.assertTrue(foreign.exists())
            self.assertLessEqual(manager.snapshot()['storage_bytes'], manager.max_storage_bytes)
        finally:
            manager.stop()

    def test_full_resolution_selection_reports_actual_receipt_age_and_offset(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.feed(101)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        self.now = 116
        frame = SimpleNamespace(width=2, height=1)
        ppm = b'P6\n2 1\n255\n' + b'\x01\x02\x03\x04\x05\x06'
        with patch.object(sequences, '_decode_records', return_value=iter(((frame, 101),))), \
                patch.object(sequences, '_frame_quality', return_value=5), \
                patch.object(sequences, '_original_ppm', return_value=ppm):
            self.manager._process_job(job)
        capture = self.published[0][1]
        self.assertEqual(capture['ppm'], ppm)
        self.assertEqual(capture['frame_age_seconds'], 15)
        self.assertEqual(capture['sequence_offset_seconds'], 1)
        self.assertEqual((capture['source_width'], capture['source_height']), (2, 1))
        self.assertEqual(capture['selection'], 'escena')

    def test_invalid_channels_nonfinite_times_stop_and_private_fields(self):
        self.assertFalse(self.manager.trigger(dict(self.event(), channel=0), 100))
        self.assertFalse(self.manager.trigger(self.event(), float('nan')))
        self.assertFalse(self.manager.trigger(self.event('Stop'), 100))
        self.manager.stop()
        self.assertFalse(self.manager.trigger(self.event(), 100))
        self.assertFalse(self.manager.start_channel(0))

    def test_terminal_auth_source_failures_are_not_retried_and_stop_is_bounded(self):
        for error_type in (AuthError, SourceError):
            calls = []
            def factory(*args):
                calls.append(1)
                raise error_type('do not expose a secret')
            manager = sequences.SequenceManager('private', self.temporary.name, lambda *args: None,
                client_factory=factory, min_free_bytes=0)
            manager.start_channel(0)
            manager._workers[0].join(timeout=1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(manager.snapshot()['cameras'][0]['last_error_kind'], error_type.__name__)
            start = time.monotonic()
            manager.stop()
            self.assertLess(time.monotonic() - start, 1.5)
            self.assertEqual(manager.snapshot()['compressed_memory_bytes'], 0)

    def test_publication_is_on_background_and_callback_can_close_manager(self):
        called = threading.Event()
        owner = threading.get_ident()
        thread_ids = []
        def callback(event, capture):
            thread_ids.append(threading.get_ident())
            manager.list_clips()
            manager.stop()
            called.set()
        manager = sequences.SequenceManager('private', self.temporary.name, callback,
            clock=lambda: self.now, min_free_bytes=0)
        try:
            manager._ingest(0, video(True), 99)
            manager.trigger(self.event(), 100)
            self.now = 116
            with patch.object(sequences, '_decode_records', return_value=iter(())):
                manager._ensure_finalizer()
                self.assertTrue(called.wait(1))
            self.assertNotEqual(thread_ids, [owner])
            self.assertFalse(manager.trigger(self.event(), 116))
        finally:
            manager.stop()

    def test_fake_pyav_preserves_receipts_through_parser_delay_and_missing_time_base(self):
        contexts = []
        class Context:
            def __init__(self):
                self.buffer = None
                self.delayed = None
            def parse(self, payload):
                previous, self.buffer = self.buffer, payload or None
                return [SimpleNamespace(size=len(previous))] if previous else []
            def decode(self, packet):
                previous = self.delayed
                self.delayed = SimpleNamespace(pts=packet.pts, time_base=None) if packet is not None else None
                return [previous] if previous is not None else []
        def create(codec, mode):
            self.assertEqual((codec, mode), ('h264', 'r'))
            context = Context()
            contexts.append(context)
            return context
        fake_av = SimpleNamespace(CodecContext=SimpleNamespace(create=create))
        self.feed(100, True)
        self.feed(101)
        with patch.dict('sys.modules', {'av': fake_av}):
            decoded = list(sequences._decode_records(self.manager._ring_records(0), threading.Event()))
        self.assertEqual([stamp for frame, stamp in decoded], [100, 101])
        self.assertEqual(contexts[0].thread_count, 1)
        self.assertEqual(contexts[0].thread_type, 'SLICE')

    def test_original_rgb_stride_and_gray_quality_do_not_need_numpy(self):
        raw = b'\x01\x02\x03padding' + b'\x04\x05\x06padding'
        rgb = SimpleNamespace(planes=[SimpleNamespace(line_size=10, __bytes__=None)])
        class Plane:
            line_size = 10
            def __bytes__(self):
                return raw
        rgb.planes = [Plane()]
        frame = SimpleNamespace(width=1, height=2, reformat=lambda **kw: rgb)
        self.assertEqual(sequences._original_ppm(frame), b'P6\n1 2\n255\n\x01\x02\x03\x04\x05\x06')

    def test_nearest_scene_requires_no_quality_scan_and_optional_selector_failure_is_isolated(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        for stamp in (100, 100.5, 101, 101.5):
            self.feed(stamp)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        self.now = 116
        frame = SimpleNamespace(width=2, height=1)
        quality = []
        class BadSelector:
            def consider(self, frame, stamp):
                raise RuntimeError('private detector detail')
        self.manager.frame_selector_factory = BadSelector
        with patch.object(sequences, '_decode_records', return_value=iter((frame, record.received) for record in job.records)), \
                patch.object(sequences, '_frame_quality', side_effect=lambda item: quality.append(1) or 5), \
                patch.object(sequences, '_original_ppm', return_value=b'P6\n2 1\n255\n' + bytes(6)):
            self.manager._process_job(job)
        # Scene proximity replaces the old one-fps sharpness scan. Optional
        # detector failure must still leave the event's original scene intact.
        self.assertEqual(len(quality), 0)
        self.assertEqual(self.published[0][1]['sequence_offset_seconds'], 0)
        self.assertIsNotNone(self.published[0][1])
        self.assertEqual(self.manager.list_clips()[0]['selector_status']['error_kind'], 'RuntimeError')
        self.assertNotIn('private detector detail', json.dumps(self.manager.list_clips()))

    def scene_job(self, stamps, *, latest_activity=100):
        records=tuple(sequences._Record(video(index==0).payload,'h264',index==0,
                                        stamp,2,1,10,0) for index,stamp in enumerate(sorted(stamps)))
        return sequences._Job(uuid.uuid4().hex,0,sequences._sanitised_event(self.event()),
                              100,time.time(),115,latest_activity,1,records,(),frozenset())

    def test_far_sharp_scene_never_replaces_event_anchor_original(self):
        before, anchor, after=SceneFrame(11),SceneFrame(22),SceneFrame(33)
        job=self.scene_job([90,99.96,100.01,113])
        self.now=116
        with patch.object(sequences,'_decode_records',return_value=iter(
                ((before,99.96),(anchor,100.01),(after,113)))), \
                patch.object(sequences,'_frame_quality',side_effect=lambda frame:
                             {11:2,22:1,33:100000}[frame.value]):
            capture,error,status=self.manager._select(job)
        self.assertIsNone(error)
        self.assertAlmostEqual(capture['sequence_offset_seconds'],.01)
        self.assertEqual(capture['ppm'],b'P6\n2 1\n255\n'+bytes([22])*6)
        self.assertAlmostEqual(capture['frame_age_seconds'],15.99)
        self.assertEqual(capture['selection_method'],'full_scene_nearest_event_receipt')

    def test_missing_pre_scene_uses_nearest_available_after_event(self):
        closest,later=SceneFrame(44),SceneFrame(55)
        job=self.scene_job([100.25,100.75,113])
        self.now=116
        with patch.object(sequences,'_decode_records',return_value=iter(
                ((later,100.75),(closest,100.25),(later,113)))), \
                patch.object(sequences,'_frame_quality',side_effect=lambda frame:frame.value):
            capture,error,status=self.manager._select(job)
        self.assertEqual(capture['sequence_offset_seconds'],.25)
        self.assertEqual(capture['ppm'],b'P6\n2 1\n255\n'+bytes([44])*6)

    def test_equal_distance_uses_quality_without_moving_away_from_anchor(self):
        before,after,later=SceneFrame(66),SceneFrame(77),SceneFrame(88)
        job=self.scene_job([99,101,113])
        self.now=116
        with patch.object(sequences,'_decode_records',return_value=iter(
                ((before,99),(after,101),(later,113)))), \
                patch.object(sequences,'_frame_quality',side_effect=lambda frame:frame.value):
            capture,error,status=self.manager._select(job)
        self.assertEqual(capture['sequence_offset_seconds'],1)
        self.assertEqual(capture['ppm'],b'P6\n2 1\n255\n'+bytes([77])*6)

    def test_invalid_quality_cannot_discard_available_original_scene(self):
        for bad_quality in (float('nan'),float('inf'),None,RuntimeError('bad quality sample')):
            with self.subTest(quality=type(bad_quality).__name__):
                frame=SceneFrame(99)
                job=self.scene_job([99,101])
                self.now=116
                def quality(item):
                    if isinstance(bad_quality,Exception): raise bad_quality
                    return bad_quality
                with patch.object(sequences,'_decode_records',return_value=iter(((frame,99),(frame,101)))), \
                        patch.object(sequences,'_frame_quality',side_effect=quality):
                    capture,error,status=self.manager._select(job)
                self.assertIsNotNone(capture)
                self.assertEqual(capture['ppm'],b'P6\n2 1\n255\n'+bytes([99])*6)
                self.assertEqual(capture['sequence_offset_seconds'],-1)
                self.assertIsNone(error)

    def test_extended_episode_keeps_original_event_anchor_and_method_after_restart(self):
        anchor,later=SceneFrame(101),SceneFrame(102)
        job=self.scene_job([90,100,113,115],latest_activity=113)
        self.now=116
        with patch.object(sequences,'_decode_records',return_value=iter(((anchor,100),(later,113)))), \
                patch.object(sequences,'_frame_quality',side_effect=lambda frame:frame.value):
            self.manager._process_job(job)
        capture=self.published[0][1]
        self.assertEqual(capture['sequence_offset_seconds'],0)
        self.assertEqual(capture['ppm'],b'P6\n2 1\n255\n'+bytes([101])*6)
        clip=self.manager.list_clips()[0]
        self.assertEqual(clip['image_selection'].get('selection_method'),'full_scene_nearest_event_receipt')
        expected_digest=hashlib.sha256(b''.join(record.payload for record in job.records)).hexdigest()
        self.assertEqual(clip['original_sha256'],expected_digest)
        restored=sequences.SequenceManager('private',self.temporary.name,lambda *args:None,min_free_bytes=0)
        try:
            restored._load_clips()
            self.assertEqual(restored.list_clips()[0]['image_selection'].get('selection_method'),
                             'full_scene_nearest_event_receipt')
            self.assertEqual(restored.list_clips()[0]['original_sha256'],expected_digest)
        finally: restored.stop()

    def test_twenty_detector_samples_cover_the_entire_extended_episode(self):
        records = tuple(sequences._Record(video(index % 10 == 0).payload, 'h264',
            index % 10 == 0, 90 + index, 2, 1, 10, 0) for index in range(71))
        job = sequences._Job(uuid.uuid4().hex, 0, sequences._sanitised_event(self.event()),
            100, time.time(), 160, 150, 10, records, (), frozenset(('duration_cap',)))
        analysed = []
        class Selector:
            def consider(self, frame, stamp):
                analysed.append(stamp)
            def finalize(self):
                return {'body_status': 'none', 'face_status': 'none', 'detector_status': 'available',
                    'considered': len(analysed), 'candidates': []}
        self.manager.frame_selector_factory = Selector
        self.now = 170
        frame = SimpleNamespace(width=2, height=1)
        with patch.object(sequences, '_decode_records', return_value=iter((frame, row.received) for row in records)), \
                patch.object(sequences, '_frame_quality', return_value=1), \
                patch.object(sequences, '_original_ppm', return_value=b'P6\n2 1\n255\n' + bytes(6)):
            capture, error, status = self.manager._select(job)
        self.assertEqual(len(analysed), 20)
        self.assertEqual((analysed[0], analysed[-1]), (90, 160))
        self.assertEqual(status['considered'], 20)

    def test_callback_is_suppressed_if_close_occurs_during_analysis(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        def decode(records, stop):
            self.manager.stop()
            return iter(())
        with patch.object(sequences, '_decode_records', side_effect=decode):
            self.manager._process_job(job)
        self.assertEqual(self.published, [])

    def test_delayed_event_excludes_frames_beyond_post_deadline(self):
        for stamp in range(99, 121):
            self.feed(stamp, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(120)
        job = self.manager._jobs.get_nowait()
        self.assertTrue(job.records)
        self.assertLessEqual(job.records[-1].received, 115)

    def test_original_file_is_persisted_before_decoder_analysis(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        found = []
        def decode(records, stop):
            found.append((Path(self.temporary.name) / (job.identifier + '.h264')).exists())
            return iter(())
        with patch.object(sequences, '_decode_records', side_effect=decode):
            self.manager._process_job(job)
        self.assertEqual(found, [True])

    def test_crashed_raw_and_tmp_are_reclaimed_but_foreign_files_are_preserved(self):
        identifier = uuid.uuid4().hex
        raw = Path(self.temporary.name) / (identifier + '.h264')
        temporary = Path(self.temporary.name) / (identifier + '.h264.' + uuid.uuid4().hex + '.tmp')
        raw.write_bytes(b'crashed')
        temporary.write_bytes(b'partial')
        foreign = Path(self.temporary.name) / 'manual-recording.h264'
        foreign.write_bytes(b'preserve')
        self.manager._load_clips()
        self.assertFalse(raw.exists())
        self.assertFalse(temporary.exists())
        self.assertTrue(foreign.exists())
        self.assertEqual(self.manager.snapshot()['storage_bytes'], 0)

    def test_delete_denial_remains_in_quota_accounting_and_blocks_replacement(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        size = self.manager.snapshot()['storage_bytes']
        self.manager.max_episodes = 1
        with patch.object(self.manager, '_delete_owned_file', return_value=False):
            self.assertFalse(self.manager._prune_storage(100, 1))
        self.assertEqual(self.manager.snapshot()['storage_bytes'], size)
        self.assertEqual(len(self.manager.list_clips()), 1)
        self.assertEqual(self.manager.snapshot()['last_error_kind'], 'RetentionDeleteBlocked')

    def test_reduced_quota_restart_reclaims_previously_valid_oversized_episode(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        reopened = sequences.SequenceManager('private', self.temporary.name, lambda *args: None,
            max_storage_bytes=100, min_free_bytes=0)
        try:
            reopened._load_clips()
            self.assertEqual(reopened.snapshot()['storage_bytes'], 0)
            self.assertEqual(reopened.list_clips(), [])
            self.assertFalse((Path(self.temporary.name) / (job.identifier + '.h264')).exists())
        finally:
            reopened.stop()

    def test_restart_reconstructs_known_metadata_and_rejects_broken_frame_index(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        metadata_path = Path(self.temporary.name) / (job.identifier + '.json')
        saved = json.loads(metadata_path.read_text())
        saved['PassWord'] = 'private'
        saved['frames'][0]['PassWord'] = 'private'
        metadata_path.write_text(json.dumps(saved))
        reopened = sequences.SequenceManager('private', self.temporary.name, lambda *args: None, min_free_bytes=0)
        try:
            reopened._load_clips()
            self.assertEqual(len(reopened.list_clips()), 1)
            self.assertNotIn('private', json.dumps(reopened.list_clips()))
        finally:
            reopened.stop()
        saved['frames'][0]['byte_offset'] = 5
        metadata_path.write_text(json.dumps(saved))
        reopened = sequences.SequenceManager('private', self.temporary.name, lambda *args: None, min_free_bytes=0)
        try:
            reopened._load_clips()
            self.assertEqual(reopened.list_clips(), [])
            self.assertEqual(reopened.snapshot()['storage_bytes'], 0)
        finally:
            reopened.stop()

    def test_full_supported_sixty_fps_extended_sequence_fits_metadata_limit(self):
        records = tuple(sequences._Record(video(index % 60 == 0).payload, 'h264',
            index % 60 == 0, 90 + index / 60, 2, 1, 60, 0) for index in range(4200))
        job = sequences._Job(uuid.uuid4().hex, 0, sequences._sanitised_event(self.event()),
            100, time.time(), 160, 150, 10, records, (), frozenset(('duration_cap',)))
        self.now = 170
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        clip = self.manager.list_clips()[0]
        self.assertEqual(len(clip['frames']), 4200)
        self.assertIn('duration_cap', clip['clipped_reasons'])
        self.assertTrue(self.manager.clip_path(job.identifier).is_file())

    def test_record_count_bounds_tiny_access_units(self):
        with patch.object(sequences, 'MAX_RECORDS_PER_CAMERA', 4):
            for stamp in range(5):
                self.manager._ingest(0, video(True, 6), stamp)
        self.assertEqual(len(self.manager._ring_records(0)), 4)
        self.assertFalse(self.manager._ingest(0, MediaFrame(0xfc, 'h264', b'\x00\x00\x01'), 100))

    def test_high_bitrate_budget_retains_ten_second_pre_and_fifteen_second_post(self):
        manager = sequences.SequenceManager('private', self.temporary.name, lambda *args: None,
            max_ring_bytes=64 * 1024 * 1024, max_total_bytes=256 * 1024 * 1024,
            min_free_bytes=0, clock=lambda: 126)
        try:
            #26MiB models a Main stream above the original8MiB episode budget.
            payload = video(True, 1024 * 1024).payload
            for stamp in range(90, 116):
                frame = MediaFrame(0xfc, 'h264', payload, 2, 1, 1)
                if stamp == 100:
                    manager.trigger(self.event(), stamp)
                manager._ingest(0, frame, stamp)
            manager._collect_due(116)
            job = manager._jobs.get_nowait()
            self.assertEqual(job.records[0].received, 90)
            self.assertEqual(job.records[-1].received, 114)
            self.assertNotIn('memory_quota', job.clipped_reasons)
            self.assertEqual(manager.max_ring_bytes, 64 * 1024 * 1024)
            self.assertEqual(manager.max_total_bytes, 256 * 1024 * 1024)
            self.assertLessEqual(manager.snapshot()['compressed_memory_bytes'], manager.max_total_bytes)
        finally:
            manager.stop()

    def test_playback_verifies_integrity_and_preserves_indexed_receipt_offsets(self):
        self.feed(99, True)
        self.feed(100)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        decoded_records = []
        def decode(records, stop):
            decoded_records.extend(records)
            return iter((SimpleNamespace(), record.received) for record in records)
        with patch.object(sequences, '_decode_records', side_effect=decode):
            output = list(self.manager.playback_frames(job.identifier, threading.Event()))
        self.assertEqual([stamp for frame, stamp in output], [-1, 0])
        self.assertEqual([record.payload for record in decoded_records], [video(True).payload, video(False).payload])
        path = self.manager.clip_path(job.identifier)
        path.write_bytes(b'X' * path.stat().st_size)
        with self.assertRaisesRegex(ValueError, 'integrity'):
            list(self.manager.playback_frames(job.identifier, threading.Event()))

    def test_public_metadata_cannot_mutate_cached_playback_index(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        clip = self.manager.list_clips()[0]
        clip['frames'][0]['bytes'] = 5000
        self.assertEqual(self.manager.list_clips()[0]['frames'][0]['bytes'], 12)

    def test_symlinked_owned_clip_is_not_followed_or_played(self):
        self.feed(99, True)
        self.manager.trigger(self.event(), 100)
        self.manager._collect_due(116)
        job = self.manager._jobs.get_nowait()
        with patch.object(sequences, '_decode_records', return_value=iter(())):
            self.manager._process_job(job)
        clip = self.manager.list_clips()[0]
        path = self.manager.clip_path(job.identifier)
        path.unlink()
        foreign = Path(self.temporary.name) / 'foreign-target'
        foreign.write_bytes(b'preserve')
        try:
            path.symlink_to(foreign)
        except (OSError, NotImplementedError):
            self.skipTest('Symlinks are unavailable')
        self.assertIsNone(self.manager.clip_path(job.identifier))
        with self.assertRaises(OSError):
            list(self.manager.playback_frames(job.identifier, threading.Event()))
        self.assertEqual(foreign.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
