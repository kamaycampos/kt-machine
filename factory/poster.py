#!/usr/bin/env python3
"""THE MOVIE CLIP'S POSTER (15 Nov 2026).

Kamay: "where is the hooks and thumbnails? since these movie clips are more futuristic and
modern, the hooks should reflect that in a similar way that our competitor was doing."
Looked at again that day (instagram.com/kevins_apprentice, the three pinned Episodes, 59K-233K
views): the cover is a full-screen film poster - the THING the story is about fills the frame
(the jet itself, the young man at the old book), a gold masthead and an "EPISODE N" plaque at
the top, the title in large gold script at the bottom over a line of light. Ours was a dark
frame with a small white sans line.

    make(picture, "EPISODE 3", "Too Good For The Casino", stem)  ->  stem__cover.jpg (1080x1920)
                                                                     stem__thumb.jpg (1280x720)
    band("EPISODE 3", "Too Good For The Casino", out.png)        ->  the same title for the black
                                                                     band above the film (9:16)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
K = os.path.expanduser("~/Kamay")
FONTS = os.environ.get("PREVIEW_FONTS", "/tmp/fonts")
GOLD_HI, GOLD_MID, GOLD_LO = (255, 236, 170), (232, 184, 92), (168, 112, 36)


def _font(name, size):
    for p in (os.path.join(FONTS, name), os.path.join(HERE, "assets", name), os.path.join(K, "bin", name)):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise SystemExit(f"font missing: {name}")


def _gold(size):
    """A vertical gold ramp: light at the top, deep at the bottom, a bright band a third down."""
    w, h = size
    g = Image.new("RGB", (w, max(1, h)))
    d = ImageDraw.Draw(g)
    for y in range(h):
        k = y / max(1, h - 1)
        a, b, t = (GOLD_HI, GOLD_MID, k / 0.45) if k < 0.45 else (GOLD_MID, GOLD_LO, (k - 0.45) / 0.55)
        d.line((0, y, w, y), fill=tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    return g


def _gold_text(canvas, xy, text, font, anchor="mm", glow=22, spacing=0):
    """Gold letters with a soft light behind them and a dark edge under them."""
    W, H = canvas.size
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    if spacing:
        total = sum(font.getlength(c) for c in text) + spacing * (len(text) - 1)
        x = xy[0] - total / 2
        for c in text:
            d.text((x, xy[1]), c, font=font, fill=255, anchor="lm")
            x += font.getlength(c) + spacing
    else:
        d.text(xy, text, font=font, fill=255, anchor=anchor)
    bb = mask.getbbox()
    if not bb:
        return canvas
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 235), (0, 6), mask)
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))
    if glow:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gl.paste((255, 190, 80, 120), (0, 0), mask)
        canvas.alpha_composite(gl.filter(ImageFilter.GaussianBlur(glow)))
    tex = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tex.paste(_gold((bb[2] - bb[0], bb[3] - bb[1])), (bb[0], bb[1]))
    canvas.paste(tex, (0, 0), mask)
    return canvas


def _light_line(canvas, y, half, cx=None):
    """The thin line of light under a title: bright in the middle, gone at the ends."""
    W, H = canvas.size
    cx = W // 2 if cx is None else cx
    ln = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ln)
    for x in range(-half, half):
        a = int(255 * (1 - abs(x) / half) ** 1.6)
        d.point((cx + x, y), fill=(255, 226, 150, a))
        d.point((cx + x, y + 1), fill=(255, 200, 110, a // 2))
    canvas.alpha_composite(ln.filter(ImageFilter.GaussianBlur(6)))
    canvas.alpha_composite(ln)
    core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(core).ellipse((cx - 90, y - 5, cx + 90, y + 7), fill=(255, 240, 200, 150))
    canvas.alpha_composite(core.filter(ImageFilter.GaussianBlur(9)))


def _fit_lines(title, font_name, top, width, max_lines=2):
    """The title in one or two lines of script, as large as the width allows."""
    title = title.replace(" ", "  ")                 # script letters need a wider word space
    words = title.split("  ")
    cands = [[title]] + [["  ".join(words[:i]), "  ".join(words[i:])] for i in range(1, len(words))]
    best = None
    for lines in cands[:1 + (len(words) - 1 if max_lines > 1 else 0)]:
        size = top
        while size > 40 and max(_font(font_name, size).getlength(l) for l in lines) > width:
            size -= 4
        score = size * (1.0 if len(lines) == 1 else 0.98)
        if best is None or score > best[0]:
            best = (score, size, lines)
    return best[1], best[2]


def _plaque(canvas, cy, tag, size=34):
    W = canvas.size[0]
    f = _font("cinema_archive_serif.ttf", size)
    tw = sum(f.getlength(c) for c in tag) + 9 * (len(tag) - 1)
    d = ImageDraw.Draw(canvas)
    box = (W / 2 - tw / 2 - 34, cy - size * 0.95, W / 2 + tw / 2 + 34, cy + size * 0.95)
    d.rounded_rectangle(box, radius=10, fill=(10, 8, 6, 215), outline=GOLD_MID + (255,), width=2)
    _gold_text(canvas, (W / 2, cy), tag, f, glow=0, spacing=9)
    _light_line(canvas, int(cy), 330)


def _masthead(canvas, y):
    W = canvas.size[0]
    _gold_text(canvas, (W / 2, y), "KEVIN TRUDEAU", _font("cinema_archive_serif.ttf", 86), glow=16, spacing=6)


def _cover_fill(im, w, h, focus=0.5):
    k = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * k + 1), int(im.height * k + 1)), Image.LANCZOS)
    x = int((im.width - w) * focus)
    y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def _shade(canvas, top, bottom):
    W, H = canvas.size
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    for y in range(H):
        a = 0
        if y < top:
            a = int(235 * (1 - y / top) ** 0.9)
        if y > H - bottom:
            a = max(a, int(245 * ((y - (H - bottom)) / bottom) ** 0.8))
        if a:
            d.line((0, y, W, y), fill=(0, 0, 0, a))
    canvas.alpha_composite(sh)


def make(picture, tag, title, stem, focus=0.5):
    src = Image.open(picture).convert("RGB")
    # upright: the phone cover
    c = _cover_fill(src, 1080, 1920, focus).convert("RGBA")
    _shade(c, 620, 900)
    _masthead(c, 190)
    _plaque(c, 318, tag)
    size, lines = _fit_lines(title, "greatvibes400.ttf", 230, 980)
    y = 1560 - (len(lines) - 1) * size * 0.46
    for l in lines:
        _gold_text(c, (540, y), l, _font("greatvibes400.ttf", size), glow=26)
        y += size * 0.92
    _light_line(c, int(y - size * 0.30), 430)
    cover = stem + "__cover.jpg"
    c.convert("RGB").save(cover, quality=93)
    # wide: YouTube's stored thumbnail
    t = _cover_fill(src, 1280, 720).convert("RGBA")
    _shade(t, 210, 360)
    _gold_text(t, (640, 70), tag, _font("cinema_archive_serif.ttf", 34), glow=0, spacing=8)
    size, lines = _fit_lines(title, "greatvibes400.ttf", 150, 1160, max_lines=1)
    _gold_text(t, (640, 610), lines[0], _font("greatvibes400.ttf", size), glow=20)
    _light_line(t, 676, 420)
    thumb = stem + "__thumb.jpg"
    t.convert("RGB").save(thumb, quality=93)
    return cover, thumb


def band(tag, title, out, top=656):
    """The title for the black band ABOVE the film in the upright file, on a clear 1080x1920."""
    c = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    size, lines = _fit_lines(title, "greatvibes400.ttf", 150, 980)
    block = size * 0.92 * len(lines)
    y0 = top - 70 - block + size * 0.46
    _gold_text(c, (540, y0 - size * 0.62 - 26), tag, _font("cinema_archive_serif.ttf", 30), glow=0, spacing=9)
    y = y0
    for l in lines:
        _gold_text(c, (540, y), l, _font("greatvibes400.ttf", size), glow=18)
        y += size * 0.92
    _light_line(c, top - 34, 400)
    c.save(out)
    return out


if __name__ == "__main__":
    print(make(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))
    print(band(sys.argv[2], sys.argv[3], sys.argv[4] + "__band.png"))
