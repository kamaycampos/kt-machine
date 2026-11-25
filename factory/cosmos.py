#!/usr/bin/env python3
"""THE COSMOS LOOK FOR EPISODES (25 Nov 2026).

Kamay: "I do not like the style of our episodes, I want it more futuristic, modern, esoteric,
universe energy, spiritual, full professional max edition."

What changed against the gold-script film look (factory/poster.py, still there with EP_LOOK=film):
  - behind the film: a living nebula (assets/cosmos_bg.jpg, drifting slowly) with energy
    particles rising through it, instead of a blurred copy of the film
  - the film: a violet/cyan grade with a soft glow, Kevin and the captions untouched in shape
    (cropped at the sides to 1080x720, never stretched)
  - the title: modern engraved capitals (Cinzel) in white-to-gold light with a cyan aura, the tag in
    wide-spaced futuristic letters (Michroma), a thin sacred-geometry ring behind it, light lines
    framing the film
  - the cover: the Episode's own scene full screen, the same title, the same ring

    band(tag, title, out)                      -> 1080x1920 transparent overlay (title + frame)
    particles(out, secs)                       -> particles on black, for a screen blend
    cover(picture, tag, title, stem)           -> stem__cover.jpg (1080x1920), stem__thumb.jpg (1280x720)
    graph(DUR)                                 -> the ffmpeg filter for inputs 0 film, 1 bg, 2 particles, 3 band
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
K = os.path.expanduser("~/Kamay")
FONTS = os.environ.get("PREVIEW_FONTS", "/tmp/fonts")
BG = os.path.join(HERE, "assets", "cosmos_bg.jpg")
FILM_Y, FILM_H = 600, 720
GOLD = (255, 214, 140)
CYAN = (120, 225, 255)
VIOLET = (170, 120, 255)


def _font(name, size):
    for p in (os.path.join(FONTS, name), os.path.join(HERE, "assets", name)):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise SystemExit(f"font missing: {name}")


def _spaced(d, xy, text, font, spacing, fill):
    total = sum(font.getlength(c) for c in text) + spacing * (len(text) - 1)
    x = xy[0] - total / 2
    for c in text:
        d.text((x, xy[1]), c, font=font, fill=fill, anchor="lm")
        x += font.getlength(c) + spacing
    return total


def _glow_layer(size, draw_fn, blur, color, strength=1.0):
    m = Image.new("L", size, 0)
    draw_fn(ImageDraw.Draw(m))
    g = m.filter(ImageFilter.GaussianBlur(blur))
    if strength != 1.0:
        g = g.point(lambda v: min(255, int(v * strength)))
    layer = Image.new("RGBA", size, color + (0,))
    layer.putalpha(g)
    return layer


def _light_text(canvas, xy, text, font, spacing=0, anchor="mm", aura=CYAN):
    """White-to-gold letters, a gold inner light, a cyan aura."""
    W, H = canvas.size

    def draw(d):
        if spacing:
            _spaced(d, xy, text, font, spacing, 255)
        else:
            d.text(xy, text, font=font, fill=255, anchor=anchor)
    canvas.alpha_composite(_glow_layer((W, H), draw, 26, aura, 1.6))
    canvas.alpha_composite(_glow_layer((W, H), draw, 7, GOLD, 1.3))
    mask = Image.new("L", (W, H), 0)
    draw(ImageDraw.Draw(mask))
    bb = mask.getbbox()
    if not bb:
        return
    ramp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ramp)
    for y in range(bb[1], bb[3] + 1):
        k = (y - bb[1]) / max(1, bb[3] - bb[1])
        c = tuple(int(255 + (GOLD[i] - 255) * k) for i in range(3))
        rd.line((0, y, W, y), fill=c + (255,))
    ramp.putalpha(mask)
    canvas.alpha_composite(ramp)


def _ring(canvas, cx, cy, r, alpha=70):
    """Seed of life inside two circles and a hexagram: thin gold lines, softly lit."""
    W, H = canvas.size

    def draw(d):
        w = 2
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=255, width=w)
        d.ellipse((cx - r * 0.93, cy - r * 0.93, cx + r * 0.93, cy + r * 0.93), outline=255, width=1)
        s = r * 0.31
        d.ellipse((cx - s, cy - s, cx + s, cy + s), outline=255, width=w)
        for k in range(6):
            a = math.pi / 3 * k
            x, y = cx + s * math.cos(a), cy + s * math.sin(a)
            d.ellipse((x - s, y - s, x + s, y + s), outline=255, width=w)
        for off in (0, math.pi / 3):
            pts = [(cx + r * 0.93 * math.cos(off + 2 * math.pi / 3 * k - math.pi / 2),
                    cy + r * 0.93 * math.sin(off + 2 * math.pi / 3 * k - math.pi / 2)) for k in range(3)]
            d.polygon(pts, outline=255, width=1)
    lines = _glow_layer((W, H), draw, 0, GOLD, 1.0)
    lines.putalpha(lines.getchannel("A").point(lambda v: v * alpha // 255))
    canvas.alpha_composite(_glow_layer((W, H), draw, 9, GOLD, 0.6 * alpha / 70))
    canvas.alpha_composite(lines)


def _beam(canvas, y, half, cx=540, color=CYAN):
    """A thin horizontal line of light, brightest in the middle."""
    W, H = canvas.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x in range(-half, half + 1):
        a = int(235 * (1 - abs(x) / half) ** 1.6)
        mix = abs(x) / half
        c = tuple(int(GOLD[i] * (1 - mix) + color[i] * mix) for i in range(3))
        d.point((cx + x, y), fill=c + (a,))
        d.point((cx + x, y + 1), fill=c + (a // 2,))
    glow = layer.filter(ImageFilter.GaussianBlur(5))
    canvas.alpha_composite(glow)
    canvas.alpha_composite(glow)
    canvas.alpha_composite(layer)


def _fit(title, font_name, top, width, max_lines=2):
    words = title.upper().split()
    cands = [[" ".join(words)]] + [[" ".join(words[:i]), " ".join(words[i:])] for i in range(1, len(words))]
    best = None
    for lines in cands[:1 + (len(words) - 1 if max_lines > 1 else 0)]:
        size = top
        while size > 30 and max(_font(font_name, size).getlength(l) + 4 * len(l) for l in lines) > width:
            size -= 3
        score = size * (1.0 if len(lines) == 1 else 0.9) - abs(len(lines[0]) - len(lines[-1])) * 0.4
        if best is None or score > best[0]:
            best = (score, size, lines)
    return best[1], best[2]


def _title_block(c, tag, title, bottom, top_size=104, width=960):
    size, lines = _fit(title, "cinzel600.ttf", top_size, width)
    lh = size * 1.08
    y = bottom - lh * (len(lines) - 1) - size * 0.55
    ty = y - size * 0.62 - 58
    _ring(c, 540, int(y + lh * (len(lines) - 1) / 2), int(min(300, 120 + size * 1.5)), alpha=60)
    if tag:
        f = _font("michroma400.ttf", 26)
        d = ImageDraw.Draw(c)
        tw = _spaced(ImageDraw.Draw(Image.new("L", (1, 1))), (0, 0), tag.upper(), f, 14, 0)
        _light_text(c, (540, ty), tag.upper(), f, spacing=14, aura=CYAN)
        for sgn in (-1, 1):
            x0 = 540 + sgn * (tw / 2 + 26)
            x1 = 540 + sgn * (tw / 2 + 150)
            d.line((x0, ty, x1, ty), fill=CYAN + (160,), width=2)
            d.ellipse((x0 - 3, ty - 3, x0 + 3, ty + 3), fill=GOLD + (230,))
    for l in lines:
        _light_text(c, (540, y), l, _font("cinzel600.ttf", size), spacing=4)
        y += lh
    return y


def band(tag, title, out):
    c = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    _title_block(c, tag, title, FILM_Y - 70)
    # the film's frame: two lines of light on its edges and four corner marks
    _beam(c, FILM_Y - 3, 540)
    _beam(c, FILM_Y + FILM_H + 1, 540, color=VIOLET)
    d = ImageDraw.Draw(c)
    for x, sx in ((18, 1), (1062, -1)):
        for y, sy in ((FILM_Y + 16, 1), (FILM_Y + FILM_H - 16, -1)):
            d.line((x, y, x + sx * 46, y), fill=GOLD + (200,), width=2)
            d.line((x, y, x, y + sy * 46), fill=GOLD + (200,), width=2)
    f = _font("michroma400.ttf", 22)
    _light_text(c, (540, FILM_Y + FILM_H + 86), "KEVIN TRUDEAU", f, spacing=16, aura=VIOLET)
    c.save(out)
    return out


def particles(out, secs=8.0, fps=30, w=540, h=960, n=170, ff="ffmpeg", seed=7):
    """Energy motes rising and twinkling, on black (screen-blended over the nebula). Rendered at half
    size and scaled up: they are soft lights, and it renders in seconds."""
    import subprocess
    import numpy as np
    rnd = random.Random(seed)
    frames = int(secs * fps)
    P = []
    for _ in range(n):
        gold = rnd.random() < 0.45
        P.append(dict(x=rnd.uniform(0, w), y=rnd.uniform(0, h), r=rnd.uniform(0.6, 2.2),
                      v=rnd.uniform(8, 34), sway=rnd.uniform(4, 16), ph=rnd.uniform(0, 6.28),
                      tw=rnd.uniform(0.4, 1.6), c=np.array(GOLD if gold else (CYAN if rnd.random() < 0.6 else VIOLET), float)))
    yy, xx = np.mgrid[-6:7, -6:7]
    p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                          "-r", str(fps), "-i", "-", "-vf", "scale=1080:1920:flags=bicubic",
                          "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", out],
                         stdin=subprocess.PIPE)
    for f in range(frames):
        t = f / fps
        img = np.zeros((h + 14, w + 14, 3), float)
        for q in P:
            # a seamless loop: every mote travels a whole number of heights in `secs`
            loops = max(1, round(q["v"] * secs / h))
            y = (q["y"] - loops * h * t / secs) % h
            x = (q["x"] + q["sway"] * math.sin(2 * math.pi * t / secs * 2 + q["ph"])) % w
            a = 0.55 + 0.45 * math.sin(2 * math.pi * t / secs * round(q["tw"] * 3) + q["ph"])
            spr = np.exp(-(xx ** 2 + yy ** 2) / (2 * q["r"] ** 2))[..., None] * q["c"] * a
            xi, yi = int(x) + 7, int(y) + 7
            img[yi - 6:yi + 7, xi - 6:xi + 7] += spr
        p.stdin.write(np.clip(img[7:h + 7, 7:w + 7], 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    return out if p.returncode == 0 else None


def graph(dur):
    """Inputs: 0 the wide film (with sound), 1 the nebula still (-loop 1), 2 the particles
    (-stream_loop -1), 3 the band PNG (-loop 1). Output [v]."""
    return (
        # the nebula drifts: a slow ellipse inside the 10% margin, about a minute a turn
        "[1:v]scale=1188:2112,crop=1080:1920:x='54+46*sin(t/9.5)':y='96+80*sin(t/12.5)',"
        "eq=brightness=-0.06:saturation=1.0,setsar=1,fps=30,format=gbrp[neb];"
        "[2:v]fps=30,setsar=1,format=gbrp[pt];"
        # screen blends in RGB: in YUV the colour planes are blended too and the sky turns flat magenta
        "[neb][pt]blend=all_mode=screen:shortest=1,format=yuv420p[sky];"
        # the film: cropped (never stretched) to 1080x720, cooled into violet/cyan, lit with a soft glow
        "[0:v]scale=1280:720:flags=lanczos,crop=1080:720,setsar=1,"
        "colorbalance=rs=-0.05:gs=-0.02:bs=0.07:rm=0.02:gm=-0.01:bm=0.04:rh=0.03:gh=0.01:bh=-0.03,"
        "eq=contrast=1.06:saturation=1.06,format=gbrp,split[fa][fb];"
        "[fb]gblur=sigma=16[fg];[fa][fg]blend=all_mode=screen:all_opacity=0.16,format=yuv420p[film];"
        f"[sky][film]overlay=0:{FILM_Y}:shortest=1[base];"
        f"[3:v]format=rgba,fade=t=in:st=0:d=0.5:alpha=1[t];[base][t]overlay=0:0:shortest=1:enable='lt(t,{dur:.2f})'[v]"
    )


def cover(picture, tag, title, stem):
    src = Image.open(picture).convert("RGB")

    def fill(im, w, h):
        k = max(w / im.width, h / im.height)
        im = im.resize((int(im.width * k + 1), int(im.height * k + 1)), Image.LANCZOS)
        x, y = (im.width - w) // 2, (im.height - h) // 2
        return im.crop((x, y, x + w, y + h))

    def shade(c, top, bottom):
        W, H = c.size
        s = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(s)
        for y in range(H):
            a = 0
            if y < top:
                a = int(200 * (1 - y / top) ** 0.9)
            if y > H - bottom:
                a = max(a, int(235 * ((y - (H - bottom)) / bottom) ** 0.8))
            if a:
                d.line((0, y, W, y), fill=(8, 4, 24, a))
        c.alpha_composite(s)

    c = fill(src, 1080, 1920).convert("RGBA")
    shade(c, 520, 980)
    f = _font("michroma400.ttf", 30)
    _light_text(c, (540, 170), "KEVIN TRUDEAU", f, spacing=18, aura=VIOLET)
    _beam(c, 220, 300)
    _title_block(c, tag, title, 1640, top_size=118, width=980)
    _beam(c, 1720, 420)
    out = stem + "__cover.jpg"
    c.convert("RGB").save(out, quality=93)
    t = fill(src, 1280, 720).convert("RGBA")
    shade(t, 150, 380)
    size, lines = _fit(title, "cinzel600.ttf", 92, 1160, max_lines=1)
    _ring(t, 640, 600, 220, alpha=50)
    _light_text(t, (640, 70), (tag or "").upper(), _font("michroma400.ttf", 24), spacing=12)
    _light_text(t, (640, 600), lines[0], _font("cinzel600.ttf", size), spacing=4)
    _beam(t, 672, 420)
    thumb = stem + "__thumb.jpg"
    t.convert("RGB").save(thumb, quality=93)
    return out, thumb
