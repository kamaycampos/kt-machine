"""PODCAST SCREENS: LOCK ON THE SPEAKER'S PANEL (17 Oct 2026).

"What Michael Jordan missed the most" (KT_EXPOSEDR2) went out showing a host's webcam,
a book advert and a "LIKE, SHARE & SUBSCRIBE" banner. Kevin was in the same frame the
whole time - in a clean, lit HD panel on the right - and never appeared, because a
9:16 crop of a three-panel stream screen centred on the middle of it.

A stream screen is told apart from a camera shot by its BORDERS: panel edges are
straight lines that stay put for the whole clip while everything inside them moves.
Sample frames, find the main (largest) face, and look for persistent edges on each side
of it. Three or four sides bordered, and the panel at most 75% of the frame = a layout;
the crop is then cut from inside the speaker's panel only. Anything less is an ordinary
camera shot and the usual tracked crop stands (a doorframe or a table edge gives one or
two persistent lines, never a box).

    panel_geo(src, t_in, t_out) -> (ffmpeg crop chain, info) or (None, info)
"""
import os

import numpy as np

MODEL = os.path.expanduser(os.environ.get("KT_HOME", "~/Kamay") + "/bin/yunet.onnx")
W, H = 1080, 1920
STRONG = 0.45            # an edge present in at least this share of frames, along the side
MIN_SIDES = 3
MAX_AREA = 0.75


def _frames(src, t_in, t_out, n):
    import cv2
    cap = cv2.VideoCapture(src)
    out = []
    for i in range(n):
        t = t_in + (t_out - t_in) * (i + 0.5) / n
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, f = cap.read()
        if ok:
            out.append(f)
    cap.release()
    return out


def _main_face(frames):
    import cv2
    h, w = frames[0].shape[:2]
    det = cv2.FaceDetectorYN_create(MODEL, "", (w, h), 0.6, 0.3, 5000)
    boxes = []
    for f in frames:
        _, faces = det.detect(f)
        if faces is not None and len(faces):
            x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])[:4]
            boxes.append((x, y, fw, fh))
    if len(boxes) < max(2, len(frames) // 2):
        return None
    return tuple(float(np.median([b[i] for b in boxes])) for i in range(4))


def _border(profile, lo, hi, prefer_far):
    """Strongest persistent line in profile[lo:hi]; None if none is strong enough."""
    lo, hi = max(0, int(lo)), min(len(profile), int(hi))
    if hi - lo < 3:
        return None
    seg = profile[lo:hi]
    if seg.max() < STRONG:
        return None
    idx = np.where(seg >= STRONG)[0]
    return lo + int(idx[0] if prefer_far == "low" else idx[-1])


def panel_box(src, t_in, t_out, n=10):
    """(x0, y0, x1, y1, face) of the speaker's panel, or None for a camera shot."""
    import cv2
    frames = _frames(src, t_in, t_out, n)
    if len(frames) < 4:
        return None, "too few frames"
    face = _main_face(frames)
    if not face:
        return None, "no steady face"
    fx, fy, fw, fh = face
    h, w = frames[0].shape[:2]
    persist = np.mean([cv2.Canny(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), 60, 160) > 0
                       for f in frames], axis=0)
    # vertical lines along the face's height band, horizontal along its width band
    ya, yb = int(max(0, fy - 0.8 * fh)), int(min(h, fy + 3.0 * fh))
    xa, xb = int(max(0, fx - 1.0 * fw)), int(min(w, fx + 2.0 * fw))
    col = persist[ya:yb].mean(axis=0)
    row = persist[:, xa:xb].mean(axis=1)
    # the line CLOSEST to the face on each side bounds its panel
    left = _border(col, 4, fx - 0.4 * fw, "high")
    right = _border(col, fx + 1.4 * fw, w - 4, "low")
    top = _border(row, 4, fy - 0.3 * fh, "high")
    bottom = _border(row, fy + 2.0 * fh, h - 4, "low")
    # A dark sweater on a dark banner leaves no visible bottom edge (the Jordan clip),
    # but the panel's SIDE border still stops where the panel stops: read a missing
    # top or bottom off the run of the side line that passes the face.
    if top is None or bottom is None:
        runs = []
        mid = int(fy + fh / 2)
        for xs in (v for v in (left, right) if v is not None):
            line = persist[:, max(0, xs - 2):xs + 3].max(axis=1)
            if line[mid] < 0.3:
                continue
            a = b = mid
            while a > 0 and line[a - 1] >= 0.3:
                a -= 1
            while b < h - 1 and line[b + 1] >= 0.3:
                b += 1
            runs.append((a, b))
        if runs:                    # the LONGEST side line: one side can fade into the dark
            a, b = max(runs, key=lambda r: r[1] - r[0])
            if top is None and a > 4:
                top = a
            if bottom is None and b < h - 5:
                bottom = b
    sides = sum(v is not None for v in (left, right, top, bottom))
    x0, x1 = (left or 0), (right or w)
    y0, y1 = (top or 0), (bottom or h)
    area = (x1 - x0) * (y1 - y0) / float(w * h)
    why = f"sides {sides}/4, panel {x1 - x0}x{y1 - y0} at {x0},{y0} ({area:.0%} of frame)"
    if sides < MIN_SIDES or area > MAX_AREA:
        return None, "camera shot: " + why
    return (x0, y0, x1, y1, face), "STREAM LAYOUT: " + why


def panel_geo(src, t_in, t_out):
    """The 9:16 crop chain from inside the speaker's panel, or None."""
    box, why = panel_box(src, t_in, t_out)
    if not box:
        return None, why
    x0, y0, x1, y1, (fx, fy, fw, fh) = box
    x0, y0, x1, y1 = x0 + 3, y0 + 3, x1 - 3, y1 - 3          # never the border itself
    pw, ph = x1 - x0, y1 - y0
    if pw >= ph * 9 / 16:
        ch = ph // 2 * 2
        cw = int(ch * 9 / 16) // 2 * 2
    else:
        cw = pw // 2 * 2
        ch = min(ph, int(cw * 16 / 9)) // 2 * 2
    cx = fx + fw / 2
    x = int(min(max(cx - cw / 2, x0), x1 - cw))
    y = int(min(max(fy - 0.45 * fh - ch * 0.12, y0), y1 - ch))
    up = H / float(ch)
    sharpen = ",unsharp=5:5:0.5" if up > 1.5 else ""
    geo = (f"crop={cw}:{ch}:{x}:{y},scale={W}:{H}:flags=lanczos{sharpen},setsar=1,fps=30")
    return geo, f"{why}; crop {cw}x{ch} at {x},{y} (x{up:.1f})"
