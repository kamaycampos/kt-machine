"""A month list may only be ADDED to, never rewritten. Exit 0 if that holds.

    python factory/append_only.py <current file> <proposed file>

The planners may extend their own list when it runs low; they may not reorder it,
drop an episode, or hand the list to the other account.

AND EVERY ADDED EPISODE MUST BE NEW (10 Nov 2026). The 7-9 Nov refill runs appended five
episodes KT had already cut in Sept-Oct under their title filenames ("luck", "kroc",
"positive_broke"...). The stocker rightly skipped them as used, so the list looked full,
nothing new was downloaded, and KT's queue fell to one clip. An appended episode that is
already planned (by id) or already cut (same title as a kt_series source) is refused,
and only those entries are dropped - the rest of the append still goes through.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())[:40]

cur, prop = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
old, new = [e["id"] for e in cur["episodes"]], [e["id"] for e in prop["episodes"]]
ok = new[:len(old)] == old and len(new) > len(old)
print(f"{sys.argv[1]}: {len(old)} -> {len(new)} episodes, {'append-only' if ok else 'NOT append-only'}")
if not ok:
    sys.exit(1)

plans = os.path.join(HERE, "plans")
planned = " ".join(open(os.path.join(plans, f)).read() for f in os.listdir(plans) if f.endswith(".json"))
used = set()
try:
    for s in json.load(open(os.path.join(HERE, "kt_series.json"))).values():
        used.add(norm(os.path.splitext(s.get("source", ""))[0]))
except (OSError, ValueError):
    pass
keep = prop["episodes"][:len(old)]
for e in prop["episodes"][len(old):]:
    if f'"{e["id"]}.mp4"' in planned or norm(e.get("title")) in used:
        print(f"  REFUSED {e['id']} '{e.get('title', '')[:60]}' - already planned or already cut")
    else:
        keep.append(e)
if len(keep) == len(old):
    print("  nothing new in the append")
    sys.exit(1)
if len(keep) < len(prop["episodes"]):
    prop["episodes"] = keep
    json.dump(prop, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
sys.exit(0)
