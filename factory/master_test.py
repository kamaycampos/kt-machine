#!/usr/bin/env python3
"""The master transcript (shared/kt_master.py), end to end on one KT plan shard.

    python factory/master_test.py <plan> <shard> <engine> [<second engine>]

Builds the episode's master (whole-episode transcription + one Claude correction call
when ANTHROPIC_API_KEY is set), then prints, clip by clip, the caption bursts today's
path burns (per-window small.en, the clip's `fix` map) against the ones cut from the
master. The workflow then renders the shard with MASTER_TRANSCRIPT=1 through every
gate. Manual test only: nothing is queued, committed or posted.
"""
import difflib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/Kamay"))
import run_plans as R            # noqa: E402
from shard import SIZE           # noqa: E402
import kt_master, kt_render, kt_words  # noqa: E402

ENGINES = {"small": "whisper:" + os.path.expanduser("~/wcache/ggml-small.en.bin"),
           "turbo": "whisper:" + os.path.expanduser("~/wturbo/ggml-large-v3-turbo.bin"),
           "turbo-names": "whisper+names:" + os.path.expanduser("~/wturbo/ggml-large-v3-turbo.bin")}


def bursts(src, c, key):
    w = kt_words.words_for(src, c["in"], c["out"], key)
    if c.get("fix"):
        low = {k.lower(): v for k, v in c["fix"].items()}
        w = [(a, b, low.get(x.lower().strip(), x)) for a, b, x in w]
    return [p[2] if isinstance(p, (list, tuple)) else str(p) for p in kt_render.phrases_from_words(w)]


plan, shard, engine = sys.argv[1], int(sys.argv[2]), sys.argv[3]
second = ENGINES.get(sys.argv[4]) if len(sys.argv) > 4 else None    # hints for Claude
p = json.load(open(os.path.join(R.PLANS, f"{plan}.json")))
src = R.fetch_source(p["source"][:-4])
m = kt_master.build(src, ENGINES[engine], True, p.get("note", ""), second=second)
for e in m["edits"]:
    print(f"    EDIT {e['at']:7.1f}s  {e['wrong']!r} -> {e['right']!r}  ({e['why']})")
for e in m["rejected"]:
    print(f"    REFUSED  {e['wrong']!r} -> {e['right']!r}: {e['rejected']}")
print(f"master: {m['engine']}, {m['seconds']}s, Claude {m['usage']}")
for c in p["clips"][shard * SIZE:(shard + 1) * SIZE]:
    os.environ.pop("MASTER_TRANSCRIPT", None)
    before = bursts(src, c, f"MASTERTEST/{c['slug']}")
    os.environ["MASTER_TRANSCRIPT"] = "1"
    after = bursts(src, c, f"MASTERTEST/{c['slug']}")
    print(f"\n### {c['slug']}  ({c['in']}-{c['out']}s): {len(before)} -> {len(after)} bursts")
    print("```")
    for line in difflib.unified_diff(before, after, "before", "after", n=0, lineterm=""):
        print(line)
    print("```")
