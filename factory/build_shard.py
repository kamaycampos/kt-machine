"""Render and check ONE shard of a clip plan (a couple of clips) on this server.

Every gate runs exactly as on the Mac (kt_batch_build in no-queue mode): hook
lint, ending verdict, render, caption sync against the waveform, first/last
seconds - plus the 1080p source gate and word-level edge snapping (run_plans).
Clips that pass are handed to factory/queue.py as an artifact; nothing is
queued from here, so parallel shards never fight over the manifest.

    python factory/build_shard.py <plan> <shard>
"""
import glob, json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/Kamay"))
import run_plans as R  # noqa: E402
from shard import SIZE  # noqa: E402

plan, shard = sys.argv[1], int(sys.argv[2])
p = json.load(open(os.path.join(R.PLANS, f"{plan}.json")))
key = f"{plan}__s{shard}"
sub = dict(p, clips=p["clips"][shard * SIZE:(shard + 1) * SIZE])
json.dump(sub, open(os.path.join(R.PLANS, f"{key}.json"), "w"), indent=1, ensure_ascii=False)

vid = p["source"][:-4]
mp4 = R.fetch_source(vid)
# The renderer reads the episode's transcript from disk, and the lock has to be
# up to date or it refuses to render at all (19 Sept: both stopped every clip).
srt = os.path.join(R.K, "transcripts", f"{vid}.srt")
if not os.path.exists(srt):
    R.sh("gh", "release", "download", "sources", "-R", os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine"),
         "-p", f"{vid}.srt.enc", "-D", "/tmp", "--clobber")
    for kname in ("TRANSCRIPT_KEY", "FACTORY_KEY"):          # new key first, old transcripts fall back
        if R.sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", f"env:{kname}",
                "-in", f"/tmp/{vid}.srt.enc", "-out", srt).returncode == 0:
            break
    print("transcript:", os.path.exists(srt), srt)
import kt_lock
print("locked now published:", kt_lock.sync())
h = R.height(mp4)
out = "/tmp/shard_out"
os.makedirs(out, exist_ok=True)
result = {"plan": plan, "shard": shard, "brand": p["brand"], "source": p["source"],
          "test": bool(p.get("test")), "height": h, "clips": [], "files": []}
if p.get("test"):
    os.environ["OPENER_PREVIEW"] = "1"          # a preview build shows the opener before it goes live
if h < 1080:
    print(f"REFUSED: source is {h}p, the gate is 1080p")
else:
    # A CLIP DROPPED HERE MUST SAY WHY (20 Oct 2026). fix_edges drops a clip that runs
    # into the next topic, has no clean ending near, or opens on B-roll with no face -
    # but only printed it to this job's log. queue.py reads reasons from report.md, so
    # 12 of Yaren's clips were filed as "no clip came out of the render", and her
    # planner refused to re-cut them ("names nothing to fix"). Keep the words.
    import contextlib, io
    buf = io.StringIO()

    class _Tee(io.TextIOBase):
        def write(self, t):
            buf.write(t); sys.__stdout__.write(t); return len(t)
    with contextlib.redirect_stdout(_Tee()):
        R.fix_edges(key)
    edge_drops = [l.strip() for l in buf.getvalue().splitlines() if "dropped" in l]
    fixed = json.load(open(os.path.join(R.PLANS, f"{key}.json")))["clips"]
    R.batch([key], test=True)                       # render + check, never queue here
    bdir = os.path.join(R.K, "POST_TODAY", p["brand"])
    for c in fixed:
        hits = [f for f in glob.glob(os.path.join(bdir, f"*_{c['slug']}_*s.mp4")) if "__" not in os.path.basename(f)]
        if not hits:
            continue                                # failed a gate (moved to _failed) or dropped
        result["clips"].append(c)
        for f in glob.glob(os.path.join(bdir, os.path.basename(hits[0])[:-4] + "*")):
            shutil.copy(f, out)
            result["files"].append(os.path.basename(f))
# TRIAL REELS (1 Nov 2026, Kamay: "the test of posting 7 clips a day in IG never got delivered").
# Daniel's method: the same clip, ONLY the hook changes, all posted the same day as Instagram
# Trial Reels (non-followers only). The planner gives ONE strong clip a day "trial_hooks"; each is
# rendered here with HOOK_OVERRIDE into its own folder, no story or YouTube cut, and queue.py
# uploads them; run_once.py posts them once the clip itself has posted, then scores them.
if h >= 1080 and not p.get("test"):
    import subprocess as _sp
    for c in result["clips"]:
        for i, hk in enumerate((c.get("trial_hooks") or [])[:7], 1):
            hk = hk if isinstance(hk, list) else [hk]
            vdir = f"/tmp/variants/{c['slug']}/V{i}"
            os.makedirs(vdir, exist_ok=True)
            _sp.run([sys.executable, os.path.join(R.K, "kt_render.py"), key, "--apply", "--only", c["slug"]],
                    cwd=R.K, env=dict(os.environ, HOOK_OVERRIDE="|".join(hk), KT_OUT=vdir, NO_SIDE_CUTS="1"))
            got = [f for f in glob.glob(os.path.join(vdir, "*.mp4")) if "__" not in os.path.basename(f)]
            if got:
                name = f"VAR__{p['brand']}__{c['slug']}__V{i}.mp4"
                shutil.copy(got[0], os.path.join(out, name))
                result.setdefault("variants", {}).setdefault(c["slug"], []).append({"file": name, "hook": hk})
        if c.get("trial_hooks"):
            print(f"trial variants for {c['slug']}: {len(result.get('variants', {}).get(c['slug'], []))}")
rep = os.path.join(R.K, "work", "proposals", "BATCH_REPORT.md")
if os.path.exists(rep):
    shutil.copy(rep, os.path.join(out, "report.md"))
if h >= 1080 and edge_drops:                      # last, so queue.py's tail always holds them
    with open(os.path.join(out, "report.md"), "a") as fh:
        fh.write("\n" + "\n".join(f"  drop {p['brand']}/{l}" for l in edge_drops) + "\n")
json.dump(result, open(os.path.join(out, "result.json"), "w"), indent=1, ensure_ascii=False)
print(f"shard {key}: {len(result['clips'])} of {len(sub['clips'])} clip(s) passed every gate")
