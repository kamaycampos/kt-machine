#!/usr/bin/env python3
"""A DESIGNED cover for every clip, made from Kevin as he looks in THAT clip.

13 Nov 2026, Kamay: "the thumbnails going out posting are with the background black, thats
not what we agreed ... whatever kt original looking is in that clip, you must make a
profesional thumbnails with that. kind of like this one [the red-accent sample] but
without me."

Until now a cover was a frame grabbed out of the finished clip. In the archive look that
frame is a small picture between two black fields, so the grid filled with black tiles.
This builds the cover from the SOURCE frame instead (no captions, no bars): Kevin large,
black and white, a red rule, the hook as a headline in two voices.

    make(src, t_in, t_out, hook_lines, stem)  ->  stem__cover.jpg  (1080x1920, Instagram/Facebook/TikTok)
                                                  stem__thumb.jpg  (1280x720, YouTube)

    python3 shared/kt_cover.py <source.mp4> <t_in> <t_out> "HOOK LINE ONE|line two" <out_stem>
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser(os.environ.get("KT_HOME", "~/Kamay"))
FFMPEG = os.environ.get("FFMPEG") or (os.path.join(HOME, "bin/ffmpeg") if os.path.exists(os.path.join(HOME, "bin/ffmpeg")) else "ffmpeg")
RED = (140, 24, 32)
IVORY = (244, 241, 234)
LABEL = os.environ.get("KT_COVER_LABEL", "KEVIN TRUDEAU")


def _font(names, size):
    from PIL import ImageFont
    for n in names:
        for d in (os.path.join(HOME, "bin"), os.path.join(os.path.dirname(HERE), "factory", "assets"),
                  os.path.join(HOME, "bin", "fonts")):
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


BIG = ["mont_black.ttf", "mont_eb.ttf", "arialbd.ttf"]
SERIF_IT = ["cinema_archive_serif_italic.ttf", "georgia_bold.ttf"]
SANS = ["cinema_sans_medium.ttf", "cinema_archive_sans.ttf", "arialbd.ttf"]


def _detector():
    try:
        import cv2
        m = os.path.join(HOME, "bin/yunet.onnx")
        if not os.path.exists(m):
            m = os.path.join(os.path.dirname(HERE), "factory", "assets", "yunet.onnx")
        return cv2.FaceDetectorYN_create(m, "", (320, 320), 0.6, 0.3, 5000)
    except Exception:
        return None


def _grab(src, t):
    """One clean source frame at t, as a BGR array (None on failure)."""
    import cv2
    import numpy as np
    r = subprocess.run([FFMPEG, "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if not r.stdout:
        return None
    return cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)


def best_frame(src, t_in, t_out, n=14):
    """The frame to build on: one big face, eyes open, mouth not mid-word, sharp.

    Eyes: YuNet returns the eye points but not whether they are open, so the eye patches are
    scored for contrast (an open eye has a dark iris on a light white; a blink is flat skin).
    12 Nov a draft cover caught Kevin mid-blink - "a cover picker must check eyes".
    """
    import cv2
    det = _detector()
    span = max(1.0, min(t_out - t_in, 40.0))
    cands = []
    for i in range(n):
        t = t_in + 0.5 + span * i / n
        im = _grab(src, t)
        if im is None:
            continue
        h, w = im.shape[:2]
        face = None
        if det is not None:
            s = 640.0 / w
            sm = cv2.resize(im, (640, int(h * s)))
            det.setInputSize((sm.shape[1], sm.shape[0]))
            _, faces = det.detect(sm)
            if faces is not None and len(faces):
                f = max(faces, key=lambda f: f[2] * f[3])
                face = [v / s for v in f[:14]]
        if face is None:
            continue
        x, y, fw, fh = face[:4]
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        fx0, fy0, fx1, fy1 = int(max(0, x)), int(max(0, y)), int(min(w, x + fw)), int(min(h, y + fh))
        roi = gray[fy0:fy1, fx0:fx1]
        if roi.size == 0:
            continue
        sharp = cv2.Laplacian(roi, cv2.CV_64F).var()
        eyes = 0.0
        ew = max(6, int(fw * 0.13))
        for ex, ey in ((face[4], face[5]), (face[6], face[7])):
            p = gray[int(max(0, ey - ew * 0.6)):int(ey + ew * 0.6), int(max(0, ex - ew)):int(ex + ew)]
            if p.size:
                eyes += float(p.std())
        # a face turned away has its eyes close together relative to its width
        frontal = abs(face[6] - face[4]) / max(1.0, fw)
        score = (sharp ** 0.5) * 1.0 + eyes * 1.6 + frontal * 60 + min(fw / w, 0.35) * 80
        cands.append((score, t, im, face))
    if not cands:
        im = _grab(src, t_in + 1.5)
        return im, None
    _s, _t, im, face = max(cands, key=lambda c: c[0])
    return im, face


def split_hook(lines, wrap=14):
    """Hook -> (big lines in capitals, the closing line in italic serif).

    'NEVER RETREAT. / Regroup.' is the model: the claim loud, the turn quiet. The last line of
    a multi-line hook becomes the quiet one; a one-line hook gives its last two or three words.
    """
    lines = [l.strip() for l in (lines or []) if l and l.strip()]
    if not lines:
        return [], ""
    if len(lines) >= 2:
        big, small = lines[:-1], lines[-1]
    else:
        w = lines[0].split()
        if len(w) <= 3:
            return [lines[0].upper()], ""
        k = 2 if len(w) <= 5 else 3
        big, small = [" ".join(w[:-k])], " ".join(w[-k:])
    out = []
    for l in big:                                  # no big line over ~wrap letters
        w, cur = l.upper().split(), ""
        for x in w:
            if cur and len(cur) + 1 + len(x) > wrap:
                out.append(cur); cur = x
            else:
                cur = (cur + " " + x).strip()
        if cur:
            out.append(cur)
    small = small.strip()
    small = small[0].upper() + small[1:].lower() if small else ""
    if small and small[-1] not in ".?!":
        small += "."
    return out[:4], small


def split_two(lines, wrap):
    """split_hook, widening the wrap until the loud part fits two lines (three climb onto his chin)."""
    for w in (wrap, wrap + 3, wrap + 6):
        big, small = split_hook(lines, wrap=w)
        if len(big) <= 2:
            break
    return big, small


def _tone(im):
    """Black and white with weight: the sample's look (lifted blacks, soft contrast)."""
    import cv2
    import numpy as np
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    g = np.clip((g - 0.5) * 1.12 + 0.5, 0, 1) ** 1.05
    g = g * 0.93 + 0.035
    return (np.dstack([g, g, g]) * 255).astype(np.uint8)


def _place(im, face, W, H, cx, cy, face_h):
    """Scale and shift the frame so the face centre lands on (cx, cy) at height face_h."""
    import cv2
    import numpy as np
    h, w = im.shape[:2]
    if face is None:
        s = max(W / w, H / h)
        fx, fy = w / 2, h * 0.4
    else:
        s = max(face_h / face[3], W / w, H / h)
        fx, fy = face[0] + face[2] / 2, face[1] + face[3] / 2
    big = cv2.resize(im, (int(w * s + 0.5), int(h * s + 0.5)), interpolation=cv2.INTER_LANCZOS4)
    bx = int(min(max(fx * s - cx, 0), big.shape[1] - W))
    by = int(min(max(fy * s - cy, 0), big.shape[0] - H))
    return np.ascontiguousarray(big[by:by + H, bx:bx + W])


def _fit(draw, text, names, size, max_w):
    f = _font(names, size)
    while size > 30 and draw.textlength(text, font=f) > max_w:
        size -= 4
        f = _font(names, size)
    return f, size


def _spaced(draw, xy, text, font, fill, gap):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + gap


def _compose(bg, big, small, box, label_size):
    """Draw the text block. box = (x, y_bottom, max_w): the block is bottom-aligned to y_bottom."""
    import numpy as np
    from PIL import Image, ImageDraw
    img = Image.fromarray(bg[:, :, ::-1]).convert("RGB")
    d = ImageDraw.Draw(img)
    x, yb, mw = box
    size = 400
    fonts = []
    for l in big:
        _f, s = _fit(d, l, BIG, size, mw)
        size = min(size, s)
    size = min(size, int(mw * 0.23))
    fb = _font(BIG, size)
    fs = _font(SERIF_IT, int(size * 0.80))
    lh = int(size * 1.06)
    block = lh * len(big) + (int(size * 1.05) if small else 0)
    y = yb - block
    top = y
    for l in big:
        d.text((x, y - int(size * 0.18)), l, font=fb, fill=IVORY)
        y += lh
    if small:
        d.text((x + 2, y - int(size * 0.02)), small, font=fs, fill=IVORY)
    bar_w = max(10, int(size * 0.10))
    bx = x - int(size * 0.36)
    d.rectangle([bx, top - int(size * 0.06), bx + bar_w, y + (int(size * 0.72) if small else -int(size * 0.14))], fill=RED)
    _spaced(d, (x + 2, max(34, top - int(size * 0.62) - label_size)), LABEL, _font(SANS, label_size), IVORY, label_size * 0.32)
    return np.array(img)[:, :, ::-1]


def _shade(bg, kind):
    """Darken where the words go so they read on any room."""
    import numpy as np
    h, w = bg.shape[:2]
    f = bg.astype(np.float32)
    if kind == "tall":
        yy = np.linspace(0, 1, h)[:, None]
        m = np.clip((yy - 0.40) / 0.26, 0, 1) * 0.90 + np.clip((yy - 0.74) / 0.06, 0, 1) * 0.10 + np.clip((0.16 - yy) / 0.16, 0, 1) * 0.45
    else:
        xx = np.linspace(0, 1, w)[None, :]
        m = np.clip((0.62 - xx) / 0.50, 0, 1) * 0.80
    yy = np.linspace(-1, 1, h)[:, None]; xx = np.linspace(-1, 1, w)[None, :]
    vig = np.clip((xx ** 2 + yy ** 2 - 1.1) * 0.25, 0, 0.25)
    m = np.clip(m + vig, 0, 0.97)
    return (f * (1 - m[:, :, None]) + 12 * m[:, :, None]).astype(np.uint8)


def make(src, t_in, t_out, hook_lines, stem, cover=None):
    """Write stem__cover.jpg (1080x1920) and stem__thumb.jpg (1280x720). Returns their paths.

    cover = ["BIG WORDS", "quiet line"] from the plan overrides the automatic split.
    Instagram's grid shows the middle 3:4 of the tall cover (and older surfaces the middle
    square), so the face and every word sit between y=440 and y=1480.
    """
    import cv2
    im, face = best_frame(src, t_in, t_out)
    if im is None:
        return None, None
    lines = [l for l in cover if l] if cover and cover[0] else hook_lines
    bw = _tone(im)
    big, small = split_two(lines, 10)
    tall = _shade(_place(bw, face, 1080, 1920, 540, 700, 480), "tall")
    tall = _compose(tall, big, small, (170, 1470, 790), 26)
    big, small = split_two(lines, 11)
    wide = _shade(_place(bw, face, 1280, 720, 960, 320, 380), "wide")
    wide = _compose(wide, big, small, (128, 610, 600), 18)
    c, t = stem + "__cover.jpg", stem + "__thumb.jpg"
    cv2.imwrite(c, tall, [cv2.IMWRITE_JPEG_QUALITY, 93])
    cv2.imwrite(t, wide, [cv2.IMWRITE_JPEG_QUALITY, 93])
    return c, t


def from_image(image, lines, stem, label=None, tag=None):
    """A cover from a PICTURE instead of a Kevin frame: a generated scene of the clip's own
    'movie' (13 Nov 2026, Kamay on the first covers: "a random face looking of kt and it looks
    off, poor ... thumbnails AI generated could be either kt, or the movies itself").
    Full colour, cinematic grade, the same red rule and two-voice headline. tag = a small line
    above the headline in place of the name ("EPISODE 5")."""
    import cv2
    import numpy as np
    global LABEL
    im = cv2.imread(image)
    if im is None:
        return None, None
    f = im.astype(np.float32) / 255.0
    f = np.clip((f - 0.5) * 1.10 + 0.5, 0, 1)
    f[..., 0] *= 0.94; f[..., 2] *= 1.03                         # a touch warmer
    im = (np.clip(f, 0, 1) * 255).astype(np.uint8)
    keep, LABEL = LABEL, (tag or label or LABEL)
    try:
        big, small = split_two(lines, 10)
        tall = _shade(_place(im, None, 1080, 1920, 540, 700, 480), "tall")
        tall = _compose(tall, big, small, (170, 1470, 790), 26)
        big, small = split_two(lines, 11)
        wide = _shade(_place(im, None, 1280, 720, 640, 360, 380), "wide")
        wide = _compose(wide, big, small, (128, 610, 600), 18)
    finally:
        LABEL = keep
    c, t = stem + "__cover.jpg", stem + "__thumb.jpg"
    cv2.imwrite(c, tall, [cv2.IMWRITE_JPEG_QUALITY, 93])
    cv2.imwrite(t, wide, [cv2.IMWRITE_JPEG_QUALITY, 93])
    return c, t


if __name__ == "__main__":
    a = sys.argv
    print(make(a[1], float(a[2]), float(a[3]), a[4].split("|"), a[5]))
