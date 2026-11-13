#!/usr/bin/env python3
"""THE EPISODE BUILDER (12 Nov 2026). One story clip in the pattern measured in
factory/EPISODE_PATTERN.md: jump cuts of Kevin telling one story, other pictures laid over his
voice where he tells it, captions in five voices in the centre of the picture, the book on white
as the last second. 16:9, like theirs. By hand, from the episode-build workflow. Never posts.

    python factory/episode_build.py factory/episodes/<slug>/spec.json list    # print the timed words
    python factory/episode_build.py factory/episodes/<slug>/spec.json         # build

spec.json (every number is a WORD INDEX from the "list" run, never a guessed second):
  vid, t_in, t_out     the stretch of the episode to time
  keeps [[a, b], ..]   the pieces kept, in order (jump cuts between them)
  scenes [{src, from, to, move}]   src = a picture beside the spec, or {"pixabay": id, "q": "..."};
                       on screen from word `from` to the end of word `to`; move = in / out / left / right
  voices {"12": "F"}   how a word is written: s plain, F formal script, B brush script, I bold italic,
                       X big capitals, XI big italic capitals, T teal, flag:US / CA / AU / ZA / UK / EU
  big_from             from this word on, every word is X unless `voices` says otherwise
  join [[a, b], ..]    words shown together as one line
  fix {"31": "Royal"}  what a mis-heard word should read
  drop [..]            words that get no caption
  states [{from, to, show: [[pos, [[text, voice], ..]], ..]}]   a hand-placed layout for a stretch
                       (pos: C centre, L left, R right, B below, T above)
  end_card, end_secs   the still that closes it
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
K = os.path.expanduser("~/Kamay")
sys.path = [p_ for p_ in sys.path if os.path.abspath(p_ or ".") != HERE]
sys.path.insert(0, K)
sys.path.append(HERE)

spec_path = os.path.abspath(sys.argv[1])
LIST = len(sys.argv) > 2 and sys.argv[2] == "list"
SP = json.load(open(spec_path))
EDIR = os.path.dirname(spec_path)
slug = SP["slug"]
OUT = os.environ.get("PREVIEW_OUT", "/tmp/previews")
FONTS = os.environ.get("PREVIEW_FONTS", "/tmp/fonts")
FF = os.path.join(K, "bin", "ffmpeg") if os.path.exists(os.path.join(K, "bin", "ffmpeg")) else "ffmpeg"
os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(OUT, f"_ep_{slug}")
os.makedirs(TMP, exist_ok=True)
W, H = 1920, 1080
a, b = float(SP["t_in"]), float(SP["t_out"])


def sh(*c):
    r = subprocess.run(c, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2500:])
    return r


if os.environ.get("PREVIEW_LOCAL_SRC"):
    src = os.environ["PREVIEW_LOCAL_SRC"]
else:
    from transcribe import fetch_source
    src = fetch_source(SP["vid"])

# --- the words, each on its own sound ---------------------------------------------------
import kt_words
words = kt_words.words_for(src, a, b, "EPISODE/" + slug)
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
words = [(float(x), float(y), str(w).strip()) for x, y, w in words if str(w).strip()]
json.dump(words, open(os.path.join(OUT, f"{slug}_words.json"), "w"))
if LIST:
    print(f"WORDS {slug}: {len(words)}")
    line = ""
    for i, (x, y, w) in enumerate(words):
        line += f"{i}:{x:.2f} {w}  "
        if len(line) > 150:
            print("W| " + line)
            line = ""
    if line:
        print("W| " + line)
    sys.exit(0)

# --- the cut: which pieces stay, and where every word lands on the new clock ------------------
keeps = SP.get("keeps") or [[0, len(words) - 1]]
_tight = float(SP.get("tighten") or 0)
if _tight:                                # split a piece wherever he pauses longer than this
    cut = []
    for i0_, i1_ in keeps:
        st = i0_
        for j in range(i0_, i1_):
            if words[j + 1][0] - words[j][1] > _tight:
                cut.append([st, j])
                st = j + 1
        cut.append([st, i1_])
    print(f"tightened: {len(keeps)} piece(s) -> {len(cut)}")
    keeps = cut
segs, off = [], 0.0                      # (source start, source end, offset on the new clock, a, b)
for (i0, i1) in keeps:
    s0 = words[i0][0] - (0.14 if _tight else 0.07)
    if i0 > 0:
        s0 = max(s0, words[i0 - 1][1] + 0.01)
    _last = (i0, i1) == tuple(keeps[-1])
    # THE LAST WORD GETS ITS BREATH (13 Nov 2026, Kamay: "the end just gets a little cut off
    # from kt voice, its not comfortable ending"). The timing pass ends a word early; the final
    # piece now runs 0.5 s past it (never into his next word) and fades over 0.25 s.
    e0 = words[i1][1] + (0.5 if _last else 0.18)
    if i1 + 1 < len(words):
        e0 = min(e0, words[i1 + 1][0] - 0.01)
        if _last:
            e0 = max(e0, min(words[i1][1] + 0.32, words[i1 + 1][0] + 0.12))
    s0, e0 = max(0.0, s0), max(s0 + 0.2, e0)
    segs.append((s0, e0, off, i0, i1))
    off += e0 - s0
DUR = off


def at(i):
    """(start, end) of word i on the new clock, or None when it was cut."""
    for s0, e0, o, i0, i1 in segs:
        if i0 <= i <= i1:
            return o + words[i][0] - s0, o + min(words[i][1], e0) - s0
    return None


def seg_end(i):
    for s0, e0, o, i0, i1 in segs:
        if i0 <= i <= i1:
            return o + e0 - s0
    return DUR


kept = [i for i in range(len(words)) if at(i)]
print(f"{len(words)} words timed, {len(kept)} kept in {len(segs)} piece(s), {DUR:.1f}s before the end card")

# --- captions ----------------------------------------------------------------------------------
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def F(name):
    for p in (os.path.join(FONTS, name), os.path.join(K, "bin", name), os.path.join(HERE, "assets", name)):
        if os.path.exists(p):
            return p
    raise SystemExit(f"font missing: {name}")


VOICE = {            # font file, size, look, capitals. Re-measured frame by frame, 12 Nov evening:
    # their big words are a Futura-style heavy face (Jost is its open twin), "of $dollars" a light
    # one, the small joining words a round bold sans, the flag words a chunky display face.
    "s": ("poppins700.ttf", 74, "plain", False),
    "S": ("poppins900.ttf", 84, "plain", True),
    "l": ("jost300.ttf", 92, "plain", False),
    "F": ("greatvibes400.ttf", 132, "glow", False),
    "B": ("yellowtail400.ttf", 112, "glow", False),
    "I": ("poppins800i.ttf", 100, "plain", False),
    "IC": ("poppins800i.ttf", 100, "plain", True),
    "IB": ("jost800i.ttf", 168, "plain", False),
    "X": ("jost900.ttf", 176, "plain", True),
    "XI": ("jost900i.ttf", 176, "plain", True),
    "T": ("poppins900.ttf", 96, "teal", False),
    "FL": ("titanone400.ttf", 150, "plain", False),
}
POS = {"C": (W // 2, 560), "L": (330, 560), "R": (1590, 560), "B": (W // 2, 870), "T": (W // 2, 250),
       "C-": (W // 2, 470), "C+": (W // 2, 640)}
_fonts = {}


def font(v):
    base = "FL" if v.startswith("flag") else v
    f, size, look, caps = VOICE[base]
    if (f, size) not in _fonts:
        _fonts[(f, size)] = ImageFont.truetype(F(f), size)
    return _fonts[(f, size)], look if not v.startswith("flag") else v, caps, size


def flag(code, w, h):
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    red, blue = (200, 16, 46), (1, 33, 105)
    if code == "US":
        for k in range(13):
            d.rectangle((0, k * h / 13, w, (k + 1) * h / 13), fill=(178, 34, 52) if k % 2 == 0 else (255, 255, 255))
        cw, ch = w * 0.42, h * 7 / 13
        d.rectangle((0, 0, cw, ch), fill=(60, 59, 110))
        for r in range(5):
            for c in range(7):
                d.ellipse((cw * (c + 0.5) / 7 - 3, ch * (r + 0.5) / 5 - 3, cw * (c + 0.5) / 7 + 3, ch * (r + 0.5) / 5 + 3), fill="white")
    elif code == "CA":
        d.rectangle((0, 0, w * 0.27, h), fill=(216, 6, 33))
        d.rectangle((w * 0.73, 0, w, h), fill=(216, 6, 33))
        cx, cy, r = w / 2, h / 2, h * 0.3
        d.polygon([(cx, cy - r), (cx + r * 0.35, cy - r * 0.2), (cx + r, cy - r * 0.1), (cx + r * 0.45, cy + r * 0.35),
                   (cx + r * 0.1, cy + r * 0.3), (cx, cy + r), (cx - r * 0.1, cy + r * 0.3), (cx - r * 0.45, cy + r * 0.35),
                   (cx - r, cy - r * 0.1), (cx - r * 0.35, cy - r * 0.2)], fill=(216, 6, 33))
    elif code in ("UK", "AU"):
        im.paste(blue if code == "UK" else (0, 0, 139), (0, 0, w, h))
        jw, jh = (w, h) if code == "UK" else (w // 2, h // 2)
        j = Image.new("RGB", (jw, jh), blue)
        jd = ImageDraw.Draw(j)
        t = max(4, jh // 5)
        jd.line((0, 0, jw, jh), fill="white", width=t); jd.line((0, jh, jw, 0), fill="white", width=t)
        jd.line((0, 0, jw, jh), fill=red, width=max(2, t // 3)); jd.line((0, jh, jw, 0), fill=red, width=max(2, t // 3))
        jd.rectangle((jw / 2 - t * 0.8, 0, jw / 2 + t * 0.8, jh), fill="white"); jd.rectangle((0, jh / 2 - t * 0.8, jw, jh / 2 + t * 0.8), fill="white")
        jd.rectangle((jw / 2 - t * 0.45, 0, jw / 2 + t * 0.45, jh), fill=red); jd.rectangle((0, jh / 2 - t * 0.45, jw, jh / 2 + t * 0.45), fill=red)
        im.paste(j, (0, 0))
        if code == "AU":
            for (fx, fy, r) in ((0.25, 0.76, 0.09), (0.74, 0.2, 0.05), (0.62, 0.48, 0.05), (0.86, 0.42, 0.05), (0.75, 0.8, 0.05), (0.8, 0.58, 0.03)):
                d.ellipse((w * fx - h * r, h * fy - h * r, w * fx + h * r, h * fy + h * r), fill="white")
    elif code == "ZA":
        d.rectangle((0, 0, w, h * 0.36), fill=(224, 60, 49))
        d.rectangle((0, h * 0.64, w, h), fill=(0, 20, 137))
        d.rectangle((0, h * 0.36, w, h * 0.64), fill="white")
        d.rectangle((0, h * 0.41, w, h * 0.59), fill=(0, 119, 73))
        d.polygon([(0, 0), (w * 0.34, h / 2), (0, h)], fill=(255, 184, 28))
        d.polygon([(0, h * 0.14), (w * 0.24, h / 2), (0, h * 0.86)], fill=(0, 0, 0))
    else:                                   # EU and anything else: solid blue
        im.paste((0, 51, 153), (0, 0, w, h))
    return im


def draw_state(els, path, fresh=None, k=1.0):
    """fresh = the elements that are new in this card; k = how far their fade-in has come."""
    if fresh is not None and k < 1.0:
        old = [e for e in els if json.dumps(e) not in fresh]
        new = [e for e in els if json.dumps(e) in fresh]
        a_p, b_p = path + ".a.png", path + ".b.png"
        draw_state(old, a_p)
        draw_state(new, b_p)
        A, B = Image.open(a_p), Image.open(b_p)
        B.putalpha(B.getchannel("A").point(lambda v: int(v * k)))
        Image.alpha_composite(A, B).save(path)
        os.remove(a_p); os.remove(b_p)
        return
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds, dg = ImageDraw.Draw(shadow), ImageDraw.Draw(glow)
    for pos, pieces in els:
        cx, cy = POS.get(pos, POS["C"])
        laid, total, tall = [], 0.0, 0
        for text, v in pieces:
            fo, look, caps, size = font(v)
            t = text.upper() if caps else text
            wd = fo.getlength(t)
            laid.append((t, fo, look, wd, size))
            total += wd
            tall = max(tall, size)
        gap = 26
        total += gap * (len(laid) - 1)
        if total > W - 120:                      # never off the picture: shrink the whole line
            k = (W - 120) / total
            laid = [(t, ImageFont.truetype(fo.path, max(20, int(sz * k))), look, 0, int(sz * k)) for t, fo, look, wd, sz in laid]
            laid = [(t, fo, look, fo.getlength(t), sz) for t, fo, look, _w, sz in laid]
            total = sum(x[3] for x in laid) + gap * (len(laid) - 1)
            tall = max(x[4] for x in laid)
        x, base = cx - total / 2, cy + tall * 0.34
        for t, fo, look, wd, size in laid:
            ds.text((x, base + 5), t, font=fo, fill=(0, 0, 0, 215), anchor="ls")
            if look == "glow":
                dg.text((x, base), t, font=fo, fill=(255, 255, 255, 150), anchor="ls")
            if look.startswith("flag") or look == "teal":
                mask = Image.new("L", (W, H), 0)
                ImageDraw.Draw(mask).text((x, base), t, font=fo, fill=255, anchor="ls")
                bb = mask.getbbox()
                if bb:
                    if look == "teal":
                        tex = Image.new("RGB", (bb[2] - bb[0], bb[3] - bb[1]))
                        for xx in range(tex.width):
                            kx = xx / max(1, tex.width - 1)
                            ImageDraw.Draw(tex).line((xx, 0, xx, tex.height), fill=(int(40 + 60 * kx), int(170 + 50 * kx), int(190 + 40 * kx)))
                    else:
                        tex = flag(look.split(":")[1], bb[2] - bb[0], bb[3] - bb[1])
                    ol = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(ol).text((x, base), t, font=fo, fill=(255, 255, 255, 255), anchor="ls",
                                            stroke_width=5, stroke_fill=(255, 255, 255, 255))
                    img.alpha_composite(ol)                       # a white edge, so a dark flag reads on a dark suit
                    full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    full.paste(tex.convert("RGBA"), (bb[0], bb[1]))
                    img.paste(full, (0, 0), mask)
            else:
                ImageDraw.Draw(img).text((x, base), t, font=fo, fill=(255, 255, 255, 255), anchor="ls")
            x += wd + gap
    out = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(9)), glow.filter(ImageFilter.GaussianBlur(14)))
    out = Image.alpha_composite(out, img)
    out.save(path)


voices = {int(k_): v for k_, v in (SP.get("voices") or {}).items()}
fix = {int(k_): v for k_, v in (SP.get("fix") or {}).items()}
drop = set(SP.get("drop") or [])
big_from = SP.get("big_from")
joins = {a_: b_ for a_, b_ in (SP.get("join") or [])}
states = SP.get("states") or []
in_state = set()
for st in states:
    in_state.update(range(st["from"], st["to"] + 1))


def voice(i):
    if i in voices:
        return voices[i]
    return "X" if big_from is not None and i >= big_from else "s"


def txt(i):
    t = fix.get(i, words[i][2])
    return t.strip().strip(",.;:\"").replace("’", "'") if voice(i) != "s" or True else t


events = []                               # (start, end or None, elements)
i, n = 0, len(words)
while i < n:
    if not at(i) or i in drop or i in in_state:
        i += 1
        continue
    if i in joins:
        grp = [j for j in range(i, joins[i] + 1) if at(j) and j not in drop]
    else:
        grp = [i]
        if voice(i) == "s":               # plain words ride together, two or three at a time
            while (len(grp) < 3 and grp[-1] + 1 < n and at(grp[-1] + 1) and grp[-1] + 1 not in drop
                   and grp[-1] + 1 not in in_state and grp[-1] + 1 not in joins and voice(grp[-1] + 1) == "s"
                   and words[grp[-1] + 1][0] - words[grp[-1]][1] < 0.3
                   and seg_end(grp[-1]) == seg_end(grp[-1] + 1)
                   and len(" ".join(txt(j) for j in grp + [grp[-1] + 1])) <= 16
                   and not words[grp[-1]][2].rstrip("\"'").endswith((".", "!", "?", ","))):
                grp.append(grp[-1] + 1)
    pieces = []
    for j in grp:
        if pieces and pieces[-1][1] == voice(j):
            pieces[-1][0] += " " + txt(j)
        else:
            pieces.append([txt(j), voice(j)])
    events.append((at(grp[0])[0], at(grp[-1])[1], [["C", pieces]]))
    i = grp[-1] + 1
for st in states:
    s0 = at(st["from"])[0]
    e0 = at(st["to"])[1]
    events.append((s0, e0, st["show"]))
events.sort(key=lambda e: e[0])
caps, t_prev = [], 0.0                   # (file, seconds) back to back from 0 to DUR
blank = os.path.join(TMP, "blank.png")
Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
for k_, (s0, e0, els) in enumerate(events):
    nxt = events[k_ + 1][0] if k_ + 1 < len(events) else DUR
    end = nxt if nxt - e0 <= 0.9 else e0 + 0.45
    end = max(end, s0 + 0.12)
    if s0 > t_prev + 0.02:
        caps.append((blank, s0 - t_prev))
    p = os.path.join(TMP, f"cap{k_:03d}.png")
    draw_state(els, p)
    span = end - max(s0, t_prev)
    prev_els = {json.dumps(e) for e in events[k_ - 1][2]} if k_ and abs(events[k_ - 1][0] - s0) < 6 and caps and caps[-1][0] != blank else set()
    fresh = {json.dumps(e) for e in els} - prev_els
    if fresh and span > 0.2:                 # two soft frames, then the full line
        for n_, kk in enumerate((0.38, 0.74)):
            pf = os.path.join(TMP, f"cap{k_:03d}_f{n_}.png")
            draw_state(els, pf, fresh, kk)
            caps.append((pf, 1 / 30))
        span -= 2 / 30
    caps.append((p, span))
    t_prev = max(end, t_prev)
    if nxt - t_prev > 0.02 and k_ + 1 < len(events) and end < nxt:
        caps.append((blank, nxt - end))
        t_prev = nxt
if DUR - t_prev > 0.02:
    caps.append((blank, DUR - t_prev))
cl = os.path.join(TMP, "caps.txt")
with open(cl, "w") as fh:
    for p, d_ in caps:
        fh.write(f"file '{p}'\nduration {max(0.034, d_):.3f}\n")
    fh.write(f"file '{caps[-1][0]}'\n")
print(f"{len(events)} caption cards")

# --- the scenes ----------------------------------------------------------------------------------
inputs, graph, last = [], "", "base"
_kc = SP.get("kevin_crop")               # [width share, height share, left share, top share] of Kevin's own picture
KCROP = f"crop=iw*{_kc[0]}:ih*{_kc[1]}:iw*{_kc[2]}:ih*{_kc[3]}," if _kc else ""
# the cut itself
parts = []
for k_, (s0, e0, o, i0, i1) in enumerate(segs):
    graph += (f"[0:v]trim=start={s0:.3f}:end={e0:.3f},setpts=PTS-STARTPTS,{KCROP}scale={W}:{H}:flags=lanczos,setsar=1,fps=30[v{k_}];"
              f"[0:a]atrim=start={s0:.3f}:end={e0:.3f},asetpts=PTS-STARTPTS,"
              f"afade=t=in:st=0:d=0.02,afade=t=out:st={max(0, e0 - s0 - (0.25 if k_ == len(segs) - 1 else 0.03)):.3f}"
              f":d={0.25 if k_ == len(segs) - 1 else 0.03}[a{k_}];")
    parts.append(f"[v{k_}][a{k_}]")
graph += "".join(parts) + f"concat=n={len(segs)}:v=1:a=1[base][abase];"
n_in = 1
CUTS = []                                # every picture change, for the sound (episode_sound.py)
for k_, sc in enumerate(SP.get("scenes") or []):
    f0 = at(sc["from"])
    f1 = at(sc["to"])
    if not f0 or not f1:
        print("scene skipped (its words were cut):", sc)
        continue
    t0 = 0.0 if sc["from"] == segs[0][3] else f0[0] - float(sc.get("lead", 0.05))
    nx = at(sc["to"] + 1)
    t1 = nx[0] - 0.02 if nx and seg_end(sc["to"]) == seg_end(sc["to"] + 1) else seg_end(sc["to"])
    t1 = min(DUR, t1 + float(sc.get("tail", 0.0)))
    d_ = t1 - t0
    if d_ < 0.4:
        print("scene skipped (too short):", sc)
        continue
    s_ = sc["src"]
    if isinstance(s_, dict) and s_.get("gen"):
        # A SCENE FROM A SENTENCE (13 Nov 2026, factory/scene_gen.py): {"gen": "what the picture
        # shows", "move": "what moves"}. Generated in the cloud, kept beside the spec as
        # g_<hash>.mp4 so it is made once. No scene = the clip simply shows Kevin there.
        import hashlib
        import scene_gen
        path = os.path.join(EDIR, "g_" + hashlib.md5((s_["gen"] + "|" + s_.get("move", "")).encode()).hexdigest()[:10] + ".mp4")
        if not scene_gen.make(s_["gen"], path, s_.get("move")):
            print("scene skipped (no generator answered):", s_["gen"][:60])
            continue
        inputs += ["-ss", f"{float(sc.get('start', 0.1)):.2f}", "-t", f"{d_ + 0.2:.2f}", "-i", path]
        chain = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},minterpolate=fps=30:mi_mode=blend,unsharp=5:5:0.6"
        s_ = os.path.basename(path)
    elif isinstance(s_, dict):
        try:
            import kt_opener as OP
            hit = next((h for h in OP.search(s_["q"], n=60) if h["id"] == s_["pixabay"]), None)
            if not hit:
                hit = next(iter(OP.search(s_["q"], n=10)), None)
                print(f"  pixabay {s_['pixabay']} not in the results for '{s_['q']}', took {hit and hit['id']}")
            path = OP.fetch(hit)
        except Exception as e:
            print("scene skipped (stock):", type(e).__name__, e)
            continue
        inputs += ["-ss", f"{float(sc.get('start', 1.0)):.2f}", "-t", f"{d_ + 0.2:.2f}", "-i", path]
        chain = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,"
                 f"eq=contrast=1.05:saturation=0.92")
    elif s_.lower().endswith(".mp4"):          # a stock clip kept beside the spec (its licence in stock_licences.json)
        path = os.path.join(EDIR, s_)
        inputs += ["-ss", f"{float(sc.get('start', 0.0)):.2f}", "-t", f"{d_ + 0.2:.2f}", "-i", path]
        chain = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30"
                 + ("" if sc.get("raw") else ",eq=contrast=1.05:saturation=0.92"))
    else:
        path = os.path.join(EDIR, s_)
        N = int(d_ * 30) + 8
        mv = sc.get("move", "in")
        z = {"in": f"1+0.10*on/{N}", "out": f"1.10-0.10*on/{N}", "left": "1.10", "right": "1.10"}[mv]
        x = {"in": "iw/2-(iw/zoom/2)", "out": "iw/2-(iw/zoom/2)",
             "left": f"(iw-iw/zoom)*(1-on/{N})", "right": f"(iw-iw/zoom)*on/{N}"}[mv]
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{d_ + 0.3:.2f}", "-i", path]
        chain = (f"scale=3840:2160:flags=lanczos,zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps=30,"
                 f"noise=alls=5:allf=t")
    graph += (f"[{n_in}:v]{chain},setsar=1,format=yuv420p,setpts=PTS-STARTPTS+{t0:.3f}/TB[s{k_}];"
              f"[{last}][s{k_}]overlay=0:0:eof_action=pass:enable='between(t,{t0:.3f},{t1:.3f})'[b{k_}];")
    last = f"b{k_}"
    n_in += 1
    CUTS += [t0, t1]
    print(f"  scene {s_ if not isinstance(s_, dict) else s_.get('pixabay')}: {t0:.2f}-{t1:.2f}s")
# captions on top
inputs += ["-f", "concat", "-safe", "0", "-i", cl]
graph += f"[{n_in}:v]fps=30,format=rgba[cap];[{last}][cap]overlay=0:0:eof_action=pass,format=yuv420p[vmain];"
n_in += 1
# the end card
end_secs = float(SP.get("end_secs", 0))
if SP.get("end_card") and end_secs > 0:
    inputs += ["-loop", "1", "-framerate", "30", "-t", f"{end_secs:.2f}", "-i", os.path.join(EDIR, SP["end_card"]),
               "-f", "lavfi", "-t", f"{end_secs:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
    graph += (f"[{n_in}:v]scale={W}:{H},setsar=1,fps=30,format=yuv420p[ev];"
              f"[abase]aresample=48000,aformat=channel_layouts=stereo[am];"
              f"[vmain][am][ev][{n_in + 1}:a]concat=n=2:v=1:a=1[v][avoice];")
    n_in += 2
else:
    end_secs = 0.0
    graph += "[vmain]null[v];[abase]aresample=48000,aformat=channel_layouts=stereo[avoice];"
# THE SOUND (13 Nov 2026): real music under his voice (spec "music": a file in factory/music/),
# a whoosh on each picture change, a low hit on the loud words, a rise into the payoff. It runs
# THROUGH the end card, so the film never drops into silence. "sound": false switches it off;
# "music_db" / "fx_db" / "voice_db" set the levels (defaults match the reference reels).
AOUT = "avoice"
if SP.get("sound", True):
    try:
        import episode_sound
        _hits = [at(int(k))[0] for k, v in (SP.get("voices") or {}).items() if v in ("X", "XI") and at(int(k))]
        _rise = at(int(SP["big_from"]))[0] if SP.get("big_from") is not None and at(int(SP["big_from"])) else None
        _mus = os.path.join(HERE, "music", SP["music"]) if SP.get("music") else None
        if _mus and not os.path.exists(_mus):
            print("music file missing:", _mus); _mus = None
        _wav = episode_sound.make(DUR + end_secs, CUTS + ([DUR] if end_secs else []), _hits, os.path.join(TMP, "sound.wav"),
                                  rise_at=_rise, bed_db=float(SP.get("music_db", -21)), fx_db=float(SP.get("fx_db", -16)),
                                  music=_mus, ffmpeg=FF)
        inputs += ["-i", _wav]
        graph += (f"[avoice]volume={float(SP.get('voice_db', 7))}dB[avo];[{n_in}:a]aresample=48000[asn];"
                  f"[avo][asn]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.6:attack=4:release=60:level=disabled[aout]")
        n_in += 1
        AOUT = "aout"
        print(f"sound: music {os.path.basename(_mus) if _mus else 'none'}, {len(CUTS)} picture changes, {len(_hits)} hits, rise at {_rise}")
    except Exception as _e:
        print("sound skipped:", type(_e).__name__, _e)
if AOUT == "avoice":
    graph += "[avoice]anull[aout]"
gp = os.path.join(TMP, "graph.txt")
open(gp, "w").write(graph)
dst = os.path.join(OUT, f"{slug}.mp4")
r = sh(FF, "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", src, *inputs,
       "-filter_complex_script", gp, "-map", "[v]", "-map", "[aout]",
       "-r", "30", "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-maxrate", "24000k", "-bufsize", "48000k",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", dst)
ok = r.returncode == 0 and os.path.exists(dst)
print("EPISODE", slug, "OK" if ok else "FAILED", f"{DUR + end_secs:.1f}s")
if not ok:
    sys.exit(1)
# the cover = the first frame, as theirs; and the same film upright for TikTok and Shorts
sh(FF, "-y", "-loglevel", "error", "-ss", "0.10", "-i", dst, "-frames:v", "1", "-q:v", "2", os.path.join(OUT, f"{slug}_cover.jpg"))
sh(FF, "-y", "-loglevel", "error", "-i", dst, "-vf", "scale=1080:-2:flags=lanczos,pad=1080:1920:0:(oh-ih)/2:black",
   "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
   os.path.join(OUT, f"{slug}_9x16.mp4"))
json.dump({"slug": slug, "seconds": round(DUR + end_secs, 2), "pieces": [[round(s0, 2), round(e0, 2)] for s0, e0, *_ in segs],
           "cards": len(events)}, open(os.path.join(OUT, f"{slug}_info.json"), "w"))
import shutil
shutil.rmtree(TMP, ignore_errors=True)
