#!/usr/bin/env python3
"""Render ONE clip in several looks, side by side, for Kamay to choose (cloud, by hand).

1 Nov 2026, Kamay, showing kevintrudeau_insights and kevins_apprentice (220K / 401K / 109K
views): "they feel much more exclusive, professional... ours feels AI, superficial, no soul,
no creativity, no aesthetic." Ours stacks a green hook card, a gold bar and shouting word-by-
word captions on every clip. RULES #17: show the thing before changing the machine. Nothing
here touches the posting queue; the files go to the 'previews' release.

    python factory/style_preview.py <vid> <in> <out> "<label>"
"""
import json, os, re, subprocess, sys, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from transcribe import fetch_source  # noqa: E402

K = os.path.expanduser("~/Kamay")
vid, a, b, label = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
OUT = "/tmp/previews"
os.makedirs(OUT, exist_ok=True)
SERIF = "/tmp/fonts/serif.ttf"
SANS = "/tmp/fonts/sans.ttf"


def sh(*c):
    r = subprocess.run(c, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-1500:])
    return r


src = os.environ.get("PREVIEW_LOCAL_SRC") or fetch_source(vid)     # local test: a stand-in video
# the transcript, for honest sentence captions
if not os.environ.get("PREVIEW_LOCAL_SRC"):
  sh("gh", "release", "download", "sources", "-R", os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine"),
   "-p", f"{vid}.srt.enc", "-D", "/tmp", "--clobber")
srt = os.environ.get("PREVIEW_LOCAL_SRT") or f"/tmp/{vid}.srt"
for kname in ([] if os.environ.get("PREVIEW_LOCAL_SRT") else ["TRANSCRIPT_KEY", "FACTORY_KEY"]):
    if sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", f"env:{kname}",
          "-in", f"/tmp/{vid}.srt.enc", "-out", srt).returncode == 0:
        break
cues = []
for h1, m1, s1, ms1, h2, m2, s2, ms2, t in re.findall(
        r"(\d+):(\d+):(\d+)[,.](\d+) --> (\d+):(\d+):(\d+)[,.](\d+)\n(.+?)(?:\n\n|\Z)", open(srt).read(), re.S):
    x = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
    y = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
    if y > a and x < b:
        cues.append((max(0.0, x - a), min(b, y) - a, " ".join(t.split())))

# where the speaker sits (median face x across the clip), for the vertical crop
xs = []
try:
    import cv2
    det = cv2.FaceDetectorYN_create(os.path.join(K, "bin", "yunet.onnx"), "", (320, 320), 0.6, 0.3, 5000)
    for k in range(8):
        t = a + (b - a) * (k + 0.5) / 8
        sh("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
           "-vf", "scale=640:-2", "/tmp/_f.jpg")
        img = cv2.imread("/tmp/_f.jpg")
        if img is None:
            continue
        det.setInputSize((img.shape[1], img.shape[0]))
        _, f = det.detect(img)
        if f is not None and len(f):
            z = max(f, key=lambda q: q[2])
            xs.append((z[0] + z[2] / 2) / img.shape[1])
except Exception as e:
    print("face detector unavailable:", e)
cx = sorted(xs)[len(xs) // 2] if xs else 0.5
print(f"speaker at x={cx:.2f} ({len(xs)} frames)")


def tf(name, text):
    p = f"/tmp/txt_{name}.txt"
    open(p, "w").write(text)
    return p


def subs(y, size, color="white", width=30, prefix="s"):
    """Sentence captions, two short lines at most, each line centred, each cue split evenly in time."""
    out = []
    for n, (x0, x1, t) in enumerate(cues):
        lines = textwrap.wrap(t, width)
        chunks = [lines[i:i + 2] for i in range(0, len(lines), 2)] or [[]]
        step = (x1 - x0) / len(chunks)
        for k, ch in enumerate(chunks):
            s0, s1 = x0 + k * step, x0 + (k + 1) * step
            for j, line in enumerate(ch):
                out.append(f"drawtext=fontfile={SANS}:textfile={tf(f'{prefix}{n}_{k}_{j}', line)}:"
                           f"fontsize={size}:fontcolor={color}:borderw=0:"
                           f"shadowcolor=black@0.6:shadowx=0:shadowy=2:x=(w-text_w)/2:y={y + j * int(size * 1.35)}:"
                           f"enable='between(t,{s0:.2f},{s1:.2f})'")
    return out


def title(y, size, text, until=3.2, font=SERIF, name="t", width=18):
    """A quiet label: up to two centred lines, fading in and out."""
    out = []
    for j, line in enumerate(textwrap.wrap(text, width)[:2]):
        out.append(f"drawtext=fontfile={font}:textfile={tf(f'{name}{j}', line)}:fontsize={size}:fontcolor=white:"
                   f"x=(w-text_w)/2:y={y + j * int(size * 1.3)}:"
                   f"alpha='if(lt(t,0.3),t/0.3,if(lt(t,{until - 0.4}),1,max(0,({until}-t)/0.4)))':"
                   f"enable='lt(t,{until})'")
    return ",".join(out)


dur = b - a
GRADE = "eq=contrast=1.07:saturation=0.88:brightness=-0.015,colorbalance=rs=0.03:gs=0.0:bs=-0.04,vignette=PI/5,noise=alls=3:allf=t"
crop = f"crop=ih*9/16:ih:max(0\\,min(iw-ih*9/16\\,{cx:.4f}*iw-ih*9/32)):0,scale=1080:1920"
looks = {
    # A: kevintrudeau_insights - the picture alone, graded like film; the caption carries the words
    "A_CINEMA_NO_TEXT": f"{crop},{GRADE}",
    # B: the same, plus a quiet serif label for 3 s and small sentence captions low in the frame
    "B_CINEMA_LABEL": ",".join([crop, GRADE, title(250, 62, label.upper())] + subs(1500, 46)),
    # C: the podcast-letterbox look: the full wide shot, a serif title above, captions below
    "C_LETTERBOX": ",".join([f"scale=1080:-2,{GRADE},pad=1080:1920:0:(1920-ih)/2-60:black",
                             title(470, 54, label.upper(), until=dur, name="t2", width=22)] + subs(1390, 44, "white@0.9", 34, "c")),
}
for name, vf in looks.items():
    dst = os.path.join(OUT, f"{vid}_{name}.mp4")
    r = sh("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.2f}", "-t", f"{dur:.2f}", "-i", src,
           "-vf", vf, "-af", f"afade=t=out:st={dur - 0.5:.2f}:d=0.5", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", dst)
    print(name, "OK" if r.returncode == 0 and os.path.exists(dst) else "FAILED")
json.dump({"vid": vid, "in": a, "out": b, "label": label, "cx": cx}, open(os.path.join(OUT, "info.json"), "w"))
