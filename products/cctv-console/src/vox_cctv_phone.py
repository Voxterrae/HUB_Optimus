"""Opt-in, text-only recorder alerts to a nonce-verified private Telegram chat.

No import-time credential reads or network calls. PhoneNotifier owns one daemon
worker; Tk may call start_pairing(), submit(), snapshot(), pairing_info(), revoke()
and close(). Complete 'Conectar y activar avisos' on the PC with a dedicated bot:
enter its token in a masked field, display pairing_info()['url'] locally, open
that link on the owner's phone and press Start within ten minutes. Do not log the
link or token. Binding then activates future Human/Car starts, not past events.
No photos, chat history, groups, arbitrary endpoints or ambiguous send retries.
Pairing never acknowledges or flushes pending bot updates. A full unrelated
batch stops with a request to use a new dedicated bot; its old queue is retained.

Telegram contract: https://core.telegram.org/bots/api and
https://core.telegram.org/bots/features#deep-linking (checked 2026-10-05).
"""
from collections import deque
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import http.client
import json
import math
import os
from pathlib import Path
import re
import secrets
import ssl
import sys
import tempfile
import threading
import time


CREDENTIAL_TARGET = 'Voxterrae/CCTV/TelegramBot/v1'
_TOKEN = re.compile(r'[0-9]{5,20}:[A-Za-z0-9_-]{20,128}\Z')
_USERNAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{4,31}\Z')
_KINDS = frozenset(('HumanDetect', 'appEventHumanDetectAlarm', 'CarShapeDetect'))
_CONFIG_KEYS = frozenset(('schema_version', 'enabled', 'credential_target', 'bot_id', 'chat_id', 'verified_at'))
_MAX_BODY = 262144


class PhoneError(Exception):
    """Only allowlisted codes survive; URL, token and Telegram text never do."""
    def __init__(self, code='network', status=None):
        self.code = code if code in ('network','unauthorized','forbidden','busy','rate_limit',
                                    'response','redirect','credential','configuration','input','cancelled') else 'network'
        self.status = status if type(status) is int and status in (401,403,409,429) else None
        super().__init__(self.code)


def _positive_id(value):
    return type(value) is int and 0 < value < 2**52


def _valid_token(value):
    return type(value) is str and _TOKEN.fullmatch(value) is not None


class TelegramAPI:
    """Fixed TLS peer, POST JSON, no environment proxy or redirect machinery."""
    def __init__(self, *, connection_factory=http.client.HTTPSConnection):
        self._connection_factory = connection_factory

    def call(self, token, method, parameters):
        if not _valid_token(token) or method not in ('getMe','getUpdates','sendMessage') or type(parameters) is not dict:
            raise PhoneError('input')
        body = json.dumps(parameters, ensure_ascii=False, separators=(',',':')).encode('utf-8')
        if len(body) > 4096:
            raise PhoneError('input')
        connection = None
        deadline = time.monotonic() + 5
        try:
            connection = self._connection_factory('api.telegram.org', timeout=5, context=ssl.create_default_context())
            connection.request('POST', '/bot'+token+'/'+method, body,
                {'Content-Type':'application/json; charset=utf-8', 'Accept':'application/json'})
            if getattr(connection, 'sock', None) is not None:
                connection.sock.settimeout(max(.01, deadline-time.monotonic()))
            response = connection.getresponse()
            if 300 <= response.status < 400:
                raise PhoneError('redirect')
            if response.status in (401,403,409,429):
                raise PhoneError({401:'unauthorized',403:'forbidden',409:'busy',429:'rate_limit'}[response.status], response.status)
            if response.status != 200:
                raise PhoneError('response')
            read1 = getattr(response, 'read1', None)
            if read1 is None:
                raw = response.read(_MAX_BODY+1)
            else:
                chunks, size = [], 0
                while True:
                    remaining = deadline-time.monotonic()
                    if remaining <= 0:
                        raise PhoneError('network')
                    if getattr(connection, 'sock', None) is not None:
                        connection.sock.settimeout(remaining)
                    chunk = read1(min(8192, _MAX_BODY+1-size))
                    if not chunk:
                        break
                    chunks.append(chunk); size += len(chunk)
                    if size > _MAX_BODY:
                        raise PhoneError('response')
                raw = b''.join(chunks)
            if len(raw) > _MAX_BODY:
                raise PhoneError('response')
            result = json.loads(raw)
            if type(result) is not dict or result.get('ok') is not True or 'result' not in result:
                code = result.get('error_code') if type(result) is dict else None
                if type(code) is int and code in (401,403,409,429):
                    raise PhoneError({401:'unauthorized',403:'forbidden',409:'busy',429:'rate_limit'}[code], code)
                raise PhoneError('response')
            return result['result']
        except PhoneError:
            raise
        except Exception:
            raise PhoneError('network') from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass


class WindowsCredentialVault:
    """Read/write/delete only one exact user-local generic Windows credential.

    The credential blob also authenticates the approved bot/chat binding, so
    modifying JSON metadata cannot redirect alerts to a different chat.
    """
    def __init__(self, target=CREDENTIAL_TARGET):
        if type(target) is not str or not (target == CREDENTIAL_TARGET or target.startswith(CREDENTIAL_TARGET+'/test-')):
            raise PhoneError('credential')
        self.target = target

    def _api(self):
        if sys.platform != 'win32':
            raise PhoneError('credential')
        class Credential(ctypes.Structure):
            _fields_ = [('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),
                ('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),
                ('CredentialBlob',ctypes.POINTER(ctypes.c_ubyte)),('Persist',wintypes.DWORD),
                ('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),('TargetAlias',wintypes.LPWSTR),
                ('UserName',wintypes.LPWSTR)]
        api=ctypes.WinDLL('advapi32',use_last_error=True)
        api.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(Credential))]
        api.CredReadW.restype=wintypes.BOOL
        api.CredWriteW.argtypes=[ctypes.POINTER(Credential),wintypes.DWORD]; api.CredWriteW.restype=wintypes.BOOL
        api.CredDeleteW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD]; api.CredDeleteW.restype=wintypes.BOOL
        api.CredFree.argtypes=[ctypes.c_void_p]; api.CredFree.restype=None
        return api,Credential

    def read(self):
        api,Credential=self._api(); pointer=ctypes.POINTER(Credential)()
        if not api.CredReadW(self.target,1,0,ctypes.byref(pointer)):
            if ctypes.get_last_error()==1168:
                return None
            raise PhoneError('credential')
        try:
            size=pointer.contents.CredentialBlobSize
            if not 0 < size <= 2048:
                raise PhoneError('credential')
            raw=ctypes.string_at(pointer.contents.CredentialBlob,size)
            return _credential(json.loads(raw.decode('utf-8')))
        except Exception:
            raise PhoneError('credential') from None
        finally:
            if pointer:
                if 0 < pointer.contents.CredentialBlobSize <= 2048:
                    ctypes.memset(pointer.contents.CredentialBlob,0,pointer.contents.CredentialBlobSize)
                api.CredFree(pointer)

    def write(self, token, bot_id, chat_id):
        record=_credential({'token':token,'bot_id':bot_id,'chat_id':chat_id})
        if record is None:
            raise PhoneError('credential')
        raw=json.dumps(record,separators=(',',':')).encode('utf-8')
        api,Credential=self._api(); buffer=(ctypes.c_ubyte*len(raw)).from_buffer_copy(raw)
        item=Credential(); item.Type=1; item.TargetName=self.target; item.Persist=2
        item.CredentialBlobSize=len(raw); item.CredentialBlob=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte))
        item.UserName='CCTV Telegram binding'
        try:
            if not api.CredWriteW(ctypes.byref(item),0):
                raise PhoneError('credential')
        finally:
            ctypes.memset(buffer,0,len(raw))

    def delete(self):
        api,_=self._api()
        if not api.CredDeleteW(self.target,1,0) and ctypes.get_last_error()!=1168:
            raise PhoneError('credential')


def _credential(record):
    if (type(record) is dict and set(record)=={'token','bot_id','chat_id'} and
        _valid_token(record['token']) and _positive_id(record['bot_id']) and _positive_id(record['chat_id']) and
        record['token'].split(':')[0] == str(record['bot_id'])):
        return dict(record)
    return None


def _disabled():
    return {'schema_version':1,'enabled':False,'credential_target':CREDENTIAL_TARGET}


def _config(path):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
            return None
        value=json.loads(path.read_text(encoding='utf-8'))
        if type(value) is not dict or not set(value)<=_CONFIG_KEYS or value.get('schema_version') != 1 or type(value.get('schema_version')) is not int:
            return None
        if value.get('credential_target') != CREDENTIAL_TARGET or type(value.get('enabled')) is not bool:
            return None
        if not value['enabled']:
            return None
        if set(value)!=_CONFIG_KEYS or not _positive_id(value['bot_id']) or not _positive_id(value['chat_id']):
            return None
        if type(value['verified_at']) is not str or len(value['verified_at'])>40:
            return None
        datetime.fromisoformat(value['verified_at'])
        return value
    except Exception:
        return None


def _atomic_config(path, value, guard=None):
    temporary=None
    try:
        if path.is_symlink():
            raise PhoneError('configuration')
        path.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
            prefix=path.name+'.',suffix='.tmp',delete=False) as output:
            temporary=Path(output.name)
            json.dump(value,output,ensure_ascii=False,separators=(',',':'))
            output.flush(); os.fsync(output.fileno())
        if guard is not None and not guard():
            raise PhoneError('cancelled')
        os.replace(temporary,path)
    except PhoneError:
        raise
    except Exception:
        raise PhoneError('configuration') from None
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


class PhoneNotifier:
    """One background worker and a bounded queue; disabled until owner pairing.

    Configuration must be an absolute metadata-only path in the local app data.
    All vault/file/network I/O belongs to the worker. Pairing activates alerts.
    revoke() blocks future work immediately; persistence completes asynchronously
    and its state reports pending/failure truthfully. An emission already begun
    may still complete. close() never waits on I/O or on the background thread.
    API acceptance does not prove phone delivery or a genuine person/vehicle.
    """
    def __init__(self, config_path, *, vault=None, api=None, clock=time.monotonic, poll_interval=4):
        self.path=Path(config_path)
        if not self.path.is_absolute():
            raise PhoneError('configuration')
        self.vault=vault if vault is not None else WindowsCredentialVault()
        self.api=api if api is not None else TelegramAPI()
        self.clock=clock
        self.poll_interval=max(.01,min(4,float(poll_interval)))
        self._lock=threading.RLock(); self._wake=threading.Event(); self._stop=threading.Event()
        self._queue=deque(); self._last={}; self._generation=0; self._pair=None
        self._record=None; self._connected=False; self._config=None
        self._state='Móvil sin conectar'
        self._command=('restore',0,None); self._active_command=None
        self._sent=0; self._ambiguous=0; self._dropped=0; self._in_flight=False
        self._thread=threading.Thread(target=self._run,name='CCTV-phone',daemon=True)
        self._thread.start()

    def snapshot(self):
        with self._lock:
            return {'state':self._state,'connected':self._connected,'queued':len(self._queue),
                'sent':self._sent,'ambiguous':self._ambiguous,'dropped':self._dropped,'in_flight':self._in_flight,
                'pending':self._command is not None or self._active_command is not None or self._pair is not None}

    def pairing_info(self):
        with self._lock:
            if self._pair:
                return {'state':self._state,'url':'https://t.me/'+self._pair['username']+'?start='+self._pair['nonce'],
                    'expires_seconds':max(0,int(self._pair['deadline']-self.clock()))}
            return {'state':self._state}

    def _clear(self, state):
        self._generation+=1; self._queue.clear(); self._last.clear()
        self._connected=False; self._record=None; self._command=None; self._pair=None
        self._state=state

    def start_pairing(self, token):
        if not _valid_token(token):
            return False
        with self._lock:
            if self._stop.is_set():
                return False
            self._clear('Preparando enlace')
            self._config=None; self._command=('pair',self._generation,token); self._wake.set()
            return True

    def revoke(self):
        with self._lock:
            if self._stop.is_set():
                return
            self._clear('Desconectando móvil'); self._config=None
            self._command=('revoke',self._generation,None)
            self._wake.set()

    def close(self):
        with self._lock:
            if self._stop.is_set():
                return
            pending_kind=self._command[0] if self._command else None
            active_kind=self._active_command[0] if self._active_command else None
            cleanup=self._pair is not None or pending_kind in ('pair','revoke') or active_kind in ('pair','revoke')
            self._clear('Móvil cerrado'); self._stop.set(); self._wake.set()
            if cleanup:
                self._command=('close_cleanup',self._generation,None)

    def _current(self, generation):
        with self._lock:
            return generation==self._generation and not self._stop.is_set()

    def _persist_disabled(self):
        """Worker-only cleanup; one failure never prevents the other attempt."""
        failures=0
        try:
            _atomic_config(self.path,_disabled())
        except Exception:
            failures+=1
        try:
            self.vault.delete()
        except Exception:
            failures+=1
        return failures

    @staticmethod
    def _cleanup_state(failures):
        if failures==2:
            return 'Avisos detenidos sólo en esta sesión; revocación no guardada'
        return 'Avisos detenidos; limpieza local pendiente' if failures else 'Móvil sin conectar'

    def _run_command(self, command):
        kind,generation,token=command
        if kind=='restore':
            self._restore_binding(generation)
            return
        failures=self._persist_disabled()
        with self._lock:
            if generation!=self._generation:
                return
            if kind in ('revoke','close_cleanup'):
                self._state=('Móvil cerrado' if kind=='close_cleanup' and not failures else self._cleanup_state(failures))
                return
            if failures:
                self._state=self._cleanup_state(failures)
                return
            if self._stop.is_set():
                return
            self._state='Comprobando bot'
        self._begin_pairing(token,generation)

    def submit(self, event):
        if (type(event) is not dict or type(event.get('event')) is not str or event.get('event') not in _KINDS or event.get('status')!='Start' or
            type(event.get('channel')) is not int or not 1<=event['channel']<=7):
            return False
        now=self.clock()
        if type(now) not in (int,float) or not math.isfinite(now):
            return False
        stamp=event.get('time')
        if type(stamp) is str and len(stamp)==19:
            try:
                datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S')
            except ValueError:
                stamp=None
        else:
            stamp=None
        safe={'channel':event['channel'],'event':event['event'],'time':stamp}
        with self._lock:
            if not self._connected or self._stop.is_set():
                return False
            channel=safe['channel']
            if now-self._last.get(channel,-math.inf)<120:
                return False
            if len(self._queue)>=16:
                self._dropped+=1
                return False
            self._last[channel]=now
            self._queue.append((self._generation,now,safe)); self._wake.set()
            return True

    def _get_bot(self, token):
        bot=self.api.call(token,'getMe',{})
        if (type(bot) is not dict or bot.get('is_bot') is not True or not _positive_id(bot.get('id')) or
            str(bot['id'])!=token.split(':')[0] or type(bot.get('username')) is not str or not _USERNAME.fullmatch(bot['username'])):
            raise PhoneError('response')
        return {'id':bot['id'],'username':bot['username']}

    def _restore_binding(self, generation):
        try:
            config=_config(self.path)
            with self._lock:
                if generation!=self._generation or self._stop.is_set():
                    return
                self._config=config
                if config is None:
                    return
                self._state='Comprobando móvil'
            record=_credential(self.vault.read())
            if not record or (record['bot_id'],record['chat_id'])!=(config['bot_id'],config['chat_id']):
                raise PhoneError('credential')
            if not self._current(generation):
                return
            bot=self._get_bot(record['token'])
            if bot['id']!=config['bot_id']:
                raise PhoneError('credential')
            with self._lock:
                if generation==self._generation and not self._stop.is_set():
                    self._record=record; self._connected=True; self._state='Móvil conectado'
        except Exception:
            with self._lock:
                if generation==self._generation:
                    self._clear('Móvil sin conectar')

    def _begin_pairing(self, token, generation):
        try:
            bot=self._get_bot(token)
            with self._lock:
                if generation!=self._generation or self._stop.is_set():
                    return
                self._pair={'token':token,'bot_id':bot['id'],'username':bot['username'],'nonce':secrets.token_urlsafe(32),
                    'deadline':self.clock()+600,'polls':0}
                self._state='Abra el enlace en su teléfono'
        except Exception as error:
            with self._lock:
                if generation==self._generation:
                    self._clear('Bot no disponible' if not isinstance(error,PhoneError) or error.status!=401 else 'Token rechazado')

    def _poll_pairing(self, generation, pair):
        if self.clock()>=pair['deadline'] or pair['polls']>=150:
            with self._lock:
                if generation==self._generation:
                    self._clear('Emparejamiento caducado')
            return
        pair['polls']+=1
        try:
            updates=self.api.call(pair['token'],'getUpdates',{'offset':0,'limit':100,'timeout':0,'allowed_updates':['message']})
            if type(updates) is not list:
                raise PhoneError('response')
            if len(updates)>100:
                with self._lock:
                    if generation==self._generation:
                        self._clear('Bot con cola pendiente; use un bot nuevo')
                return
            full_batch=len(updates)==100
            chat_ids=set()
            for update in updates:
                if type(update) is not dict or type(update.get('update_id')) is not int or update['update_id']<0:
                    continue
                message=update.get('message')
                if type(message) is not dict or any(k in message for k in ('sender_chat','forward_origin','forward_from',
                    'forward_date','forward_sender_name','forward_from_chat','via_bot','business_connection_id')):
                    continue
                chat,sender=message.get('chat'),message.get('from')
                if (type(chat) is dict and type(sender) is dict and chat.get('type')=='private' and
                    _positive_id(chat.get('id')) and _positive_id(sender.get('id')) and chat['id']==sender['id'] and
                    sender.get('is_bot') is False and type(message.get('text')) is str and message['text'].isascii() and
                    len(message['text'])==len('/start '+pair['nonce']) and
                    secrets.compare_digest(message['text'],'/start '+pair['nonce'])):
                    chat_ids.add(chat['id'])
            # Other updates and all their text are discarded, never persisted.
            updates=None
            if len(chat_ids)>1:
                with self._lock:
                    if generation==self._generation:
                        self._clear('Emparejamiento ambiguo; vuelva a conectar')
                return
            if not chat_ids and full_batch:
                with self._lock:
                    if generation==self._generation:
                        self._clear('Bot con cola pendiente; use un bot nuevo')
                return
            if chat_ids:
                chat_id=chat_ids.pop()
                with self._lock:
                    if generation!=self._generation or self._stop.is_set() or self.clock()>=pair['deadline']:
                        return
                config={'schema_version':1,'enabled':True,'credential_target':CREDENTIAL_TARGET,
                    'bot_id':pair['bot_id'],'chat_id':chat_id,'verified_at':datetime.now(timezone.utc).isoformat()}
                try:
                    self.vault.write(pair['token'],pair['bot_id'],chat_id)
                    valid=lambda:self._current(generation) and self.clock()<pair['deadline']
                    if not valid():
                        self._persist_disabled()
                        return
                    _atomic_config(self.path,config,guard=valid)
                except Exception:
                    self._persist_disabled()
                    raise PhoneError('configuration') from None
                with self._lock:
                    current=generation==self._generation and not self._stop.is_set() and self.clock()<pair['deadline']
                    if current:
                        self._record={'token':pair['token'],'bot_id':pair['bot_id'],'chat_id':chat_id}
                        self._config=config; self._connected=True; self._pair=None; self._state='Móvil conectado'
                if not current:
                    self._persist_disabled()
        except Exception as error:
            with self._lock:
                if generation==self._generation:
                    status=error.status if isinstance(error,PhoneError) else None
                    self._clear('Telegram ocupado; use un bot propio sin webhook' if status==409 else
                                'Token rechazado' if status==401 else 'No se pudo emparejar')

    def _send(self, generation, queued_at, event):
        with self._lock:
            if generation!=self._generation or not self._connected or self._stop.is_set():
                return
            if self.clock()-queued_at>30 or self.clock()<queued_at:
                self._dropped+=1
                return
        attempted=False
        try:
            record=_credential(self.vault.read())
            config=_config(self.path)
            with self._lock:
                if generation!=self._generation or not self._connected or self._stop.is_set():
                    return
                if not record or record!=self._record or config!=self._config:
                    self._clear('Móvil sin conectar')
                    return
                now=self.clock()
                if type(now) not in (int,float) or not math.isfinite(now) or not 0<=now-queued_at<=30:
                    self._dropped+=1
                    return
                self._in_flight=True
            detector='vehículo' if event['event']=='CarShapeDetect' else 'persona'
            text=f"Aviso del grabador, sin confirmar.\nCámara {event['channel']}: detector de {detector}."
            if event['time']:
                text+='\nHora del grabador: '+event['time']
            text+='\nRevisa la imagen en el PC.'
            attempted=True
            result=self.api.call(record['token'],'sendMessage',{'chat_id':record['chat_id'],'text':text})
            if (type(result) is not dict or not _positive_id(result.get('message_id')) or
                type(result.get('chat')) is not dict or result['chat'].get('id')!=record['chat_id'] or result['chat'].get('type')!='private'):
                raise PhoneError('response')
            with self._lock:
                self._sent+=1
                if generation==self._generation:
                    self._state='Móvil conectado; aviso aceptado por Telegram'
        except Exception as error:
            cleanup=False
            with self._lock:
                if attempted:
                    self._ambiguous+=1
                if generation==self._generation:
                    if not attempted or isinstance(error,PhoneError) and error.status in (401,403):
                        self._clear('Móvil sin conectar')
                        cleanup=True
                    else:
                        self._state='Envío sin confirmar; no se reintenta'
            if cleanup:
                self._persist_disabled()
        finally:
            with self._lock:
                self._in_flight=False

    def _run(self):
        while True:
            with self._lock:
                generation=self._generation
                command=self._command; self._command=None
                if command:
                    self._active_command=command
                pair=self._pair
                queued=self._queue.popleft() if self._queue and not command else None
            if command:
                try:
                    self._run_command(command)
                finally:
                    with self._lock:
                        self._active_command=None
            elif self._stop.is_set():
                break
            elif pair:
                self._poll_pairing(generation,pair)
            elif queued:
                self._send(*queued)
                continue
            if self._stop.is_set():
                continue
            self._wake.wait(self.poll_interval if self._pair else 1)
            self._wake.clear()
