"""Behavioural tests: no Telegram traffic or production credentials."""
import json
from pathlib import Path
import tempfile
import threading
import time
import sys
import uuid
import unittest
from unittest import mock

try:
    import vox_cctv_phone as phone
except ImportError:
    phone = None


TOKEN = '123456789:' + 'a' * 35


def wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    raise AssertionError('bounded asynchronous operation did not complete')


def clean_worker(worker):
    # Tests must wait before deleting their files; GUI close intentionally does not.
    worker.close()
    worker._thread.join(timeout=2)


class MemoryVault:
    def __init__(self):
        self.record = None
    def read(self):
        return dict(self.record) if self.record else None
    def write(self, token, bot_id, chat_id):
        self.record = {'token': token, 'bot_id': bot_id, 'chat_id': chat_id}
    def delete(self):
        self.record = None


class FakeAPI:
    def __init__(self):
        self.calls = []
        self.updates = []
        self.sent = []
        self.failure = None
        self.gate = None
    def call(self, token, method, parameters):
        self.calls.append((method, dict(parameters)))
        if method == 'getMe':
            return {'id': 123456789, 'is_bot': True, 'first_name': 'CCTV', 'username': 'OwnerCCTVBot'}
        if method == 'getUpdates':
            result, self.updates = self.updates, []
            return result
        if method == 'sendMessage':
            if self.gate:
                self.gate.wait(1)
            self.sent.append(dict(parameters))
            if self.failure:
                raise self.failure
            return {'message_id': len(self.sent), 'chat': {'id': parameters['chat_id'], 'type': 'private'}, 'date': 1791200000, 'text': parameters['text']}
        raise AssertionError('unexpected method')


class NotifierTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(phone, 'phone notifier implementation is missing')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'phone.json'
        self.vault, self.api = MemoryVault(), FakeAPI()
        self.clock = [100.0]
        self.worker = phone.PhoneNotifier(self.path, vault=self.vault, api=self.api,
            clock=lambda: self.clock[0], poll_interval=.01)
        self.addCleanup(clean_worker,self.worker)

    def pair(self):
        self.assertTrue(self.worker.start_pairing(TOKEN))
        wait_for(lambda: self.worker.pairing_info().get('url'))
        info = self.worker.pairing_info()
        nonce = info['url'].split('start=')[1]
        self.api.updates = [{'update_id': 10, 'message': {'message_id': 1, 'date': 1791200000,
            'chat': {'id': 222, 'type': 'private', 'first_name': 'Owner'},
            'from': {'id': 222, 'is_bot': False, 'first_name': 'Owner'}, 'text': '/start ' + nonce}}]
        wait_for(lambda: self.worker.snapshot()['connected'])
        return info

    def test_missing_configuration_never_contacts_or_queues(self):
        self.assertEqual(self.worker.snapshot()['state'], 'Móvil sin conectar')
        self.assertFalse(self.worker.submit({'channel': 1, 'event': 'HumanDetect', 'status': 'Start'}))
        self.assertEqual(self.api.calls, [])

    def test_nonce_binds_private_chat_without_persisting_token_or_other_messages(self):
        info = self.pair()
        self.assertRegex(info['url'], r'^https://t\.me/OwnerCCTVBot\?start=[A-Za-z0-9_-]{43}$')
        raw = self.path.read_text()
        self.assertNotIn(TOKEN, raw)
        self.assertNotIn('nonce', raw)
        self.assertEqual(json.loads(raw)['chat_id'], 222)
        self.assertEqual(self.vault.record['chat_id'], 222)
        self.assertEqual(self.api.sent, [])
        self.assertIsNone(self.worker.pairing_info().get('url'))

    def test_pairing_rejects_groups_spoofed_senders_and_inexact_nonce(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        nonce = self.worker.pairing_info()['url'].split('start=')[1]
        cases = [('group', -222, -222, '/start '+nonce), ('private', 222, 223, '/start '+nonce),
                 ('private', 222, 222, '/start '+nonce+' extra'), ('private', True, True, '/start '+nonce)]
        self.api.updates = [{'update_id': i+1, 'message': {'chat': {'type': kind, 'id': chat},
            'from': {'id': sender, 'is_bot': False}, 'text': text}} for i,(kind,chat,sender,text) in enumerate(cases)]
        wait_for(lambda: len([c for c in self.api.calls if c[0]=='getUpdates']) >= 3)
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertFalse(json.loads(self.path.read_text())['enabled'])
        self.assertIsNone(self.vault.record)

    def test_expired_pairing_and_replayed_nonce_cannot_bind(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        self.clock[0] += 601
        wait_for(lambda: self.worker.snapshot()['state'] == 'Emparejamiento caducado')
        self.assertFalse(self.worker.snapshot()['connected'])
        wait_for(lambda:self.worker.snapshot()['state']!='Desconectando móvil')
        self.assertIsNone(self.vault.record)

    def test_only_recorder_human_car_starts_send_with_camera_cooldown(self):
        self.pair()
        for kind,status in [('VideoBlind','Start'),('MotionDetect','Start'),('HumanDetect','Stop'),('FaceDetect','Start')]:
            self.assertFalse(self.worker.submit({'channel': 1, 'event': kind, 'status': status}))
        self.assertTrue(self.worker.submit({'channel': 1, 'event': 'HumanDetect', 'status': 'Start', 'time': '2026-10-05 15:00:00'}))
        wait_for(lambda: len(self.api.sent)==1)
        self.assertFalse(self.worker.submit({'channel': 1, 'event': 'CarShapeDetect', 'status': 'Start'}))
        self.clock[0] += 120
        self.assertTrue(self.worker.submit({'channel': 1, 'event': 'CarShapeDetect', 'status': 'Start'}))
        wait_for(lambda: len(self.api.sent)==2)
        self.assertEqual(self.api.sent[0]['chat_id'], 222)
        self.assertIn('sin confirmar', self.api.sent[0]['text'])
        self.assertNotIn('intruso', self.api.sent[0]['text'].lower())
        self.assertFalse(self.worker.submit({'channel': True, 'event': 'HumanDetect', 'status': 'Start'}))

    def test_ambiguous_send_is_consumed_once_without_retry(self):
        self.pair()
        self.api.failure = TimeoutError('https://api.telegram.org/bot'+TOKEN+'/sendMessage')
        self.worker.submit({'channel': 3, 'event': 'HumanDetect', 'status': 'Start'})
        wait_for(lambda: self.worker.snapshot()['ambiguous']==1)
        time.sleep(.03)
        self.assertEqual(len(self.api.sent), 1)
        self.assertNotIn(TOKEN, json.dumps(self.worker.snapshot()))
        self.assertFalse(self.worker.submit({'channel': 3, 'event': 'HumanDetect', 'status': 'Start'}))

    def test_revoke_clears_binding_and_prevents_later_submissions(self):
        self.pair()
        self.worker.revoke()
        self.assertFalse(self.worker.submit({'channel': 4, 'event': 'HumanDetect', 'status': 'Start'}))
        self.assertFalse(self.worker.snapshot()['connected'])
        wait_for(lambda:self.worker.snapshot()['state']!='Desconectando móvil')
        self.assertIsNone(self.vault.record)
        self.assertFalse(json.loads(self.path.read_text())['enabled'])
        self.assertEqual(self.api.sent, [])

    def test_forged_config_cannot_redirect_vault_bound_destination(self):
        self.pair()
        self.worker.close()
        config=json.loads(self.path.read_text()); config['chat_id']=999
        self.path.write_text(json.dumps(config))
        other=phone.PhoneNotifier(self.path, vault=self.vault, api=self.api, poll_interval=.01)
        self.addCleanup(clean_worker,other)
        wait_for(lambda:not other.snapshot()['pending'])
        self.assertFalse(other.snapshot()['connected'])
        self.assertFalse(other.submit({'channel': 1, 'event': 'HumanDetect', 'status': 'Start'}))
        self.assertEqual(self.api.sent, [])

    def test_malformed_config_is_disabled_without_network(self):
        self.worker.close()
        self.path.write_text('{"enabled": "true", "chat_id": 222}')
        other=phone.PhoneNotifier(self.path, vault=self.vault, api=self.api)
        self.addCleanup(clean_worker,other)
        self.assertFalse(other.snapshot()['connected'])
        self.assertEqual(self.api.calls, [])

    def test_forwarded_bot_and_edited_messages_cannot_pair(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        nonce=self.worker.pairing_info()['url'].split('start=')[1]
        normal={'chat': {'type':'private','id':222}, 'from': {'id':222,'is_bot':False}, 'text':'/start '+nonce}
        self.api.updates=[{'update_id':1,'edited_message':normal},
            {'update_id':2,'message':dict(normal, forward_origin={'type':'user'})},
            {'update_id':3,'message':dict(normal, via_bot={'id':333})},
            {'update_id':4,'message':dict(normal, **{'from':{'id':222,'is_bot':True}})}]
        wait_for(lambda: len([c for c in self.api.calls if c[0]=='getUpdates']) >=3)
        self.assertFalse(self.worker.snapshot()['connected'])

    def test_queue_is_bounded_and_drops_stale_events_without_blocking_submit(self):
        self.pair()
        self.api.gate=threading.Event()
        self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'})
        wait_for(lambda: any(c[0]=='sendMessage' for c in self.api.calls))
        started=time.monotonic()
        for _ in range(40):
            self.clock[0]+=121
            self.worker.submit({'channel':2,'event':'HumanDetect','status':'Start'})
        self.assertLess(time.monotonic()-started,.1)
        self.assertLessEqual(self.worker.snapshot()['queued'],16)
        self.assertGreater(self.worker.snapshot()['dropped'],0)
        self.clock[0]+=31
        self.api.gate.set()
        wait_for(lambda: self.worker.snapshot()['queued']==0)
        self.assertEqual(len(self.api.sent),1)

    def test_external_disable_prevents_send_even_if_already_paired(self):
        self.pair()
        config=json.loads(self.path.read_text()); config['enabled']=False
        self.path.write_text(json.dumps(config))
        self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'})
        wait_for(lambda: not self.worker.snapshot()['connected'])
        self.assertEqual(self.api.sent,[])

    def test_deleted_credential_prevents_send(self):
        self.pair(); self.vault.delete()
        self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'})
        wait_for(lambda: not self.worker.snapshot()['connected'])
        self.assertEqual(self.api.sent,[])

    def test_restart_revalidates_bot_identity_before_accepting_events(self):
        self.pair(); self.worker.close()
        original=self.api.call
        def wrong_bot(token,method,parameters):
            if method=='getMe': return {'id':999,'is_bot':True,'username':'DifferentBot'}
            return original(token,method,parameters)
        self.api.call=wrong_bot
        other=phone.PhoneNotifier(self.path,vault=self.vault,api=self.api,poll_interval=.01)
        self.addCleanup(clean_worker,other)
        wait_for(lambda:not other.snapshot()['pending'])
        self.assertFalse(other.snapshot()['connected'])
        self.assertFalse(other.submit({'channel':1,'event':'HumanDetect','status':'Start'}))

    def test_auth_failure_stops_future_events_without_exception_detail(self):
        self.pair(); self.api.failure=phone.PhoneError('unauthorized',401)
        self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'})
        wait_for(lambda: not self.worker.snapshot()['connected'])
        self.assertFalse(self.worker.submit({'channel':2,'event':'HumanDetect','status':'Start'}))
        self.assertEqual(len(self.api.sent),1)

    def test_bad_event_types_never_raise_or_send(self):
        self.pair()
        for event in [{'channel':1,'event':[],'status':'Start'}, {'channel':1,'event':{},'status':'Start'},
                      {'channel':1,'event':'HumanDetect','status':[]}, {'channel':'1','event':'HumanDetect','status':'Start'}]:
            with self.subTest(event=event):
                self.assertFalse(self.worker.submit(event))
        self.assertEqual(self.api.sent,[])

    def test_vault_read_failure_disables_future_events(self):
        self.pair()
        def denied(): raise PermissionError('credential denied')
        self.vault.read=denied
        self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'})
        wait_for(lambda: not self.worker.snapshot()['connected'])
        self.assertFalse(self.worker.submit({'channel':2,'event':'HumanDetect','status':'Start'}))
        self.assertEqual(self.api.sent,[])

    def test_two_different_nonce_owners_in_one_batch_do_not_choose_first(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        nonce=self.worker.pairing_info()['url'].split('start=')[1]
        self.api.updates=[{'update_id':i,'message':{'chat':{'id':chat,'type':'private'},
            'from':{'id':chat,'is_bot':False},'text':'/start '+nonce}} for i,chat in [(1,222),(2,333)]]
        wait_for(lambda: self.worker.snapshot()['state']=='Emparejamiento ambiguo; vuelva a conectar')
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertIsNone(self.vault.record)

    def test_repair_rotates_nonce_and_replay_of_previous_nonce_does_not_bind(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        old=self.worker.pairing_info()['url'].split('start=')[1]
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url') and old not in self.worker.pairing_info()['url'])
        self.api.updates=[{'update_id':1,'message':{'chat':{'id':222,'type':'private'},
            'from':{'id':222,'is_bot':False},'text':'/start '+old}}]
        wait_for(lambda: len([c for c in self.api.calls if c[0]=='getUpdates'])>=3)
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertIsNone(self.vault.record)

    def test_other_private_unicode_text_is_ignored_without_cancelling_pairing(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        self.api.updates=[{'update_id':1,'message':{'chat':{'id':999,'type':'private'},
            'from':{'id':999,'is_bot':False},'text':'hola ñ'}}]
        wait_for(lambda: len([c for c in self.api.calls if c[0]=='getUpdates'])>=3)
        self.assertIn('url',self.worker.pairing_info())
        self.assertFalse(self.worker.snapshot()['connected'])

    def test_revoke_attempts_credential_delete_even_when_config_save_fails(self):
        self.pair()
        with mock.patch.object(phone,'_atomic_config',side_effect=phone.PhoneError('configuration')):
            self.worker.revoke()
            wait_for(lambda:self.worker.snapshot()['state']!='Desconectando móvil')
        self.assertIsNone(self.vault.record)
        other=phone.PhoneNotifier(self.path,vault=self.vault,api=self.api,poll_interval=.01)
        self.addCleanup(clean_worker,other)
        wait_for(lambda:not other.snapshot()['pending'])
        self.assertFalse(other.snapshot()['connected'])

    def test_late_getme_after_revoke_cannot_restore_pairing(self):
        entered,release=threading.Event(),threading.Event()
        original=self.api.call
        def delayed(token,method,parameters):
            if method=='getMe': entered.set(); release.wait(1)
            return original(token,method,parameters)
        self.api.call=delayed
        self.worker.start_pairing(TOKEN)
        self.assertTrue(entered.wait(1))
        self.worker.revoke(); release.set()
        time.sleep(.03)
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertNotIn('url',self.worker.pairing_info())
        self.assertFalse(json.loads(self.path.read_text())['enabled'])

    def test_late_nonce_reply_after_revoke_cannot_commit_binding(self):
        entered,release=threading.Event(),threading.Event()
        original=self.api.call
        def delayed(token,method,parameters):
            if method=='getUpdates': entered.set(); release.wait(1)
            return original(token,method,parameters)
        self.api.call=delayed
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        nonce=self.worker.pairing_info()['url'].split('start=')[1]
        self.assertTrue(entered.wait(1))
        self.api.updates=[{'update_id':1,'message':{'chat':{'id':222,'type':'private'},
            'from':{'id':222,'is_bot':False},'text':'/start '+nonce}}]
        self.worker.revoke(); release.set()
        time.sleep(.03)
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertIsNone(self.vault.record)

    def test_valid_nonce_reply_arriving_after_deadline_does_not_commit(self):
        entered,release=threading.Event(),threading.Event()
        original=self.api.call
        def delayed(token,method,parameters):
            if method=='getUpdates': entered.set(); release.wait(1)
            return original(token,method,parameters)
        self.api.call=delayed
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        nonce=self.worker.pairing_info()['url'].split('start=')[1]
        self.assertTrue(entered.wait(1))
        self.api.updates=[{'update_id':1,'message':{'chat':{'id':222,'type':'private'},
            'from':{'id':222,'is_bot':False},'text':'/start '+nonce}}]
        self.clock[0]+=601; release.set()
        wait_for(lambda: self.worker.snapshot()['state']=='Emparejamiento caducado')
        self.assertIsNone(self.vault.record)

    def test_failed_pairing_commit_leaves_disabled_configuration_and_no_credential(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        nonce=self.worker.pairing_info()['url'].split('start=')[1]
        with mock.patch.object(phone,'_atomic_config',side_effect=phone.PhoneError('configuration')):
            self.api.updates=[{'update_id':1,'message':{'chat':{'id':222,'type':'private'},
                'from':{'id':222,'is_bot':False},'text':'/start '+nonce}}]
            wait_for(lambda: self.worker.snapshot()['state']=='No se pudo emparejar')
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertIsNone(self.vault.record)
        self.assertFalse(json.loads(self.path.read_text())['enabled'])

    def test_failed_credential_delete_still_persists_disabled_configuration(self):
        self.pair()
        self.vault.delete=lambda: (_ for _ in ()).throw(PermissionError('denied'))
        self.worker.revoke()
        wait_for(lambda:self.worker.snapshot()['state']!='Desconectando móvil')
        self.assertFalse(json.loads(self.path.read_text())['enabled'])
        other=phone.PhoneNotifier(self.path,vault=self.vault,api=self.api,poll_interval=.01)
        self.addCleanup(clean_worker,other)
        self.assertFalse(other.snapshot()['connected'])

    def test_double_revocation_failure_reports_session_only_stop(self):
        self.pair()
        self.vault.delete=lambda: (_ for _ in ()).throw(PermissionError('denied'))
        with mock.patch.object(phone,'_atomic_config',side_effect=phone.PhoneError('configuration')):
            self.worker.revoke()
            wait_for(lambda:self.worker.snapshot()['state']!='Desconectando móvil')
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertIn('sólo en esta sesión',self.worker.snapshot()['state'])
        self.assertFalse(self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'}))

    def test_ui_commands_remain_prompt_while_worker_vault_write_is_blocked(self):
        entered,release=threading.Event(),threading.Event()
        original=self.vault.write
        def delayed(token,bot_id,chat_id):
            entered.set(); release.wait(2); original(token,bot_id,chat_id)
        self.vault.write=delayed
        self.worker.start_pairing(TOKEN)
        wait_for(lambda: self.worker.pairing_info().get('url'))
        nonce=self.worker.pairing_info()['url'].split('start=')[1]
        self.api.updates=[{'update_id':1,'message':{'chat':{'id':222,'type':'private'},
            'from':{'id':222,'is_bot':False},'text':'/start '+nonce}}]
        self.assertTrue(entered.wait(1))
        durations=[]
        for action in [self.worker.snapshot,self.worker.pairing_info,
            lambda:self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'}),self.worker.revoke]:
            before=time.monotonic(); action(); durations.append(time.monotonic()-before)
        release.set()
        wait_for(lambda: self.vault.record is None and self.worker.snapshot()['state']=='Móvil sin conectar')
        self.assertFalse(json.loads(self.path.read_text())['enabled'])
        self.assertLess(max(durations),.1)
        self.assertEqual(self.api.sent,[])

    def test_start_pairing_and_close_do_not_wait_for_blocked_metadata_write(self):
        entered,release=threading.Event(),threading.Event()
        original=phone._atomic_config
        def delayed(*args,**kwargs):
            entered.set(); release.wait(2); return original(*args,**kwargs)
        with mock.patch.object(phone,'_atomic_config',side_effect=delayed):
            before=time.monotonic(); self.worker.start_pairing(TOKEN); elapsed=time.monotonic()-before
            self.assertTrue(entered.wait(1))
            before=time.monotonic(); self.worker.close(); closing=time.monotonic()-before
            release.set()
            wait_for(lambda: self.path.exists())
        self.assertLess(elapsed,.1)
        self.assertLess(closing,.1)
        self.assertFalse(json.loads(self.path.read_text())['enabled'])

    def test_constructor_does_not_wait_for_blocked_configuration_read(self):
        self.worker.close()
        entered,release=threading.Event(),threading.Event()
        original=phone._config
        def delayed(path):
            entered.set(); release.wait(2); return original(path)
        with mock.patch.object(phone,'_config',side_effect=delayed):
            before=time.monotonic()
            other=phone.PhoneNotifier(self.path,vault=self.vault,api=self.api,poll_interval=.01)
            elapsed=time.monotonic()-before
            self.addCleanup(clean_worker,other)
            self.assertTrue(entered.wait(1)); release.set()
        self.assertLess(elapsed,.1)

    def test_revoke_wins_when_enabled_metadata_commit_is_blocked(self):
        entered,release=threading.Event(),threading.Event()
        original=phone._atomic_config
        def delayed(path,value,*args,**kwargs):
            if value.get('enabled'):
                entered.set(); release.wait(2)
            return original(path,value,*args,**kwargs)
        self.worker.start_pairing(TOKEN)
        wait_for(lambda:self.worker.pairing_info().get('url'))
        nonce=self.worker.pairing_info()['url'].split('start=')[1]
        with mock.patch.object(phone,'_atomic_config',side_effect=delayed):
            self.api.updates=[{'update_id':1,'message':{'chat':{'id':222,'type':'private'},
                'from':{'id':222,'is_bot':False},'text':'/start '+nonce}}]
            self.assertTrue(entered.wait(1))
            before=time.monotonic(); self.worker.revoke(); elapsed=time.monotonic()-before
            self.assertFalse(self.worker.snapshot()['connected'])
            release.set()
            wait_for(lambda:self.worker.snapshot()['state']=='Móvil sin conectar')
        self.assertLess(elapsed,.1)
        self.assertIsNone(self.vault.record)
        self.assertFalse(json.loads(self.path.read_text())['enabled'])

    def test_snapshot_stays_prompt_during_auth_failure_metadata_cleanup(self):
        self.pair()
        entered,release=threading.Event(),threading.Event()
        original=phone._atomic_config
        def delayed(*args,**kwargs):
            entered.set(); release.wait(2); return original(*args,**kwargs)
        self.api.failure=phone.PhoneError('unauthorized',401)
        with mock.patch.object(phone,'_atomic_config',side_effect=delayed):
            self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'})
            self.assertTrue(entered.wait(1))
            before=time.monotonic(); snapshot=self.worker.snapshot(); elapsed=time.monotonic()-before
            release.set()
        self.assertFalse(snapshot['connected'])
        self.assertLess(elapsed,.1)

    def test_event_expiring_during_slow_credential_read_is_not_sent(self):
        self.pair()
        entered,release=threading.Event(),threading.Event()
        original=self.vault.read
        def delayed():
            entered.set(); release.wait(2); return original()
        self.vault.read=delayed
        self.worker.submit({'channel':1,'event':'HumanDetect','status':'Start'})
        self.assertTrue(entered.wait(1))
        self.clock[0]+=31; release.set()
        wait_for(lambda:self.worker.snapshot()['dropped']>=1 or bool(self.api.sent))
        self.assertEqual(self.api.sent,[])
        self.assertEqual(self.worker.snapshot()['dropped'],1)

    def test_pairing_never_acknowledges_unrelated_pending_updates(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda:self.worker.pairing_info().get('url'))
        self.api.updates=[{'update_id':75,'message':{'chat':{'id':999,'type':'private'},
            'from':{'id':999,'is_bot':False},'text':'unrelated old message'}}]
        wait_for(lambda:len([c for c in self.api.calls if c[0]=='getUpdates'])>=3)
        polls=[parameters for method,parameters in self.api.calls if method=='getUpdates']
        self.assertTrue(all(parameters['offset']==0 for parameters in polls))
        self.assertTrue(all(method in ('getMe','getUpdates') for method,_ in self.api.calls))
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertNotIn('unrelated old message',self.path.read_text())

    def test_full_unmatched_backlog_stops_without_acknowledging_or_flushing(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda:self.worker.pairing_info().get('url'))
        self.api.updates=[{'update_id':i+1,'message':{'chat':{'id':999,'type':'private'},
            'from':{'id':999,'is_bot':False},'text':'old message'}} for i in range(100)]
        wait_for(lambda:self.worker.snapshot()['state']=='Bot con cola pendiente; use un bot nuevo')
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertIsNone(self.vault.record)
        self.assertTrue(all(p['offset']==0 for method,p in self.api.calls if method=='getUpdates'))
        self.assertTrue(all(method in ('getMe','getUpdates') for method,_ in self.api.calls))

    def test_oversized_backlog_stops_at_budget_without_acknowledging(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda:self.worker.pairing_info().get('url'))
        self.api.updates=[{'update_id':i+1} for i in range(101)]
        wait_for(lambda:self.worker.snapshot()['state']=='Bot con cola pendiente; use un bot nuevo')
        self.assertFalse(self.worker.snapshot()['connected'])
        self.assertIsNone(self.vault.record)

    def test_valid_nonce_among_one_hundred_pending_updates_still_pairs_without_ack(self):
        self.worker.start_pairing(TOKEN)
        wait_for(lambda:self.worker.pairing_info().get('url'))
        nonce=self.worker.pairing_info()['url'].split('start=')[1]
        self.api.updates=[{'update_id':i+1,'message':{'chat':{'id':999,'type':'private'},
            'from':{'id':999,'is_bot':False},'text':'old message'}} for i in range(99)] + [
            {'update_id':100,'message':{'chat':{'id':222,'type':'private'},
            'from':{'id':222,'is_bot':False},'text':'/start '+nonce}}]
        wait_for(lambda:self.worker.snapshot()['connected'])
        count=len([c for c in self.api.calls if c[0]=='getUpdates'])
        time.sleep(.03)
        self.assertEqual(len([c for c in self.api.calls if c[0]=='getUpdates']),count)
        self.assertTrue(all(p['offset']==0 for method,p in self.api.calls if method=='getUpdates'))
        self.assertEqual(self.vault.record['chat_id'],222)


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(phone, 'phone notifier implementation is missing')

    def test_transport_uses_fixed_tls_host_post_and_bounded_response(self):
        calls=[]
        class Response:
            status=200
            def read(self, amount):
                calls.append(('read', amount))
                return b'{"ok":true,"result":{"id":123456789,"is_bot":true}}'
        class Connection:
            def __init__(self, host, **options): calls.append(('host',host,options))
            def request(self, method, path, body, headers): calls.append(('request',method,path,body,headers))
            def getresponse(self): return Response()
            def close(self): calls.append(('closed',))
        api=phone.TelegramAPI(connection_factory=Connection)
        self.assertEqual(api.call(TOKEN,'getMe',{})['id'],123456789)
        self.assertEqual(calls[0][1], 'api.telegram.org')
        self.assertLessEqual(calls[0][2]['timeout'], 5)
        self.assertEqual(calls[1][1], 'POST')
        self.assertGreater(calls[2][1], 0)

    def test_redirects_and_oversized_or_invalid_replies_never_follow_or_leak(self):
        for status,body in [(302,b''),(200,b'x'*262145),(200,b'{"ok":"true","result":{}}'),(401,b'{"ok":false,"description":"secret"}')]:
            class Response:
                def read(self, amount): return body
            Response.status=status
            class Connection:
                def __init__(self,*a,**kw): pass
                def request(self,*a,**kw): pass
                def getresponse(self): return Response()
                def close(self): pass
            with self.subTest(status=status), self.assertRaises(phone.PhoneError) as err:
                phone.TelegramAPI(connection_factory=Connection).call(TOKEN,'getMe',{})
            self.assertNotIn(TOKEN,str(err.exception))
            self.assertNotIn('secret',str(err.exception))

    def test_read1_rejects_overflow_and_closes_connection(self):
        closed=[]
        class Response:
            status=200
            def read1(self,amount): return b'x'*amount
        class Connection:
            def __init__(self,*args,**kwargs): pass
            def request(self,*args,**kwargs): pass
            def getresponse(self): return Response()
            def close(self): closed.append(True)
        with self.assertRaises(phone.PhoneError):
            phone.TelegramAPI(connection_factory=Connection).call(TOKEN,'getMe',{})
        self.assertEqual(closed,[True])

    def test_transport_exception_does_not_expose_token_or_endpoint(self):
        class Connection:
            def __init__(self,*args,**kwargs): pass
            def request(self,*args,**kwargs): raise TimeoutError('https://api.telegram.org/bot'+TOKEN+'/getMe')
            def close(self): pass
        with self.assertRaises(phone.PhoneError) as err:
            phone.TelegramAPI(connection_factory=Connection).call(TOKEN,'getMe',{})
        self.assertEqual(str(err.exception),'network')
        self.assertIsNone(err.exception.__cause__)


@unittest.skipUnless(sys.platform=='win32','native Windows Credential Manager test')
class WindowsVaultTests(unittest.TestCase):
    def test_temporary_exact_target_roundtrip_and_cleanup_without_real_token(self):
        self.assertIsNotNone(phone)
        vault=phone.WindowsCredentialVault(phone.CREDENTIAL_TARGET+'/test-'+uuid.uuid4().hex)
        try:
            self.assertIsNone(vault.read())
            vault.write(TOKEN,123456789,222)
            record=vault.read()
            self.assertEqual(record['bot_id'],123456789)
            self.assertEqual(record['chat_id'],222)
            self.assertEqual(record['token'],TOKEN)
        finally:
            vault.delete()
        self.assertIsNone(vault.read())


if __name__ == '__main__':
    unittest.main()
