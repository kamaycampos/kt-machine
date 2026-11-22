#!/usr/bin/env python3
"""Which music is under the reels that broke out? (22 Nov 2026)

Kamay: "the tracks Kevin's apprentice uses ... he does not show what song it is ... he brought it
from outside the platform. We need a way to find our 20 best tracks."

A reel's music is either an Instagram library sound (its name shows on the reel, and anyone can
attach it - but only on a post made by hand in the app) or music mixed into the video before
upload (no name shown anywhere). This reads BOTH: it downloads the public reel, cuts windows of
its sound and asks a song recogniser what is playing.

    python music_scout.py reels.json            # [{"id": "DbxZBEUNhTQ", "views": 234000, "by": "kevins_apprentice"}, ..]
    -> factory/reports/music_scout.md   (one line per track, ranked by the views of the reels it sits under)

Needs:  pip install shazamio   (and ffmpeg + yt-dlp on PATH, or ~/Kamay/bin).  By hand, on the Mac.
A track found here is NOT cleared for our uploads: music we mix in ourselves must come from
factory/music (no Content ID). An Instagram library sound may be attached by hand in the app.
"""
import sys
# NEVER RUN A TOOL FROM INSIDE factory/ (22 Nov 2026): Python puts the script's folder first on its
# path, factory/queue.py then answers "import queue" (the standard module asyncio needs), and the
# factory's queue step ran by accident. This file lives at the top of the machine, and its own
# folder is taken off the path before anything else is imported.
sys.path[:] = [p for p in sys.path if p not in ("", __import__("os").path.dirname(__import__("os").path.abspath(__file__)))]
import asyncio
import collections
import json
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.expanduser("~/Kamay/bin")
FF = shutil.which("ffmpeg") or os.path.join(BIN, "ffmpeg")
YT = shutil.which("yt-dlp") or os.path.join(BIN, "yt-dlp_macos")
WINDOWS = (0, 8, 16, 26, 38, 52)        # seconds into the reel; 12 s each


def fetch(rid, work):
    out = os.path.join(work, rid + ".mp4")
    if not os.path.exists(out):
        subprocess.run([YT, "--no-warnings", "-q", "-f", "best", "-o", out,
                        f"https://www.instagram.com/reel/{rid}/"], timeout=180)
    return out if os.path.exists(out) else None


async def tracks_of(path, work, sh):
    found = collections.Counter()
    for t in WINDOWS:
        seg = os.path.join(work, f"seg_{os.path.basename(path)[:-4]}_{t}.mp3")
        subprocess.run([FF, "-v", "error", "-y", "-ss", str(t), "-t", "12", "-i", path,
                        "-vn", "-ac", "1", "-ar", "44100", seg])
        if not os.path.exists(seg) or os.path.getsize(seg) < 20000:
            continue
        try:
            tr = (await sh.recognize(seg)).get("track")
        except Exception as x:
            print(f"   recogniser error on {os.path.basename(seg)}: {type(x).__name__}: {str(x)[:80]}")
            tr = None
        if tr:
            found[f"{tr['title']} - {tr['subtitle']}"] += 1
    return found


async def main(listing):
    from shazamio import Shazam
    reels = json.load(open(listing))
    work = os.environ.get("SCOUT_WORK") or os.path.join(os.path.dirname(os.path.abspath(listing)), "scout_work")
    os.makedirs(work, exist_ok=True)
    sh = Shazam()
    by_track, rows = collections.defaultdict(list), []
    for r in reels:
        p = fetch(r["id"], work)
        if not p:
            rows.append((r, None))
            print(f"{r['id']}: could not download")
            continue
        found = await tracks_of(p, work, sh)
        rows.append((r, found))
        print(f"{r['by']:<20} {r['views']:>8,}  {r['id']}: " + ("; ".join(f"{k} (x{v})" for k, v in found.most_common()) or "no music recognised"))
        for k in found:
            by_track[k].append(r)
    lines = ["# Music under the reels that broke out (music_scout.py)", "",
             f"{len(reels)} reels read. A track counts once per reel. 'No music recognised' = voice only, or music the",
             "recogniser does not know (custom or generated).", "",
             "| track | reels | views of those reels | where |", "|---|---|---|---|"]
    for k, rs in sorted(by_track.items(), key=lambda kv: -sum(r["views"] for r in kv[1])):
        lines.append(f"| {k} | {len(rs)} | {sum(r['views'] for r in rs):,} | "
                     + ", ".join(f"{r['by']} {r['views']:,}" for r in sorted(rs, key=lambda r: -r['views'])) + " |")
    none = [r for r, f in rows if f is not None and not f]
    lines += ["", f"No music recognised in {len(none)} reel(s): " + ", ".join(f"{r['by']} {r['views']:,}" for r in none)]
    rep = os.path.join(HERE, "factory", "reports", "music_scout.md")
    open(rep, "w").write("\n".join(lines) + "\n")
    print("wrote", rep)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    asyncio.run(main(sys.argv[1]))
