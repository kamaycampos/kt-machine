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


def main():
    key = sys.argv[1]
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
