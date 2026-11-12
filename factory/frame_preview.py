#!/usr/bin/env python3
"""THE FRAME LOOK, as prototypes for Kamay to choose (cloud, by hand). Nothing here posts.

11 Nov 2026, Kamay, showing instagram.com/trudeau_files: "his hooks and the way his clips are
placed in the space of the phone specifically are really great, comfortable to watch and very
calling." Measured from five of that account's reels (1080x1920):

  - the picture is a 9:8 window (1080x960) in the MIDDLE of the phone, y 480-1440. From a 16:9
    source that shows 63% of the width, scaled DOWN (x0.89). Ours fills 9:16: 32% of the
    width, scaled UP x1.78 on a 1080p source. Theirs is sharper and shows his hands.
  - the headline sits in the black band right above the picture and stays for the whole clip.
  - nothing sits under Instagram's own buttons and caption (the bottom ~20% is plain black).
  - captions are one or two words, small, in the middle of the picture.

Two looks of the same clip, word timing from the production engine (kt_words + anchor + align):

  F1_FILES    their layout as measured: black, a white geometric sans headline, 1-2 word captions.
  F2_ARCHIVE  the same layout in Kamay's "Hidden Knowledge Archive" brief: charcoal + film grain,
              Cormorant Garamond headline in ivory with the last line in aged gold, a tracked
              gold slug above, a real source credit under the picture, calm sentence captions.
  F3_ARCHIVE_TIE  Kamay, 11 Nov, on seeing F2: "Archive look but I do not want the CC under, I
              want them where the tie was." The Archive look with the captions back INSIDE the
              picture at tie height (under his chin, on his chest), a soft shade behind them so
              ivory reads on a white shirt. The picture returns to the middle (480-1440).

  F4_APPRENTICE  Kamay, 12 Nov, showing instagram.com/kevins_apprentice ("100% duplicate that
              guy's clips, but with our KT clips ... hooks, CC, all of the effects, the other
              videos going along with KT"). Measured on their three breakout reels (45K-232K
              views): the WHOLE 16:9 picture in the middle of the phone on black, no headline,
              captions one or two words at a time in the centre of the picture - small white
              for ordinary words, BIG heavy capitals for the money and power words, italic
              serif for names and places - and other footage laid over his voice where he
              tells the story (the jet, the old book). PREVIEW_SCENES gives those shots:
              "0|4|vintage telephone;@Bellagio|3.5|lake como italy" = start (seconds, or
              @the-word-he-says) | seconds | what to look for on Pixabay.

PREVIEW_LOOKS=F3_ARCHIVE_TIE renders only the looks named (comma separated); default all.

    python factory/frame_preview.py <vid> <in> <out> "<line 1|line 2>" "<SOURCE CREDIT>" <slug>
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
K = os.path.expanduser("~/Kamay")
# factory/ holds a queue.py. Python puts the script's own folder FIRST, so "import queue"
# inside torch found ours, torch failed to import and every preview said "aligner not
# installed". Our folder goes LAST: transcribe is still found, the standard library wins.
sys.path = [p_ for p_ in sys.path if os.path.abspath(p_ or ".") != HERE]
sys.path.insert(0, K)
sys.path.append(HERE)

vid, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
hook = [x.strip() for x in sys.argv[4].split("|") if x.strip()]
credit, slug = sys.argv[5], sys.argv[6]
OUT = os.environ.get("PREVIEW_OUT", "/tmp/previews")
FONTS = os.environ.get("PREVIEW_FONTS", "/tmp/fonts")
FF = os.path.join(K, "bin", "ffmpeg") if os.path.exists(os.path.join(K, "bin", "ffmpeg")) else "ffmpeg"
os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(OUT, "_tmp")
os.makedirs(TMP, exist_ok=True)
F_JOSEFIN = os.path.join(FONTS, "josefin600.ttf")
F_SERIF = os.path.join(FONTS, "cormorant600.ttf")
F_SERIF_I = os.path.join(FONTS, "cormorant600i.ttf")
F_MONT = os.path.join(FONTS, "montserrat600.ttf")

W, H = 1080, 1920
PIC_Y, PIC_H = 480, 960
IVORY, GOLD, CHARCOAL = (243, 236, 221), (185, 151, 91), (13, 13, 15)


def sh(*c):
    r = subprocess.run(c, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-1500:])
    return r


if os.environ.get("PREVIEW_LOCAL_SRC"):
    src = os.environ["PREVIEW_LOCAL_SRC"]
else:
    from transcribe import fetch_source
    src = fetch_source(vid)
dur = b - a

# --- the words, timed exactly as production times them -------------------------------------
words = []
try:
    import kt_words
    words = kt_words.words_for(src, a, b, "PREVIEW/" + slug)
    try:
        import vsc_v2_time
        words = vsc_v2_time.anchor_words(src, a, b, words)
    except Exception as e:
        print("anchor skipped:", e)
    try:
        import kt_align
        words = kt_align.align(src, a, b, words)
    except Exception as e:
        print("align skipped:", e)
except Exception as e:
    print("word timing unavailable:", type(e).__name__, e)
words = [(float(x), float(y), str(w).strip()) for x, y, w in words if str(w).strip()]
print(f"{len(words)} words")


def bursts(ws, max_words=2, max_chars=13, gap=0.28):
    """1-2 words on screen, each from its own first sound to its last."""
    out, cur = [], []
    for w in ws:
        if cur and (len(cur) >= max_words or w[0] - cur[-1][1] > gap
                    or len(" ".join(x[2] for x in cur) + " " + w[2]) > max_chars
                    or cur[-1][2][-1:] in ".!?,"):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    res = []
    for k, g in enumerate(out):
        end = g[-1][1]
        if k + 1 < len(out):                       # hold through a short gap, never past the next word
            end = min(max(end, g[0][0] + 0.18), out[k + 1][0][0])
        res.append((g[0][0], end, " ".join(x[2] for x in g).strip(",.").strip()))
    return [r for r in res if r[2]]


def phrases(ws):
    try:
        import kt_render as KR
        KR.CAP_MAX = 26
        ws2 = KR.drop_stutters(list(ws))
        return [(x, y, t) for x, y, t in KR.phrases_from_words(ws2)]
    except Exception as e:
        print("production phrases unavailable, using bursts:", type(e).__name__, e)
        return bursts(ws, 4, 24, 0.4)


# --- where he is, and how tight we may go without ever scaling the picture up --------------
def probe_size():
    import re
    r = subprocess.run([FF, "-hide_banner", "-i", src], capture_output=True, text=True)
    m = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", r.stderr)
    return int(m.group(1)), int(m.group(2))


sw, shh = probe_size()
faces = []
try:
    import cv2
    det = cv2.FaceDetectorYN_create(os.path.join(K, "bin", "yunet.onnx"), "", (320, 320), 0.6, 0.3, 5000)
    for k in range(10):
        t = a + dur * (k + 0.5) / 10
        fp = os.path.join(TMP, "_f.jpg")
        sh(FF, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", "-vf", "scale=640:-2", fp)
        img = cv2.imread(fp)
        if img is None:
            continue
        det.setInputSize((img.shape[1], img.shape[0]))
        _, f = det.detect(img)
        if f is not None and len(f):
            z = max(f, key=lambda q: q[2] * q[3])
            faces.append(((z[0] + z[2] / 2) / img.shape[1], (z[1] + z[3] / 2) / img.shape[0], z[3] / img.shape[0]))
except Exception as e:
    print("face detector unavailable:", e)
med = lambda v: sorted(v)[len(v) // 2]
fx, fy, fh = (med([f[0] for f in faces]), med([f[1] for f in faces]), med([f[2] for f in faces])) if faces else (0.5, 0.4, 0.3)
# his face about a third of the picture's height; the window never smaller than 960 source
# pixels tall (so it is never scaled up) and never taller than the source.
# a wide desk shot may come in a little (never more than x1.35 up), so he is not a small figure
ch = max(min(shh, 960 / 1.35), min(shh, fh * shh / 0.34))
cw = min(sw, ch * 9 / 8)
ch = cw * 8 / 9
x0 = max(0, min(sw - cw, fx * sw - cw / 2))
y0 = max(0, min(shh - ch, fy * shh - ch * 0.42))
crop = f"crop={int(cw) // 2 * 2}:{int(ch) // 2 * 2}:{int(x0)}:{int(y0)},scale={W}:{PIC_H}:flags=lanczos"
PIC_A = 440                    # the Archive look: picture 440-1400, captions on their own black line under it
print(f"source {sw}x{shh}, face at x={fx:.2f} y={fy:.2f} h={fh:.2f} ({len(faces)} frames); "
      f"window {int(cw)}x{int(ch)} -> scale x{PIC_H / ch:.2f}")


# --- the still graphics, drawn once -----------------------------------------------------
def fit(font_path, lines, size, max_w, floor=40):
    from PIL import ImageFont
    fo = ImageFont.truetype(font_path, size)
    while size > floor and max(fo.getlength(t) for t in lines) > max_w:
        size -= 2
        fo = ImageFont.truetype(font_path, size)
    return fo, size


def tracked(d, xy_center, text, font, fill, track):
    """Letter-spaced capitals, centred on x."""
    wid = sum(font.getlength(c) for c in text) + track * (len(text) - 1)
    x, y = xy_center[0] - wid / 2, xy_center[1]
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += font.getlength(c) + track
    return wid


def overlay_files(path, PIC_Y=PIC_Y):
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fo, size = fit(F_JOSEFIN, hook, 62, W - 110)
    step = int(size * 1.12)
    top = PIC_Y - 30 - step * len(hook)
    for layer, fill in ((glow, (255, 255, 255, 90)), (img, (255, 255, 255, 255))):
        d = ImageDraw.Draw(layer)
        for i, t in enumerate(hook):
            d.text(((W - fo.getlength(t)) / 2, top + i * step), t, font=fo, fill=fill)
    out = Image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(9)), img)
    out.save(path)
    return path


def overlay_archive(path, PIC_Y=PIC_A, credit_dy=112, shade_y=None):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shade_y:                # captions inside the picture: a soft shade, strongest on their line
        for yy in range(max(PIC_Y, shade_y - 130), min(PIC_Y + PIC_H, shade_y + 130)):
            k = 1 - abs(yy - shade_y) / 130
            d.line((0, yy, W, yy), fill=(8, 8, 10, int(118 * k * k * (3 - 2 * k))))
    fo, size = fit(F_SERIF, hook, 84, W - 120, floor=52)
    fi = ImageFont.truetype(F_SERIF_I, size)
    step = int(size * 1.08)
    top = PIC_Y - 44 - step * len(hook)
    for i, t in enumerate(hook):
        last = i == len(hook) - 1 and len(hook) > 1
        f_ = fi if last else fo
        d.text(((W - f_.getlength(t)) / 2, top + i * step), t, font=f_, fill=(GOLD if last else IVORY) + (255,))
    # the slug above the headline: tracked gold capitals between two short rules
    fs = ImageFont.truetype(F_MONT, 23)
    sy = top - 58
    wid = tracked(d, (W / 2, sy), "THE HIDDEN KNOWLEDGE ARCHIVE", fs, GOLD + (235,), 7)
    for sx in (W / 2 - wid / 2 - 96, W / 2 + wid / 2 + 26):
        d.line((sx, sy + 13, sx + 70, sy + 13), fill=GOLD + (150,), width=2)
    # hairlines hugging the picture, and the real source under it
    for yy in (PIC_Y - 1, PIC_Y + PIC_H):
        d.line((0, yy, W, yy), fill=GOLD + (120,), width=2)
    fc = ImageFont.truetype(F_MONT, 19)
    tracked(d, (W / 2, PIC_Y + PIC_H + credit_dy), credit.upper(), fc, IVORY + (105,), 5)
    img.save(path)
    return path


def tf(name, text):
    p = os.path.join(TMP, f"{name}.txt")
    open(p, "w").write(text)
    return p


def caps(items, font, size, y, color, prefix, shadow="black@0.75", border=0):
    out = []
    for n, (x0_, x1_, t) in enumerate(items):
        out.append(f"drawtext=fontfile={font}:textfile={tf(f'{prefix}{n}', t)}:fontsize={size}:fontcolor={color}:"
                   f"shadowcolor={shadow}:shadowx=0:shadowy=3:borderw={border}:bordercolor=black@0.55:"
                   f"x=(w-text_w)/2:y={y}-text_h/2:"
                   f"enable='between(t,{max(0, x0_):.2f},{x1_:.2f})'")
    return out


# captions never sit on his eyes or mouth: under his chin when the picture has the room,
# else low in the picture (trudeau_files leaves them dead centre, which lands on the nose in
# a close-up).
chin = PIC_Y + ((fy + fh * 0.5) * shh - y0) / ch * PIC_H
CAP_F1 = int(max(PIC_Y + PIC_H // 2 + 60, min(chin + 70, PIC_Y + PIC_H - 90)))
# "where the tie was": about half a face below his chin, never nearer than 70 px to the chin
# and never in the bottom edge of the picture.
face_px = fh * shh / ch * PIC_H
CAP_TIE = int(max(chin + 70, min(chin + 0.45 * face_px, PIC_Y + PIC_H - 120)))
print(f"chin at y={chin:.0f}, face {face_px:.0f}px tall, tie captions at y={CAP_TIE}")
GRADE = "eq=contrast=1.06:saturation=0.9:brightness=-0.01,colorbalance=rs=0.025:bs=-0.035"
looks = {
    "F1_FILES": {
        "pic": crop, "canvas": "black", "post": [], "y": PIC_Y,
        "overlay": overlay_files(os.path.join(TMP, "ov_files.png")),
        "caps": caps(bursts(words), F_JOSEFIN, 46, CAP_F1, "white", "f", border=3),
    },
    "F2_ARCHIVE": {
        "pic": f"{crop},{GRADE}", "canvas": "0x0D0D0F", "post": ["noise=alls=5:allf=t"], "y": PIC_A,
        "overlay": overlay_archive(os.path.join(TMP, "ov_archive.png")),
        "caps": caps(phrases(words), F_MONT, 48, PIC_A + PIC_H + 54, "0xF3ECDD", "a"),
    },
    "F3_ARCHIVE_TIE": {
        "pic": f"{crop},{GRADE}", "canvas": "0x0D0D0F", "post": ["noise=alls=5:allf=t"], "y": PIC_Y,
        "overlay": overlay_archive(os.path.join(TMP, "ov_archive_tie.png"), PIC_Y, 58, CAP_TIE),
        "caps": caps(phrases(words), F_MONT, 50, CAP_TIE, "0xF3ECDD", "t", shadow="black@0.85", border=3),
    },
}
only = [x.strip() for x in os.environ.get("PREVIEW_LOOKS", "").split(",") if x.strip()]
if only:
    looks = {k_: v_ for k_, v_ in looks.items() if k_ in only}
for k_, t_ in enumerate((0.25, 0.5, 0.75)):
    sh(FF, "-y", "-loglevel", "error", "-ss", f"{a + dur * t_:.2f}", "-i", src, "-frames:v", "1", "-q:v", "2",
       os.path.join(OUT, f"{slug}_still{k_}.jpg"))
made = []
for name, L in looks.items():
    dst = os.path.join(OUT, f"{slug}_{name}.mp4")
    graph = (f"[0:v]{L['pic']},pad={W}:{H}:0:{L['y']}:color={L['canvas']}"
             + "".join("," + p for p in L["post"]) + "[bg];[bg][1:v]overlay=0:0"
             + "".join("," + c for c in L["caps"])
             + f",fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.6:.2f}:d=0.6,format=yuv420p[v]")
    gp = os.path.join(TMP, f"{name}.graph")
    open(gp, "w").write(graph)
    r = sh(FF, "-y", "-loglevel", "error", "-ss", f"{a:.2f}", "-t", f"{dur:.2f}", "-i", src,
           "-loop", "1", "-t", f"{dur:.2f}", "-i", L["overlay"],
           "-filter_complex_script", gp, "-map", "[v]", "-map", "0:a?",
           "-af", f"afade=t=in:st=0:d=0.05,afade=t=out:st={dur - 0.6:.2f}:d=0.6",
           "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", dst)
    ok = r.returncode == 0 and os.path.exists(dst)
    print(name, "OK" if ok else "FAILED")
    if ok:
        made.append(dst)
        # the cover: the frame Instagram and YouTube would show, taken while he is mid-thought
        sh(FF, "-y", "-loglevel", "error", "-ss", f"{min(1.2, dur / 2):.2f}", "-i", dst, "-frames:v", "1",
           os.path.join(OUT, f"{slug}_{name}_cover.jpg"))
if "F4_APPRENTICE" in only:
    import re
    PH4 = 608
    PY4 = (H - PH4) // 2
    CY4 = PY4 + PH4 // 2
    F_BLACK = os.path.join(K, "bin", "mont_black.ttf")
    POWER = set("money rich richest wealth wealthy millionaire billionaire millions billions million billion "
                "cash free freedom secret secrets never always nothing everything broke bankrupt".split())
    I_WORDS = {"i", "i'd", "i'm", "i'll", "i've"}

    def tier(k):
        w = words[k][2]
        core = w.strip(".,!?\"'()").lower()
        if re.search(r"\d", w) or core in POWER:
            return "big"
        prev = words[k - 1][2] if k else "."
        if (w[:1].isupper() and core not in I_WORDS and core != "mr"
                and not prev.rstrip("\"')").endswith((".", "!", "?"))):
            return "ital"
        return "small"

    groups, cur = [], []                 # (tier, [word indexes])
    for k, w in enumerate(words):
        t_ = tier(k)
        if t_ != "small":
            if cur:
                groups.append(("small", cur)); cur = []
            if groups and groups[-1][0] == t_ == "ital" and w[0] - words[groups[-1][1][-1]][1] < 0.25:
                groups[-1][1].append(k)                 # "American Express", "Royal Families"
            else:
                groups.append((t_, [k]))
            continue
        if cur and (len(cur) >= 2 or w[0] - words[cur[-1]][1] > 0.28
                    or len(" ".join(words[j][2] for j in cur) + " " + w[2]) > 12
                    or words[cur[-1]][2][-1:] in ".!?,"):
            groups.append(("small", cur)); cur = []
        cur.append(k)
    if cur:
        groups.append(("small", cur))
    style = {"small": (F_MONT, 46, "white"), "big": (F_BLACK, 104, "white"), "ital": (F_SERIF_I, 76, "white")}
    cap4 = []
    for n, (t_, idx) in enumerate(groups):
        st = words[idx[0]][0]
        en = words[idx[-1]][1]
        if n + 1 < len(groups):
            en = min(max(en, st + 0.16), words[groups[n + 1][1][0]][0])
        txt = " ".join(words[j][2] for j in idx).strip(",.\"").strip()
        if t_ == "big":
            txt = txt.upper().rstrip("!?")
        if not txt:
            continue
        font, size, col = style[t_]
        cap4.append(f"drawtext=fontfile={font}:textfile={tf(f'p{n}', txt)}:expansion=none:fontsize={size}:fontcolor={col}:"
                    f"shadowcolor=black@0.8:shadowx=0:shadowy=3:borderw=2:bordercolor=black@0.45:"
                    f"x=(w-text_w)/2:y={CY4}-text_h/2:enable='between(t,{max(0, st):.2f},{en:.2f})'")
    # the other footage, laid over his voice
    scenes, extra_in = [], []
    for spec in [x for x in os.environ.get("PREVIEW_SCENES", "").split(";") if x.strip()]:
        try:
            at, secs, query = [x.strip() for x in spec.split("|")]
            secs = float(secs)
            if at.startswith("@"):
                hit = next((w for w in words if w[2].strip(".,!?\"'").lower().startswith(at[1:].lower())), None)
                if not hit:
                    print(f"scene skipped: he never says '{at[1:]}'")
                    continue
                t0 = max(0.0, hit[0] - 0.15)
            else:
                t0 = float(at)
            import kt_opener as OP
            shot = OP.pick(query, secs)
            if not shot:
                print(f"scene skipped: no shot for '{query}'")
                continue
            scenes.append((t0, min(secs, dur - t0 - 0.7), shot))
        except Exception as e:
            print("scene skipped:", spec, type(e).__name__, e)
    graph = (f"[0:v]scale={W}:{PH4}:flags=lanczos,eq=contrast=1.04:saturation=1.05,"
             f"pad={W}:{H}:0:{PY4}:color=black,setsar=1,fps=30[b0];")
    last = "b0"
    for i, (t0, d_, shot) in enumerate(scenes):
        extra_in += ["-ss", f"{float(shot.get('start', 0)):.2f}", "-t", f"{d_:.2f}", "-i", shot["path"]]
        graph += (f"[{i + 1}:v]scale={W}:{PH4}:force_original_aspect_ratio=increase,crop={W}:{PH4},setsar=1,fps=30,"
                  f"eq=contrast=1.05:saturation=0.95,format=yuva420p,"
                  f"fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={d_ - 0.3:.2f}:d=0.3:alpha=1,"
                  f"setpts=PTS-STARTPTS+{t0:.2f}/TB[s{i}];"
                  f"[{last}][s{i}]overlay=0:{PY4}:eof_action=pass:enable='between(t,{t0:.2f},{t0 + d_:.2f})'[b{i + 1}];")
        last = f"b{i + 1}"
    graph += (f"[{last}]" + ",".join(cap4 + [f"fade=t=out:st={dur - 0.6:.2f}:d=0.6", "format=yuv420p"]) + "[v]")
    gp = os.path.join(TMP, "F4.graph")
    open(gp, "w").write(graph)
    dst = os.path.join(OUT, f"{slug}_F4_APPRENTICE.mp4")
    r = sh(FF, "-y", "-loglevel", "error", "-ss", f"{a:.2f}", "-t", f"{dur:.2f}", "-i", src, *extra_in,
           "-filter_complex_script", gp, "-map", "[v]", "-map", "0:a?",
           "-af", f"afade=t=in:st=0:d=0.05,afade=t=out:st={dur - 0.6:.2f}:d=0.6",
           "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "9000k", "-bufsize", "18000k",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{dur:.2f}", dst)
    ok = r.returncode == 0 and os.path.exists(dst)
    print("F4_APPRENTICE", "OK" if ok else "FAILED", f"- {len(groups)} caption pieces, {len(scenes)} scene(s): "
          + ", ".join(f"{t0:.1f}s '{sh_['query']}'" for t0, _d, sh_ in scenes))
    if ok:
        made.append(dst)
        json.dump([[round(words[i[0]][0], 2), t_, " ".join(words[j][2] for j in i)] for t_, i in groups],
                  open(os.path.join(OUT, f"{slug}_F4_caps.json"), "w"))
json.dump({"vid": vid, "in": a, "out": b, "hook": hook, "credit": credit, "slug": slug,
           "source": [sw, shh], "window": [int(cw), int(ch)], "scale": round(PIC_H / ch, 3),
           "words": len(words)}, open(os.path.join(OUT, f"{slug}_info.json"), "w"))
import shutil
shutil.rmtree(TMP, ignore_errors=True)
if not made:
    sys.exit("no look rendered")
