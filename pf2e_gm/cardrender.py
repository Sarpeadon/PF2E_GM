"""Printable item cards as PNG images, in one hand-drawn look: crooked crayon borders, ink blots, doodled teeth and a skull,
and lettering that won't sit still.

A card is a plain dict (see card_model): a title, traits, a quoted description, an action table, rules text, a footer, and the
item's level. render() draws it and returns a list of PIL images: one card, or more ("continued") when the text will not fit
even at the smallest readable size. Builders at the bottom turn the app's things into cards: a generated magic item, an entry
from your rules data (items, spells, feats...), a custom item, or a plain thing with only a name and a price.

Sizes are at 300 dpi: poker 2.5 x 3.5 in (750 x 1050), tarot 2.75 x 4.75 in (825 x 1425).
Backgrounds: white (for printing), transparent (a PNG with only the ink, for screens and handouts), or parchment.
Unused space (what a short card does with the room under its text):
  blank    leave it empty
  center   center the text between the name and the footer
  doodles  fill it with goblin doodles (mushrooms, cheese, angry chickens, notes to self...)

Fonts are looked up on the computer: Ink Free for the name, Segoe Print for the text (both come with Windows 10 and 11). If they
are missing, a plain font is used. Everything random is seeded from the item's name (and the doodle variant), so a card always
draws the same way until you ask for different doodles. Needs Pillow (python -m pip install pillow).
"""
import math
import os
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZES = {"poker": (750, 1050), "tarot": (825, 1425)}
SIZE_LABELS = {"poker": "Poker (2.5 x 3.5 in)", "tarot": "Tarot (2.75 x 4.75 in)"}
BACKGROUNDS = {"white": "White", "transparent": "Transparent", "parchment": "Parchment"}
FILLS = {"blank": "Leave blank", "center": "Center the text", "doodles": "Goblin doodles"}
DPI = 300

# ------------------------------------------------------------------------------------------------ fonts
FONT_DIRS = [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
             Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
             Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts",
             Path("/Library/Fonts"), Path("/System/Library/Fonts")]
FONTS = {"title": ["Inkfree.ttf", "segoeprb.ttf", "DejaVuSans-Bold.ttf"],
         "body": ["segoepr.ttf", "Inkfree.ttf", "DejaVuSansCondensed.ttf"],
         "bold": ["segoeprb.ttf", "Inkfree.ttf", "DejaVuSansCondensed-Bold.ttf"],
         "italic": ["Inkfree.ttf", "segoepr.ttf", "DejaVuSansCondensed-Oblique.ttf"]}
_paths, _cache = {}, {}


def _find(name):
    if name in _paths:
        return _paths[name]
    found, low = None, name.lower()
    for d in FONT_DIRS:
        try:
            if not d.is_dir():
                continue
            if (d / name).exists():
                found = d / name
                break
            found = next((p for p in d.rglob("*") if p.name.lower() == low), None)
        except OSError:
            continue
        if found:
            break
    _paths[name] = found
    return found


def font(role, size):
    key = (role, int(size))
    if key not in _cache:
        f = None
        for name in FONTS[role]:
            p = _find(name)
            if p:
                try:
                    f = ImageFont.truetype(str(p), int(size))
                    break
                except OSError:
                    continue
        _cache[key] = f or ImageFont.load_default(int(size))
    return _cache[key]


def fonts_used():
    """{role: font file found, or 'built-in'} so the app can say what it is drawing with."""
    out = {}
    for role, names in FONTS.items():
        p = next((_find(n) for n in names if _find(n)), None)
        out[role] = p.name if p else "built-in"
    return out


def handwriting_found():
    """True when Ink Free or Segoe Print is installed (the lettering looks hand-written)."""
    u = fonts_used()
    return u["title"] in ("Inkfree.ttf", "segoeprb.ttf") or u["body"] in ("segoepr.ttf", "Inkfree.ttf")


PAL = dict(paper=(205, 190, 150), paper2=(160, 140, 96), ink=(40, 30, 20), accent=(156, 40, 24), rule=(70, 52, 30),
           muted=(84, 66, 44))


# ------------------------------------------------------------------------------------------------ drawing helpers
def _jitter(rng, pts, amt, step=18):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(n):
            t = i / n
            out.append((x0 + (x1 - x0) * t + rng.uniform(-amt, amt), y0 + (y1 - y0) * t + rng.uniform(-amt, amt)))
    out.append((pts[-1][0] + rng.uniform(-amt, amt), pts[-1][1] + rng.uniform(-amt, amt)))
    return out


def wobble_line(d, rng, pts, fill, width, amt=1.5):
    d.line(_jitter(rng, pts, amt), fill=fill, width=width, joint="curve")


def wobble_rect(d, rng, box, fill, width, amt=1.5, skew=0.0):
    x0, y0, x1, y1 = box
    wobble_line(d, rng, [(x0 + skew, y0), (x1, y0 + skew), (x1 - skew, y1), (x0, y1 - skew), (x0 + skew, y0)], fill, width, amt)


def paper(size, rng, background="white"):
    """The sheet the card is drawn on: plain white, transparent (only the ink is drawn), or mottled parchment."""
    if background == "transparent":
        return Image.new("RGBA", size, (0, 0, 0, 0))
    if background != "parchment":
        return Image.new("RGB", size, (255, 255, 255))
    w, h = size
    img = Image.new("RGB", size, PAL["paper"])
    noise = Image.effect_noise((w // 6, h // 6), 40).resize(size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))
    img = Image.composite(Image.new("RGB", size, PAL["paper2"]), img, noise.point(lambda v: int(max(0, v - 110) * 1.2)))
    grain = Image.effect_noise(size, 18).point(lambda v: int(abs(v - 128) * 0.35))
    img = Image.composite(Image.new("RGB", size, PAL["ink"]), img, grain)
    edge = Image.new("L", size, 0)
    ed = ImageDraw.Draw(edge)
    for i in range(40):
        ed.rectangle((i, i, w - 1 - i, h - 1 - i), outline=int(120 * (1 - i / 40) ** 2))
    img = Image.composite(Image.new("RGB", size, PAL["paper2"]), img, edge.filter(ImageFilter.GaussianBlur(8)))
    for _ in range(4):
        st = Image.new("L", size, 0)
        sd = ImageDraw.Draw(st)
        cx, cy, r = rng.randint(0, w), rng.randint(0, h), rng.randint(40, 140)
        sd.ellipse((cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), outline=60, width=6)
        sd.ellipse((cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), fill=14)
        img = Image.composite(Image.new("RGB", size, PAL["paper2"]), img, st.filter(ImageFilter.GaussianBlur(4)))
    return img


def _skull(d, rng, sx, sy, k=1.0):
    ink, w = PAL["ink"], max(2, int(3 * k))
    d.ellipse((sx - 22 * k, sy - 24 * k, sx + 22 * k, sy + 14 * k), outline=ink, width=w)
    d.rectangle((sx - 12 * k, sy + 10 * k, sx + 12 * k, sy + 24 * k), outline=ink, width=w)
    d.ellipse((sx - 13 * k, sy - 9 * k, sx - 3 * k, sy + 1 * k), fill=ink)
    d.ellipse((sx + 3 * k, sy - 9 * k, sx + 13 * k, sy + 1 * k), fill=ink)
    for i in range(3):
        d.line((sx - 7 * k + i * 7 * k, sy + 10 * k, sx - 7 * k + i * 7 * k, sy + 24 * k), fill=ink, width=max(1, int(2 * k)))


def frame(img, rng):
    """The crooked double border, teeth along the top, ink blots on the border, and a skull in the top corner."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    for amt, width in ((4.5, 6), (3, 3)):
        wobble_rect(d, rng, (24 + rng.uniform(-4, 4), 26 + rng.uniform(-4, 4), w - 26, h - 24), PAL["ink"], width, amt,
                    skew=rng.uniform(-6, 6))
    for _ in range(rng.randint(3, 6)):
        side = rng.choice("lrt")
        cx = rng.randint(10, 22) if side == "l" else rng.randint(w - 22, w - 10) if side == "r" else rng.randint(60, w - 60)
        cy = rng.randint(70, h - 140) if side in "lr" else rng.randint(10, 18)
        r = rng.randint(4, 9)                            # on or outside the border, never over the text
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PAL["ink"])
        for _ in range(rng.randint(2, 5)):
            a, dist, rr = rng.uniform(0, 6.28), rng.uniform(r, r * 1.8), rng.randint(1, 3)
            d.ellipse((cx + math.cos(a) * dist - rr, cy + math.sin(a) * dist - rr, cx + math.cos(a) * dist + rr,
                       cy + math.sin(a) * dist + rr), fill=PAL["ink"])
    x = 50
    while x < w - 70:
        t = rng.randint(14, 24)
        wobble_line(d, rng, [(x, 34), (x + t / 2, 34 + rng.randint(12, 22)), (x + t, 34)], PAL["ink"], 3, 1.2)
        x += t + rng.randint(0, 6)
    _skull(d, rng, w - 64, 112)
    return 46


def action_glyph(d, x, y, cost, s, fill):
    """The action symbol for '1', '2', '3', 'R' (reaction), or 'F' (free) at (x, y), height s. Returns its width."""
    def diamond(cx, filled=True):
        pts = [(cx, y), (cx + s / 2, y + s / 2), (cx, y + s), (cx - s / 2, y + s / 2)]
        if filled:
            d.polygon(pts, fill=fill)
        else:
            d.polygon(pts, outline=fill, width=max(2, int(s / 9)))
    c = str(cost).upper()
    if c in ("1", "2", "3"):
        for i in range(int(c)):
            diamond(x + s / 2 + i * s * 0.62)
        return s * (1 + 0.62 * (int(c) - 1))
    if c == "F":
        diamond(x + s / 2, False)
        return s
    if c == "R":
        d.arc((x, y, x + s, y + s), 200, 20, fill=fill, width=max(2, int(s / 7)))
        ax, ay = x + s * 0.92, y + s * 0.38
        d.polygon([(ax, ay - s * 0.28), (ax + s * 0.22, ay + s * 0.12), (ax - s * 0.24, ay + s * 0.1)], fill=fill)
        return s
    return 0


# ------------------------------------------------------------------------------------------------ text
TOKEN = re.compile(r"\*\*(.+?)\*\*|(\S+)")


def _runs(text):
    """'**Effect** You cast' -> [(word, bold)]."""
    out = []
    for m in TOKEN.finditer(text):
        if m.group(1):
            out += [(w, True) for w in m.group(1).split()]
        else:
            out.append((m.group(2), False))
    return out


def wrap(text, width, f, fb, draw):
    lines, cur, cur_w = [], [], 0
    space = draw.textlength(" ", font=f)
    for word, bold in _runs(text):
        ww = draw.textlength(word, font=fb if bold else f)
        add = ww + (space if cur else 0)
        if cur and cur_w + add > width:
            lines.append(cur)
            cur, cur_w, add = [], 0, ww
        cur.append((word, bold))
        cur_w += add
    if cur:
        lines.append(cur)
    return lines


class Writer:
    """Sets each word down at a slight tilt and bounce, like it was written by hand."""

    def __init__(self, img, rng):
        self.img, self.d, self.rng = img, ImageDraw.Draw(img), rng

    def word(self, x, y, text, f, fill, wob=2.2):
        tw, th = int(self.d.textlength(text, font=f)) + 8, int(f.size * 1.5) + 8
        tile = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(tile).text((4, 4), text, font=f, fill=255)
        tile = tile.rotate(self.rng.uniform(-wob, wob), resample=Image.BICUBIC)
        ink = Image.new(self.img.mode, tile.size, fill + ((255,) if self.img.mode == "RGBA" else ()))
        self.img.paste(ink, (int(x - 4), int(y - 4 + self.rng.uniform(-wob * 0.6, wob * 0.6))), tile)
        return tw - 8

    def line(self, x, y, runs, f, fb, fill, bold_fill=None, center_w=None):
        space = self.d.textlength(" ", font=f)
        if center_w is not None:
            total = sum(self.d.textlength(w, font=fb if b else f) for w, b in runs) + space * (len(runs) - 1)
            x += (center_w - total) / 2
        for w, b in runs:
            x += self.word(x, y, w, fb if b else f, (bold_fill or fill) if b else fill) + space


# ------------------------------------------------------------------------------------------------ goblin doodles
# Each doodle is drawn inside a square of side s centered on (cx, cy). They are crude on purpose.
def _st(d, rng, pts, w=3, amt=1.4):
    wobble_line(d, rng, pts, PAL["ink"], w, amt)


def _ring(d, rng, cx, cy, rx, ry, w=3, n=22):
    pts = [(cx + rx * math.cos(a * 6.2832 / n), cy + ry * math.sin(a * 6.2832 / n)) for a in range(n + 1)]
    _st(d, rng, pts, w, 1.2)


def doodle_mushroom(img, rng, cx, cy, s):
    d, r = ImageDraw.Draw(img), s * 0.36
    base = cy - r * 0.2
    _st(d, rng, [(cx - r * math.cos(a * math.pi / 12), base - r * 0.9 * math.sin(a * math.pi / 12)) for a in range(13)])
    _st(d, rng, [(cx - r, base), (cx + r, base)])
    _st(d, rng, [(cx - r * 0.35, base), (cx - r * 0.3, cy + r * 1.2), (cx + r * 0.3, cy + r * 1.2), (cx + r * 0.35, base)])
    for dx, dy in ((-0.45, -0.35), (0.05, -0.62), (0.5, -0.3)):
        d.ellipse((cx + dx * r - 4, base + dy * r - 4, cx + dx * r + 4, base + dy * r + 4), fill=PAL["ink"])


def doodle_cheese(img, rng, cx, cy, s):
    d, a = ImageDraw.Draw(img), s * 0.4
    _st(d, rng, [(cx - a, cy + a * 0.3), (cx + a, cy - a * 0.5), (cx + a, cy + a * 0.3), (cx - a, cy + a * 0.3)])
    _st(d, rng, [(cx - a, cy + a * 0.3), (cx - a, cy + a * 0.7), (cx + a, cy + a * 0.7), (cx + a, cy + a * 0.3)])
    for dx, dy, rr in ((0.1, 0.1, 6), (0.45, -0.05, 4), (-0.3, 0.5, 5), (0.5, 0.5, 5)):
        _ring(d, rng, cx + dx * a, cy + dy * a, rr, rr, 2, 10)


def doodle_goblin(img, rng, cx, cy, s):
    d, r = ImageDraw.Draw(img), s * 0.3
    _ring(d, rng, cx, cy, r, r * 1.05)
    _st(d, rng, [(cx - r, cy - r * 0.2), (cx - r * 1.9, cy - r * 0.9), (cx - r * 0.9, cy + r * 0.3)])
    _st(d, rng, [(cx + r, cy - r * 0.2), (cx + r * 1.9, cy - r * 0.9), (cx + r * 0.9, cy + r * 0.3)])
    for dx in (-0.4, 0.4):
        d.ellipse((cx + dx * r - 5, cy - r * 0.3 - 5, cx + dx * r + 5, cy - r * 0.3 + 5), fill=PAL["ink"])
    _st(d, rng, [(cx, cy - r * 0.1), (cx - r * 0.1, cy + r * 0.25), (cx + r * 0.12, cy + r * 0.25)], 2)
    mouth = [(cx - r * 0.55, cy + r * 0.5)]
    for i in range(5):
        mouth += [(cx - r * 0.55 + (i + 0.5) * r * 0.22, cy + r * 0.78), (cx - r * 0.55 + (i + 1) * r * 0.22, cy + r * 0.5)]
    _st(d, rng, mouth, 2, 0.8)


def doodle_dragon(img, rng, cx, cy, s):
    d, a = ImageDraw.Draw(img), s * 0.4
    _ring(d, rng, cx, cy + a * 0.2, a * 0.7, a * 0.4)
    _st(d, rng, [(cx + a * 0.5, cy), (cx + a * 0.9, cy - a * 0.6), (cx + a * 0.85, cy - a * 0.95)])
    _st(d, rng, [(cx + a * 0.85, cy - a * 0.95), (cx + a * 1.25, cy - a * 0.85), (cx + a * 0.95, cy - a * 0.7)], 3)
    _st(d, rng, [(cx - a * 0.2, cy - a * 0.1), (cx - a * 0.6, cy - a * 0.95), (cx + a * 0.15, cy - a * 0.2)])
    _st(d, rng, [(cx - a * 0.7, cy + a * 0.2), (cx - a * 1.2, cy + a * 0.5), (cx - a * 1.0, cy + a * 0.05)])
    for dx in (-0.35, 0.3):
        _st(d, rng, [(cx + dx * a, cy + a * 0.55), (cx + dx * a, cy + a * 0.9)])
    _st(d, rng, [(cx + a * 1.25, cy - a * 0.85), (cx + a * 1.45, cy - a * 0.95), (cx + a * 1.4, cy - a * 0.8),
                 (cx + a * 1.62, cy - a * 0.82)], 2)
    d.ellipse((cx + a * 0.98 - 2, cy - a * 0.82 - 2, cx + a * 0.98 + 2, cy - a * 0.82 + 2), fill=PAL["ink"])


def doodle_chicken(img, rng, cx, cy, s):
    d, a = ImageDraw.Draw(img), s * 0.36
    _ring(d, rng, cx + a * 0.1, cy + a * 0.2, a * 0.8, a * 0.6)
    _ring(d, rng, cx - a * 0.55, cy - a * 0.55, a * 0.35, a * 0.35, 3, 14)
    _st(d, rng, [(cx - a * 0.88, cy - a * 0.55), (cx - a * 1.25, cy - a * 0.45), (cx - a * 0.88, cy - a * 0.35)], 3)
    _st(d, rng, [(cx - a * 0.7, cy - a * 0.95), (cx - a * 0.55, cy - a * 1.15), (cx - a * 0.4, cy - a * 0.9)], 2)
    d.ellipse((cx - a * 0.62 - 3, cy - a * 0.6 - 3, cx - a * 0.62 + 3, cy - a * 0.6 + 3), fill=PAL["ink"])
    _st(d, rng, [(cx - a * 0.8, cy - a * 0.8), (cx - a * 0.4, cy - a * 0.68)], 3)            # an angry eyebrow
    for dx in (-0.1, 0.35):
        _st(d, rng, [(cx + dx * a, cy + a * 0.8), (cx + dx * a, cy + a * 1.2), (cx + dx * a + 8, cy + a * 1.25)], 2)
    _st(d, rng, [(cx + a * 0.9, cy), (cx + a * 1.3, cy - a * 0.3), (cx + a * 1.1, cy + a * 0.1), (cx + a * 1.35, cy + a * 0.05)], 2)


def doodle_map(img, rng, cx, cy, s):
    d, a = ImageDraw.Draw(img), s * 0.42
    _st(d, rng, [(cx - a, cy - a * 0.6), (cx + a, cy - a * 0.6), (cx + a, cy + a * 0.6), (cx - a, cy + a * 0.6), (cx - a, cy - a * 0.6)])
    _st(d, rng, [(cx - a * 0.3, cy - a * 0.6), (cx - a * 0.3, cy + a * 0.6)], 1)
    for i in range(6):                                                                         # a dotted path
        x, y = cx - a * 0.8 + i * a * 0.28, cy + a * 0.25 - math.sin(i) * a * 0.2
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=PAL["ink"])
    _st(d, rng, [(cx + a * 0.45, cy - a * 0.3), (cx + a * 0.75, cy - a * 0.05)], 3)           # X marks the spot
    _st(d, rng, [(cx + a * 0.75, cy - a * 0.3), (cx + a * 0.45, cy - a * 0.05)], 3)
    _st(d, rng, [(cx - a * 1.05, cy - a * 0.7), (cx + a * 1.05, cy + a * 0.7)], 4, 2)          # crossed out
    _st(d, rng, [(cx + a * 1.05, cy - a * 0.7), (cx - a * 1.05, cy + a * 0.7)], 4, 2)


def _stick(d, rng, x, y, a, sword=False, dirn=1):
    _ring(d, rng, x, y - a * 0.7, a * 0.2, a * 0.2, 2, 10)
    _st(d, rng, [(x, y - a * 0.5), (x, y + a * 0.3)], 2)
    _st(d, rng, [(x - a * 0.35, y - a * 0.1), (x, y - a * 0.35), (x + a * 0.35 * dirn, y - a * 0.5)], 2)
    _st(d, rng, [(x - a * 0.3, y + a * 0.75), (x, y + a * 0.3), (x + a * 0.3, y + a * 0.75)], 2)
    if sword:
        _st(d, rng, [(x + a * 0.35 * dirn, y - a * 0.5), (x + a * 0.8 * dirn, y - a * 0.95)], 3)


def doodle_battle(img, rng, cx, cy, s):
    d, a = ImageDraw.Draw(img), s * 0.4
    _stick(d, rng, cx - a * 0.6, cy, a, True, 1)
    _stick(d, rng, cx + a * 0.6, cy, a, True, -1)
    _st(d, rng, [(cx - a * 0.05, cy - a * 0.9), (cx + a * 0.05, cy - a * 0.55), (cx - a * 0.1, cy - a * 0.5), (cx + a * 0.1, cy - a * 0.25)], 2)


def doodle_arrow(img, rng, cx, cy, s):
    d, a = ImageDraw.Draw(img), s * 0.4
    _st(d, rng, [(cx, cy + a), (cx, cy - a * 0.8)], 4)
    _st(d, rng, [(cx - a * 0.4, cy - a * 0.3), (cx, cy - a * 0.9), (cx + a * 0.4, cy - a * 0.3)], 4)
    Writer(img, rng).word(cx + a * 0.15, cy - a * 0.1, "?", font("title", int(a * 0.7)), PAL["accent"], wob=8)


def doodle_warning(img, rng, cx, cy, s):
    d, a = ImageDraw.Draw(img), s * 0.4
    _st(d, rng, [(cx, cy - a), (cx + a * 1.05, cy + a * 0.8), (cx - a * 1.05, cy + a * 0.8), (cx, cy - a)], 4)
    _st(d, rng, [(cx, cy - a * 0.35), (cx, cy + a * 0.2)], 5)
    d.ellipse((cx - 4, cy + a * 0.42 - 4, cx + 4, cy + a * 0.42 + 4), fill=PAL["ink"])


def doodle_ruler(img, rng, cx, cy, s):
    d, a = ImageDraw.Draw(img), s * 0.45
    _st(d, rng, [(cx - a, cy), (cx + a, cy)], 3)
    for i in range(7):
        x = cx - a + i * a / 3
        _st(d, rng, [(x, cy - 9), (x, cy + 9)], 2)
    Writer(img, rng).word(cx - a * 0.5, cy + 14, rng.choice(["7 ish", "3 and a bit", "TOO LONG", "about"]), font("body", int(s * 0.17)), PAL["muted"], wob=4)


def doodle_skull(img, rng, cx, cy, s):
    _skull(ImageDraw.Draw(img), rng, cx, cy, s / 90.0)


DOODLES = [doodle_mushroom, doodle_cheese, doodle_goblin, doodle_dragon, doodle_chicken, doodle_map, doodle_battle,
           doodle_arrow, doodle_warning, doodle_ruler, doodle_skull]
NOTES = ["DO NOT EAT", "PROBABLY SAFE", "NOT CURSED*", "ASK GREG", "MINE", "MOSTLY WORKS", "DON'T TELL", "*SEE OTHER SIDE",
         "SMELLS FUNNY", "OWES ME 3 CP", "NO REFUNDS", "IT BIT ME", "NOT MINE", "WHO MADE THIS", "STILL WARM"]


def doodles(img, rng, box, scale):
    """Fill a rectangle with goblin doodles and notes. Nothing is drawn outside box. Returns how many things were drawn."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if h < 90 * scale or w < 120 * scale:
        return 0
    cell = 165 * scale
    cols, rows = max(1, int(w // cell)), max(1, min(3, int(h // cell)))
    cw, ch = w / cols, h / rows
    s = min(cw, ch) * 0.8
    slots = [(c, r) for r in range(rows) for c in range(cols)]
    rng.shuffle(slots)
    if len(slots) > 4:
        slots = slots[:max(4, int(len(slots) * 0.75))]
    kinds = rng.sample(DOODLES, min(len(DOODLES), len(slots)))
    notes = rng.sample(NOTES, min(len(NOTES), 3))
    wr, n = Writer(img, rng), 0
    for i, (c, r) in enumerate(slots):
        cx = x0 + cw * (c + 0.5) + rng.uniform(-cw * 0.06, cw * 0.06)
        cy = y0 + ch * (r + 0.5) + rng.uniform(-ch * 0.06, ch * 0.06)
        if i % 4 == 3 and notes:                                           # every fourth slot is a note to self
            text, f = notes.pop(), font("bold", int(24 * scale))
            while wr.d.textlength(text, font=f) > cw * 0.92 and f.size > 12:
                f = font("bold", f.size - 1)
            tw = wr.d.textlength(text, font=f)
            wr.word(cx - tw / 2, cy - f.size / 2, text, f, PAL["accent"] if rng.random() < 0.5 else PAL["muted"], wob=6)
        else:
            kinds[i % len(kinds)](img, rng, cx, cy, s)
        n += 1
    return n


# ------------------------------------------------------------------------------------------------ the card
def card_model(title, traits=(), quote="", actions=(), sections=(), footer=(), level=None, notes="", level_label="LVL"):
    """actions: [{"cost": "2", "name": "Cast a Spell", "trait": "manipulate", "effect": "..."}].
    sections: [text]; **Label** marks a bold label, and a line starting **Critical Success** (and so on) is indented."""
    return {"title": title, "traits": list(traits), "quote": quote, "actions": list(actions), "sections": list(sections),
            "footer": [f for f in footer if f], "level": level, "notes": notes, "level_label": level_label}


def title_plate(img, rng, x0, y0, x1, card, scale):
    d = ImageDraw.Draw(img)
    w = x1 - x0
    title = card["title"].upper()
    room = w - int(130 * scale)                          # clear of the skull in the corner
    size = int(64 * scale)
    while size > int(38 * scale) and d.textlength(title, font=font("title", size)) > room:
        size -= 2
    f = font("title", size)
    lines = [title]
    if d.textlength(title, font=f) > room:
        words = title.split()
        half = max(1, len(words) // 2)
        lines = [" ".join(words[:half]), " ".join(words[half:])]
    lh = int(size * 1.15)
    plate_h = lh * len(lines) + int(26 * scale)
    wobble_rect(d, rng, (x0 + 4, y0, x1 - 4, y0 + plate_h), PAL["ink"], 4, 3, skew=rng.uniform(-8, 8))
    wr = Writer(img, rng)
    ty = y0 + int(12 * scale)
    for ln in lines:
        while d.textlength(ln, font=f) > room and f.size > 16:
            f = font("title", f.size - 2)
        tx = x0 + (w - d.textlength(ln, font=f)) / 2
        for ch in ln:                                     # letters that won't sit still
            tx += wr.word(tx, ty + rng.uniform(-4, 4), ch, f, PAL["ink"], wob=7)
        ty += lh
    y = y0 + plate_h + int(30 * scale)                    # a clear gap between the title box and the traits
    if card.get("traits"):
        ft = font("bold", int(22 * scale))
        line = "  \u2022  ".join(t.title() for t in card["traits"])
        while d.textlength(line, font=ft) > w - 20 and ft.size > 12:
            ft = font("bold", ft.size - 1)
        wr.line(x0, y, [(line, False)], ft, ft, PAL["accent"], center_w=w)
        y += int(ft.size * 1.4)
    return y


def level_badge(img, rng, level, label, scale):
    if level in (None, ""):
        return
    d = ImageDraw.Draw(img)
    w, h = img.size
    s = int(92 * scale)
    cx, cy = w - int(30 * scale) - s // 2, h - int(30 * scale) - s // 2
    wobble_line(d, rng, [(cx - s / 2, cy - s / 2), (cx + s / 2, cy - s / 2 + 6), (cx + s / 2 - 4, cy + s / 2),
                         (cx - s / 2 + 3, cy + s / 2 - 2), (cx - s / 2, cy - s / 2)], PAL["ink"], 4, 3)
    fs, fb = font("bold", int(15 * scale)), font("title", int(40 * scale))
    label = str(label or "LVL")
    d.text((cx - d.textlength(label, font=fs) / 2, cy - s / 2 + 12 * scale), label, font=fs, fill=PAL["ink"])
    d.text((cx - d.textlength(str(level), font=fb) / 2, cy - 8 * scale), str(level), font=fb, fill=PAL["ink"])


def _blocks(card):
    out = [("quote", card["quote"])] if card.get("quote") else []
    out += [("action", a) for a in card.get("actions") or []]
    if card.get("actions"):
        out.append(("rule",))
    out += [("para", s) for s in card.get("sections") or []]
    if card.get("notes"):
        out.append(("note", card["notes"]))
    return out


def _lay(img, rng, blocks, width, size, draw=False, x0=0, y0=0):
    """Height the blocks take at this size (and draw them when draw is True)."""
    d = ImageDraw.Draw(img)
    f, fb, fi = font("body", size), font("bold", size), font("italic", size)
    lh = int(size * 1.32)
    wr = Writer(img, rng) if draw else None
    y = y0
    for kind, *rest in blocks:
        if kind == "quote":
            for ln in wrap(f"\u201c{rest[0]}\u201d", width - 20, fi, fi, d):
                if draw:
                    wr.line(x0, y, ln, fi, fi, PAL["muted"], center_w=width)
                y += lh
            y += int(size * 0.5)
        elif kind == "action":
            a, gs = rest[0], int(size * 1.05)
            longest = max([d.textlength(w, font=fb) for w, _ in _runs(f"{a.get('name', '')} ({a.get('trait') or ''})")] or [0])
            name_w = int(min(width * 0.42, max(width * 0.28, longest + 12)))
            ex = x0 + int(gs * 2.3) + name_w
            nl = wrap(f"**{a.get('name', '')}**" + (f" ({a['trait']})" if a.get("trait") else ""), name_w - 6, f, fb, d)
            el = wrap(a.get("effect", ""), width - (ex - x0), f, fb, d)
            if draw:
                action_glyph(d, x0 + 2, y + 2, a.get("cost", ""), gs, PAL["ink"])
                for i, ln in enumerate(nl):
                    wr.line(x0 + int(gs * 2.3), y + i * lh, ln, f, fb, PAL["ink"], PAL["accent"])
                for i, ln in enumerate(el):
                    wr.line(ex, y + i * lh, ln, f, fb, PAL["ink"])
            y += max(len(nl), len(el), 1) * lh + int(size * 0.35)
        elif kind == "rule":
            if draw:
                wobble_line(d, rng, [(x0, y + 4), (x0 + width, y + 4)], PAL["rule"], 3, 2)
            y += int(size * 0.8)
        else:
            text = rest[0]
            indent = int(size) if re.match(r"\*\*(Critical Success|Success|Failure|Critical Failure)\*\*", text) else 0
            fu = fi if kind == "note" else f
            for ln in wrap(text, width - indent, fu, fb, d):
                if draw:
                    wr.line(x0 + indent, y, ln, fu, fb, PAL["muted"] if kind == "note" else PAL["ink"], PAL["ink"])
                y += lh
            y += int(size * 0.35)
    return y - y0


def _split_block(block, img, rng, width, pt, avail):
    """A block too tall for one card on its own, cut in two at the last word that fits. Returns (first, rest or None). An
    action's long effect goes on as a plain paragraph on the next card."""
    kind, body = block[0], block[1]
    text = body.get("effect", "") if kind == "action" else body
    words = text.split()

    def build(k):
        first = " ".join(words[:k])
        return ("action", dict(body, effect=first)) if kind == "action" else (kind, first)
    lo, hi = 1, len(words)
    while lo < hi:                                        # the most words that still fit
        mid = (lo + hi + 1) // 2
        if _lay(img, rng, [build(mid)], width, pt) <= avail:
            lo = mid
        else:
            hi = mid - 1
    k = lo
    while " ".join(words[:k]).count("**") % 2 and k > 1:    # never cut inside a **bold label**
        k -= 1
    rest = " ".join(words[k:])
    return build(k), ((("para" if kind == "action" else kind), rest) if rest else None)


TEXT_CAP = {"blank": 34, "center": 32, "doodles": 27}       # largest text size (points at poker size) for each fill


def render(card, size="poker", background="white", fill="blank", variant=0):
    """[PIL image]: one card, or more when the text doesn't fit even at the smallest size. fill is blank, center, or doodles;
    variant changes the doodles (and nothing else) so you can ask for a different set."""
    W, H = SIZES.get(size, SIZES["poker"])
    fill = fill if fill in FILLS else "blank"
    scale = W / 750
    blocks, pages, part = _blocks(card), [], 0
    while True:
        rng = random.Random(f"{card.get('title', '')}|{size}|{part}")
        img = paper((W, H), rng, background)
        pad = frame(img, rng)
        x0, x1 = pad, W - pad
        shown = dict(card, title=card["title"] + (" (continued)" if part else ""), traits=[] if part else card["traits"])
        y = title_plate(img, rng, x0, pad, x1, shown, scale) + int(20 * scale)
        avail = H - pad - int(70 * scale) - y
        width = x1 - x0
        pt, fit = int(TEXT_CAP[fill] * scale), None
        while pt >= int(17 * scale):
            if _lay(img, rng, blocks, width, pt) <= avail:
                fit = len(blocks)
                break
            pt -= 1
        if fit is None:
            pt, fit = int(17 * scale), 0
            for i in range(1, len(blocks) + 1):
                if _lay(img, rng, blocks[:i], width, pt) > avail:
                    break
                fit = i
            if fit == 0:                                  # the first block alone is taller than a card: split it
                first, rest = _split_block(blocks[0], img, rng, width, pt, avail)
                blocks = [first] + ([rest] if rest else []) + blocks[1:]
                fit = 1
        used = _lay(img, rng, blocks[:fit], width, pt)
        last = fit >= len(blocks)
        top = y + (max(0, (avail - used) // 2) if (fill == "center" and last) else 0)
        _lay(img, rng, blocks[:fit], width, pt, draw=True, x0=x0, y0=top)
        if fill == "doodles" and last:
            drng = random.Random(f"{card.get('title', '')}|{size}|doodles|{variant}")
            doodles(img, drng, (x0, y + used + int(14 * scale), x1, y + avail - int(6 * scale)), scale)
        d = ImageDraw.Draw(img)
        ff = font("bold", int(22 * scale))
        foot = " | ".join(card.get("footer") or [])
        while d.textlength(foot, font=ff) > width - 120 * scale and ff.size > 12:
            ff = font("bold", ff.size - 1)
        Writer(img, rng).line(x0, H - pad - int(40 * scale), [(w, False) for w in foot.split(" ")], ff, ff, PAL["ink"],
                              center_w=width - int(100 * scale))
        level_badge(img, rng, card.get("level"), card.get("level_label"), scale)
        pages.append(img)
        blocks, part = blocks[fit:], part + 1
        if not blocks or part > 6:
            return pages


def save(card, path, size="poker", background="white", fill="blank", variant=0):
    """Write the card as PNG (path_2.png and so on for continued cards). Returns the paths written."""
    base, out = Path(path), []
    for i, img in enumerate(render(card, size, background, fill, variant)):
        p = base if i == 0 else base.with_name(f"{base.stem}_{i + 1}{base.suffix}")
        img.save(p, dpi=(DPI, DPI))
        out.append(str(p))
    return out


def print_sheet(images, size="poker", path=None):
    """Cards laid out on US letter at 300 dpi with cut marks: 9 poker or 6 tarot per sheet. Returns [sheets]."""
    W, H = 2550, 3300
    cw, ch = SIZES[size]
    cols, rows = (3, 3) if size == "poker" else (3, 2)
    gx, gy = (W - cols * cw) // 2, (H - rows * ch) // 2
    sheets = []
    for start in range(0, len(images), cols * rows):
        sheet = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(sheet)
        for i, img in enumerate(images[start:start + cols * rows]):
            img = img.resize((cw, ch))
            sheet.paste(img, (gx + i % cols * cw, gy + i // cols * ch), img if img.mode == "RGBA" else None)
        for c in range(cols + 1):
            x = gx + c * cw
            d.line((x, gy - 40, x, gy - 10), fill="black", width=2)
            d.line((x, gy + rows * ch + 10, x, gy + rows * ch + 40), fill="black", width=2)
        for r in range(rows + 1):
            y = gy + r * ch
            d.line((gx - 40, y, gx - 10, y), fill="black", width=2)
            d.line((gx + cols * cw + 10, y, gx + cols * cw + 40, y), fill="black", width=2)
        sheets.append(sheet)
    if path:
        base = Path(path)
        for i, s in enumerate(sheets):
            s.save(base if i == 0 else base.with_name(f"{base.stem}_{i + 1}{base.suffix}"), dpi=(DPI, DPI))
    return sheets


# ------------------------------------------------------------------------------------------------ cards from the app's things
def _gp(gp):
    """'12 gp', '5 sp', '1,200 gp' for a price in gold."""
    cp = int(round(float(gp or 0) * 100))
    if cp <= 0:
        return ""
    g, rem = divmod(cp, 100)
    sp, c = divmod(rem, 10)
    return " ".join(x for x in (f"{g:,} gp" if g else "", f"{sp} sp" if sp else "", f"{c} cp" if c else "") if x)


def _trim(text):
    return str(text or "").strip().rstrip(". ").strip()


def _label_first(text):
    """'Name: what it does' -> '**Name** what it does'."""
    head, sep, rest = str(text).partition(": ")
    return f"**{head}** {rest}" if sep and len(head) <= 40 else str(text)


def _act_row(act):
    """An activation dict (name, actions, traits, frequency, trigger, requirements, effect) as a card action row."""
    bits = [f"**{lab}** {_trim(act.get(key))}." for lab, key in (("Frequency", "frequency"), ("Trigger", "trigger"),
                                                                   ("Requirements", "requirements")) if _trim(act.get(key))]
    if str(act.get("effect") or "").strip():
        bits.append(str(act["effect"]).strip())
    return {"cost": str(act.get("actions", "2")), "name": act.get("name", "Activate"),
            "trait": ", ".join(act.get("traits") or []), "effect": " ".join(bits)}


def card_from_magic_item(item):
    """A card for an item from the Magic Item Generator (a plain dict). Player-facing: it leaves out the GM notes, history, and
    knowledge checks."""
    try:
        from . import itemgen as IG
    except ImportError:
        import itemgen as IG
    kind = item["kind"]
    custom = item.get("mode") == "custom"
    look = IG.part(item, "look")
    actions, sections = [], []
    for label, text, style in IG.stat_lines(item):               # a runic weapon's or armor's own numbers
        if style == "row":
            sections.append(f"**{label}** {text}")
    if kind in IG.RUNIC_KINDS and not custom:
        for p in item["parts"]:
            if p["key"] in ("potency", "striking", "resilient") or p["key"].startswith("rune"):
                sections.append(_label_first(p["text"]))
    elif kind in ("wand", "scroll", "potion", "device") and not custom:
        act = IG.spell_ability(item)
        if act:
            actions.append(_act_row(act))
    for p in item["parts"]:
        act = (p.get("data") or {}).get("act")
        if act and p["key"].startswith(("act", "effect")):
            actions.append(_act_row(act))
        elif p["key"].startswith("effect") and p.get("text"):
            sections.append(p["text"])
    if kind in IG.BOOK_KINDS and not custom:
        sp = IG.part(item, "spells")
        if sp and sp.get("text"):
            if kind == "staff":
                sections.append("**Spells** " + sp["text"])
            else:
                if item.get("owner"):
                    sections.append(f"**Owner** {item['owner']}")
                sections += [_label_first(ln) for ln in sp["text"].splitlines() if ln.strip()]
                for g in (sp.get("data") or {}).get("generated") or []:
                    try:
                        from . import spellgen as SG
                    except ImportError:
                        import spellgen as SG
                    sections.append("**New spell** " + SG.spell_text(g).replace("\n", " "))
    for key, label in (("oddity", "Oddity"), ("absurd", "Absurd ability"), ("limit", "Limit"), ("quirk", "Quirk"),
                       ("drawback", "Drawback")):
        p = IG.part(item, key)
        if p and p.get("text"):
            sections.append(f"**{(p.get('label') or label) if key == 'drawback' else label}** {p['text']}")
    bulk = str(item.get("bulk") or "")
    footer = [f"Bulk {bulk}" if bulk else "", item.get("usage") or "", str(item.get("rarity") or "common").title(),
              _gp(item.get("price_gp"))]
    return card_model(item["name"], item.get("traits") or [], look["text"] if look and look.get("text") else "", actions, sections,
                      footer, item.get("level"), item.get("notes") or "")


_LEVEL_LABEL = {"Item": "LVL", "Spell": "RANK", "Cantrip": "RANK", "Focus": "RANK", "Feat": "LVL", "Hazard": "LVL"}


def card_from_entry(e, title=None, extra_sections=(), footer_extra=(), price=None):
    """A card for an entry from your rules data (an item, spell, feat, action...), or a custom item entry. e is the dict the app's
    rules lookup returns: name, header ('Item 3'), traits, rarity, meta [[label, value]], text. price replaces the entry's own
    price in the footer (a Pathbuilder weapon is worth more than its base item once its runes are counted)."""
    try:
        from .statblock import ability_lines, strip_links
    except ImportError:
        from statblock import ability_lines, strip_links
    kind = e.get("kind") or ""
    header = str(e.get("header") or "")
    m = re.match(r"^([A-Za-z]+)\s+(-?\d+)\s*$", header)
    level, label = (int(m.group(2)), _LEVEL_LABEL.get(m.group(1), "LVL")) if m else (None, "LVL")
    meta = {str(k).lower(): str(v) for k, v in (e.get("meta") or [])}
    sections = []
    for k, v in e.get("meta") or []:
        if kind == "item" and str(k).lower() in ("price", "bulk", "usage"):
            continue
        sections.append(f"**{k}** {v}")
    if e.get("glyph"):
        sections.insert(0, "**Actions** " + {"[1]": "1 action", "[2]": "2 actions", "[3]": "3 actions", "[R]": "reaction",
                                              "[F]": "free action"}.get(e["glyph"], e["glyph"]))
    for kind_, lab, rest in ability_lines(strip_links(e.get("text") or ""), level):
        if kind_ in ("head", "lab", "out"):
            sections.append(f"**{lab}** {rest}".strip())
        elif rest:
            sections.append(rest)
    sections = [s for s in sections if s.strip()] + [s for s in extra_sections if s]
    footer = []
    if kind == "item":
        footer = [f"Bulk {meta['bulk']}" if meta.get("bulk") else "", meta.get("usage") or ""]
    footer += [str(e.get("rarity") or "common").title()]
    shown_price = price if price else meta.get("price")
    if kind == "item" and shown_price:
        footer.append(shown_price.upper() if len(shown_price) < 12 else shown_price)
    footer += [f for f in footer_extra if f]
    traits = [t for t in (e.get("traits") or [])]
    return card_model(title or e["name"], traits, "", [], sections, footer, level, "", label)


def card_from_models_item(it):
    """A card for a models.Item (Custom Content, Treasure, Shops) that has no rules entry in your data."""
    notes = [ln.strip() for ln in str(it.notes or "").splitlines() if ln.strip()]
    footer = [str(it.rarity or "common").title(), "Consumable" if it.consumable else "", _gp(it.price_gp)]
    return card_model(it.name, [t for t in it.traits if t != it.rarity], "", [], notes, footer, it.level)


def card_basic(name, level=None, value_gp=0, qty=1, holder="", source="", notes="", extra=()):
    """A card for a thing that has only a name: an everyday item, a keepsake, something you typed into Party Loot."""
    sections = [str(notes).strip()] if str(notes or "").strip() else []
    sections += [s for s in extra if s]
    if source:
        sections.append(f"**From** {source}")
    footer = [f"x{qty}" if qty and int(qty) > 1 else "", _gp(value_gp), f"Held by {holder}" if holder else ""]
    return card_model(name, [], "", [], sections, footer, level)
