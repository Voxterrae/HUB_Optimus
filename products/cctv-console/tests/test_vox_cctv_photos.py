import os
import unittest
from unittest.mock import patch

class PhotoContracts(unittest.TestCase):
    def test_fit_uses_actual_window_instead_of700_pixel_cap(self):
        from vox_cctv_photos import fit_size
        self.assertEqual(fit_size(2560,1440,1600,1000),(1600,900))
        self.assertEqual(fit_size(220,150,1600,1000),(1466,1000))

    @unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'),'Needs Tk')
    def test_inspector_fit_original_zoom_and_close(self):
        import tkinter as tk
        from vox_cctv_photos import PhotoInspector
        root=tk.Tk(); root.withdraw()
        ppm=b'P6\n64 48\n255\n'+b'\x20\x70\x40'*(64*48)
        box=PhotoInspector(root,ppm,{'bbox':[10,10,20,20]})
        try:
            root.update()
            box.set_zoom(1.0); root.update()
            self.assertEqual((box.photo.width(),box.photo.height()),(64,48))
            self.assertEqual(box.photo.get(0,0),(32,112,64))
            box.set_zoom(2.0); root.update()
            self.assertEqual((box.photo.width(),box.photo.height()),(128,96))
            box.toggle_crop(); box.set_zoom(1.0); root.update()
            self.assertEqual((box.photo.width(),box.photo.height()),(20,20))
            box.toggle_crop(); box.fit(); root.update()
            self.assertGreater(box.photo.width(),64)
        finally: box.close(); root.destroy()

if __name__=='__main__': unittest.main()
