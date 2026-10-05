"""Photo inspection uses original pixels, fit/zoom and optional exact crops."""
import math

MAX_VIEW_PIXELS = 16 * 1024 * 1024

def dimensions(ppm):
    magic, size, maximum, pixels = ppm.split(b'\n', 3)
    width, height = map(int, size.split())
    if (magic != b'P6' or maximum != b'255' or
            not 1 <= width <= 4096 or not 1 <= height <= 4096 or
            len(pixels) != width * height * 3 or len(ppm) > 32 * 1024 * 1024):
        raise ValueError('Invalid photo')
    return width, height

def fit_size(width, height, available_width, available_height):
    ratio = min(max(1,available_width)/width, max(1,available_height)/height)
    ratio = min(ratio, math.sqrt(MAX_VIEW_PIXELS/(width*height)))
    return max(1,int(width*ratio)), max(1,int(height*ratio))

def resize_ppm(ppm, width, height):
    source_width, source_height = dimensions(ppm)
    width, height = int(width), int(height)
    if width < 1 or height < 1 or width*height > MAX_VIEW_PIXELS:
        raise ValueError('Photo view too large')
    if (width,height) == (source_width,source_height):
        return ppm
    import av
    pixels = ppm.split(b'\n',3)[3]
    frame = av.VideoFrame(source_width,source_height,'rgb24')
    plane = frame.planes[0]
    stride = source_width*3
    if plane.line_size == stride:
        plane.update(pixels)
    else:
        padding = b'\0'*(plane.line_size-stride)
        plane.update(b''.join(pixels[row*stride:(row+1)*stride]+padding for row in range(source_height)))
    scaled = frame.reformat(width=width,height=height,format='rgb24')
    raw = bytes(scaled.planes[0]); stride = width*3; line = scaled.planes[0].line_size
    pixels = b''.join(raw[row*line:row*line+stride] for row in range(height))
    return f'P6\n{width} {height}\n255\n'.encode()+pixels

def crop_original(ppm,box):
    width,height = dimensions(ppm)
    if (not isinstance(box,(list,tuple)) or len(box)!=4 or any(type(v) is not int for v in box)):
        raise ValueError('Invalid crop')
    x,y,w,h = box
    if min(x,y)<0 or min(w,h)<1 or x+w>width or y+h>height:
        raise ValueError('Invalid crop')
    pixels = ppm.split(b'\n',3)[3]
    return f'P6\n{w} {h}\n255\n'.encode()+b''.join(
        pixels[((y+row)*width+x)*3:((y+row)*width+x+w)*3] for row in range(h))

class PhotoInspector:
    def __init__(self,master,ppm,row=None,*,authorise=None):
        import tkinter as tk
        self.tk = tk; self.original = ppm; self.row = row or {}
        self.source = ppm; self.cropped = False; self.zoom = None; self.photo = None
        self.authorise = authorise
        dimensions(ppm)
        self.window = tk.Toplevel(master)
        self.window.title('Voxterrae · Imagen original')
        self.window.configure(bg='#101722')
        self.window.geometry(f'{min(1500,master.winfo_screenwidth()-40)}x{min(1000,master.winfo_screenheight()-80)}')
        self.window.minsize(640,420)
        toolbar=tk.Frame(self.window,bg='#101722'); toolbar.pack(fill='x')
        for label,callback in (('Ajustar',self.fit),('100 %',lambda:self.set_zoom(1)),
                ('−',lambda:self.set_zoom((self.zoom or self.fit_ratio())/1.25)),
                ('+',lambda:self.set_zoom((self.zoom or self.fit_ratio())*1.25))):
            tk.Button(toolbar,text=label,command=callback,bg='#26384e',fg='white',relief='flat').pack(side='left',padx=4,pady=6)
        if self.row.get('bbox'):
            tk.Button(toolbar,text='Recorte detectado / contexto',command=self.toggle_crop,
                bg='#26384e',fg='white',relief='flat').pack(side='left',padx=4)
        self.notice=tk.Label(toolbar,bg='#101722',fg='#b8c9db'); self.notice.pack(side='right',padx=8)
        panel=tk.Frame(self.window,bg='#070c13'); panel.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(panel,bg='#070c13',highlightthickness=0)
        xbar=tk.Scrollbar(panel,orient='horizontal',command=self.canvas.xview)
        ybar=tk.Scrollbar(panel,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xbar.set,yscrollcommand=ybar.set)
        panel.grid_columnconfigure(0,weight=1); panel.grid_rowconfigure(0,weight=1)
        self.canvas.grid(row=0,column=0,sticky='nsew'); ybar.grid(row=0,column=1,sticky='ns'); xbar.grid(row=1,column=0,sticky='ew')
        self.item=self.canvas.create_image(0,0,anchor='nw')
        self.canvas.bind('<Configure>',lambda event:self.render() if self.zoom is None else None)
        self.canvas.bind('<ButtonPress-1>',lambda event:self.canvas.scan_mark(event.x,event.y))
        self.canvas.bind('<B1-Motion>',lambda event:self.canvas.scan_dragto(event.x,event.y,gain=1))
        self.canvas.bind('<MouseWheel>',self.wheel)
        self.window.bind('<Escape>',lambda event:self.close())
        self.window.bind('<F11>',lambda event:self.window.attributes('-fullscreen',not self.window.attributes('-fullscreen')))
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        tk.Label(self.window,text='Original conservado · Arrastra para desplazarte · F11: pantalla completa',
            bg='#101722',fg='#99aec4',pady=6).pack(fill='x')
        self.after_id = self.window.after_idle(self.render)

    def fit_ratio(self):
        w,h=dimensions(self.source)
        return min(max(1,self.canvas.winfo_width())/w,max(1,self.canvas.winfo_height())/h)

    def fit(self): self.zoom=None; self.render()
    def set_zoom(self,value):
        w,h=dimensions(self.source)
        self.zoom=max(.05,min(4,float(value),math.sqrt(MAX_VIEW_PIXELS/(w*h))))
        self.render()
    def wheel(self,event): self.set_zoom((self.zoom or self.fit_ratio())*(1.15 if event.delta>0 else 1/1.15))
    def access_valid(self):
        if not self.window.winfo_exists(): return False
        if self.authorise is not None:
            try:
                allowed = bool(self.authorise())
            except Exception:
                allowed = False
            if not allowed:
                self.close()
                return False
        return True
    def toggle_crop(self):
        if not self.access_valid(): return
        source=crop_original(self.original,self.row['bbox']) if not self.cropped else self.original
        self.cropped=not self.cropped
        self.source=source
        self.zoom=None; self.render()
    def render(self):
        if not self.access_valid(): return
        w,h=dimensions(self.source)
        size=fit_size(w,h,self.canvas.winfo_width(),self.canvas.winfo_height()) if self.zoom is None else (max(1,int(w*self.zoom)),max(1,int(h*self.zoom)))
        display=resize_ppm(self.source,*size)
        self.photo=self.tk.PhotoImage(data=display,format='PPM',master=self.window)
        self.canvas.itemconfigure(self.item,image=self.photo)
        self.canvas.configure(scrollregion=(0,0,*size))
        self.notice.configure(text=f'{w} × {h} · {size[0]/w:.0%}'+(' · recorte' if self.cropped else ' · contexto'))
    def close(self):
        try:
            self.window.after_cancel(self.after_id)
        except self.tk.TclError:
            pass
        self.photo=None; self.original=None; self.source=None
        self.window.destroy()
