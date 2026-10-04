"""Bounded local playback of verified original elementary sequence streams."""
import math
import threading
import time

def playback_times(metadata):
    offsets=[]
    for row in metadata.get('frames',[]):
        value=row.get('event_offset_seconds')
        if type(value) in (int,float) and math.isfinite(value):
            offsets.append(value)
    if not offsets: return []
    return [round(max(0,value-offsets[0]),6) for value in offsets]

def _ppm(frame):
    plane=frame.planes[0];raw=bytes(plane);stride=frame.width*3
    pixels=b''.join(raw[row*plane.line_size:row*plane.line_size+stride] for row in range(frame.height))
    return f'P6\n{frame.width} {frame.height}\n255\n'.encode()+pixels

class SequenceInspector:
    def __init__(self,master,manager,identifier):
        import tkinter as tk
        self.tk=tk;self.manager=manager;self.identifier=identifier
        self.metadata=next((row for row in manager.list_clips() if row['id']==identifier),None)
        self.path=manager.clip_path(identifier)
        if self.metadata is None or self.path is None: raise ValueError('Clip unavailable')
        self.window=tk.Toplevel(master);self.window.title('Voxterrae · Secuencia original')
        self.window.geometry(f'{min(1450,master.winfo_screenwidth()-40)}x{min(960,master.winfo_screenheight()-80)}')
        self.window.configure(bg='#101722')
        self.stop_event=threading.Event();self.pause_event=threading.Event();self.lock=threading.Lock()
        self.latest=None;self.version=0;self.shown=-1;self.photo=None;self.closed=False;self.error=None;self.done=False
        self.target=(1280,720)
        bar=tk.Frame(self.window,bg='#101722');bar.pack(fill='x')
        tk.Button(bar,text='Pausa / continuar',command=self.pause,bg='#26384e',fg='white').pack(side='left',padx=5,pady=8)
        tk.Button(bar,text='Repetir',command=self.replay,bg='#26384e',fg='white').pack(side='left',padx=5)
        self.notice=tk.Label(bar,bg='#101722',fg='#dce8f4',text='Cargando vídeo original…');self.notice.pack(side='left',padx=12)
        self.image=tk.Label(self.window,bg='#070c13',fg='#99aec4');self.image.pack(fill='both',expand=True)
        self.image.bind('<Configure>',lambda event:self.set_size(event.width,event.height))
        state='Cobertura parcial' if self.metadata.get('status')!='complete' else 'Cobertura guardada'
        tk.Label(self.window,text=f"{state} · Antes: {self.metadata.get('pre_coverage_seconds',0):.1f} s · Después: {self.metadata.get('post_coverage_seconds',0):.1f} s · Tiempo de recepción local · Vídeo original sin audio",
            bg='#101722',fg='#b8c9db',pady=8).pack(fill='x')
        self.window.protocol('WM_DELETE_WINDOW',self.close);self.window.bind('<Escape>',lambda event:self.close())
        self.window.bind('<F11>',lambda event:self.window.attributes('-fullscreen',not self.window.attributes('-fullscreen')))
        self.worker=None;self.start();self.after_id=self.window.after(80,self.refresh)

    def set_size(self,width,height):
        with self.lock:self.target=(max(32,min(1920,width-8)),max(32,min(1080,height-8)))
    def pause(self):
        if self.pause_event.is_set():self.pause_event.clear()
        else:self.pause_event.set()
    def start(self):
        self.done=False;self.error=None
        self.worker=threading.Thread(target=self.decode,name='CCTV-local-playback',daemon=True);self.worker.start()
    def replay(self):
        if self.worker is not None and self.worker.is_alive():return
        self.pause_event.clear();self.start()
    def decode(self):
        begin=None; first=None; paused=0.0; last_display=-1.0
        try:
            for frame, receipt in self.manager.playback_frames(self.identifier,self.stop_event):
                if self.stop_event.is_set():break
                if first is None:
                    first=receipt;begin=time.monotonic()
                stamp=max(0,receipt-first)
                while not self.stop_event.is_set():
                    if self.pause_event.is_set():
                        pause_start=time.monotonic();self.stop_event.wait(.05);paused+=time.monotonic()-pause_start
                        continue
                    remaining=begin+paused+stamp-time.monotonic()
                    if remaining<=0:break
                    self.stop_event.wait(min(remaining,.05))
                if self.stop_event.is_set():break
                if stamp-last_display<.1:continue
                with self.lock:width,height=self.target
                ratio=min(width/frame.width,height/frame.height)
                rgb=frame.reformat(width=max(1,int(frame.width*ratio)),height=max(1,int(frame.height*ratio)),format='rgb24')
                picture=_ppm(rgb)
                with self.lock:
                    if self.stop_event.is_set() or self.closed:break
                    self.latest=(picture,stamp);self.version+=1
                last_display=stamp
        except Exception as error:
            self.error=type(error).__name__
        finally:self.done=True
    def refresh(self):
        if self.closed:return
        try:
            with self.lock:latest,version=self.latest,self.version
            if latest is not None and version!=self.shown:
                self.photo=self.tk.PhotoImage(data=latest[0],format='PPM',master=self.window)
                self.image.configure(image=self.photo,text='');self.shown=version
                self.notice.configure(text=f'{latest[1]:.1f} s'+(' · fin' if self.done else ''))
            if self.error:self.notice.configure(text='No se pudo reproducir: '+self.error)
        except self.tk.TclError:
            self.error='Imagen no disponible'
        finally:
            if not self.closed:self.after_id=self.window.after(80,self.refresh)
    def close(self):
        with self.lock:
            self.closed=True;self.stop_event.set();self.photo=None;self.latest=None
        try:self.window.after_cancel(self.after_id)
        except self.tk.TclError:pass
        self.window.destroy()
