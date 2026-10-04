#!/usr/bin/env python3
"""Where is Kevin, second by second, and what crop keeps him in a 9:16 frame.

Project 15 / VSC. The brief is explicit that framing must be checked across the
WHOLE clip, not just the opening frame - and this source proves why: Kevin sits
right of centre, and the interview cuts between 2-4 camera angles that are
framed differently. One fixed crop cannot serve all of them.

Deliberately NOT a continuous tracker. The camera is locked off inside a shot,
so a crop that follows the face frame-by-frame would wobble on a still picture,
which reads as amateur. One crop per SHOT is invisible and correct.

Writes <video>.frame.json: [{"start","end","cx","fw"}], cx/fw as fractions.
"""
import cv2, glob, json, os, subprocess, sys, numpy as np

FFMPEG = os.path.expanduser("~/Kamay/bin/ffmpeg")
MODEL  = os.path.expanduser("~/Kamay/bin/yunet.onnx")
SAMPLE_W = 640          # YuNet is happy well below this; 4K decode is the cost
FPS      = 1.0          # one probe per second


def duration(src):
    out = subprocess.run([FFMPEG, "-i", src], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise SystemExit("cannot read duration")


def shot_cuts(src, threshold=6):
    """Times where the picture changes enough to be a different camera."""
    p = subprocess.run([FFMPEG, "-i", src, "-vf", f"scale=320:-2,scdet=threshold={threshold}",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    cuts = []
    for line in p.splitlines():
        if "lavfi.scd.time:" in line:
            try: cuts.append(float(line.split("lavfi.scd.time:")[1].strip().split()[0]))
            except (IndexError, ValueError): pass
    return sorted(set(cuts))


# FRAME THE MAN WHO IS TALKING, NOT THE BIGGEST HEAD. 2 Oct 2026, Kamay, looking
# at the control room: in the two-person interviews the clip's thumbnail did not
# show Kevin. Every crop here was chosen by "biggest face = Kevin" - true in his
# close-ups, false the moment the camera favours the interviewer, who sits nearer
# the lens in a two-shot. So each second is sampled SUB times and every face's
# MOUTH is compared frame to frame; the face whose mouth moves is the speaker.
# Clips are cut on Kevin's speech, so the speaker is Kevin almost always - and when
# the other person really is talking, framing them is right too.
# VSC_SPEAKER=1 turns it on; off, the old biggest-face choice is exactly preserved.
# 3 Oct 2026: ON by default. Proven on the ep_v6vm6pp probe sheets (2 Oct): the old
# choice flipped between people up to 14 times a clip; this follows the speaker.
# Known follow-up: a listener drinking from a cup can read as talking.
# VSC_SPEAKER=0 restores the old biggest-face choice exactly.
SPEAKER = os.environ.get("VSC_SPEAKER", "1") == "1"
SUB = 5                 # frames per second when choosing who is speaking
SAME = 0.08             # two boxes within this fraction of width are one person


def _mouth(gray, f):
    """A brightness-normalised patch of the mouth, from YuNet's mouth corners."""
    x1, y1, x2, y2 = float(f[10]), float(f[11]), float(f[12]), float(f[13])
    mw = max(abs(x2 - x1), float(f[2]) * 0.3)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    h, w = gray.shape[:2]
    t, b = int(max(0, cy - 0.35 * mw)), int(min(h, cy + 0.65 * mw))
    l, r = int(max(0, cx - 0.75 * mw)), int(min(w, cx + 0.75 * mw))
    if b - t < 4 or r - l < 4:
        return None
    patch = cv2.resize(gray[t:b, l:r], (32, 20)).astype(np.float32)
    return patch / (patch.mean() + 1.0)


def _speaker(frames, w, h, prev_cx):
    """frames: [[face rows] per sub-frame] plus their gray images. Returns the
    chosen face as (cx, fw, cy) or None."""
    people = []                               # [{cx, boxes:[(j, row)]}]
    for j, (faces, gray) in enumerate(frames):
        for f in faces:
            cx = float((f[0] + f[2] / 2) / w)
            hit = next((p for p in people if abs(p["cx"] - cx) <= SAME), None)
            if hit is None:
                hit = {"cx": cx, "boxes": []}
                people.append(hit)
            hit["boxes"].append((j, f, gray))
    if not people:
        return None
    for p in people:
        pats = {j: _mouth(g, f) for j, f, g in p["boxes"]}
        js = sorted(k for k, v in pats.items() if v is not None)
        diffs = [float(np.mean(np.abs(pats[a] - pats[b])))
                 for a, b in zip(js, js[1:]) if b - a == 1]
        p["motion"] = float(np.mean(diffs)) if diffs else 0.0
        p["area"] = float(np.median([f[2] * f[3] for _, f, _ in p["boxes"]]))
    biggest = max(people, key=lambda p: p["area"])
    pick = biggest
    if SPEAKER and len(people) > 1:
        ranked = sorted(people, key=lambda p: -p["motion"])
        top, second = ranked[0], ranked[1]
        if top["motion"] > 0.02 and top["motion"] >= 1.35 * second["motion"]:
            pick = top                         # one mouth is clearly moving
        elif prev_cx is not None:              # undecided: stay on who we had
            pick = min(people, key=lambda p: abs(p["cx"] - prev_cx))
    fs = [f for _, f, _ in pick["boxes"]]
    return (float(np.median([(f[0] + f[2] / 2) / w for f in fs])),
            float(np.median([f[2] / w for f in fs])),
            float(np.median([(f[1] + f[3] / 2) / h for f in fs])))


def face_track(src, dur):
    """cx/fw/cy per sampled second, of the person SPEAKING. None where no face."""
    tmp = "/tmp/vsc_probe_%05d.jpg"
    rate = SUB if SPEAKER else FPS
    subprocess.run([FFMPEG, "-i", src, "-vf", f"fps={rate},scale={SAMPLE_W}:-2",
                    "-q:v", "4", "-y", tmp, "-loglevel", "error"], check=True)
    det = cv2.FaceDetectorYN_create(MODEL, "", (320, 320), 0.6, 0.3, 5000)
    files, i = [], 1
    while os.path.exists(tmp % i):
        files.append(tmp % i); i += 1
    per = int(rate) if SPEAKER else 1
    track, prev = [], None
    for s in range(0, len(files), per):
        frames, w, h = [], 0, 0
        for f in files[s:s + per]:
            img = cv2.imread(f); h, w = img.shape[:2]
            det.setInputSize((w, h))
            ok, faces = det.detect(img)
            frames.append(([] if faces is None else list(faces),
                           cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)))
            os.remove(f)
        if not SPEAKER:                          # the old rule, byte for byte
            faces = frames[0][0] if frames else []
            if not faces:
                got = None
            else:
                b = max(faces, key=lambda r: r[2] * r[3])       # biggest face
                got = (float((b[0] + b[2] / 2) / w), float(b[2] / w),
                       float((b[1] + b[3] / 2) / h))
        else:
            got = _speaker(frames, w, h, prev) if w else None
        track.append(got)
        if got:
            prev = got[0]
    return track


def smooth(track, k=3):
    """Median-filter the per-second track so one bad detection cannot split a shot."""
    out = []
    for i in range(len(track)):
        win = [t for t in track[max(0, i-k//2):i+k//2+1] if t is not None]
        out.append(None if not win or track[i] is None else
                   tuple(float(np.median([w[j] for w in win])) for j in range(3)))
    return out


def face_breaks(track, dcx=0.10, dfw=0.11):
    """Seconds where the framing jumps - a cut scdet did not score.

    6 Sept: scdet at threshold 6 reported ONE shot from 13.5s to 26.3s, and the
    source actually holds three setups in there - black-and-white close-ups, near
    black cave footage, then colour wides. The transitions are dissolves, which
    frame-difference scoring reads as gradual. But the FACE jumps, and the face
    is the only thing the crop cares about, so segment on that instead.
    """
    t = smooth(track)
    b = []
    for i in range(1, len(t)):
        if (t[i-1] is None) != (t[i] is None):
            b.append(float(i)); continue
        pre  = [x for x in t[max(0,i-3):i]   if x]
        post = [x for x in t[i:i+3]          if x]
        if not pre or not post:
            continue
        # a real cut changes the framing and STAYS changed; a blip does not
        if (abs(np.median([x[0] for x in pre]) - np.median([x[0] for x in post])) > dcx or
            abs(np.median([x[1] for x in pre]) - np.median([x[1] for x in post])) > dfw):
            b.append(float(i))
    return b


def segments(cuts, dur, track):
    # A REAL CAMERA CUT BEATS A ROUNDED ONE. 16 Sept 2026, measured on the YWIYC
    # story: the scene detector put the camera change at 28.03s; the face
    # tracker, which samples once a second, put a break at 27.0; the merge below
    # keeps whichever comes FIRST, so 27.0 won and 28.03 was thrown away. For a
    # full second the crop was aimed for the new camera while the old one was
    # still on screen - Kevin half out of frame. The next change was off by
    # 1.25s the same way, with a phantom one-second "shot" in between.
    #
    # This is Kamay's recurring complaint about interview clips not following
    # their camera. Per-shot framing existed; its boundaries were a second late.
    #
    # A face-tracker break now only stands on its own when there is NO scene cut
    # near it - a slow pan or a lean, where the face moves without a hard cut.
    hard = [c for c in cuts if 0 < c < dur]
    soft = [t for t in face_breaks(track) if 0 < t < dur
            and not any(abs(t - c) <= 1.5 for c in hard)]
    bounds = sorted(set([0.0] + hard + soft + [dur]))
    merged = [bounds[0]]
    for t in bounds[1:]:
        if t - merged[-1] >= 1.2: merged.append(t)
    if merged[-1] < dur: merged[-1] = dur
    bounds = merged
    segs = []
    last_cx, last_fw, last_cy = 0.5, 0.25, 0.40
    for a, b in zip(bounds, bounds[1:]):
        if b - a < 0.4: continue
        vals = [track[i] for i in range(int(a), min(int(b) + 1, len(track)))
                if i < len(track) and track[i] is not None]
        if vals and SPEAKER:
            # ONE PERSON PER SHOT. A median across two people lands on the empty
            # space between them; keep the person framed for the most seconds.
            groups = []
            for v in vals:
                g = next((g for g in groups if abs(g[0][0] - v[0]) <= SAME), None)
                (g.append(v) if g is not None else groups.append([v]))
            vals = max(groups, key=len)
        if vals:
            cx = float(np.median([v[0] for v in vals]))
            fw = float(np.median([v[1] for v in vals]))
            cy = float(np.median([v[2] for v in vals]))
            last_cx, last_fw, last_cy = cx, fw, cy
        else:                                   # no face in this shot - hold the last known
            cx, fw, cy = last_cx, last_fw, last_cy
        segs.append({"start": round(a, 3), "end": round(b, 3),
                     "cx": round(cx, 4), "cy": round(cy, 4),
                     "fw": round(fw, 4), "faces": len(vals)})
    out = [segs[0]]
    for s2 in segs[1:]:
        p = out[-1]
        same = (abs(p["cx"]-s2["cx"]) < 0.06 and abs(p["fw"]-s2["fw"]) < 0.08)
        if same:                      # one real shot that detection split - put it back
            n1, n2 = p["end"]-p["start"], s2["end"]-s2["start"]
            for k in ("cx", "cy", "fw"):
                p[k] = round((p[k]*n1 + s2[k]*n2)/(n1+n2), 4)
            p["end"] = s2["end"]; p["faces"] += s2["faces"]
        else:
            out.append(s2)
    return out


# ------------------------------------------------------------ who is talking
# A numpy port of Resemblyzer's VoiceEncoder (Apache-2.0, github.com/resemble-ai/
# Resemblyzer): 40 mel bands -> 3-layer LSTM(256) -> a 256-d voiceprint. Its
# published weights are factory/assets/voice_encoder.npz, copied to ~/Kamay/bin
# by setup.sh. No torch: the whole forward pass is below and runs a 75-second
# clip in about a second. Without the file, speaker_turns() changes nothing.
VOICE = os.path.expanduser("~/Kamay/bin/voice_encoder.npz")
_SR, _NFFT, _HOP, _PART = 16000, 400, 160, 160


def _mel_basis(n_mels=40):
    """librosa.filters.mel(sr=16000, n_fft=400, n_mels=40): Slaney scale and norm."""
    lin, logstep = 1000.0 / (200.0 / 3), np.log(6.4) / 27.0
    def hz2mel(f):
        return np.where(f >= 1000.0, lin + np.log(np.maximum(f, 1e-10) / 1000.0) / logstep,
                        f / (200.0 / 3))
    def mel2hz(m):
        return np.where(m >= lin, 1000.0 * np.exp(logstep * (m - lin)), m * (200.0 / 3))
    fft = np.linspace(0, _SR / 2, _NFFT // 2 + 1)
    mf = mel2hz(np.linspace(hz2mel(np.array(0.0)), hz2mel(np.array(_SR / 2.0)), n_mels + 2))
    fd, ramps = np.diff(mf), mf[:, None] - fft[None, :]
    w = np.stack([np.maximum(0, np.minimum(-ramps[i] / fd[i], ramps[i + 2] / fd[i + 1]))
                  for i in range(n_mels)])
    return (w * (2.0 / (mf[2:] - mf[:-2]))[:, None]).astype(np.float32)


class _Voices:
    def __init__(self, path):
        z = np.load(path)
        f = lambda k: z[k].astype(np.float32)
        self.lstm = [(f(f"lstm.weight_ih_l{k}"), f(f"lstm.weight_hh_l{k}"),
                      f(f"lstm.bias_ih_l{k}") + f(f"lstm.bias_hh_l{k}")) for k in range(3)]
        self.W, self.b, self.mel = f("linear.weight"), f("linear.bias"), _mel_basis()

    def _forward(self, X):                          # batch x 160 frames x 40
        h = X
        for Wi, Wh, bias in self.lstm:
            pre = h @ Wi.T + bias
            hs = np.zeros((len(X), 256), np.float32)
            cs = np.zeros_like(hs)
            out = np.empty(pre.shape[:2] + (256,), np.float32)
            for t in range(pre.shape[1]):           # PyTorch gate order: i, f, g, o
                g = np.clip(pre[:, t] + hs @ Wh.T, -30, 30)
                i, fg, o = (1 / (1 + np.exp(-g[:, k:k + 256])) for k in (0, 256, 768))
                cs = fg * cs + i * np.tanh(g[:, 512:768])
                hs = o * np.tanh(cs)
                out[:, t] = hs
            h = out
        e = np.maximum(0, hs @ self.W.T + self.b)
        return e / (np.linalg.norm(e, axis=1, keepdims=True) + 1e-9)

    def embed(self, wav):
        """One L2-normed voiceprint for a stretch of 16 kHz mono audio."""
        x = np.pad(wav.astype(np.float32), _NFFT // 2)
        fr = np.lib.stride_tricks.sliding_window_view(x, _NFFT)[::_HOP]
        win = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(_NFFT) / _NFFT)).astype(np.float32)
        M = (np.abs(np.fft.rfft(fr * win, axis=1)) ** 2) @ self.mel.T
        if len(M) < _PART:
            M = np.pad(M, ((0, _PART - len(M)), (0, 0)))
        step = int(round(_SR / 1.3 / _HOP))         # Resemblyzer's partials, rate 1.3/s
        e = self._forward(np.stack([M[k:k + _PART] for k in
                                    range(0, len(M) - _PART + 1, step)])).mean(0)
        return e / (np.linalg.norm(e) + 1e-9)


TURN_MIN = 1.5          # no speaker segment shorter than this
TURN_BOTH = 0.8         # both faces on screen in this share of a block's frames
TURN_MARGIN = 0.04      # a span changes hands only when one voice is clearly nearer
TURN_SHORT = 0.8        # spans shorter than this are too little sound to judge
TURN_ISLAND = 2.5       # a run this short between two of the other person is a reaction


def sentence_starts(words, gap=0.7):
    """Clip-relative times a new sentence begins: after . ? ! or a long pause."""
    out, prev = [], None
    for a, b, w in words:
        end = prev and prev[2].strip().strip("\"'\u201d\u2019)").endswith((".", "?", "!"))
        if prev is None or end or a - prev[1] >= gap:
            out.append(float(a))
        prev = (a, b, w)
    return out


def speaker_turns(src, t_in, t_out, segs, cuts, starts):
    """Two people in one shot: frame whoever is TALKING, switching on sentences.

    3 Oct 2026, member clip 1 (a remote interview: interviewer left, Kevin
    right, one shot, no cuts). The tracker switched to Kevin at 23.0s; he
    starts answering at 19.4s ("Yeah."). For three and a half seconds the crop
    held the silent interviewer while Kevin talked - Kamay saw it as lag.

    The tracker reads MOUTHS, once a second, and holds its choice until one
    clearly out-moves the other. On this clip that is the wrong signal:
    measured, the listener nodding under a noisy webcam moved his mouth patch
    more than Kevin talking (0.117 vs 0.107 over 19.4-26.8s). Lip/sound sync
    and hand-made voice features were tried and each named the wrong man
    somewhere on the two test clips.

    A VOICEPRINT does not. Seeded with the tracker's own framing, refined
    twice, each sentence goes to the nearer voice: on clip 1 the interviewer
    scores 0.72-0.80 against his own voice to 18.5s and Kevin wins every second
    from 19.0s; on clip 2 it recovers the confirmed 0-2 / 2-4 / 4-8 turns and
    keeps 72-84s on Kevin, where sync had put the interviewer.

    Only inside a stretch between camera cuts where both faces are on screen
    (TURN_BOTH) and the tracker already framed both people. A switch lands on
    a sentence start, so the reframe meets the new speaker's first word, and
    no segment is shorter than TURN_MIN. Anything else is returned unchanged.
    """
    if not SPEAKER or len(segs) < 2 or len(starts) < 2 or not os.path.exists(VOICE):
        return segs
    dur = t_out - t_in
    hard = sorted(c for c in cuts if 0 < c < dur)
    blocks = [(a, b) for a, b in zip([0.0] + hard, hard + [dur]) if b - a >= 2 * TURN_MIN]
    todo = []
    for a, b in blocks:
        inner = [sg for sg in segs if sg["end"] > a + 0.01 and sg["start"] < b - 0.01]
        people = []                                  # [[cx, fw, cy, seconds]]
        for sg in inner:
            n = min(sg["end"], b) - max(sg["start"], a)
            p = next((p for p in people if abs(p[0] - sg["cx"]) <= 2 * SAME), None)
            if p is None:
                people.append([sg["cx"], sg["fw"], sg["cy"], n])
            else:
                p[3] += n
        if len(people) == 2:
            todo.append((a, b, inner, people))
    if not todo:
        return segs
    raw = subprocess.run([FFMPEG, "-ss", f"{t_in:.2f}", "-t", f"{dur:.2f}", "-i", src,
                          "-vn", "-ac", "1", "-ar", str(_SR), "-f", "s16le", "-",
                          "-loglevel", "error"], capture_output=True).stdout
    pcm = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    if len(pcm) < _SR * 2:
        return segs
    enc = _Voices(VOICE)
    det = cv2.FaceDetectorYN_create(MODEL, "", (320, 320), 0.6, 0.3, 5000)
    out = []
    for a, b, inner, people in todo:
        # both faces really on screen? one probe a second
        tmp = "/tmp/vsc_turn_%04d.jpg"
        for f in glob.glob("/tmp/vsc_turn_*.jpg"):
            os.remove(f)
        subprocess.run([FFMPEG, "-ss", f"{t_in + a:.2f}", "-t", f"{b - a:.2f}", "-i", src,
                        "-vf", f"fps=1,scale={SAMPLE_W}:-2", "-q:v", "5", "-y", tmp,
                        "-loglevel", "error"], check=True)
        hits = []
        for f in sorted(glob.glob("/tmp/vsc_turn_*.jpg")):
            img = cv2.imread(f)
            os.remove(f)
            if img is None:
                continue
            h, w = img.shape[:2]
            det.setInputSize((w, h))
            _, faces = det.detect(img)
            xs = [float((r[0] + r[2] / 2) / w) for r in (faces if faces is not None else [])]
            hits.append(all(any(abs(x - p[0]) <= 2 * SAME for x in xs) for p in people))
        if not hits or sum(hits) < TURN_BOTH * len(hits):
            continue
        # sentence spans, each first labelled with whom the tracker framed
        # A sentence too short to judge ("Yeah.") opens the turn after it more
        # often than it closes the one before, so it joins the NEXT sentence.
        cut = [a] + [s for s in starts if a + 0.3 < s < b - 0.3] + [b]
        spans = []
        for s, e in zip(cut, cut[1:]):
            if spans and spans[-1][1] - spans[-1][0] < TURN_SHORT:
                spans[-1] = (spans[-1][0], e)
            elif e - s > 0.05:
                spans.append((s, e))

        def tracked(t):
            sg = next((sg for sg in inner if sg["start"] <= t < sg["end"]), inner[-1])
            return min((0, 1), key=lambda k: abs(people[k][0] - sg["cx"]))
        lab = [tracked((s + e) / 2) for s, e in spans]
        vec = [enc.embed(pcm[int(s * _SR):int(e * _SR)]) if e - s >= TURN_SHORT else None
               for s, e in spans]
        for _ in range(2):                           # refine the two voiceprints
            refs = []
            for k in (0, 1):
                v = [vec[i] * (spans[i][1] - spans[i][0]) for i in range(len(spans))
                     if lab[i] == k and vec[i] is not None]
                refs.append(np.sum(v, 0) / (np.linalg.norm(np.sum(v, 0)) + 1e-9) if v else None)
            if refs[0] is None or refs[1] is None:
                break
            lab = [(int(v @ refs[1] > v @ refs[0])
                    if v is not None and abs(v @ refs[1] - v @ refs[0]) >= TURN_MARGIN
                    else tracked((s + e) / 2))
                   for (s, e), v in zip(spans, vec)]
        if refs[0] is None or refs[1] is None:
            continue
        if os.environ.get("VSC_TURN_DEBUG"):
            print("    spans: " + " ".join(
                f"{s:.1f}:{'AB'[k]}{'' if v is None else f'({v @ refs[1] - v @ refs[0]:+.2f})'}"
                for (s, e), k, v in zip(spans, lab, vec)))
        runs = []
        for (s, e), k in zip(spans, lab):
            if runs and runs[-1][2] == k:
                runs[-1][1] = e
            else:
                runs.append([s, e, k])
        while len(runs) > 1:                         # nothing shorter than TURN_MIN
            i = min(range(len(runs)), key=lambda i: runs[i][1] - runs[i][0])
            if runs[i][1] - runs[i][0] >= TURN_MIN:
                break
            j = i - 1 if i == len(runs) - 1 or (i > 0 and runs[i - 1][1] - runs[i - 1][0]
                                                  >= runs[i + 1][1] - runs[i + 1][0]) else i + 1
            runs[j] = [min(runs[i][0], runs[j][0]), max(runs[i][1], runs[j][1]), runs[j][2]]
            del runs[i]
            k = 1
            while k < len(runs):
                if runs[k][2] == runs[k - 1][2]:
                    runs[k - 1][1] = runs.pop(k)[1]
                else:
                    k += 1
        # A REACTION IS NOT A TURN. Both men laugh at 37.8-40.0s on clip 1 and
        # the interviewer is the louder voice, so his face would come in for two
        # seconds and leave again. A short run with the same person on both
        # sides is a laugh or an "mm-hm"; clip 2's real 2.7s interjection stays.
        i = 1
        while i < len(runs) - 1:
            if (runs[i - 1][2] == runs[i + 1][2] != runs[i][2]
                    and runs[i][1] - runs[i][0] < TURN_ISLAND):
                runs[i - 1][1] = runs[i + 1][1]
                del runs[i:i + 2]
                i = max(1, i - 1)
            else:
                i += 1
        merged = runs
        if os.environ.get("VSC_TURN_DEBUG"):
            print("    voices: " + " ".join(f"{s:.1f}-{e:.1f}:{'AB'[k]}" for s, e, k in merged))
        out.append((a, b, [{"start": round(s, 3), "end": round(e, 3),
                            "cx": round(people[k][0], 4), "cy": round(people[k][2], 4),
                            "fw": round(people[k][1], 4), "faces": 0, "turn": True}
                           for s, e, k in merged]))
    if not out:
        return segs
    new = []                                         # segments() everywhere else
    for sg in segs:
        pieces = [(sg["start"], sg["end"])]
        for a, b, _ in out:
            pieces = [q for s, e in pieces for q in ((s, min(e, a)), (max(s, b), e))
                      if q[1] - q[0] > 0.01]
        new += [dict(sg, start=round(s, 3), end=round(e, 3)) for s, e in pieces]
    for _, _, rs in out:
        new += rs
    return sorted(new, key=lambda sg: sg["start"])


if __name__ == "__main__":
    src = sys.argv[1]
    dur = duration(src)
    print(f"duration {dur:.1f}s"); sys.stdout.flush()
    cuts = shot_cuts(src); print(f"{len(cuts)} shot cuts"); sys.stdout.flush()
    track = face_track(src, dur)
    found = sum(1 for t in track if t)
    print(f"probed {len(track)}s, face found in {found} ({100*found//max(len(track),1)}%)")
    segs = segments(cuts, dur, track)
    out = os.path.splitext(src)[0] + ".frame.json"
    json.dump({"src": os.path.basename(src), "duration": dur, "segments": segs,
               "track": [list(t) if t else None for t in track]},
              open(out, "w"), indent=1)
    print(f"{len(segs)} shots -> {out}")
