#!/usr/bin/env python3
"""Regenerate the original Optimus mark, offline (Python 3 + Pillow).

Run from any directory: python tools/brand/generate_assets.py
All formats share the coordinates below; PNG/ICO use 4x supersampling.
The faceted open O and detached northeast point suggest forward movement.
"""

from io import BytesIO
from pathlib import Path
import struct

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "src" / "Optimus.App" / "Assets"
SURFACE = "#14232E"
ACCENT = "#54E0C1"
TEXT = "#F2FAF8"
RING = [(88, 40), (148, 40), (112, 76), (104, 76), (76, 104),
        (76, 152), (104, 180), (152, 180), (180, 152), (180, 112),
        (216, 76), (216, 168), (168, 216), (88, 216), (40, 168), (40, 88)]
POINT = [(168, 40), (216, 40), (216, 88)]
SIZES = (16, 32, 48, 64, 256)


def geometry(points):
    return "M " + " L ".join(f"{x},{y}" for x, y in points) + " Z"


def render(size):
    scale = size * 4 / 256
    canvas = Image.new("RGBA", (size * 4, size * 4))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((0, 0, size * 4 - 1, size * 4 - 1),
                           radius=56 * scale, fill=SURFACE)
    for points, color in ((RING, ACCENT), (POINT, TEXT)):
        draw.polygon([(x * scale, y * scale) for x, y in points], fill=color)
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    ring, point = geometry(RING), geometry(POINT)
    (ASSETS / "optimus.svg").write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256" role="img" aria-labelledby="title desc">
  <title id="title">Optimus</title>
  <desc id="desc">An open mint octagon and a pale northeast point on a dark rounded square.</desc>
  <rect width="256" height="256" rx="56" fill="{SURFACE}"/>
  <path d="{ring}" fill="{ACCENT}"/>
  <path d="{point}" fill="{TEXT}"/>
</svg>
''', encoding="utf-8")
    (ASSETS / "OptimusBrand.xaml").write_text(f'''<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
    <!-- Original Optimus geometry. Regenerate with tools/brand/generate_assets.py. -->
    <SolidColorBrush x:Key="OptimusAccentBrush" Color="{ACCENT}" />
    <SolidColorBrush x:Key="OptimusSurfaceBrush" Color="{SURFACE}" />
    <SolidColorBrush x:Key="OptimusTextBrush" Color="{TEXT}" />
    <DrawingImage x:Key="OptimusLogo">
        <DrawingImage.Drawing>
            <DrawingGroup>
                <GeometryDrawing Brush="{{StaticResource OptimusSurfaceBrush}}">
                    <GeometryDrawing.Geometry>
                        <RectangleGeometry Rect="0,0,256,256" RadiusX="56" RadiusY="56" />
                    </GeometryDrawing.Geometry>
                </GeometryDrawing>
                <GeometryDrawing Brush="{{StaticResource OptimusAccentBrush}}" Geometry="{ring}" />
                <GeometryDrawing Brush="{{StaticResource OptimusTextBrush}}" Geometry="{point}" />
            </DrawingGroup>
        </DrawingImage.Drawing>
    </DrawingImage>
</ResourceDictionary>
''', encoding="utf-8")
    render(256).save(ASSETS / "optimus.png")
    # Individual PNG frames retain the separately rendered small-size antialiasing.
    frames = []
    for size in SIZES:
        buffer = BytesIO()
        render(size).save(buffer, format="PNG")
        frames.append(buffer.getvalue())
    offset = 6 + 16 * len(SIZES)
    directory = bytearray(struct.pack("<HHH", 0, 1, len(SIZES)))
    for size, frame in zip(SIZES, frames):
        directory.extend(struct.pack("<BBBBHHII", size % 256, size % 256,
                                     0, 0, 1, 32, len(frame), offset))
        offset += len(frame)
    (ASSETS / "optimus.ico").write_bytes(directory + b"".join(frames))
    print("Generated SVG, WPF DrawingImage, PNG256 and ICO16/32/48/64/256.")


if __name__ == "__main__":
    main()
