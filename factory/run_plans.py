"""Turn committed clip plans into verified, queued clips - in the cloud.

A plan is factory/plans/<key>.json, the same shape kt_batch_build.py reads on the
Mac: {"source": "<youtube id>.mp4", "brand": "KT_...", "clips": [...]}. Plans are
written by a Claude session from the episode's transcript; everything after that
is mechanical and runs here with the Mac shut.

Every clip passes every gate the Mac uses (hook lint, ending verdict, render,
caption sync against the waveform, first/last seconds) plus one more: the source
must really be 1080p (18 Sept 2026 - 18 clips went out blurry from 360p copies).

A plan with "test": true is rendered and checked but NEVER uploaded or queued;
the clips come back as a workflow artifact for inspection.
"""
import json, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transcribe import fetch_source, sh  # noqa: E402

K = os.path.expanduser("~/Kamay")
HERE = os.path.dirname(os.path.abspath(__file__))
PLANS = os.path.join(HERE, "plans")
DONE = os.path.join(PLANS, "_done.json")
PROP = os.path.join(K, "work", "proposals")
OUT = "/tmp/factory_out"


def height(path):
    m = re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", sh("ffmpeg", "-i", path).stderr)
    return int(m[2]) if m else 0


def batch(keys, test):
    for f in os.listdir(PROP):
        if f.endswith(".json") and not f.startswith("_"):
            os.remove(os.path.join(PROP, f))
    for k in keys:
        shutil.copy(os.path.join(PLANS, f"{k}.json"), os.path.join(PROP, f"{k}.json"))
    env = dict(os.environ, **({"KT_FACTORY_NOQUEUE": "1"} if test else {}))
    r = subprocess.run([sys.executable, "-u", os.path.join(K, "kt_batch_build.py")],
                       cwd=K, env=env, text=True, capture_output=True)
    print(r.stdout[-6000:], r.stderr[-2000:])
    merged = json.load(open(os.path.join(PROP, "_merged.json"))) if os.path.exists(
        os.path.join(PROP, "_merged.json")) else []
    return [k for k in keys if k in merged]


def main():
    done = json.load(open(DONE)) if os.path.exists(DONE) else []
    plans = sorted(f[:-5] for f in os.listdir(PLANS) if f.endswith(".json") and not f.startswith("_"))
    todo = [k for k in plans if k not in done]
    print(f"{len(todo)} plan(s) to build: {todo}")
    ready = {True: [], False: []}
    for k in todo:
        p = json.load(open(os.path.join(PLANS, f"{k}.json")))
        vid = p["source"][:-4]
        mp4 = fetch_source(vid)
        h = height(mp4)
        if h < 1080:
            print(f"  {k}: REFUSED - source is {h}p, the gate is 1080p")
            continue
        ready[bool(p.get("test"))].append(k)
    built = []
    if ready[True]:
        built += batch(ready[True], test=True)
        os.makedirs(OUT, exist_ok=True)
        for root, _d, files in os.walk(os.path.join(K, "POST_TODAY")):
            for f in files:
                if f.endswith(".mp4") or f.endswith("__caps.json"):
                    shutil.copy(os.path.join(root, f), OUT)
    if ready[False]:
        built += batch(ready[False], test=False)
    json.dump(sorted(set(done + built)), open(DONE, "w"), indent=1)
    shutil.copy(os.path.join(K, "kt_series.json"), os.path.join(HERE, "kt_series.json"))
    rep = os.path.join(K, "work", "proposals", "BATCH_REPORT.md")
    if os.path.exists(rep):
        os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
        shutil.copy(rep, os.path.join(HERE, "reports", "latest.md"))
    print(f"built: {built}")


if __name__ == "__main__":
    main()
