"""Ephemeral RGB display copies for one selected detail camera.

Original camera state and captured evidence never pass through this module.
No decoder, network, disk writes or external image packages are used here.
"""
import re

MODES = ('Original', 'Sombras suaves', 'Sombras fuertes')
GAMMAS = {'Original': 1.0, 'Sombras suaves': .85, 'Sombras fuertes': .70}
LUTS = {mode: bytes(round(255 * (value / 255) ** gamma) for value in range(256))
        for mode, gamma in GAMMAS.items() if mode != 'Original'}
_HEADER = re.compile(br'P6\n([1-9][0-9]{0,3}) ([1-9][0-9]{0,3})\n255\n')
MAX_DISPLAY_BYTES = 1920 * 1080 * 3 + 32


def enhance_ppm(original, mode):
    """Return an exact Original or a validated RGB copy; malformed input raises."""
    if mode == 'Original':
        return original
    if not isinstance(original, bytes) or len(original) > MAX_DISPLAY_BYTES:
        raise ValueError('Invalid display picture')
    header = _HEADER.match(original)
    if header is None:
        raise ValueError('Invalid display PPM header')
    width, height = int(header[1]), int(header[2])
    if width > 1920 or height > 1080 or len(original) != header.end() + width * height * 3:
        raise ValueError('Invalid display PPM dimensions')
    return original[:header.end()] + original[header.end():].translate(LUTS[mode])


class DetailDisplay:
    """Keep at most the latest source reference and one derived frame/setting."""
    def __init__(self):
        self.mode = 'Original'
        self.reset()

    def reset(self):
        self._source = None
        self._derived = None
        self._key = None

    def select(self, mode):
        mode = mode if mode in MODES else 'Original'
        if mode != self.mode:
            self.reset()
            self.mode = mode

    def render(self, channel, original, version):
        if self.mode == 'Original':
            self.reset()
            return original, 'Original'
        key = (channel, version, self.mode)
        if self._key == key and self._source is original:
            return self._derived, self.mode
        self.reset()
        try:
            derived = enhance_ppm(original, self.mode)
        except Exception:
            return original, 'Original'
        self._source, self._derived, self._key = original, derived, key
        return derived, self.mode
