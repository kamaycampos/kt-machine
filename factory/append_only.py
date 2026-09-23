"""A month list may only be ADDED to, never rewritten. Exit 0 if that holds.

    python factory/append_only.py <current file> <proposed file>

The planners may extend their own list when it runs low; they may not reorder it,
drop an episode, or hand the list to the other account.
"""
import json
import sys

ids = lambda p: [e["id"] for e in json.load(open(p))["episodes"]]
old, new = ids(sys.argv[1]), ids(sys.argv[2])
ok = new[:len(old)] == old and len(new) > len(old)
print(f"{sys.argv[1]}: {len(old)} -> {len(new)} episodes, {'append-only' if ok else 'NOT append-only'}")
sys.exit(0 if ok else 1)
