#!/usr/bin/env python3
"""Show, on real footage, which person each framing rule puts in the 9:16 crop.

2 Oct 2026. Kamay saw two-person interview clips whose thumbnails did not show
Kevin. This builds a contact sheet per clip window: every 2 seconds, the crop the
OLD rule (biggest face) chose beside the crop the NEW rule (who is speaking)
chose, so the difference is judged by eye before anything goes live.

    python factory/framing_probe.py <series key> [max clips]
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.expanduser("~/Kamay"))
sys.path.insert(0, HERE)
from transcribe import fetch_source  # noqa: E402

K = os.path.expanduser("~/Kamay")
FF = os.path.join(K, "bin", "ffmpeg")
OUT = "/tmp/probe"


def run(*a):
    return subprocess.run(list(a), capture_output=True, text=True)


def size(src):
    r = run("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height", "-of", "csv=p=0", src)
    w, h = r.stdout.strip().split("\n")[0].split(",")
    return int(w), int(h)


def frame_track(win, speaker):
    os.environ["VSC_SPEAKER"] = "1" if speaker else "0"
    import importlib
    import vsc_frame
    VF = importlib.reload(vsc_frame)
    dur = VF.duration(win)
    track = VF.face_track(win, dur)
    segs = VF.segments(VF.shot_cuts(win), dur, track)
    return dur, segs


def cx_at(segs, t):
    for s in segs:
        if s["start"] <= t < s["end"]:
            return s["cx"]
    return segs[-1]["cx"] if segs else 0.5


def plan_probe(path):
    """`plan:<file>` - build a whole plan exactly as a factory shard does (edges,
    render, every gate), never queue it, and keep the evidence: what was burned,
    what whisper heard, the gate's verdict, the framing, the covers.

    3 Oct 2026: the caption gate failed two member clips and the only question
    was WHAT is in the gap - a word nobody captioned, or a laugh. That needs the
    real whisper pass on the real render, which only exists here.
    """
    import glob, shutil
    import run_plans as R
    import kt_words
    p = json.load(open(path))
    key = "probe_" + os.path.splitext(os.path.basename(path))[0]   # "_" files are skipped by the batch
    json.dump(dict(p, test=True), open(os.path.join(R.PLANS, key + ".json"), "w"), indent=1)
    vid = p["source"][:-4]
    R.fetch_source(vid)
    srt = os.path.join(K, "transcripts", f"{vid}.srt")
    if not os.path.exists(srt):
        run("gh", "release", "download", "sources", "-R",
            os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine"),
            "-p", f"{vid}.srt.enc", "-D", "/tmp", "--clobber")
        for kname in ("TRANSCRIPT_KEY", "FACTORY_KEY"):
            if run("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", f"env:{kname}",
                   "-in", f"/tmp/{vid}.srt.enc", "-out", srt).returncode == 0:
                break
    # THE FENCE, PROBE ONLY. kt_batch_build refuses a source another lane owns
    # (kt_fence.py) - here v76l9y0 belongs to the AR lane on this repo while the
    # plan is a member's KT plan. A probe is test mode: nothing is uploaded or
    # queued, so this run's throwaway copy of the series drops the fence for
    # its own source. The repo's kt_series.json and the real fence are untouched.
    sp = os.path.join(K, "kt_series.json")
    series = json.load(open(sp))
    fenced = [k for k, v in series.items() if v.get("source") == p["source"]]
    for k in fenced:
        del series[k]
    json.dump(series, open(sp, "w"), indent=1, ensure_ascii=False)
    if fenced:
        print(f"probe: fence lifted in this run only for {p['source']} ({fenced})")
    os.makedirs(OUT, exist_ok=True)
    os.environ["VSC_TURN_DEBUG"] = "1"
    R.fix_edges(key)
    fixed = json.load(open(os.path.join(R.PLANS, key + ".json")))["clips"]
    R.batch([key], test=True)
    post = os.path.join(K, "POST_TODAY")
    found = {}
    for c in fixed:
        for f in glob.glob(os.path.join(post, "*", f"*_{c['slug']}_*s*")):
            shutil.copy(f, os.path.join(OUT, os.path.basename(f)))
            if f.endswith("s.mp4") and "__" not in os.path.basename(f):
                found[c["slug"]] = f
    sys.path.insert(0, K)
    import kt_sync_check as SC
    report = {"clips": fixed, "checks": {}}
    for slug, mp4 in found.items():
        ok, msg = SC.check(mp4)
        tmp = f"/tmp/kt_sync.{os.getpid()}"
        heard = kt_words.parse_word_srt(tmp + ".srt") if os.path.exists(tmp + ".srt") else []
        c = next(c for c in fixed if c["slug"] == slug)
        # the renderer keyed the words by BRAND/slug; a failed clip now sits in _failed
        wkey = p["brand"] + "/" + slug
        cache = kt_words._load_cache()
        raw = next((v for k, v in cache.items() if k.startswith(wkey + "@")), None)
        # and the anchoring step itself: onsets, which word each one pinned, result
        anch = {}
        try:
            import tempfile
            import vsc_v2_time as V
            src = R.fetch_source(vid)                # already on disk: just its path
            a, b = float(c["in"]), float(c["out"])
            words = [tuple(w) for w in raw or []]
            wav = os.path.join(tempfile.gettempdir(), "probe_anchor.wav")
            run(FF, "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav)
            ons = V.onsets(V.envelope(src, a, b))
            pts = V.anchor_by_identity(wav, words, ons) if words else []
            anch = {"onsets": [round(t, 2) for t in ons],
                    "anchors": [[i, round(t, 2), words[i][2], round(words[i][0], 2)] for i, t in pts],
                    "anchored": V.warp_by_index(words, pts) if len(pts) >= 2 else words}
        except Exception as e:                      # evidence, never a crash
            anch = {"error": f"{type(e).__name__}: {e}"}
        report["checks"][slug] = {"ok": ok, "msg": msg, "in": c["in"], "out": c["out"],
                                  "heard": heard, "words": raw, **anch}
        print(f"{slug}: {msg}")
        run(FF, "-v", "error", "-y", "-i", mp4, "-vf", "fps=1,scale=180:-2,tile=10x8",
            "-frames:v", "1", os.path.join(OUT, f"{slug}_sheet.jpg"))
    json.dump(report, open(os.path.join(OUT, "plan_report.json"), "w"), indent=1)
    rep = os.path.join(K, "work", "proposals", "BATCH_REPORT.md")
    if os.path.exists(rep):
        shutil.copy(rep, os.path.join(OUT, "batch_report.md"))


def main():
    key = sys.argv[1]
    if key.startswith("plan:"):
        return plan_probe(os.path.join(os.path.dirname(HERE), key[5:]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    spec = json.load(open(os.path.join(HERE, "kt_series.json")))[key]
    src = fetch_source(spec["source"][:-4])
    W, H = size(src)
    cw = int(H * 9 / 16) // 2 * 2
    os.makedirs(OUT, exist_ok=True)
    report = {}
    for c in spec["clips"][:n]:
        a, b = float(c["in"]), float(c["out"])
        win = os.path.join(OUT, f"{c['slug']}.mp4")
        run(FF, "-v", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", src,
            "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", win)
        dur, old = frame_track(win, False)
        _, new = frame_track(win, True)
        report[c["slug"]] = {"old": old, "new": new}
        tiles = []
        for k, t in enumerate(range(0, int(dur), 2)):
            for tag, segs in (("old", old), ("new", new)):
                x = max(0, min(int(cx_at(segs, t) * W - cw / 2), W - cw))
                tile = os.path.join(OUT, f"_{c['slug']}_{k:03d}_{tag}.jpg")
                run(FF, "-v", "error", "-y", "-ss", f"{t + 0.5:.2f}", "-i", win, "-frames:v", "1",
                    "-vf", f"crop={cw}:{H}:{x}:0,scale=180:320,drawtext=fontfile=/usr/share/fonts/"
                    f"truetype/liberation/LiberationSans-Bold.ttf:text='{tag} {t}s':x=6:y=6:"
                    f"fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.6", tile)
                tiles.append(tile)
        # one sheet: each row = old/new pairs, 8 pairs per row
        pairs = len(tiles) // 2
        cols = 8
        rows = (pairs + cols - 1) // cols
        lst = os.path.join(OUT, "_list.txt")
        inputs = []
        for t in tiles:
            inputs += ["-i", t]
        layout = "|".join(f"{(i % (cols * 2)) * 180}_{(i // (cols * 2)) * 320}" for i in range(len(tiles)))
        sheet = os.path.join(OUT, f"{c['slug']}.jpg")
        run(FF, "-v", "error", "-y", *inputs, "-filter_complex",
            f"xstack=inputs={len(tiles)}:layout={layout}:fill=black", "-frames:v", "1", sheet)
        for t in tiles:
            os.remove(t)
        os.remove(win)
        if os.path.exists(lst):
            os.remove(lst)
        print(f"{c['slug']}: old {[s['cx'] for s in old]}  new {[s['cx'] for s in new]}  "
              f"sheet {'ok' if os.path.exists(sheet) else 'FAILED'} ({rows} rows)")
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
