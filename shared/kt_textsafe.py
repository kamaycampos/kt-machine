"""KEVIN'S OWN WORDS ON SCREEN ARE NEVER CUT IN HALF (4 Nov 2026).

Kamay on KT's first post from "Want to Get Rich? Read These 10 Books First" (LIBERACES-SECRET-BOOK):
"this does not look professional ... look at it." His editor puts big kinetic words across the WIDE
frame ("CREATE ... YOUR ... REALITY"); our 9:16 crop keeps the middle third, so the post showed a
giant "EALITY" running off both edges. Every clip from that episode had it ("N NAT", "UNICARACTI",
"D IT ONCE?").

So: find the moments where the source shows a line of big overlay letters that the crop would cut,
and for those seconds show the WHOLE picture (full width, letterboxed on black) instead of
the crop. Text the crop keeps whole, or misses entirely, changes nothing.

Detection without OCR: overlay words are rows of big white or yellow letter shapes - several
same-height blobs on one baseline. A lamp, a shirt or a face is one blob, not a row of letters.

    spans = kt_textsafe.cut_text_spans(src, t_in, t_out, crop_at)   # crop_at(t) -> (x0, x1) in 0..1
"""
import os
import subprocess

FF = os.path.expanduser("~/Kamay/bin/ffmpeg")
FPS = 4                 # samples a second
SW, SH = 640, 360       # analysis size


def _frames(src, t_in, t_out):
    import numpy as np
    raw = subprocess.run([FF, "-loglevel", "error", "-ss", f"{t_in:.3f}", "-to", f"{t_out:.3f}", "-i", src,
                          "-vf", f"fps={FPS},scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    n = len(raw) // (SW * SH * 3)
    return np.frombuffer(raw[:n * SW * SH * 3], np.uint8).reshape(n, SH, SW, 3)


def text_rows(img):
    """[(x0, x1, y0, y1)] in 0..1 - rows of big overlay letters in one frame."""
    import cv2
    import numpy as np
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    mask = (((v >= 222) & (s <= 45)) | ((h >= 15) & (h <= 35) & (s >= 130) & (v >= 200))).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, _lab, st, _c = cv2.connectedComponentsWithStats(mask, 8)
    blobs = []
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if not (0.045 * SH <= hh <= 0.32 * SH):
            continue
        if not (0.08 <= w / hh <= 1.6):               # letter-shaped, not a bar or a lamp
            continue
        fill = a / float(w * hh)
        # an "I" or an "L" stroke is a solid bar; anything wider must have the holes of a letter
        if not (0.15 <= fill <= (1.0 if w / hh <= 0.35 else 0.88)):
            continue
        blobs.append((x, y, w, hh))
    blobs.sort()
    rows, used = [], set()
    for i, (x, y, w, hh) in enumerate(blobs):
        if i in used:
            continue
        row, cy, last = [i], y + hh / 2, x + w
        for j in range(i + 1, len(blobs)):
            if j in used:
                continue
            x2, y2, w2, h2 = blobs[j]
            if x2 - last > 1.6 * hh:
                break
            if abs((y2 + h2 / 2) - cy) <= 0.3 * hh and 0.6 <= h2 / hh <= 1.6:
                row.append(j)
                last = max(last, x2 + w2)
        if len(row) >= 3:
            used.update(row)
            xs = [blobs[k] for k in row]
            rows.append((min(b[0] for b in xs) / SW, max(b[0] + b[2] for b in xs) / SW,
                         min(b[1] for b in xs) / SH, max(b[1] + b[3] for b in xs) / SH))
    return rows


def cut_text_spans(src, t_in, t_out, crop_at, pad=0.35, min_len=0.5):
    """[(a, b)] clip seconds where a row of overlay letters crosses the crop's left or right edge."""
    fr = _frames(src, t_in, t_out)
    hits = []
    for k, img in enumerate(fr):
        t = k / FPS
        x0, x1 = crop_at(t)
        m = 0.012                                     # a letter must really be sliced, not just touch
        if any((r[0] < x0 - m < r[1]) or (r[0] < x1 + m < r[1]) for r in text_rows(img)):
            hits.append(t)
    spans = []
    for t in hits:
        if spans and t - spans[-1][1] <= 0.6:
            spans[-1][1] = t
        else:
            spans.append([t, t])
    dur = t_out - t_in
    out = []
    for a, b in spans:
        a, b = max(0.0, a - pad), min(dur, b + 1.0 / FPS + pad)
        if b - a >= min_len:
            if out and a - out[-1][1] < 1.0:          # never flip back and forth inside a second
                out[-1] = (out[-1][0], b)
            else:
                out.append((a, b))
    return [(round(a, 2), round(b, 2)) for a, b in out]


def fit_graph(w=1080, h=1920):
    """The whole wide picture centred on black - a cinema letterbox. A blurred fill was tried first
    (4 Nov 2026): it showed a giant smeared copy of the very words being saved."""
    return f"scale={w}:-2,pad={w}:{h}:0:(oh-ih)/2:black,setsar=1,fps=30"


def with_fit(geo, spans):
    """Wrap a crop geometry so the spans show the whole picture instead. No spans = geo unchanged."""
    if not spans:
        return geo
    en = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in spans)
    return (f"split=2[tsc][tsw];[tsc]{geo}[tscc];[tsw]{fit_graph()}[tsww];"
            f"[tscc][tsww]overlay=0:0:enable='{en}'")
