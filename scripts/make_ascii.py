"""Photo -> ASCII (dark + light). Run only when the photo changes.
Usage: pip install pillow ; python scripts/make_ascii.py photo.png"""
import sys, pathlib
from PIL import Image, ImageDraw, ImageFilter, ImageOps

COLS = 120
CW, LH = 4.15, 7.0     # must match card() in generate.py
RAMP = " .:-=+*#%@"
img = Image.open(sys.argv[1]).convert("RGBA")
bg = Image.new("RGBA", img.size, "white"); bg.alpha_composite(img)
g = bg.convert("L")

# background = near-white area connected to the border
m = g.point(lambda v: 255 if v > 246 else 0)
w, h = m.size
for x in range(0, w, 8):
    for p in ((x, 0), (x, h - 1), (0, x * h // w), (w - 1, x * h // w)):
        if m.getpixel(p) == 255: ImageDraw.floodfill(m, p, 128)
mask = m.point(lambda v: 0 if v == 128 else 255)
box = mask.getbbox()
g, mask = g.crop(box), mask.crop(box)
mask = mask.filter(ImageFilter.MinFilter(5))          # trim the white fringe
rows = round(COLS * g.height / g.width * CW / LH)
small = mask.resize((COLS, rows), Image.LANCZOS)
out = pathlib.Path(__file__).resolve().parent.parent / "assets"
for theme in ("dark", "light"):
    # same-toned backdrop per theme, so sharpening leaves no halo at the edges
    t = Image.composite(g, Image.new("L", g.size, 40 if theme == "dark" else 235), mask)
    t = t.filter(ImageFilter.UnsharpMask(radius=30, percent=80, threshold=0))
    t = t.filter(ImageFilter.GaussianBlur(1.5)).resize((COLS, rows), Image.LANCZOS)
    t = t.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=0))
    inside = sorted(v for v, a in zip(t.getdata(), small.getdata()) if a >= 128)
    lo, hi = inside[len(inside)//50], inside[-len(inside)//50]
    lines = []
    for y in range(rows):
        s = ""
        for x in range(COLS):
            if small.getpixel((x, y)) < 128: s += " "; continue
            v = min(1.0, max(0.0, (t.getpixel((x, y)) - lo) / (hi - lo)))
            # dark mode: bright pixel = more ink. light mode: dark pixel = more ink.
            ink = v ** 1.7 if theme == "dark" else (1 - v) ** 1.25
            ink = 0.11 + 0.89 * ink   # floor keeps hair / shirt / skin visible
            s += RAMP[max(1, min(len(RAMP) - 1, round(ink * (len(RAMP) - 1))))]
        lines.append(s.rstrip())
    (out / f"ascii-{theme}.txt").write_text("\n".join(lines) + "\n")
print("done", COLS, rows)
