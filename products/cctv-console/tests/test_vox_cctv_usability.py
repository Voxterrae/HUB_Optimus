"""Consumer effects for session menus, missing photos and original crops.

The headless doubles replace Tk widgets only; policies, viewer handlers and
crop extraction run as production code. Real Tk coverage is included for the
Windows validation runner.
"""
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import vox_cctv_viewer as viewer
from vox_cctv_photos import PhotoInspector
from vox_home.access import AccessDenied


class Widget:
    def __init__(self, **values):
        self.values = values
        self.rows = []
        self.selected = ()
        self.exists = True
        self.callbacks = {}
    def configure(self, **values): self.values.update(values)
    def cget(self, key): return self.values.get(key, '')
    def delete(self, first, last): self.rows.clear(); self.selected = ()
    def insert(self, where, value): self.rows.append(value)
    def selection_set(self, index): self.selected = (index,)
    def curselection(self): return self.selected
    def size(self): return len(self.rows)
    def winfo_exists(self): return self.exists
    def destroy(self): self.exists = False
    def after_cancel(self, identifier): self.callbacks.pop(identifier, None)
    def winfo_width(self): return 3
    def winfo_height(self): return 2
    def itemconfigure(self, item, **values): self.values.update(values)


class MemoryEvidence:
    def __init__(self, rows=(), pictures=None):
        self.rows = list(rows)
        self.pictures = pictures or {}
    def list_entries(self): return list(self.rows)
    def read_image(self, identifier): return self.pictures.get(identifier)


class HeadlessInspector(PhotoInspector):
    def __init__(self, master, ppm, row=None, *, authorise=None):
        self.original = self.source = ppm
        self.row = row or {}
        self.cropped = False
        self.zoom = None
        self.authorise = authorise
        self.window = Widget()
    def render(self): pass
    def close(self):
        self.original = self.source = None
        self.window.destroy()


def app_fixture(evidence=None):
    app = viewer.Viewer.__new__(viewer.Viewer)
    app.ui_thread = threading.get_ident()
    app.root = SimpleNamespace(bell=lambda: None)
    app.closed = False
    app.home_facade = None
    app.sequence_manager = None
    app.home_context = object()
    app.evidence = evidence or MemoryEvidence()
    app.zones = viewer.load_zones(Path('nonexistent-zone-fixture.json'))
    app.alarm_state = viewer.AlarmState()
    app.event_group = 'detections'
    app.visible_events = []
    app.alarm_events = Widget()
    app.event_history_note = Widget()
    app.alarm_status = Widget()
    app.banner = Widget()
    app.health = Widget()
    app.gallery = Widget()
    app.gallery_list = Widget()
    app.gallery_image = Widget(text='Selecciona una captura')
    app.gallery_details = Widget()
    app.gallery_crop_button = Widget(state='disabled')
    app.gallery_rows = []
    app.gallery_filter = None
    app.gallery_photo = app.gallery_original = None
    app.gallery_resize_pending = False
    app.inspectors = []
    app.tk = SimpleNamespace(TclError=RuntimeError)
    app.states = {channel: viewer.CameraState(channel) for channel in viewer.CHANNELS}
    app.headers = {channel: Widget() for channel in viewer.CHANNELS}
    app.images = {channel: Widget() for channel in viewer.CHANNELS}
    app.photos = {}; app.versions = {}
    app.detail = None
    app.rain = SimpleNamespace(get=lambda: False)
    app.last_metrics = time.monotonic()
    app.last_capture = {}
    return app


def report(kind, status='Start', channel=4, stamp='2026-10-05 13:31:23'):
    return {'Channel': channel, 'Event': kind, 'Status': status, 'StartTime': stamp}


class MenuAndCaptureContracts(unittest.TestCase):
    def test_group_selection_populates_now_without_video_refresh(self):
        app = app_fixture()
        app.alarm_state.add(report('VideoBlind'), now=1)
        app.alarm_state.add(report('VideoMotion'), now=2)
        app.select_group('technical')
        self.assertEqual(len(app.visible_events), 1)
        self.assertIn('Inicio', app.alarm_events.rows[0])
        app.select_group('activity')
        self.assertEqual(app.visible_events[0]['event'], 'VideoMotion')
        self.assertNotIn('VideoBlind', app.alarm_events.rows[0])
        self.assertIn('sesión', app.event_history_note.cget('text'))
        self.assertIn('25', app.event_history_note.cget('text'))

    def test_stop_and_aggregation_are_visible_without_claiming_new_detection(self):
        app = app_fixture()
        app.alarm_state.add(report('HumanDetect'), now=1)
        app.alarm_state.add(report('HumanDetect', 'Stop'), now=2)
        app.alarm_state.add(report('HumanDetect', stamp='2026-10-05 13:31:25'), now=3)
        app.alarm_state.add(report('HumanDetect', 'Stop', stamp='2026-10-05 13:31:26'), now=4)
        app.select_group('detections')
        self.assertEqual(app.alarm_events.size(), 1, 'Selection must render the closed episode immediately')
        line = app.alarm_events.rows[0]
        self.assertLess(line.index('Finalizado'), line.index('C5'))
        self.assertIn('rep. ×2', line)
        self.assertIn('sin confirmar', line)
        self.assertIn('repeticiones', app.event_history_note.cget('text'))

    def test_initial_empty_gallery_and_empty_filter_change_explain_absence(self):
        app = app_fixture()
        app.update_gallery()
        self.assertIn('No hay capturas', app.gallery_image.cget('text'))
        app.gallery_filter = (5, 'VideoBlind')
        app.update_gallery()
        self.assertIn('técnicos', app.gallery_details.cget('text').lower())
        app.gallery_filter = (5, 'VideoMotion')
        app.update_gallery()
        self.assertIn('actividad', app.gallery_details.cget('text').lower())
        self.assertNotIn('técnicos', app.gallery_details.cget('text').lower())
        self.assertEqual(app.evidence.list_entries(), [])

    def test_gallery_distinguishes_stored_context_and_detection_targets(self):
        rows = [dict(id=str(i),event='HumanDetect',camera=5,received_at=None,
                     selection=selection,state='Sin imagen')
                for i, selection in enumerate(('escena','cuerpo_detectado','rostro_detectado',None))]
        app = app_fixture(MemoryEvidence(rows))
        app.update_gallery()
        for line, name in zip(app.gallery_list.rows,
                              ('Escena completa','Cuerpo','Rostro','Fotograma inicial')):
            self.assertIn(name, line)
        self.assertEqual(app.gallery_crop_button.cget('state'), 'disabled')

    def test_sequence_metadata_explains_missing_face_and_independent_selections(self):
        row = dict(id='face-none',event='HumanDetect',camera=5,sequence_id='seq',
                   received_at=None,selection='escena')
        app = app_fixture(MemoryEvidence([row]))
        app.sequence_manager = SimpleNamespace(list_clips=lambda: [
            {'id':'seq','image_status':'selected','selector_status':{
                'face_status':'sin_rostro_con_calidad_suficiente',
                'body_status':'disponible','detector_status':'disponible'}}])
        app.update_gallery()
        text = app.gallery_details.cget('text').lower()
        self.assertIn('rostro', text)
        self.assertIn('calidad suficiente', text)
        self.assertIn('independientes', text)

    def test_pending_metadata_refreshes_without_new_gallery_rows(self):
        row=dict(id='same',event='HumanDetect',camera=5,sequence_id='seq',selection='escena')
        clip={'id':'seq','image_status':'selection_pending'}
        app=app_fixture(MemoryEvidence([row]))
        app.sequence_manager=SimpleNamespace(list_clips=lambda:[clip])
        app.update_gallery()
        self.assertIn('pendiente',app.gallery_details.cget('text'))
        clip.update(image_status='selected',selector_status={'face_status':'no_disponible',
                                                            'body_status':'disponible'})
        app.update_gallery()
        text=app.gallery_details.cget('text')
        self.assertNotIn('selección pendiente',text)
        self.assertIn('Rostro: selección no disponible',text)
        self.assertEqual(len(app.gallery_rows),1)

    def test_permission_refusal_clears_enabled_crop_control(self):
        app=app_fixture()
        app.gallery_crop_button.configure(state='normal')
        def denied(*args): raise AccessDenied('permission_denied')
        app.home_facade=SimpleNamespace(evidence_entries=denied)
        app.update_gallery()
        self.assertEqual(app.gallery_crop_button.cget('state'),'disabled')
        self.assertIsNone(app.gallery_original)

    def test_expired_selected_photo_disables_crop_when_resizing(self):
        row={'id':'expired','bbox':[0,0,1,1]}
        app=app_fixture(MemoryEvidence([row]))
        app.gallery_rows=[row]; app.gallery_list.selection_set(0)
        app.gallery_original=b'P6\n1 1\n255\n'+bytes([2,3,4])
        app.gallery_crop_button.configure(state='normal')
        app.render_gallery_photo()
        self.assertIsNone(app.gallery_original)
        self.assertEqual(app.gallery_crop_button.cget('state'),'disabled')

    def test_revocation_between_image_read_and_render_keeps_refusal_visible(self):
        row={'id':'race','event':'HumanDetect','camera':5,'bbox':[0,0,1,1]}
        app=app_fixture(MemoryEvidence([row]))
        app.gallery_rows=[row]; app.gallery_list.selection_set(0)
        reads=[b'P6\n1 1\n255\n'+bytes([2,3,4])]
        def read(*args):
            if reads: return reads.pop()
            raise AccessDenied('permission_denied')
        app.home_facade=SimpleNamespace(read_evidence=read)
        app.show_capture()
        self.assertEqual(app.gallery_details.cget('text'),'permission_denied')
        self.assertIsNone(app.gallery_original)
        self.assertEqual(app.gallery_crop_button.cget('state'),'disabled')

    def test_vehicle_details_do_not_invent_plate_or_model(self):
        row = dict(id='car',event='CarShapeDetect',camera=7,received_at=None)
        app = app_fixture(MemoryEvidence([row]))
        app.update_gallery()
        self.assertIn('Matrícula/marca/modelo no disponibles', app.gallery_details.cget('text'))
        self.assertEqual(app.gallery_crop_button.cget('state'), 'disabled')

    def test_direct_crop_uses_original_pixels_and_replaces_prior_inspector(self):
        original = b'P6\n3 2\n255\n' + bytes(range(18))
        row = dict(id='crop',event='HumanDetect',camera=5,bbox=[1,0,2,2])
        app = app_fixture(MemoryEvidence([row],{'crop':original}))
        app.gallery_rows = [row]; app.gallery_list.selection_set(0)
        old = HeadlessInspector(None, original)
        app.inspectors = [old]
        action = getattr(app, 'open_capture_crop', None)
        self.assertTrue(callable(action), 'The gallery needs a direct crop action')
        with patch.object(viewer, 'PhotoInspector', HeadlessInspector):
            action()
        self.assertFalse(old.window.winfo_exists())
        self.assertEqual(len(app.inspectors), 1)
        box = app.inspectors[0]
        self.assertEqual(box.source, b'P6\n2 2\n255\n' + bytes([3,4,5,6,7,8,12,13,14,15,16,17]))
        self.assertEqual(box.original, original)
        box.toggle_crop()
        self.assertEqual(box.source, original)
        self.assertEqual(app.evidence.read_image('crop'), original)

    def test_direct_crop_rechecks_access_and_rejects_invalid_box(self):
        original = b'P6\n3 2\n255\n' + bytes(range(18))
        row = dict(id='crop',event='HumanDetect',camera=5,bbox=[3,0,2,2])
        app = app_fixture(MemoryEvidence([row], {'crop':original}))
        app.gallery_rows=[row]; app.gallery_list.selection_set(0)
        action = getattr(app, 'open_capture_crop', None)
        self.assertTrue(callable(action))
        with patch.object(viewer, 'PhotoInspector', HeadlessInspector): action()
        self.assertEqual(app.inspectors, [])
        row['bbox']=[1,0,2,2]
        def denied(*args): raise AccessDenied('permission_denied')
        app.home_facade=SimpleNamespace(read_evidence=denied)
        action()
        self.assertEqual(app.inspectors, [])
        self.assertEqual(app.gallery_crop_button.cget('state'), 'disabled')

    def test_open_crop_guard_remains_bound_to_its_original_row_after_selection_changes(self):
        original=b'P6\n2 1\n255\n'+bytes(range(6))
        row={'id':'first','bbox':[0,0,1,1]}; second={'id':'second'}
        store=MemoryEvidence([row,second],{'first':original})
        app=app_fixture(store); app.gallery_rows=[row,second]; app.gallery_list.selection_set(0)
        with patch.object(viewer,'PhotoInspector',HeadlessInspector): app.open_capture_crop()
        box=app.inspectors[0]
        app.gallery_list.selection_set(1)
        store.rows=[second]
        self.assertFalse(box.access_valid())
        self.assertFalse(box.window.winfo_exists())
        self.assertIsNone(box.original)

    def test_recovered_home_issue_is_historical_without_erasing_audit(self):
        app = app_fixture()
        status={'worker_status':'ok','alarm_issue':'unavailable','event_loss':False}
        app.home_facade=SimpleNamespace(status=lambda: status,
                                       evidence_entries=lambda *a: [])
        app.alarm_state.connected()
        app.refresh_view()
        self.assertIn('Incidencia anterior', app.alarm_status.cget('text'))
        self.assertEqual(status['alarm_issue'], 'unavailable')
        status['event_loss']=True
        app.refresh_view()
        self.assertIn('Pérdida de avisos', app.alarm_status.cget('text'))
        self.assertNotIn('Incidencia anterior', app.alarm_status.cget('text'))

    def test_quick_enhancement_changes_only_detail_display_copy(self):
        from vox_cctv_display import DetailDisplay
        app = app_fixture()
        app.detail=6; app.display=DetailDisplay()
        app.display_mode=SimpleNamespace(get=lambda: app.display.mode,
                                         set=lambda value: app.display.select(value))
        original=b'P6\n2 1\n255\n'+bytes([22,22,22,72,72,72])
        app.states[6].publish_original(original,2,1,now=10)
        app.states[6].publish(original,2,1,now=10)
        action=getattr(app,'enhance_detail',None)
        self.assertTrue(callable(action), 'Detail needs an obvious enhancement action')
        action()
        enhanced, mode=app.display.render(6,original,1)
        self.assertEqual(mode,'Sombras fuertes')
        self.assertGreater(enhanced[-6],22)
        self.assertEqual(app.states[6].capture_snapshot(now=11)['ppm'],original)
        self.assertEqual(app.states[6].image()[0],original)


class PhotoPermissionContracts(unittest.TestCase):
    def test_revoked_inspector_access_closes_before_showing_a_crop(self):
        box=HeadlessInspector(None,b'P6\n2 1\n255\n'+bytes(range(6)),
                              {'bbox':[0,0,1,1]},authorise=lambda: False)
        box.toggle_crop()
        self.assertFalse(box.window.winfo_exists())
        self.assertIsNone(box.original)

    def test_open_inspector_revocation_clears_pixels_and_callbacks_on_all_actions(self):
        for action in ('render','fit','zoom','crop'):
            with self.subTest(action=action):
                allowed={'yes':True}
                box=PhotoInspector.__new__(PhotoInspector)
                box.original=box.source=b'P6\n3 2\n255\n'+bytes(range(18))
                box.row={'bbox':[1,0,2,2]}; box.cropped=False; box.zoom=None; box.photo=None
                box.authorise=lambda:allowed['yes']
                box.window=Widget(); box.canvas=Widget(); box.notice=Widget(); box.item=1
                box.after_id='first-render'; box.window.callbacks[box.after_id]=box.render
                box.tk=SimpleNamespace(TclError=RuntimeError,
                                       PhotoImage=lambda **kw:SimpleNamespace(data=kw['data']))
                box.render()
                self.assertEqual(box.photo.data,box.original)
                allowed['yes']=False
                if action=='zoom': box.set_zoom(1)
                elif action=='crop': box.toggle_crop()
                else: getattr(box,action)()
                self.assertFalse(box.window.winfo_exists())
                self.assertIsNone(box.original); self.assertIsNone(box.source); self.assertIsNone(box.photo)
                self.assertEqual(box.window.callbacks,{})


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'Needs an interactive Tk display')
class RealTkUsabilityContracts(unittest.TestCase):
    def test_gallery_first_empty_open_and_live_menu_action(self):
        import tkinter as tk
        class OfflineWorker:
            def __init__(self,*args): self.stream_type='Extra1'
            def start(self): pass
            def stop(self): pass
            def is_alive(self): return False
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {'LOCALAPPDATA':directory}), \
                patch.object(viewer,'CameraWorker',OfflineWorker), \
                patch.object(viewer,'AlarmWorker',OfflineWorker):
            root=tk.Tk(); root.withdraw()
            app=viewer.Viewer(root,'unused')
            try:
                app.open_gallery(); root.update_idletasks()
                self.assertIn('No hay capturas',app.gallery_image.cget('text'))
                app.alarm_state.add(report('VideoBlind'),now=time.monotonic())
                app.select_group('technical')
                self.assertIn('Inicio',app.alarm_events.get(0))
                self.assertEqual(app.gallery_crop_button.cget('state'),'disabled')
            finally: app.close()

    def test_crop_button_invokes_original_crop_and_keeps_context_accessible(self):
        import tkinter as tk
        from vox_cctv_evidence import EvidenceStore
        class OfflineWorker:
            def __init__(self,*args): self.stream_type='Extra1'
            def start(self): pass
            def stop(self): pass
            def is_alive(self): return False
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ,{'LOCALAPPDATA':directory}), \
                patch.object(viewer,'CameraWorker',OfflineWorker), \
                patch.object(viewer,'AlarmWorker',OfflineWorker):
            store=EvidenceStore(Path(directory)/'captures',min_free_bytes=0)
            original=b'P6\n3 2\n255\n'+bytes(range(18))
            store.add({'channel':5,'event':'HumanDetect','status':'Start'},
                      dict(ppm=original,width=3,height=2,source_width=3,source_height=2,
                           stream='Main',frame_age_seconds=1,sequence_id='a'*32,
                           sequence_offset_seconds=0,selection='rostro_detectado',bbox=[1,0,2,2]))
            store.close()
            store=EvidenceStore(Path(directory)/'captures',min_free_bytes=0)
            root=tk.Tk(); root.withdraw()
            app=viewer.Viewer(root,'unused',evidence_store=store)
            try:
                app.open_gallery(); root.update_idletasks()
                self.assertEqual(app.gallery_crop_button.cget('state'),'normal')
                app.gallery_crop_button.invoke(); root.update_idletasks()
                self.assertEqual(len(app.inspectors),1)
                box=app.inspectors[0]
                self.assertTrue(box.cropped)
                self.assertEqual(box.original,original)
                self.assertEqual(box.source,b'P6\n2 2\n255\n'+bytes([3,4,5,6,7,8,12,13,14,15,16,17]))
                box.toggle_crop(); self.assertEqual(box.source,original)
                self.assertEqual(store.read_image(app.gallery_rows[0]['id']),original)
            finally: app.close()


if __name__ == '__main__': unittest.main()
