"""Split pending clip plans into shards so clips render on several servers at once.

19 Sept 2026, Kamay: "make sure its running fast". One server rendered clips one
after another (~25 min for a plan). Each shard takes SIZE clips on its own server;
factory/queue.py collects what passed and queues it once.

    python factory/shard.py            # writes matrix=<json> and count=<n> to $GITHUB_OUTPUT
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PLANS = os.path.join(HERE, "plans")
SIZE = 2
VSIZE = 2              # trial hook variants per server

done = json.load(open(os.path.join(PLANS, "_done.json"))) if os.path.exists(os.path.join(PLANS, "_done.json")) else []
shards = []
for f in sorted(os.listdir(PLANS)):
    if not f.endswith(".json") or f.startswith("_") or f[:-5] in done:
        continue
    clips = json.load(open(os.path.join(PLANS, f)))["clips"]
    n = len(clips)
    shards += [{"plan": f[:-5], "shard": i} for i in range((n + SIZE - 1) // SIZE)]
    # TRIAL VARIANTS ON THEIR OWN SERVERS (2 Nov 2026). Rendered after the clips in the same
    # job, 2 clips + 7 variants (~15 min each) hit the 2-hour limit twice and lost the shard,
    # real clips included. Shard "v<clip>_<first>" renders VSIZE variants of one clip.
    for ci, c in enumerate(clips):
        k = min(len(c.get("trial_hooks") or []), 7)
        shards += [{"plan": f[:-5], "shard": f"v{ci}_{j}"} for j in range(0, k, VSIZE)]
print(f"{len(shards)} shard(s): {shards}")
with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as fh:
    fh.write(f"matrix={json.dumps(shards)}\ncount={len(shards)}\n")
