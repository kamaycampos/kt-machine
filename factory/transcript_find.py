#!/usr/bin/env python3
"""Where does Kevin say this? Scores every stocked transcript for a set of phrases and prints the
best windows (episode, title, time, the words). By hand, from the transcript-find workflow.

    python factory/transcript_find.py "secret society|royal families|south africa|parts of europe"
"""
import json, os, re, subprocess, sys, urllib.request
BASE = "https://github.com/" + os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine") + "/releases/download/sources/"
keys = [k.strip().lower() for k in sys.argv[1].split("|") if k.strip()]
need = int(sys.argv[2]) if len(sys.argv) > 2 else max(2, len(keys) // 2)
span = int(sys.argv[3]) if len(sys.argv) > 3 else 10


def get(name):
    return urllib.request.urlopen(BASE + name, timeout=120).read()


idx = json.loads(get("sources_index.json"))
hits = []
for v, e in idx.items():
    if not e.get("transcript"):
        continue
    try:
        open(f"/tmp/{v}.srt.enc", "wb").write(get(f"{v}.srt.enc"))
        txt = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:TRANSCRIPT_KEY",
                              "-in", f"/tmp/{v}.srt.enc"], capture_output=True).stdout.decode("utf-8", "ignore")
    except Exception as x:
        print("skip", v, type(x).__name__)
        continue
    cues = [(a, x.replace("\n", " ").strip()) for a, x in
            re.findall(r"(\d+:\d+:\d+)[,.]\d+ --> [^\n]+\n(.+?)(?:\n\n|\Z)", txt, re.S)]
    best = None
    for i in range(len(cues)):
        w = " ".join(y for _, y in cues[i:i + span]).lower()
        sc = sum(k in w for k in keys)
        if sc >= need and (best is None or sc > best[0]):
            best = (sc, cues[i][0], " ".join(y for _, y in cues[max(0, i - 1):i + span + 2]))
    if best:
        hits.append((best[0], v, e.get("title", ""), e.get("height"), e.get("duration"), best[1], best[2]))
print(f"{len(idx)} episodes searched for {keys}")
for sc, v, title, hgt, dur, at, words in sorted(hits, reverse=True)[:8]:
    print(f"\n== {sc}/{len(keys)}  {v}  {hgt}p  {(dur or 0) / 60:.0f} min  at {at}  '{title}'\n   {words[:1400]}")
if not hits:
    print("no episode has that many of the phrases close together")
